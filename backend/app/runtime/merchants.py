"""Observable merchant data only. Never import researcher ground truth here."""

import json
from pathlib import Path
from urllib.parse import urlparse
from .schemas import Merchant
from .sites import registry, site_for

ROOT = Path(__file__).resolve().parents[2]
MERCHANT_PATH = ROOT / "data/merchants/merchants.json"


def merchants():
    records = [
        Merchant.model_validate(x)
        for x in json.loads(MERCHANT_PATH.read_text(encoding="utf-8-sig"))
    ]
    if len({m.id for m in records}) != len(records):
        raise ValueError("Duplicate merchant IDs")
    for m in records:
        if not (urlparse(m.website).hostname or "").endswith(".test"):
            raise ValueError(
                "Simulated merchant websites must use reserved .test domains"
            )
    sites = registry()
    return {m.id: m.model_copy(update={"site": site_for(m.website, sites)}) for m in records}


def merchant_for(product, session=None):
    if product.source == "browser_use":
        if session is None or product.merchant_id not in session.live_merchants:
            raise ValueError("Missing live listing source")
        return session.live_merchants[product.merchant_id]
    record = merchants().get(product.merchant_id)
    if record is None:
        raise ValueError("Unknown merchant: request a fresh catalogue proposal")
    return record
