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
    {"budget": F("120", hard=True)},                                  # higher budget
    {"features": F("comfortable, durable, practical, waterproof")},   # new feature
    {"usage": F("hiking")},
    {"size": F("30L")},
    {"preferred_brands": F("osprey")},
    {"excluded_brands": F("coofay")},
    {"category": F("Backpack")},                                      # same value, other case
])
def test_edits_that_keep_product_and_currency_refilter_the_batch(changes):
    assert covered(BASE, brief(**changes))


@pytest.mark.parametrize("changes", [{"category": F("suitcase")}, {"currency": F("USD")}])
def test_new_product_or_currency_needs_a_new_search(changes):
    assert not covered(BASE, brief(**changes))


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
    monkeypatch.setattr(shopify_catalog, "discover", fake("shopify_catalog", [30, 70]))
    monkeypatch.setattr(browser_search, "discover", fake("browser_use", [45, 75]))
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
    s.brief["budget"] = F("72", hard=True)
    again = discovery.discover(s)
    assert len(providers) == 2
    assert {s.live_products[i].price for i in again} == {30, 45, 70}


def test_asking_again_after_a_recheck_searches_the_web(providers):
    s = session()
    first = discovery.discover(s)
    s.brief["budget"] = F("72", hard=True)
    discovery.discover(s)                           # recheck of the current batch
    assert len(providers) == 2
    discovery.discover(s)                           # same needs again: a real search
    assert len(providers) == 4
    assert not set(first) & set(s.live_fetch.product_ids)


def test_fewer_than_three_left_searches_again(providers):
    s = session()
    discovery.discover(s)
    s.brief["budget"] = F("50", hard=True)          # only 30 and 45 still fit
    again = discovery.discover(s)
    assert len(providers) == 4
    assert set(again) <= set(s.live_fetch.product_ids)


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


def test_added_needs_refilter_and_search_only_when_nothing_fits(providers):
    s = session()
    discovery.discover(s)
    s.brief["budget"] = F("120", hard=True)
    s.brief["features"] = F("waterproof")                 # preferred: the batch still fits
    discovery.discover(s)
    assert len(providers) == 2
    s.brief["features"] = F("waterproof", hard=True)      # nothing in the batch shows it
    discovery.discover(s)
    assert len(providers) == 4


def test_a_new_search_replaces_the_batch(providers):
    s = session()
    first = set(discovery.discover(s))
    discovery.discover(s)                                 # unchanged needs: fresh search
    assert not first & set(s.live_fetch.product_ids)


def test_old_results_expire(providers):
    s = session()
    discovery.discover(s)
    s.live_fetch.at = (datetime.now(timezone.utc) - timedelta(minutes=26)).isoformat()
    s.brief["budget"] = F("60", hard=True)
    discovery.discover(s)
    assert len(providers) == 4


def test_partial_search_keeps_the_listings_it_found(providers, monkeypatch):
    from app.runtime.search_errors import SearchProviderError
    def timeout(session, query=""):
        providers.append("browser_use")
        raise SearchProviderError("timeout")
    monkeypatch.setattr(browser_search, "discover", timeout)
    monkeypatch.setattr(shopify_catalog, "discover", providers.fake("shopify_catalog", [30, 40, 70]))
    s = session()
    found = discovery.discover(s)
    assert found and sorted(found) == sorted(i for i in s.live_fetch.product_ids)
    s.brief["budget"] = F("72", hard=True)
    discovery.discover(s)
    assert len(providers) == 2


def test_live_fetch_is_not_shown_to_participants(providers):
    from app.runtime.schemas import SessionView
    s = session()
    discovery.discover(s)
    assert "live_fetch" not in SessionView.model_validate(s.model_dump()).model_dump()


def test_recheck_label_survives_the_friendly_history(providers):
    from app.runtime import shop_workspace
    s = shop_workspace.adopt(session())
    shop_workspace.meta(s)["history"] = [{"message_index": 0, "proposal_id": "x", "activity": [
        {"id": "search", "label": "Rechecked 3 web listing offers from your last search", "state": "completed",
         "evidence": ["a", "b", "c"]},
        {"id": "search", "label": "Search returned 1 web listing offers", "state": "completed", "evidence": ["a"]}]}]
    labels = [a["label"] for a in shop_workspace.friendly_history(s)[0]["activity"]]
    assert labels == ["Rechecked 3 offers from your last search", "Found 1 matching offer"]
