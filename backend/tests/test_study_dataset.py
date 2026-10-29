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
from app.runtime.sites import registry

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
    "site-mid",
    "site-bad",
    "site-fake",
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
    "site-mid": {"signals": ["site_reputation_mid"], "ground_truth": "UNCERTAIN"},
    "site-bad": {"signals": ["site_reputation_poor"], "ground_truth": "SUSPICIOUS"},
    "site-fake": {"signals": ["site_reputation_poor"], "ground_truth": "MALICIOUS"},
}

STUDY_CATEGORIES: list[str] = ["hp", "rs", "bp"]

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
    "bp": {
        "category": "Backpacks",
        "P": 99,
        "budget": 120,
        "features": "laptop, water-resistant",
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
    "site-mid": 0.75,
    "site-bad": 0.80,
    "site-fake": 0.80,
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
]

BRAND_DENYLIST = [
    "Sony", "Bose", "Apple", "AirPods", "Beats", "JBL", "Sennheiser", "Jabra",
    "Anker", "Soundcore", "Nike", "Adidas", "Asics", "Brooks", "Hoka",
    "New Balance", "Saucony", "Puma", "Under Armour", "Reebok", "JanSport",
    "Herschel", "North Face", "Osprey", "Samsonite", "Amazon",
    # Real shopping platforms the site registry is modelled on.
    "eBay", "Pinduoduo", "Temu", "Lazada", "Shopee", "Taobao", "AliExpress",
    # Source product lines and model numbers (spec §3: remove model numbers).
    "Soundcore", "Life Q", "Q35", "N700", "XBT", "MT3", "Recon", "Lone Peak",
    "Peregrine", "Revel", "BioMoGo", "Phantom", "HOVR", "520", "Prime", "Dynamo",
]

ALL_MERCHANT_KEYS = ["trusted", "neutral", *VARIANTS]

# Website placement (docs/data/2026-10-29-website-reputation-design.md §2.2).
# "own" means the merchant's own independent site.
PLACEMENT = {
    "trusted": "northline-outfitters.test",
    **{v: "shopverse.test" for v in ["lowprice", "nobiz", "external", "pressure", "inconsistent", "injection", "concealed", "lookalike"]},
    **{v: "own" for v in ["neutral", "benign", "payment", "returns", "data-mid", "data-high"]},
    "site-mid": "dealbazaar.test",
    "site-bad": "best-gear-outlet.test",
    "site-fake": "north1ine-outfitters.test",
}
MARKETPLACES = {"shopverse.test", "dealbazaar.test"}
KNOCKOFF = {
    "hp": ("Lumin Hush ANC", "Lumin"),
    "rs": ("Vella Tempo Daily", "Vella"),
    "bp": ("Atlis Scholar 30", "Atlis"),
}


def test_study_merchants_exist():
    assert {f"study-m-{v}" for v in ALL_MERCHANT_KEYS} <= set(merchants())


@pytest.mark.parametrize("v", ["trusted", "neutral", "lowprice", "benign", "concealed", "site-mid", "site-bad", "site-fake"])
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
def test_study_merchant_site_is_registered(v):
    m = merchants()[f"study-m-{v}"]
    assert m.site is not None
    assert ("/store/" in m.website) == (m.site.kind == "marketplace")


@pytest.mark.parametrize(
    "v", [v for v in ALL_MERCHANT_KEYS if not any(s.startswith("site_reputation") for s in EXPECTED[v]["signals"])]
)
def test_single_signal_variants_sit_on_good_sites(v):
    assert merchants()[f"study-m-{v}"].site.tier == "good"


def test_placement_matches_spec():
    ms = merchants()
    own = [ms[f"study-m-{v}"].site.domain for v, d in PLACEMENT.items() if d == "own"]
    assert len(set(own)) == len(own) and not set(own) & MARKETPLACES
    for v, domain in PLACEMENT.items():
        site = ms[f"study-m-{v}"].site
        assert site.kind == ("marketplace" if domain in MARKETPLACES else "independent"), v
        if domain != "own":
            assert site.domain == domain, v


@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_merchant_text_names_only_its_own_host(v):
    m = merchants()[f"study-m-{v}"]
    texts = [m.contact, m.description, m.return_policy, m.checkout_note] + [
        t for r in m.merchant_reviews for t in (r.title, r.text)
    ]
    assert set(re.findall(r"[a-z0-9.-]+\.test", " ".join(texts).lower())) <= {m.site.domain}


def test_site_fake_copies_the_trusted_name_on_an_imitation_domain():
    t, f = merchants()["study-m-trusted"], merchants()["study-m-site-fake"]
    assert f.name == t.name == "Northline Outfitters"
    assert f.site.domain == "north1ine-outfitters.test" and f.site.tier == "poor"


@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_merchant_reviews_count(v):
    assert 3 <= len(merchants()[f"study-m-{v}"].merchant_reviews) <= 5


def test_concealed_is_a_distinct_store_with_trusted_terms():
    t, c = merchants()["study-m-trusted"], merchants()["study-m-concealed"]
    same_terms = [
        "payment_methods",
        "requested_information",
        "verified_business",
        "external_payment",
        "misleading_returns",
        "lookalike_identity",
        "pressure_tactics",
        "inconsistent_information",
        "checkout_note",
    ]
    assert all(getattr(t, f) == getattr(c, f) for f in same_terms)
    # Its own store, not a copy: own wording everywhere a shopper reads.
    for f in ["name", "website", "contact", "description", "return_policy"]:
        assert getattr(t, f) != getattr(c, f), f
    assert not {r.text for r in t.merchant_reviews} & {r.text for r in c.merchant_reviews}
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
    assert trusted.rating is not None
    for v in ["neutral", *VARIANTS]:
        o = ps[offer(cat, v)]
        fields = [f for f in SHARED if v != "lookalike" or f not in ("name", "brand")]
        assert all(getattr(o, f) == getattr(trusted, f) for f in fields), v


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_lookalike_is_a_knockoff(cat):
    ps = products()
    trusted, knockoff = ps[offer(cat, "trusted")], ps[offer(cat, "lookalike")]
    assert (knockoff.name, knockoff.brand) == KNOCKOFF[cat]
    assert knockoff.brand != trusted.brand
    assert f"Same design as the {trusted.name} at a fraction of the price." in knockoff.description
    for f in ["specifications", "attributes", "rating", "rating_count"]:
        assert getattr(knockoff, f) == getattr(trusted, f), f


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
    for s in registry().values():
        yield s.domain, [s.name, s.label, s.summary]


def test_no_real_brands_or_placeholder_text():
    brands = re.compile(r"\b(" + "|".join(map(re.escape, BRAND_DENYLIST)) + r")\b", re.I)
    placeholder = re.compile(r"fictional|for simulation only|https?://|www\.", re.I)
    leaks = [
        (i, t) for i, texts in study_texts() for t in texts
        if brands.search(t) or placeholder.search(t)
    ]
    assert leaks == []


def test_manifest_complete():
    entries = manifest()
    assert len(entries) == 48
    assert {e["category"] for e in entries.values()} == {"Headphones", "Running shoes", "Backpacks"}


OLD_FIXTURE_PREFIXES = ("shoe-", "audio-", "bag-", "offer-")


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_study_brands_absent_from_old_fixtures(cat):
    # Shared brands would mix old and study prices in each other's low_price comparables.
    ps = products()
    old = {p.brand for i, p in ps.items() if i.startswith(OLD_FIXTURE_PREFIXES) and p.category == PINNED[cat]["category"]}
    ours = {p.brand for i, p in ps.items() if i.startswith(f"study-{cat}-")}
    assert ours and not ours & old


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_candidates_fire_no_signals(cat):
    ps, scope = products(), list(products().values())
    for p in candidates(cat):
        r = assess(p, merchants()[p.merchant_id], scope, load_config())
        assert r.evidence == [], (p.id, [e.rule_id for e in r.evidence])


def fired(product_id, scope):
    ps = products()
    p = ps[product_id]
    r = assess(p, merchants()[p.merchant_id], scope, load_config())
    return {e.rule_id for e in r.evidence}


def assert_scenario_matches_manifest(product_ids):
    """Spec §6.3: re-check every study offer's signals against the scenario's actual product set."""
    ps, entries = products(), manifest()
    scope = [ps[i] for i in product_ids]
    for i in product_ids:
        if i in entries:
            assert fired(i, scope) == set(entries[i]["signals"]), i


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
@pytest.mark.parametrize("v", VARIANTS)
@pytest.mark.parametrize("width", ["category", "catalogue"])
def test_signals_hold_in_wider_scopes(cat, v, width):
    ps = products()
    if width == "category":
        ids = [i for i in ps if i.startswith(f"study-{cat}-")]
    else:
        ids = list(ps)
    assert offer(cat, v) in ids
    assert fired(offer(cat, v), [ps[i] for i in ids]) == set(EXPECTED[v]["signals"])


def study_scenarios():
    specs = json.loads((ROOT / "data/scenarios/scenarios.json").read_text(encoding="utf-8-sig"))
    return [s for s in specs if any(i.startswith("study-") for i in s.get("product_ids") or [])]


@pytest.mark.parametrize("spec", study_scenarios(), ids=lambda s: s["id"])
def test_study_scenarios_match_manifest(spec):
    assert_scenario_matches_manifest(spec["product_ids"])


def test_scenario_validator_catches_a_flipped_signal():
    ids = [offer("hp", k) for k in ("trusted", "neutral", "benign")]
    assert_scenario_matches_manifest(ids)
    # A scope where benign is the only same-brand offer has no comparables, so low_price cannot fire.
    with pytest.raises(AssertionError):
        assert_scenario_matches_manifest([offer("hp", "benign")])


@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_each_offer_has_its_own_reviews(cat):
    ps = products()
    sets = {v: {r.text for r in ps[offer(cat, v)].reviews} for v in ["trusted", "neutral", *VARIANTS]}
    assert all(len(texts) == 3 for texts in sets.values())
    keys = list(sets)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            assert len(sets[a] & sets[b]) <= 1, (a, b)
