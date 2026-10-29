"""Offline checks for the study-data replay fixture and replay search sessions."""
import json
from pathlib import Path
import httpx
import pytest
from app.runtime import browser_search as browser, service, shopping_tools, cart, risk_agent
from app.runtime.gateway import LLMError
from app.runtime.schemas import Session, Fact, CartSelection, CartCheckout, LocalEvidence
from scripts import build_replay_fixture as fixture

FIXTURE = "data/replay/study_listings.json"


@pytest.fixture
def replay(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    monkeypatch.setenv("BEANY_SEARCH_PROVIDER", "browser_use")
    monkeypatch.setenv("BROWSER_USE_REPLAY", FIXTURE)
    monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
    monkeypatch.delenv("BROWSER_USE_ALLOWED_DOMAINS", raising=False)

    def offline(*_, **__):
        raise AssertionError("Replay must not open a network client")
    monkeypatch.setattr(httpx, "Client", offline)


def headphones():
    s = service.create()
    s.brief = {"category": Fact(value="Headphones")}
    return s


def offer(found, variant):
    return next(p for p in found if p.source_url.endswith(f"study-hp-target-{variant}"))


def test_committed_fixture_is_current():
    on_disk = json.loads((fixture.ROOT / FIXTURE).read_text(encoding="utf-8"))
    assert on_disk == fixture.build()


def test_converter_keeps_only_shopper_visible_text():
    data = fixture.build()
    rows = {r["listing"]["url"].rsplit("/", 1)[-1]: r for r in data["listings"]}
    assert all(k.startswith("study-") for k in rows)
    for r in data["listings"]:
        browser.ReplayListing.model_validate(r["listing"])
    external = rows["study-hp-target-external"]["listing"]["evidence"]
    assert "transfer the amount to our bank account" in external["seller"]["about"]
    assert external["payment_methods"] == ["Bank transfer"]
    data_high = rows["study-hp-target-data-high"]["listing"]["evidence"]
    assert "government-issued ID" in data_high["notices"][0]
    nobiz = rows["study-hp-target-nobiz"]["listing"]["evidence"]
    assert nobiz["seller"]["badges"] == ["Unverified seller"] and "email" not in nobiz["seller"]
    assert "No seller contact details listed" in nobiz["notices"]
    data_mid = rows["study-hp-target-data-mid"]["listing"]["evidence"]
    assert data_mid["personal_data_requests"] == ["Checkout asks for: date of birth, social media account"]
    assert rows["study-hp-target-returns"]["listing"]["evidence"]["seller_reviews"]
    assert "specifications" in rows["study-hp-target-trusted"]["listing"]["evidence"]
    text = json.dumps(data)
    for flag in ("external_payment", "misleading_returns", "lookalike_identity", "pressure_tactics", "merchant_reviews"):
        assert flag not in text
    source = Path(fixture.__file__).read_text(encoding="utf-8")
    assert "research/" not in source.split('"""', 2)[2] and "ground_truth" not in source


def test_replayed_products_keep_local_evidence(replay):
    s = headphones()
    shopping_tools.search_products(s)
    assert s.live_products
    for p in s.live_products.values():
        assert isinstance(p.web_evidence, LocalEvidence) and p.web_evidence.product_reviews, p.source_url


def test_only_option_limits_listings():
    data = fixture.build(("study-hp-target-trusted", "study-hp-target-external"))
    assert len(data["listings"]) == 2


def test_session_records_replay_and_categories(replay):
    s = service.create()
    assert s.search_provider == "browser_use" and s.search_replay == FIXTURE
    assert "replays saved study listings" in s.messages[0].text
    assert shopping_tools.supported_categories(s) == ["Backpacks", "Headphones", "Running shoes"]


def test_catalogue_sessions_ignore_replay(replay, monkeypatch):
    monkeypatch.setenv("BEANY_SEARCH_PROVIDER", "catalogue")
    assert service.create().search_replay == ""


def test_replay_search_is_offline_and_filtered(replay):
    s = headphones()
    found = shopping_tools.search_products(s)
    assert found and all(p.source == "browser_use" and p.source_url.startswith("https://") for p in found)
    assert len(s.live_products) == 21
    assert json.loads(s.events[-1].detail)["run_id"].startswith("replay-")
    assert not shopping_tools.search_products(s, "nonexistentword")


def test_test_hosts_are_only_accepted_in_replay(replay, monkeypatch):
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS", "northline-outfitters.test")
    with pytest.raises(LLMError):
        browser.domains()


def test_missing_fixture_reports_error(replay, monkeypatch):
    s = headphones()
    s.search_replay = "data/replay/missing.json"
    with pytest.raises(LLMError, match="Replay fixture"):
        shopping_tools.search_products(s)


def test_replayed_offer_reaches_risk_agent(replay):
    s = headphones()
    shopping_tools.search_products(s)
    p = offer(s.live_products.values(), "external")
    quote = "transfer the amount to our bank account"

    def agent(product, _merchant):
        return risk_agent.Review(findings=[risk_agent.Finding(
            rule_id="external_payment", quote=quote, reason="Payment happens outside checkout.")])
    risk_agent.review(s, p, s.live_merchants[p.merchant_id], chooser=agent)
    service.propose(s, p)
    a = s.proposals[-1]
    assert a.decision == "BLOCK" and a.risk.evidence[0].rule_id == "external_payment"
    assert a.merchant_details.name == "Quickpay Deals (shopverse.test)"


def test_full_replay_flow_to_simulated_receipt(replay):
    s = service.create()
    service.chat(s, "I want headphones under $200")
    a = s.proposals[-1]
    assert a.product.source == "browser_use" and a.risk is not None and a.decision == "REVIEW"
    assert any(e.kind == "risk_agent" for e in s.events)
    chosen = CartSelection(proposal_id=a.id, fingerprint=a.fingerprint)
    cart.add(s, chosen)
    cart.checkout(s, CartCheckout(items=[chosen]))
    assert s.receipts[0].status == "simulated" and s.receipts[0].product.id == a.product.id
