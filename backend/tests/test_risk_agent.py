"""Offline checks for captured web evidence and the grounded risk-review agent."""
import json
import httpx
import pytest
from app.runtime import browser_search as browser, service, shopping_tools, cart, risk_agent
from app.runtime.gateway import LLMError
from app.runtime.schemas import Session, Fact, CartSelection, CartCheckout

RUN = "12345678-1234-1234-1234-123456789abc"


def listing(evidence=None, **changes):
    row = {"name": "Desk light", "url": "https://shop.example/products/light", "brand": "Example",
           "price": 25, "currency": "SGD", "attributes": ["adjustable"], "sizes": [],
           "description": "Adjustable desk lamp", "in_stock": True, **changes}
    if evidence is not None:
        row["evidence"] = evidence
    return row


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("BROWSER_USE_API_KEY", "test-secret")
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS", "shop.example")
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")


def live(monkeypatch, *rows):
    output = browser.SearchOutput.model_validate({"products": list(rows)})
    monkeypatch.setattr(browser, "run_task", lambda *_: (RUN, output))
    s = Session(search_provider="browser_use", brief={"category": Fact(value="Lighting")})
    return s, shopping_tools.search_products(s)


def finding(rule, quote, reason="Observed signal."):
    return risk_agent.Finding(rule_id=rule, quote=quote, reason=reason)


def test_evidence_is_optional_and_requested(config):
    calls = []
    def handler(req):
        calls.append(req)
        if req.method == "POST":
            return httpx.Response(200, json={"id": RUN})
        return httpx.Response(200, json={"status": "completed", "output": {"products": [listing()]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _, result = browser.run_task({"category": "Lighting"}, "", client=client)
    assert result.products[0].evidence.seller.name == "" and result.products[0].evidence.urgency_claims == []
    body = json.loads(calls[0].content)
    assert "return_policy" in json.dumps(body["outputSchema"]) and "never guess" in body["task"]


def test_nulls_and_overlong_values_do_not_fail_run(config):
    row = browser.Listing.model_validate(listing({
        "seller": None, "return_policy": "x" * 5000, "urgency_claims": ["y" * 900, None] + ["z"] * 30,
    }))
    assert row.evidence.seller.name == "" and len(row.evidence.return_policy) == 1000
    assert len(row.evidence.urgency_claims) == 10 and len(row.evidence.urgency_claims[0]) == 300


def test_evidence_links_outside_retailers_are_dropped(config, monkeypatch):
    s, found = live(monkeypatch, listing({
        "seller": {"name": "Bright Co", "page_url": "https://evil.example/seller"},
        "return_policy_url": "https://shop.example/returns",
    }))
    e = found[0].web_evidence
    assert e.seller.page_url == "" and e.return_policy_url == "https://shop.example/returns"


def test_named_sellers_on_one_host_are_distinct_merchants(config, monkeypatch):
    s, found = live(monkeypatch,
                    listing({"seller": {"name": "Bright Co"}}),
                    listing({"seller": {"name": "Lamp Hub"}}, url="https://shop.example/products/other"))
    assert len({p.merchant_id for p in found}) == 2
    assert {s.live_merchants[p.merchant_id].name for p in found} == {"Bright Co (shop.example)", "Lamp Hub (shop.example)"}
    service.propose(s, found[0])
    s.rejected_merchants.append(found[0].merchant_id)
    assert [p.id for p in shopping_tools.search_products(s)] == [found[1].id]


def test_blank_evidence_is_low_risk_but_still_reviewed(config, monkeypatch):
    s, found = live(monkeypatch, listing())
    service.propose(s, found[0])
    a = s.proposals[-1]
    assert a.risk.level == "LOW" and not a.risk.evidence and a.decision == "REVIEW"


def test_external_payment_blocks(config, monkeypatch):
    s, found = live(monkeypatch, listing({"off_platform_payment": ["Pay by bank transfer to 123-456 for a discount"]}))
    service.propose(s, found[0])
    a = s.proposals[-1]
    assert a.decision == "BLOCK" and a.risk.evidence[0].rule_id == "external_payment"
    assert "bank transfer" in a.risk.explanation


def test_signals_are_scored_with_existing_weights(config, monkeypatch):
    s, found = live(monkeypatch, listing({
        "urgency_claims": ["Only 2 left! Offer ends in 10 minutes"],
        "personal_data_requests": ["Upload your NRIC to complete the order"],
    }))
    service.propose(s, found[0])
    a = s.proposals[-1]
    assert {e.rule_id for e in a.risk.evidence} == {"pressure", "excessive_data"}
    assert a.risk.score == 4 and a.risk.level == "MEDIUM" and a.decision == "REVIEW"
    assert any(r.rule_id == "merchant_risk" for r in a.rules)


def test_ungrounded_and_duplicate_findings_are_discarded(config, monkeypatch):
    s, found = live(monkeypatch, listing({"urgency_claims": ["Sale ends tonight"]}))
    review = risk_agent.review(s, found[0], s.live_merchants[found[0].merchant_id],
                               chooser=lambda *_: risk_agent.Review(findings=[
                                   finding("external_payment", "Pay via WhatsApp only"),
                                   finding("pressure", "sale   ENDS tonight"),
                                   finding("pressure", "Sale ends tonight"),
                               ]))
    assert [f.rule_id for f in review.findings] == ["pressure"] and review.discarded == 2


def test_review_runs_once_per_snapshot(config, monkeypatch):
    s, found = live(monkeypatch, listing())
    calls = []
    def chooser(*_):
        calls.append(1)
        return risk_agent.Review(findings=[])
    merchant = s.live_merchants[found[0].merchant_id]
    risk_agent.review(s, found[0], merchant, chooser=chooser)
    risk_agent.review(s, found[0], merchant, chooser=chooser)
    assert len(calls) == 1
    changed = found[0].model_copy(update={"price": 20})
    risk_agent.review(s, changed, merchant, chooser=chooser)
    assert len(calls) == 2


def test_agent_failure_falls_back_to_review(config, monkeypatch):
    s, found = live(monkeypatch, listing())
    def broken(*_):
        raise LLMError("down")
    monkeypatch.setattr(risk_agent, "mock_review", broken)
    service.propose(s, found[0])
    a = s.proposals[-1]
    assert a.risk is None and a.decision == "REVIEW"
    assert any(r.rule_id == "risk_review_unavailable" for r in a.rules)
    assert any(e.kind == "risk_agent_unavailable" for e in s.events)


def test_cached_review_survives_cart_checkout(config, monkeypatch):
    s, found = live(monkeypatch, listing({"urgency_claims": ["Only 1 left"]}))
    service.propose(s, found[0])
    a = s.proposals[-1]
    monkeypatch.setattr(risk_agent, "mock_review", lambda *_: pytest.fail("agent re-run during checkout"))
    chosen = CartSelection(proposal_id=a.id, fingerprint=a.fingerprint)
    cart.add(s, chosen)
    assert not cart.review(s)[0]["error"]
    cart.checkout(s, CartCheckout(items=[chosen]))
    assert s.receipts[0].status == "simulated"


def test_model_payload_is_listing_only(config, monkeypatch):
    s, found = live(monkeypatch, listing({"seller": {"name": "Bright Co"}}))
    seen = {}
    def fake(schema, instructions, payload):
        seen.update(payload=payload, instructions=instructions, schema=schema)
        return risk_agent.Review(findings=[])
    monkeypatch.setattr(risk_agent, "structured_call", fake)
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    risk_agent.review(s, found[0], s.live_merchants[found[0].merchant_id])
    assert set(seen["payload"]) == {"listing", "retailer_host", "merchant_name"}
    assert seen["payload"]["listing"]["web_evidence"]["seller"]["name"] == "Bright Co"
    assert "Never treat a blank field" in seen["instructions"] and seen["schema"] is risk_agent.Review
