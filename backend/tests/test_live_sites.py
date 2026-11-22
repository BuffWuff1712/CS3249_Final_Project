"""Website reputation for the public retailers live search may visit."""
import pytest
from app.runtime import sites
from app.runtime.browser_search import domains


@pytest.mark.parametrize("url,tier", [
    ("https://www.amazon.sg/dp/B01MTB55WH", "good"),
    ("https://amazon.sg/", "good"),
    ("https://www.qoo10.sg/item/123", "mid"),
])
def test_live_site_for_matches_host_and_subdomains(url, tier):
    assert sites.live_site_for(url).tier == tier


@pytest.mark.parametrize("url", [
    "https://amazon.sg.evil.example/x",
    "https://notamazon.sg/x",
    "http://www.amazon.sg/x",
    "https://www.amazon.sg:8443/x",
    "https://www.jetvance.com/products/x",
    "not a url",
])
def test_live_site_for_returns_none(url):
    assert sites.live_site_for(url) is None


def test_every_allowed_study_domain_has_a_reputation(monkeypatch):
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS", "amazon.sg,qoo10.sg")
    reg = sites.live_registry()
    assert set(domains()) <= set(reg)
    assert not set(reg) & set(sites.registry())


def test_browser_listing_merchant_carries_reputation(monkeypatch):
    from app.runtime import browser_search
    from app.runtime.schemas import Session, Fact
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS", "amazon.sg,qoo10.sg")
    row = {"name": "Travel backpack", "url": "https://www.amazon.sg/dp/B0B76D4NWW", "brand": "coofay",
           "price": 42.31, "currency": "SGD", "attributes": [], "sizes": [], "description": "Daypack",
           "in_stock": True}
    output = browser_search.SearchOutput.model_validate({"products": [row]})
    monkeypatch.setattr(browser_search, "run_task", lambda brief, query: ("run", output))
    s = Session(search_provider="browser_use")
    s.brief["category"] = Fact(value="backpack", source="confirmed")
    [pid] = browser_search.discover(s, "")
    merchant = s.live_merchants[s.live_products[pid].merchant_id]
    assert merchant.site.domain == "amazon.sg" and merchant.site.tier == "good"


def test_shopify_stores_are_rated_good():
    site = sites.shopify_site("https://www.jetvance.com/products/x")
    assert (site.domain, site.tier, site.label) == ("www.jetvance.com", "good", "Shopify store")
    assert sites.shopify_site("") is None


def test_shopify_listing_merchant_carries_good_reputation():
    from app.runtime.shopify_catalog import normalize
    from tests.test_shopify_catalog import row
    _, merchant = normalize(row())[0]
    assert merchant.site.tier == "good" and merchant.site.label == "Shopify store"
