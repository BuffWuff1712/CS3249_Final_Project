"""Fictional site registry: website reputation for local merchants, looked up by exact host."""

import json
from pathlib import Path
from urllib.parse import urlparse
from .schemas import Site

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data/sites/site_registry.json"


def registry():
    records = [Site.model_validate(x) for x in json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))]
    if len({s.domain for s in records}) != len(records):
        raise ValueError("Duplicate site domain")
    return {s.domain: s for s in records}


def site_for(url, sites=None):
    parsed = urlparse(url)
    if parsed.port is not None:
        return None
    return (registry() if sites is None else sites).get(parsed.hostname or "")
