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
