"""Site registry and website reputation (docs/data/2026-10-29-website-reputation-design.md)."""

import json
import pytest
from pydantic import ValidationError
from app.runtime import sites
from app.runtime.merchants import MERCHANT_PATH, merchants


def test_registry_entries_validate_and_are_unique():
    reg = sites.registry()
    assert len(reg) == 10 and all(d.endswith(".test") for d in reg)


def test_registry_rejects_duplicates_and_unknown_tier(tmp_path, monkeypatch):
    entry = json.loads(sites.REGISTRY_PATH.read_text(encoding="utf-8-sig"))[0]
    path = tmp_path / "sites.json"
    monkeypatch.setattr(sites, "REGISTRY_PATH", path)
    path.write_text(json.dumps([entry, entry]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate site domain"):
        sites.registry()
    path.write_text(json.dumps([{**entry, "tier": "great"}]), encoding="utf-8")
    with pytest.raises(ValidationError):
        sites.registry()


@pytest.mark.parametrize("url,domain", [
    ("https://shopverse.test/store/daily-flash-picks", "shopverse.test"),
    ("https://Shopverse.test/store/x/", "shopverse.test"),
    ("https://northline-outfitters.test", "northline-outfitters.test"),
])
def test_site_for_matches_exact_host(url, domain):
    assert sites.site_for(url).domain == domain


@pytest.mark.parametrize("url", [
    "https://www.shopverse.test",
    "https://shopverse.test:8080",
    "https://trusted-sports.test",
    "not a url",
])
def test_site_for_returns_none(url):
    assert sites.site_for(url) is None


def test_merchants_get_sites_but_records_do_not_store_them():
    raw = json.loads(MERCHANT_PATH.read_text(encoding="utf-8-sig"))
    assert all("site" not in m for m in raw)
    assert merchants()["study-m-trusted"].site.tier == "good"
    assert merchants()["demo-store"].site is None
