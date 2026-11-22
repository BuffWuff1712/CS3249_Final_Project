"""Reusing the last live search when an edit only changes local filtering."""
from datetime import datetime, timedelta, timezone
import pytest
from app.runtime import discovery, browser_search, shopify_catalog
from app.runtime.discovery import covered
from app.runtime.schemas import Fact, Product, Merchant, Session

F = lambda value, hard=False: Fact(value=value, source="confirmed", hard=hard)
BASE = {"category": F("backpack"), "budget": F("80", hard=True), "currency": F("SGD"),
        "features": F("comfortable, durable, practical", hard=True), "usage": F("travelling")}


def brief(**changes):
    out = dict(BASE)
    for k, v in changes.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = v
    return out


@pytest.mark.parametrize("changes", [
    {"features": F("comfortable, durable, practical", hard=False)},   # must-have -> preferred
    {"budget": F("60", hard=True)},                                   # lower budget
    {"features": F("comfortable, durable")},                          # drop a feature
    {"usage": None},                                                  # drop usage
    {"excluded_brands": F("coofay")},                                 # exclude a brand
    {"category": F("Backpack")},                                      # same value, other case
])
def test_filter_only_edits_are_covered(changes):
    assert covered(BASE, brief(**changes))


@pytest.mark.parametrize("changes", [
    {"category": F("suitcase")},
    {"features": F("comfortable, durable, practical, waterproof")},   # new feature
    {"features": F("lightweight")},                                    # reworded feature
    {"budget": F("120", hard=True)},                                   # higher budget
    {"budget": F("80", hard=False)},                                   # hard cap loosened
    {"budget": None},
    {"usage": F("hiking")},
    {"size": F("30L")},
    {"preferred_brands": F("osprey")},
    {"currency": F("USD")},
])
def test_edits_that_need_new_listings_are_not_covered(changes):
    assert not covered(BASE, brief(**changes))


def test_un_excluding_a_brand_needs_a_new_search():
    assert not covered(brief(excluded_brands=F("coofay")), BASE)


DESC = "travel backpack, padded straps, durable ripstop, laptop compartment and pockets"


class Calls(list):
    fake = None


@pytest.fixture
def providers(monkeypatch):
    calls = Calls()
    def fake(source, prices):
        def run(session, query=""):
            calls.append(source)
            ids = []
            for n, price in enumerate(prices):
                pid = f"{source}-{len(calls)}-{n}"
                session.live_merchants["m"] = Merchant(
                    id="m", name="Amazon US (www.amazon.sg)", website="https://www.amazon.sg", description="",
                    payment_methods=["Demo Visa"], return_policy="", contact="", review_count=0,
                    verified_business=False, requested_information=[])
                session.live_products[pid] = Product(
                    id=pid, name=f"Backpack {pid}", category="backpack", brand="", price=price, currency="SGD",
                    merchant="Amazon US (www.amazon.sg)", merchant_id="m", attributes=[], stock=True,
                    description=DESC, trust="unverified", source=source)
                ids.append(pid)
            return ids
        return run
    # Shopify finds nothing by default, so every hybrid search also reaches Browser Use.
    monkeypatch.setattr(shopify_catalog, "discover", fake("shopify_catalog", []))
    monkeypatch.setattr(browser_search, "discover", fake("browser_use", [30, 45, 70, 75]))
    calls.fake = fake
    return calls


def session(**changes):
    s = Session(search_provider="hybrid")
    s.brief = brief(**changes)
    return s


def test_preferred_toggle_reuses_the_last_search(providers):
    s = session()
    first = discovery.discover(s)
    assert providers == ["shopify_catalog", "browser_use"] and len(first) == 4
    s.brief["features"] = F("comfortable, durable, practical", hard=False)
    assert sorted(discovery.discover(s)) == sorted(first)
    assert len(providers) == 2
    assert s.events[-1].kind == "search_reuse"


def test_lower_budget_refilters_without_searching(providers):
    s = session()
    discovery.discover(s)
    s.brief["budget"] = F("50", hard=True)
    again = discovery.discover(s)
    assert len(providers) == 2
    assert {s.live_products[i].price for i in again} == {30, 45}


def test_empty_reuse_falls_back_to_a_real_search(providers):
    s = session()
    discovery.discover(s)
    s.brief["budget"] = F("20", hard=True)
    discovery.discover(s)
    assert len(providers) == 4


def test_unchanged_needs_mean_a_fresh_search(providers):
    s = session()
    discovery.discover(s)
    discovery.discover(s)
    assert len(providers) == 4


def test_rejected_offer_with_unchanged_needs_reuses(providers):
    s = session()
    first = discovery.discover(s)
    s.rejected_products.append(first[0])
    assert first[0] not in discovery.discover(s)
    assert len(providers) == 2


def test_new_feature_and_higher_budget_search_again(providers):
    s = session()
    discovery.discover(s)
    s.brief["features"] = F("waterproof")
    discovery.discover(s)
    assert len(providers) == 4
    s.brief["budget"] = F("120", hard=True)
    discovery.discover(s)
    assert len(providers) == 6


def test_old_results_expire(providers):
    s = session()
    discovery.discover(s)
    s.live_fetch.at = (datetime.now(timezone.utc) - timedelta(minutes=26)).isoformat()
    s.brief["budget"] = F("60", hard=True)
    discovery.discover(s)
    assert len(providers) == 4


def test_partial_search_is_never_reused(providers, monkeypatch):
    from app.runtime.search_errors import SearchProviderError
    def down(session, query=""):
        providers.append("shopify_catalog")
        raise SearchProviderError("unavailable", provider="shopify_catalog")
    monkeypatch.setattr(shopify_catalog, "discover", down)
    s = session()
    assert discovery.discover(s)
    assert s.live_fetch is None
    s.brief["budget"] = F("60", hard=True)
    discovery.discover(s)
    assert len(providers) == 4


def test_eligible_shopify_offers_skip_browser_use_and_are_reused(providers, monkeypatch):
    monkeypatch.setattr(shopify_catalog, "discover", providers.fake("shopify_catalog", [30, 70]))
    s = session()
    first = discovery.discover(s)
    assert list(providers) == ["shopify_catalog"] and len(first) == 2
    s.brief["budget"] = F("50", hard=True)
    assert [s.live_products[i].price for i in discovery.discover(s)] == [30]
    assert list(providers) == ["shopify_catalog"]


def test_required_features_are_checked_before_skipping_browser_use(providers, monkeypatch):
    from app.runtime import feature_check
    from app.runtime.feature_check import Review, Verdict
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.setattr(shopify_catalog, "discover", providers.fake("shopify_catalog", [30]))
    def fake(schema, instructions, payload):
        return Review(verdicts=[Verdict(product_id=x["product_id"], feature=f, status="met", quote="laptop compartment")
                                for x in payload["listings"] for f in x["features"]])
    monkeypatch.setattr("app.runtime.gateway.structured_call", fake)
    s = session(features=F("fits a 15 inch laptop", hard=True))
    assert discovery.discover(s) == ["shopify_catalog-1-0"]
    assert list(providers) == ["shopify_catalog"]


def test_offers_that_never_mention_a_required_feature_do_not_skip_browser_use(providers, monkeypatch):
    from app.runtime.feature_check import Review, Verdict
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.setattr(shopify_catalog, "discover", providers.fake("shopify_catalog", [30]))
    def fake(schema, instructions, payload):
        return Review(verdicts=[Verdict(product_id=x["product_id"], feature=f, status="unstated")
                                for x in payload["listings"] for f in x["features"]])
    monkeypatch.setattr("app.runtime.gateway.structured_call", fake)
    s = session(features=F("fits a 15 inch laptop", hard=True))
    found = discovery.discover(s)
    assert list(providers) == ["shopify_catalog", "browser_use"]
    assert "shopify_catalog-1-0" in found and len(found) == 5  # Unconfirmed offers stay, flagged for review.


def test_live_fetch_is_not_shown_to_participants(providers):
    from app.runtime.schemas import SessionView
    s = session()
    discovery.discover(s)
    assert "live_fetch" not in SessionView.model_validate(s.model_dump()).model_dump()
