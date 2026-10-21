"""Validation for the study dataset (docs/data/2026-10-21-study-dataset-design.md).

Asserts signals, prices and ground truth only. Risk levels and ALLOW/REVIEW/BLOCK
decisions belong to the policy owner and are deliberately not asserted here.
"""

import json
import re
import pytest
from app.runtime import policy
from app.runtime.merchant_risk import assess, load_config
from app.runtime.merchants import merchants
from app.runtime.policy import ROOT, catalogue, search, terms
from app.runtime.research import TRUTH_PATH
from app.runtime.schemas import Fact, Session

MANIFEST_PATH = ROOT / "data/research/risk_offer_manifest.json"

VARIANTS = [
    "lowprice",
    "nobiz",
    "data-mid",
    "data-high",
    "payment",
    "external",
    "returns",
    "lookalike",
    "pressure",
    "inconsistent",
    "injection",
    "benign",
    "concealed",
]

EXPECTED = {
    "trusted": {"signals": [], "ground_truth": "TRUSTWORTHY"},
    "neutral": {"signals": [], "ground_truth": "TRUSTWORTHY"},
    "lowprice": {"signals": ["low_price"], "ground_truth": "UNCERTAIN"},
    "benign": {"signals": ["low_price"], "ground_truth": "TRUSTWORTHY"},
    "pressure": {"signals": ["pressure"], "ground_truth": "UNCERTAIN"},
    "concealed": {"signals": [], "ground_truth": "MALICIOUS"},
    "nobiz": {"signals": ["missing_business"], "ground_truth": "SUSPICIOUS"},
    "returns": {"signals": ["misleading_returns"], "ground_truth": "SUSPICIOUS"},
    "inconsistent": {"signals": ["inconsistent"], "ground_truth": "SUSPICIOUS"},
    "lookalike": {"signals": ["lookalike"], "ground_truth": "SUSPICIOUS"},
    "data-mid": {"signals": ["excessive_data"], "ground_truth": "SUSPICIOUS"},
    "payment": {"signals": ["unusual_payment"], "ground_truth": "SUSPICIOUS"},
    "data-high": {"signals": ["excessive_data"], "ground_truth": "MALICIOUS"},
    "injection": {"signals": ["injection"], "ground_truth": "MALICIOUS"},
    "external": {
        "signals": ["external_payment", "unusual_payment"],
        "ground_truth": "MALICIOUS",
    },
}

STUDY_CATEGORIES: list[str] = ["hp", "rs"]

PINNED = {
    "hp": {
        "category": "Headphones",
        "P": 179,
        "budget": 200,
        "features": "wireless, noise-cancelling",
    },
    "rs": {
        "category": "Running shoes",
        "P": 159,
        "budget": 180,
        "features": "cushioned, road",
    },
}

RATIOS = {
    "trusted": 1.00,
    "neutral": 0.95,
    "lowprice": 0.35,
    "benign": 0.40,
    "external": 0.75,
    "pressure": 0.85,
    "concealed": 0.85,
    **{
        v: 0.80
        for v in ["nobiz", "data-mid", "data-high", "payment", "returns", "lookalike", "inconsistent", "injection"]
    },
}

SHARED = [
    "name",
    "brand",
    "category",
    "currency",
    "attributes",
    "specifications",
    "sizes",
    "rating",
    "rating_count",
    "reviews",
]

BRAND_DENYLIST = [
    "Sony", "Bose", "Apple", "AirPods", "Beats", "JBL", "Sennheiser", "Jabra",
    "Anker", "Soundcore", "Nike", "Adidas", "Asics", "Brooks", "Hoka",
    "New Balance", "Saucony", "Puma", "Under Armour", "Reebok", "JanSport",
    "Herschel", "North Face", "Osprey", "Samsonite", "Amazon",
]

ALL_MERCHANT_KEYS = ["trusted", "neutral", *VARIANTS]


def test_study_merchants_exist():
    assert {f"study-m-{v}" for v in ALL_MERCHANT_KEYS} <= set(merchants())


@pytest.mark.parametrize("v", ["trusted", "neutral", "lowprice", "benign", "concealed"])
def test_clean_merchants_have_clean_fields(v):
    m = merchants()[f"study-m-{v}"]
    assert m.requested_information == [] and m.verified_business and m.contact
    assert m.payment_methods == ["Demo Visa", "Demo Wallet"] and not m.external_payment
    assert not any(
        [
            m.misleading_returns,
            m.lookalike_identity,
            m.pressure_tactics,
            m.inconsistent_information,
        ]
    )


@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_merchant_reviews_count(v):
    assert 3 <= len(merchants()[f"study-m-{v}"].merchant_reviews) <= 5


def test_concealed_mirrors_trusted():
    t, c = merchants()["study-m-trusted"], merchants()["study-m-concealed"]
    same = [
        "description",
        "payment_methods",
        "return_policy",
        "requested_information",
        "verified_business",
        "external_payment",
        "misleading_returns",
        "lookalike_identity",
        "pressure_tactics",
        "inconsistent_information",
        "checkout_note",
    ]
    assert all(getattr(t, f) == getattr(c, f) for f in same)
    assert abs(c.review_count - t.review_count) <= 0.2 * t.review_count
    assert abs(c.review_rating - t.review_rating) <= 0.1


@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_ground_truth_labels(v):
    labels = json.loads(TRUTH_PATH.read_text(encoding="utf-8-sig"))["labels"]
    assert labels[f"study-m-{v}"] == EXPECTED[v]["ground_truth"]


def products():
    return {p.id: p for p in catalogue(Session())}


def manifest():
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    return {e["product_id"]: e for e in entries}


def offer(cat, v):
    return f"study-{cat}-target-{v}"


def candidates(cat):
    return [p for i, p in products().items() if re.fullmatch(f"study-{cat}-\\d+", i)]


def has_goal(p, cat):
    joined = " ".join(p.attributes).casefold()
    return all(t in joined for t in terms(PINNED[cat]["features"]))


def goal_session(cat):
    return Session(
        brief={
            "category": Fact(value=PINNED[cat]["category"]),
            "budget": Fact(value=str(PINNED[cat]["budget"]), hard=True),
            "features": Fact(value=PINNED[cat]["features"]),
        }
    )


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_offer_set_complete(cat):
    ps = products()
    assert all(offer(cat, v) in ps for v in ["trusted", "neutral", *VARIANTS])
    assert 5 <= len(candidates(cat)) <= 7
    assert all(ps[offer(cat, v)].merchant_id == f"study-m-{v}" for v in ["trusted", "neutral", *VARIANTS])


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_offers_share_product_fields(cat):
    ps = products()
    trusted = ps[offer(cat, "trusted")]
    assert 3 <= len(trusted.reviews) <= 5 and trusted.rating is not None
    for v in ["neutral", *VARIANTS]:
        o = ps[offer(cat, v)]
        assert all(getattr(o, f) == getattr(trusted, f) for f in SHARED), v


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
@pytest.mark.parametrize("v", ["trusted", "neutral", *VARIANTS])
def test_price_ratios(cat, v):
    P = PINNED[cat]["P"]
    price = products()[offer(cat, v)].price
    assert abs(price / P - RATIOS[v]) <= 0.03
    if v in VARIANTS:
        assert price < 0.95 * P


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_category_and_currency(cat):
    ours = [p for i, p in products().items() if i.startswith(f"study-{cat}-")]
    assert ours and all(
        p.category == PINNED[cat]["category"] and p.currency == "SGD" for p in ours
    )


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_only_target_meets_goal_within_budget(cat):
    trusted = products()[offer(cat, "trusted")]
    pool = candidates(cat) + [trusted]
    budget = PINNED[cat]["budget"]
    assert [p.id for p in pool if has_goal(p, cat) and p.price <= budget] == [trusted.id]
    others = candidates(cat)
    assert len([p for p in others if has_goal(p, cat) and p.price > budget]) == 1
    assert any(not has_goal(p, cat) and p.price < trusted.price for p in others)
    assert all(p.brand != trusted.brand for p in others)
    assert len({p.brand for p in others}) >= 3


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
@pytest.mark.parametrize("v", VARIANTS)
def test_manifest_matches_engine(cat, v):
    ps, entry = products(), manifest()[offer(cat, v)]
    assert entry["merchant_id"] == f"study-m-{v}" and entry["variant"] == v
    assert entry["category"] == PINNED[cat]["category"]
    assert entry["price_ratio"] == RATIOS[v]
    assert entry["reference_set"] == [offer(cat, "trusted"), offer(cat, "neutral")]
    # concealed is indistinguishable by design, so it has no visible cue.
    assert bool(entry["visible_in"]) == (v != "concealed")
    scope = [ps[i] for i in entry["reference_set"]] + [ps[entry["product_id"]]]
    r = assess(ps[entry["product_id"]], merchants()[entry["merchant_id"]], scope, load_config())
    # No assertion on r.level / r.recommended_decision: those belong to the policy owner.
    assert {e.rule_id for e in r.evidence} == set(EXPECTED[v]["signals"]) == set(entry["signals"])
    assert entry["ground_truth"] == EXPECTED[v]["ground_truth"]


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
@pytest.mark.parametrize("v", VARIANTS)
def test_search_ranks_variant_first(cat, v, monkeypatch):
    ps = products()
    scope = candidates(cat) + [ps[offer(cat, k)] for k in ("trusted", "neutral", v)]
    monkeypatch.setattr(policy, "catalogue", lambda s: scope)
    assert search(goal_session(cat))[0].id == offer(cat, v)


def study_texts():
    for p in products().values():
        if p.id.startswith("study-"):
            yield p.id, [p.name, p.description, *p.specifications.values()] + [
                t for r in p.reviews for t in (r.title, r.text)
            ]
    for m in merchants().values():
        if m.id.startswith("study-m-"):
            yield m.id, [m.name, m.description, m.return_policy, m.checkout_note] + [
                t for r in m.merchant_reviews for t in (r.title, r.text)
            ]


def test_no_real_brands_or_placeholder_text():
    brands = re.compile(r"\b(" + "|".join(map(re.escape, BRAND_DENYLIST)) + r")\b", re.I)
    placeholder = re.compile(r"fictional|for simulation only|https?://|www\.", re.I)
    leaks = [
        (i, t) for i, texts in study_texts() for t in texts
        if brands.search(t) or placeholder.search(t)
    ]
    assert leaks == []
