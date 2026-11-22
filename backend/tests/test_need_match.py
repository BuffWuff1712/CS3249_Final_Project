"""Tolerant size, brand and seller matching, and how policy uses it (cases from the 22 Nov 2026 runs)."""
import pytest
from app.runtime import policy
from app.runtime.feature_match import size_rule, brand_rule, merchant_rule
from app.runtime.feature_check import Review, Verdict, ensure
from app.runtime.schemas import Action, Fact, Merchant, Product, Session

F = lambda value, hard=True: Fact(value=value, source="confirmed", hard=hard)


@pytest.mark.parametrize("need,sizes,expected", [
    ("7-8 years", ["7-8 Years"], True),
    ("7-8 years", ["7-8 jaar (122-128)"], True),
    ("7-8 years", ["7T-8T"], True),
    ("7-8 years", ["6/7 YEARS"], True),
    ("7-8 years", ["5-6 Years", "7-8 Years"], True),
    ("M", ["Medium"], True),
    ("42", ["EU 42"], True),
    ("7-8 years", ["9-12 M"], False),        # months
    ("7-8 years", ["2Y"], False),
    ("10-11 years", ["7-8 Years"], False),
    ("M", ["L"], False),
    ("7-8 years", ["Small (S)"], None),      # adult letter size: the model decides
    ("7-8 years", ["150"], None),
    ("7-8 years", [], None),
])
def test_size_rule(need, sizes, expected):
    assert size_rule(need, sizes) is expected


def make(pid="web-1", source="browser_use", **kw):
    base = dict(id=pid, name="Kids Christmas Jumper", category="sweaters", brand="", price=30, currency="SGD",
                merchant="Amazon US (www.amazon.sg)", merchant_id="m", attributes=[], stock=True,
                description="Festive knit jumper", trust="unverified", source=source,
                source_url="https://www.amazon.sg/dp/B0X")
    return Product(**base | kw)


def test_brand_rule_reads_the_title_when_the_brand_field_is_empty():
    assert brand_rule("ugreen", make(name="UGREEN HiTune Max5c")) is True
    assert brand_rule("sony", make(name="Wireless earbuds")) is None
    assert brand_rule("sony", make(brand="Sony Electronics")) is True
    assert brand_rule("sony", make(brand="JBL")) is False


def test_merchant_rule_matches_seller_name_or_host():
    assert merchant_rule("amazon", make())
    assert merchant_rule("amazon", make(merchant="Amazon Germany"))
    assert not merchant_rule("qoo10", make())


def session(**brief):
    s = Session(search_provider="hybrid")
    s.brief = {"category": F("sweaters"), **brief}
    return s


def rules(s, p):
    s.live_merchants["m"] = Merchant(id="m", name=p.merchant, website="https://www.amazon.sg", description="",
                                     payment_methods=["Demo Visa"], return_policy="", contact="", review_count=0,
                                     verified_business=False, requested_information=[])
    return {r.rule_id: r.decision for r in policy.evaluate(s, Action(product=p, merchant_details=s.live_merchants["m"])).rules}


def test_size_written_differently_is_kept():
    s = session(size=F("7-8 years"))
    p = make(sizes=["7-8 Years"])
    s.live_products[p.id] = p
    assert policy.search(s, limit=None) == [p]
    assert "size" not in rules(s, p) and "size_unconfirmed" not in rules(s, p)


def test_hard_size_clearly_wrong_is_excluded_and_soft_size_is_reviewed():
    s = session(size=F("7-8 years"))
    p = make(sizes=["9-12 M"])
    s.live_products[p.id] = p
    assert policy.search(s, limit=None) == []
    s.brief["size"] = F("7-8 years", hard=False)
    assert policy.search(s, limit=None) == [p]
    assert rules(s, p)["size"] == "REVIEW"


def test_undecided_size_is_kept_for_review():
    s = session(size=F("7-8 years"))
    p = make(sizes=["Small (S)"])
    s.live_products[p.id] = p
    assert policy.search(s, limit=None) == [p]
    assert rules(s, p)["size_unconfirmed"] == "REVIEW"


def test_model_settles_sizes_the_rules_cannot(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    s = session(size=F("7-8 years"))
    adult, kid = make("a", sizes=["Small (S)"]), make("k", sizes=["150"], description="Fits height 122-128 cm")
    s.live_products.update({"a": adult, "k": kid})
    seen = []
    def fake(schema, instructions, payload):
        seen.append(payload)
        return Review(verdicts=[Verdict(product_id="a", feature="size: 7-8 years", status="absent", quote="Small (S)"),
                                Verdict(product_id="k", feature="size: 7-8 years", status="met", quote="122-128 cm")])
    monkeypatch.setattr("app.runtime.gateway.structured_call", fake)
    ensure(s, ["a", "k"])
    assert {x["product_id"]: x["features"] for x in seen[0]["listings"]} == {"a": ["size: 7-8 years"], "k": ["size: 7-8 years"]}
    assert policy.search(s, limit=None) == [kid]
    fit = {f.kind: f for f in policy.feature_fit(s, kid)}
    assert fit["size"].status == "met" and fit["size"].quote == "122-128 cm"


def test_required_brand_missing_from_a_shopify_listing_is_reviewed_not_excluded():
    s = session(preferred_brands=F("ugreen"))
    unnamed, named, other = make("u", source="shopify_catalog"), make("n", name="UGREEN Max5c"), make("o", brand="JBL")
    for p in (unnamed, named, other):
        s.live_products[p.id] = p
    assert {p.id for p in policy.search(s, limit=None)} == {"u", "n"}
    assert policy.search(s, limit=None)[0].id == "n"   # a confirmed brand ranks first
    assert rules(s, unnamed)["brand_unconfirmed"] == "REVIEW"


def test_excluded_brand_in_the_title_is_excluded():
    s = session(excluded_brands=F("disney", hard=False))
    p = make(name="Disney Lilo & Stitch Christmas Jumper")
    s.live_products[p.id] = p
    assert policy.search(s, limit=None) == []


def test_seller_preference_and_restriction_match_tolerantly():
    s = session(merchants=F("amazon"))
    p = make()
    s.live_products[p.id] = p
    assert policy.search(s, limit=None) == [p]
    s.permissions.restricted_merchants = ["amazon"]
    assert policy.search(s, limit=None) == []
