"""Offline checks for LocalEvidence, the local-record mapping and AI risk routing."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.runtime import storage
from app.runtime.browser_search import Listing, ReplayListing, SearchOutput
from app.runtime.schemas import LocalEvidence, Product, Session, WebEvidence

SCHEMA_SNAPSHOT = Path(__file__).parent / "fixtures/browser_use_output_schema.json"


def row(**evidence):
    return {"name": "Desk light", "url": "https://shop.test/products/light", "brand": "Example",
            "price": 25, "currency": "SGD", "attributes": ["adjustable"], "sizes": [],
            "description": "Adjustable desk lamp", "in_stock": True, "evidence": evidence}


def web_product(pid, evidence):
    return Product(id=pid, name="Desk light", category="Lighting", brand="Example", price=25,
                   merchant="shop.test", merchant_id="web-m", attributes=[], description="Lamp",
                   source="browser_use", source_url="https://shop.test/p", web_evidence=evidence)


def test_browser_use_schema_is_unchanged():
    assert SearchOutput.model_json_schema() == json.loads(SCHEMA_SNAPSHOT.read_text())


def test_local_evidence_fields_default_empty():
    e = LocalEvidence()
    assert e.product_reviews == [] and e.seller_reviews == [] and e.specifications == []
    assert e.product_rating == "" and isinstance(e, WebEvidence)


def test_session_round_trips_local_evidence():
    s = Session()
    s.live_products = {
        "local": web_product("local", LocalEvidence(seller_reviews=["★1 Bad — asked for bank transfer"])),
        "web": web_product("web", WebEvidence(return_policy="30 days")),
    }
    storage.save(s)
    loaded = storage.load(s.id)
    local, web = loaded.live_products["local"].web_evidence, loaded.live_products["web"].web_evidence
    assert isinstance(local, LocalEvidence) and local.seller_reviews == ["★1 Bad — asked for bank transfer"]
    assert type(web) is WebEvidence and web.return_policy == "30 days"


def test_replay_listing_accepts_local_fields():
    data = row(seller_reviews=["★5 Ok — fine"])
    assert ReplayListing.model_validate(data).evidence.seller_reviews == ["★5 Ok — fine"]
    with pytest.raises(ValidationError):
        Listing.model_validate(data)


# --- Mapping (spec §2.2) ---------------------------------------------------

from app.runtime.local_evidence import local_evidence, request_label, review_view  # noqa: E402
from app.runtime.merchants import merchants  # noqa: E402
from app.runtime.policy import catalogue  # noqa: E402

FLAGS = ("external_payment", "misleading_returns", "lookalike_identity", "pressure_tactics", "inconsistent_information")


def products():
    return {p.id: p for p in catalogue(Session())}


def mapped(product_id):
    p = products()[product_id]
    return local_evidence(p, merchants()[p.merchant_id])


def test_seller_fields_copied():
    e, m = mapped("study-hp-target-trusted"), merchants()["study-m-trusted"]
    assert (e.seller.name, e.seller.page_url, e.seller.about) == (m.name, m.website, m.description)
    assert e.seller.email == m.contact and e.seller.badges == ["Verified business"]
    assert e.seller.rating == "4.7/5 (2,140 reviews)"
    assert e.return_policy == m.return_policy and e.payment_methods == m.payment_methods


def test_unverified_and_no_contact_are_explicit():
    e = mapped("study-hp-target-nobiz")
    assert e.seller.badges == ["Unverified seller"] and e.seller.email == "" and e.seller.phone == ""
    assert "No seller contact details listed" in e.notices


def test_checkout_note_is_a_notice():
    assert merchants()["study-m-data-mid"].checkout_note in mapped("study-hp-target-data-mid").notices


def test_requested_information_becomes_readable_request():
    p = products()["study-hp-target-data-mid"]
    m = merchants()["study-m-data-mid"]
    assert local_evidence(p, m).personal_data_requests == ["Checkout asks for: date of birth, social media account"]
    delivery = m.model_copy(update={"requested_information": ["fictional_name", "fictional_delivery_address"]})
    assert local_evidence(p, delivery).personal_data_requests == ["Checkout asks for: name, delivery address"]
    assert local_evidence(p, m.model_copy(update={"requested_information": []})).personal_data_requests == []
    assert request_label("government_id") == "government ID"


def test_reviews_specs_and_rating():
    p = products()["study-hp-target-trusted"]
    e = mapped("study-hp-target-trusted")
    assert e.product_reviews == [f"★{r.rating} {r.title} — {r.text}" for r in p.reviews] and len(e.product_reviews) == 3
    seller = merchants()["study-m-trusted"].merchant_reviews
    assert e.seller_reviews == [f"★{r.rating} {r.title} — {r.text}" for r in seller]
    assert "Type: Over-ear, closed back" in e.specifications
    assert e.product_rating == "4.6/5 (2,310 ratings)"


def test_no_flags_or_labels_leak():
    ps = products()
    for pid, p in ps.items():
        if pid.startswith("study-"):
            text = local_evidence(p, merchants()[p.merchant_id]).model_dump_json()
            assert not any(word in text for word in (*FLAGS, "TRUSTWORTHY", "MALICIOUS", "SUSPICIOUS", "UNCERTAIN")), pid


def test_old_fixture_merchant_maps():
    e = local_evidence(products()["audio-1"], merchants()["privacy"])
    assert e.personal_data_requests == ["Checkout asks for: email, government ID, bank password"]
    assert e.seller_reviews == [] and e.product_reviews == [] and e.product_rating == ""


def test_review_view_is_a_copy():
    p = products()["study-hp-target-returns"]
    view = review_view(p, merchants()[p.merchant_id])
    assert isinstance(view.web_evidence, LocalEvidence) and p.web_evidence is None
    assert (view.id, view.price) == (p.id, p.price)


# --- Switch and AI routing (spec §3) ----------------------------------------

from app.runtime import risk_agent, service  # noqa: E402
from app.runtime.gateway import LLMError  # noqa: E402


def agent(monkeypatch, findings=None, error=None):
    """Route risk_agent.review to a fake model; returns the call log."""
    calls = []

    def fake(product, merchant):
        calls.append(product.id)
        if error:
            raise error
        return risk_agent.Review(findings=findings or [])
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.setattr(risk_agent, "ask_model", fake)
    return calls


def returns_finding():
    return [risk_agent.Finding(rule_id="misleading_returns", quote="Refunds are issued as store credit only",
                               reason="The refund promise conflicts with the policy.")]


def ai_session(monkeypatch):
    monkeypatch.setenv("BEANY_RISK_DETECTION", "ai")
    return service.create()


def propose(s, product_id):
    p = next(x for x in catalogue(s) if x.id == product_id)
    service.propose(s, p)
    return s.proposals[-1]


def test_switch_defaults_to_rules(monkeypatch):
    monkeypatch.delenv("BEANY_RISK_DETECTION", raising=False)
    assert service.create().risk_detection == "rules"


def test_switch_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("BEANY_RISK_DETECTION", "maybe")
    with pytest.raises(ValueError, match="rules or ai"):
        service.create()


def test_rules_mode_never_calls_agent(monkeypatch):
    monkeypatch.delenv("BEANY_RISK_DETECTION", raising=False)
    s = service.create()
    calls = agent(monkeypatch, error=AssertionError("agent must not run in rules mode"))
    a = propose(s, "study-hp-target-external")
    assert a.decision == "BLOCK" and calls == []
    assert not any(e.kind in ("risk_agent", "risk_agent_fallback") for e in s.events)


def test_ai_mode_scores_catalogue_offer_with_agent_findings(monkeypatch):
    s = ai_session(monkeypatch)
    agent(monkeypatch, returns_finding())
    a = propose(s, "study-hp-target-returns")
    assert [e.rule_id for e in a.risk.evidence] == ["misleading_returns"]
    assert "Observed:" in a.risk.evidence[0].evidence
    assert a.product.web_evidence is None


def test_ai_mode_calls_agent_once_per_offer(monkeypatch):
    s = ai_session(monkeypatch)
    calls = agent(monkeypatch, returns_finding())
    propose(s, "study-hp-target-returns")
    propose(s, "study-hp-target-returns")
    assert calls == ["study-hp-target-returns"]


def test_ai_mode_falls_back_to_rules(monkeypatch):
    s = ai_session(monkeypatch)
    agent(monkeypatch, error=LLMError("provider down"))
    a = propose(s, "study-hp-target-returns")
    assert {e.rule_id for e in a.risk.evidence} == {"misleading_returns"}
    assert "Observed:" not in a.risk.evidence[0].evidence
    assert any(e.kind == "risk_agent_fallback" and e.detail == "study-hp-target-returns" for e in s.events)


def test_ai_mode_applies_to_scenario_sessions(monkeypatch):
    s = ai_session(monkeypatch)
    s.scenario_id = "risk-c"
    agent(monkeypatch, [risk_agent.Finding(rule_id="excessive_data", quote="government ID",
                                           reason="Checkout asks for an ID document.")])
    a = propose(s, "offer-privacy")
    assert [e.rule_id for e in a.risk.evidence] == ["excessive_data"] and "Observed:" in a.risk.evidence[0].evidence


# --- Final review fixes -----------------------------------------------------

from app.runtime import research  # noqa: E402


@pytest.mark.parametrize("product_id", ["study-hp-target-injection", "study-hp-target-data-high", "study-hp-target-external"])
def test_ai_mode_keeps_non_negotiable_safeguards(monkeypatch, product_id):
    s = ai_session(monkeypatch)
    s.permissions.share_personal_data = True  # so merchant_privacy does not mask the risk decision
    agent(monkeypatch, [])  # the model reports nothing
    a = propose(s, product_id)
    assert a.risk.recommended_decision == "BLOCK" and a.decision == "BLOCK"


def report_row(s):
    return research.report(s)["rows"][-1]


def test_report_records_risk_basis(monkeypatch):
    s = ai_session(monkeypatch)
    agent(monkeypatch, returns_finding())
    propose(s, "study-hp-target-returns")
    row = report_row(s)
    assert row["risk_basis"] == "ai" and row["risk_detection"] == "ai"


def test_report_marks_rules_fallback(monkeypatch):
    s = ai_session(monkeypatch)
    agent(monkeypatch, error=LLMError("provider down"))
    propose(s, "study-hp-target-returns")
    assert report_row(s)["risk_basis"] == "rules_fallback"


def test_report_marks_rules_mode(monkeypatch):
    monkeypatch.delenv("BEANY_RISK_DETECTION", raising=False)
    s = service.create()
    propose(s, "study-hp-target-returns")
    row = report_row(s)
    assert row["risk_basis"] == "rules" and row["risk_detection"] == "rules"
