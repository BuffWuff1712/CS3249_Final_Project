import pytest
from pydantic import ValidationError
from app.runtime.merchants import merchants
from app.runtime.policy import catalogue
from app.runtime.schemas import Review, Session


def test_existing_fixtures_still_validate():
    products = catalogue(Session())
    assert products and all(
        p.reviews == [] for p in products if not p.id.startswith("study-")
    )


def test_review_rating_bounds():
    with pytest.raises(ValidationError):
        Review(rating=6, title="t", text="x", date="2026-01-01")


def test_new_fields_default_and_forbid_extra():
    m = merchants()["demo-store"]
    assert m.merchant_reviews == [] and m.checkout_note == ""
    with pytest.raises(ValidationError):
        Review(rating=5, title="t", text="x", date="2026-01-01", user_id="u1")
