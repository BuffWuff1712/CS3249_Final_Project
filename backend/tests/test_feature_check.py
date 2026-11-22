"""LLM fallback for required features the rules cannot confirm (feature_check.py)."""
import pytest
from app.runtime import feature_check, policy
from app.runtime.feature_check import Review, Verdict, ensure
from app.runtime.gateway import LLMError
from app.runtime.schemas import Action, Fact, Merchant, Product, Session

HEADPHONES = "Over-ear headphones with multipoint Bluetooth 5.3 and 60 hours playtime"


def make(pid, description, source="browser_use"):
    return Product(id=pid, name=f"Headphones {pid}", category="headphones", brand="", price=90, currency="SGD",
                   merchant="Amazon US (www.amazon.sg)", merchant_id="m", attributes=[], stock=True,
                   description=description, trust="unverified", source=source)


@pytest.fixture
def s(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    session = Session(search_provider="hybrid")
    session.brief["features"] = Fact(value="connects to two devices, foldable", source="confirmed", hard=True)
    for p in [make("a", HEADPHONES), make("b", "Wired headphones with 3.5mm cable"), make("c", "Black headphones")]:
        session.live_products[p.id] = p
    return session


def answer(monkeypatch, verdicts, seen=None):
    def fake(schema, instructions, payload):
        if seen is not None:
            seen.append(payload)
        return Review(verdicts=[Verdict(**v) for v in verdicts])
    monkeypatch.setattr("app.runtime.gateway.structured_call", fake)


def test_only_unconfirmed_required_features_are_sent(s, monkeypatch):
    s.live_products["a"].description += ", foldable design"
    seen = []
    answer(monkeypatch, [], seen)
    ensure(s, ["a", "b", "c"])
    asked = {x["product_id"]: x["features"] for x in seen[0]["listings"]}
    assert asked["a"] == ["connects to two devices"]
    assert asked["b"] == asked["c"] == ["connects to two devices", "foldable"]


def test_verdicts_decide_search_and_review(s, monkeypatch):
    answer(monkeypatch, [
        {"product_id": "a", "feature": "connects to two devices", "status": "met", "quote": "multipoint Bluetooth 5.3"},
        {"product_id": "a", "feature": "foldable", "status": "unstated"},
        {"product_id": "b", "feature": "connects to two devices", "status": "absent", "quote": "Wired headphones"},
        {"product_id": "c", "feature": "connects to two devices", "status": "unstated"},
        {"product_id": "c", "feature": "foldable", "status": "unstated"},
    ])
    ensure(s, ["a", "b", "c"])
    kept = [p.id for p in policy.search(s, limit=None)]
    assert kept == ["a", "c"]  # b contradicts a required feature; a ranks first on a confirmed match
    assert policy.unstated_features(s, s.live_products["a"]) == ["foldable"]
    assert policy.missing_features(s, s.live_products["a"]) == []


def test_ungrounded_quote_counts_as_unstated(s, monkeypatch):
    answer(monkeypatch, [
        {"product_id": "c", "feature": "connects to two devices", "status": "met", "quote": "dual connection"},
        {"product_id": "b", "feature": "foldable", "status": "absent", "quote": "rigid headband"},
    ])
    ensure(s, ["b", "c"])
    assert s.feature_checks["c"]["connects to two devices"].status == "unstated"
    assert s.feature_checks["b"]["foldable"].status == "unstated"


def test_verdicts_for_unasked_products_or_features_are_ignored(s, monkeypatch):
    answer(monkeypatch, [
        {"product_id": "zzz", "feature": "foldable", "status": "met", "quote": "foldable"},
        {"product_id": "c", "feature": "waterproof", "status": "met", "quote": "Black"},
    ])
    ensure(s, ["c"])
    assert set(s.feature_checks) == {"c"}
    assert {t: v.status for t, v in s.feature_checks["c"].items()} == {
        "connects to two devices": "unstated", "foldable": "unstated"}


def test_model_failure_keeps_strict_rules(s, monkeypatch):
    def down(*a, **k):
        raise LLMError("unavailable")
    monkeypatch.setattr("app.runtime.gateway.structured_call", down)
    ensure(s, ["a", "b", "c"])
    assert policy.search(s, limit=None) == []


def test_cached_verdicts_are_not_asked_again(s, monkeypatch):
    answer(monkeypatch, [{"product_id": "c", "feature": "connects to two devices", "status": "unstated"},
                         {"product_id": "c", "feature": "foldable", "status": "unstated"}])
    ensure(s, ["c"])
    seen = []
    answer(monkeypatch, [], seen)
    ensure(s, ["c"])
    assert seen == []


def test_soft_features_and_catalogue_products_skip_the_model(s, monkeypatch):
    seen = []
    answer(monkeypatch, [], seen)
    s.brief["features"] = Fact(value="connects to two devices", source="confirmed", hard=False)
    ensure(s, ["a", "b", "c"])
    s.brief["features"] = Fact(value="connects to two devices", source="confirmed", hard=True)
    s.live_products["d"] = make("d", "Black headphones", source="catalogue")
    ensure(s, ["d"])
    assert seen == []


def test_unstated_required_feature_adds_review_rule(s, monkeypatch):
    answer(monkeypatch, [{"product_id": "c", "feature": "connects to two devices", "status": "unstated"},
                         {"product_id": "c", "feature": "foldable", "status": "unstated"}])
    ensure(s, ["c"])
    p = s.live_products["c"]
    s.live_merchants["m"] = Merchant(id="m", name=p.merchant, website="https://www.amazon.sg", description="",
                                     payment_methods=["Demo Visa"], return_policy="", contact="", review_count=0,
                                     verified_business=False, requested_information=[])
    a = Action(product=p, merchant_details=s.live_merchants["m"])
    rules = {r.rule_id: r for r in policy.evaluate(s, a).rules}
    assert "features" not in rules
    assert rules["features_unconfirmed"].decision == "REVIEW"
    assert "connects to two devices, foldable" in rules["features_unconfirmed"].explanation


def test_feature_checks_are_not_shown_to_participants(s):
    from app.runtime.schemas import SessionView
    assert "feature_checks" not in SessionView.model_validate(s.model_dump()).model_dump()


def test_skipped_pairs_count_as_unstated(s, monkeypatch):
    answer(monkeypatch, [{"product_id": "c", "feature": "foldable", "status": "unstated"}])
    ensure(s, ["c"])
    assert s.feature_checks["c"]["connects to two devices"].status == "unstated"
    assert "c" in [p.id for p in policy.search(s, limit=None)]
