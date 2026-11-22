"""Tolerant feature matching for live listings (cases from the 22 Nov 2026 user study)."""
import pytest
from app.runtime.feature_match import met, listing_text
from app.runtime.policy import search, missing_features
from app.runtime.schemas import Fact, Product, Session

HEADPHONES = "over-ear wireless headphones with hybrid active noise cancellation, bluetooth 5.4, 75 hours playback"
BACKPACK = ("20l water-resistant polyester travel backpack, padded shoulder straps and mesh back panel, "
            "laptop compartment, luggage strap, 11 pockets")
SPEAKER = "portable bluetooth speaker 20w driver (30w peak), 480g with carry strap, ipx6, up to 24 hours playtime"


@pytest.mark.parametrize("feature,text", [
    ("blocking out background noise", HEADPHONES),
    ("noise cancelling", HEADPHONES),
    ("comfortable", BACKPACK),
    ("practical", BACKPACK),
    ("lightweight", SPEAKER),
    ("strong bass", "deep bassup technology, 12w stereo"),
    ("long battery life", SPEAKER),
    ("loud volume", SPEAKER),
    ("waterproof", SPEAKER),
    ("durable", "made of durable ripstop nylon"),
])
def test_paraphrased_features_match(feature, text):
    assert met(feature, text)


@pytest.mark.parametrize("feature,text", [
    ("noise cancelling", "wired earbuds with inline microphone"),
    ("waterproof", HEADPHONES),
    ("durable", "stylish canvas tote"),
    ("usb-c charging", "classic wired headphones"),
    ("induction heating", "rice cooker with aluminium inner pot and heating plate"),
])
def test_absent_features_do_not_match(feature, text):
    assert not met(feature, text)


def live(**kw):
    base = dict(id="web-1", name="Travel Backpack", category="backpack", brand="", price=30, currency="SGD",
                merchant="Amazon US (www.amazon.sg)", merchant_id="web-m", attributes=[], stock=True,
                description=BACKPACK, trust="unverified", source="browser_use")
    return Product(**base | kw)


def test_listing_text_reads_beyond_attributes():
    p = live(description="Padded straps", specifications={"Material": "Ripstop nylon"})
    text = listing_text(p)
    assert "padded straps" in text and "ripstop nylon" in text


def test_provider_inferred_features_never_confirm():
    p = live(name="Headphones", description="Black edition", inferred_attributes=["Wireless connectivity"],
             selling_points=["Lightweight for travel"])
    text = listing_text(p)
    assert not met("wireless", text) and not met("lightweight", text)


def test_hard_paraphrased_features_keep_live_listing():
    s = Session(search_provider="browser_use")
    s.brief["features"] = Fact(value="comfortable, durable, practical", source="confirmed", hard=True)
    p = live(description=BACKPACK + ", durable fabric")
    s.live_products[p.id] = p
    assert missing_features(s, p) == []
    assert [x.id for x in search(s, limit=None)] == [p.id]


def test_hard_feature_still_excludes_live_listing_without_it():
    s = Session(search_provider="browser_use")
    s.brief["features"] = Fact(value="waterproof", source="confirmed", hard=True)
    p = live(description="cotton canvas daypack with two pockets")
    s.live_products[p.id] = p
    assert missing_features(s, p) == ["waterproof"]
    assert search(s, limit=None) == []


def test_concept_words_match_as_prefixes_only():
    assert not met("keeps my things safe from pickpockets", BACKPACK)
