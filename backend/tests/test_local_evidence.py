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


# --- Mapping (spec §2.2) ---------------------------------------------------

from app.runtime.local_evidence import local_evidence, request_label, review_view  # noqa: E402
from app.runtime.merchants import merchants  # noqa: E402
from app.runtime.policy import catalogue  # noqa: E402

FLAGS = ("external_payment", "misleading_returns", "lookalike_identity", "pressure_tactics", "inconsistent_information")


def products():
    return {p.id: p for p in catalogue(Session())}


def mapped(product_id):
    p = products()[product_id]
    return local_evidence(p, merchants()[p.merchant_id])


def test_seller_fields_copied():
    e, m = mapped("study-hp-target-trusted"), merchants()["study-m-trusted"]
    assert (e.seller.name, e.seller.page_url, e.seller.about) == (m.name, m.website, m.description)
    assert e.seller.email == m.contact and e.seller.badges == ["Verified business"]
    assert e.seller.rating == "4.7/5 (2,140 reviews)"
    assert e.return_policy == m.return_policy and e.payment_methods == m.payment_methods


def test_unverified_and_no_contact_are_explicit():
    e = mapped("study-hp-target-nobiz")
    assert e.seller.badges == ["Unverified seller"] and e.seller.email == "" and e.seller.phone == ""
    assert "No seller contact details listed" in e.notices


def test_checkout_note_is_a_notice():
    assert merchants()["study-m-data-mid"].checkout_note in mapped("study-hp-target-data-mid").notices


def test_requested_information_becomes_readable_request():
    p = products()["study-hp-target-data-mid"]
    m = merchants()["study-m-data-mid"]
    assert local_evidence(p, m).personal_data_requests == ["Checkout asks for: date of birth, social media account"]
    delivery = m.model_copy(update={"requested_information": ["fictional_name", "fictional_delivery_address"]})
    assert local_evidence(p, delivery).personal_data_requests == ["Checkout asks for: name, delivery address"]
    assert local_evidence(p, m.model_copy(update={"requested_information": []})).personal_data_requests == []
    assert request_label("government_id") == "government ID"


def test_reviews_specs_and_rating():
    p = products()["study-hp-target-trusted"]
    e = mapped("study-hp-target-trusted")
    assert e.product_reviews == [f"★{r.rating} {r.title} — {r.text}" for r in p.reviews] and len(e.product_reviews) == 3
    seller = merchants()["study-m-trusted"].merchant_reviews
    assert e.seller_reviews == [f"★{r.rating} {r.title} — {r.text}" for r in seller]
    assert "Type: Over-ear, closed back" in e.specifications
    assert e.product_rating == "4.6/5 (2,310 ratings)"


def test_no_flags_or_labels_leak():
    ps = products()
    for pid, p in ps.items():
        if pid.startswith("study-"):
            text = local_evidence(p, merchants()[p.merchant_id]).model_dump_json()
            assert not any(word in text for word in (*FLAGS, "TRUSTWORTHY", "MALICIOUS", "SUSPICIOUS", "UNCERTAIN")), pid


def test_old_fixture_merchant_maps():
    e = local_evidence(products()["audio-1"], merchants()["privacy"])
    assert e.personal_data_requests == ["Checkout asks for: email, government ID, bank password"]
    assert e.seller_reviews == [] and e.product_reviews == [] and e.product_rating == ""


def test_review_view_is_a_copy():
    p = products()["study-hp-target-returns"]
    view = review_view(p, merchants()[p.merchant_id])
    assert isinstance(view.web_evidence, LocalEvidence) and p.web_evidence is None
    assert (view.id, view.price) == (p.id, p.price)
