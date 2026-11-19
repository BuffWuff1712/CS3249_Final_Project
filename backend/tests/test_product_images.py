import pytest
from app.runtime.product_images import image_url,select_image
from app.runtime.shopify_catalog import normalize
from app.runtime.schemas import Action
from app.runtime.policy import fingerprint
from test_shopify_catalog import row

@pytest.mark.parametrize("url",["http://example.com/a.png","https://127.0.0.1/a","https://localhost/a","data:image/png;base64,abc","javascript:alert(1)","https://user:password@example.com/a","https://example.com:8080/a"])
def test_unsafe_images_are_dropped(url):
    assert image_url(url)==""


def test_variant_image_preferred_and_parent_fallback():
    parent={"title":"Lamp","media":[{"type":"image","url":"https://cdn.shopify.com/parent.jpg"}]}
    variant={"media":[{"type":"image","url":"https://cdn.shopify.com/variant.jpg","alt_text":"Black lamp"}]}
    assert select_image(variant,parent)==("https://cdn.shopify.com/variant.jpg","Black lamp")
    assert select_image({},parent)[0].endswith("parent.jpg")
    assert select_image({},{} )==("","")


def test_live_variant_url_without_parent_url_is_supported():
    data=row();url=data.pop("url")
    data["variants"][0]["url"]=url+"?variant=1"
    data["variants"][0]["media"]=[{"type":"image","url":"https://cdn.shopify.com/variant.jpg"}]
    p,_=normalize(data)[0]
    assert p.source_url.endswith("?variant=1") and p.image_url.endswith("variant.jpg")


def test_image_metadata_not_approval_authority():
    p,_=normalize(row())[0]
    a=Action(product=p)
    before=fingerprint(a)
    a.product.image_url="https://cdn.shopify.com/new.jpg"
    a.product.image_alt="Photo"
    assert fingerprint(a)==before


def test_recorded_live_shopify_shape():
    import json
    from pathlib import Path
    data=json.loads((Path(__file__).parent / "fixtures/shopify_live_shape.json").read_text(encoding="utf-8"))
    offers=normalize(data)
    assert offers and all(p.image_url and p.provider_ids["variant"] for p,m in offers)
