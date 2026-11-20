"""Saved Shopify response shape, without live requests or model calls."""
from copy import deepcopy
import pytest
from app.runtime import shopify_catalog as shopify, policy
from app.runtime.schemas import Session, Action, Product
from test_shopify_catalog import row


def listing():
    data = row()
    data["description"] = {"plain":"<p>Wireless headphones</p><ul><li>50 hours battery life</li></ul>"}
    data["metadata"] = {"top_features":["Wireless connectivity", "Active noise cancellation"],
                        "unique_selling_points":["Lightweight for travel"]}
    data["rating"] = {"value":4.8,"scale_min":1,"scale_max":5,"count":483}
    v=data["variants"][0]
    v["description"]={"html":"<p>Black edition &amp; carrying case</p>"}
    v["condition"]=["new"]
    v["list_price"]={"amount":15000,"currency":"SGD"}
    v["seller"]["links"]=[{"type":"refund_policy","url":"https://checkout.shopify.com/10/policies/123.html"},
                            {"type":"shipping_policy","url":"https://merchant.example/policies/shipping"}]
    return data


def test_returned_evidence_is_preserved_without_promoting_inference():
    p,m=shopify.normalize(listing())[0]
    assert p.rating==4.8 and p.rating_count==483 and p.rating_scope=="product"
    assert p.reviews==[] and m.review_rating is None
    assert p.attributes==[] and len(p.inferred_attributes)==2
    assert p.selling_points==["Lightweight for travel"]
    assert "Black edition & carrying case" in p.description and "50 hours battery life" in p.description
    assert "<p>" not in p.description
    assert p.list_price==150 and p.specifications=={"Color":"Black","Condition":"new"}
    assert p.policy_links["refund_policy"]==p.web_evidence.return_policy_url
    assert m.return_policy=="Unknown; check the merchant."
    assert Product.model_validate(p.model_dump()).model_dump()==p.model_dump()


def test_variant_rating_precedence_and_invalid_rating_fallback():
    data=listing();v=data["variants"][0]
    v["rating"]={"value":5,"scale_min":1,"scale_max":5,"count":10}
    p,_=shopify.normalize(data)[0]
    assert (p.rating,p.rating_count,p.rating_scope)==(5,10,"variant")
    v["rating"]["value"]=8
    assert shopify.normalize(data)[0][0].rating==4.8
    del data["rating"]
    assert shopify.normalize(data)[0][0].rating is None


def test_description_not_truncated_and_unsafe_links_not_exposed():
    data=listing();data["description"]={"html":"<script>evil()</script><p>"+"A "*1500+"Final feature</p>"}
    data["variants"][0]["seller"]["links"] += [
        {"type":"privacy_policy","url":"javascript:alert(1)"},
        {"type":"terms_of_service","url":"https://merchant.example/checkout"}]
    p,_=shopify.normalize(data)[0]
    assert "Final feature" in p.description and "evil()" not in p.description
    assert set(p.policy_links)=={"refund_policy","shipping_policy"}


def test_sparse_details_preserve_search_evidence_and_explicit_empty_clears(monkeypatch):
    data=listing();p,m=shopify.normalize(data)[0];s=Session(search_provider="shopify_catalog")
    s.live_products[p.id]=p;s.live_merchants[m.id]=m
    sparse=deepcopy(data)
    for key in ("description","metadata","rating"):sparse.pop(key,None)
    for key in ("description", "options", "condition", "list_price"): sparse["variants"][0].pop(key)
    sparse["variants"][0]["seller"].pop("links")
    sparse["variants"][0]["price"]["amount"]=13000
    monkeypatch.setattr(shopify,"call",lambda *_:{"product":sparse})
    fresh=shopify.details(s,p)
    assert fresh.price==130 and fresh.detail_checked
    assert fresh.rating==4.8 and fresh.description==p.description and fresh.inferred_attributes==p.inferred_attributes
    assert fresh.policy_links==p.policy_links
    assert fresh.list_price==p.list_price and fresh.specifications==p.specifications
    sparse.update(description=None,metadata=None,rating=None)
    sparse["variants"][0]["seller"]["links"]=[]
    fresh=shopify.details(s,fresh)
    assert fresh.rating is None and fresh.inferred_attributes==[] and fresh.description=="" and fresh.policy_links=={}


def test_new_evidence_changes_fingerprint_but_empty_defaults_are_omitted():
    p,m=shopify.normalize(listing())[0]
    a=Action(product=p,merchant_details=m)
    before=policy.fingerprint(a)
    a.product.rating_count+=1
    assert policy.fingerprint(a)!=before
    a.product.rating_count-=1
    a.product.policy_links["refund_policy"]="https://merchant.example/new-policy"
    assert policy.fingerprint(a)!=before
