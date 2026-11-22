"""Site registries: fictional local sites (exact host) and the public retailers live search may visit."""

import json
from pathlib import Path
from urllib.parse import urlparse
from .schemas import Site

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data/sites/site_registry.json"
LIVE_REGISTRY_PATH = ROOT / "data/sites/live_site_registry.json"


def load(path):
    records = [Site.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8-sig"))]
    if len({s.domain for s in records}) != len(records):
        raise ValueError("Duplicate site domain")
    return {s.domain: s for s in records}


def registry():
    return load(REGISTRY_PATH)


def live_registry():
    return load(LIVE_REGISTRY_PATH)


def live_site_for(url, sites=None):
    """Reputation for a public retailer host or any of its subdomains (www.amazon.sg -> amazon.sg)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.port not in (None, 443) or not host:
        return None
    for domain, site in (live_registry() if sites is None else sites).items():
        if host == domain or host.endswith("." + domain):
            return site
    return None


def shopify_site(url):
    """Every Shopify Catalog store is rated good: it sells through Shopify's hosted checkout."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return None
    return Site(domain=host, name=host, kind="independent", tier="good", label="Shopify store",
                summary="Independent store selling through Shopify, whose hosted checkout and "
                        "payment processing handle the order.")


def site_for(url, sites=None):
    parsed = urlparse(url)
    if parsed.port is not None:
        return None
    return (registry() if sites is None else sites).get(parsed.hostname or "")
