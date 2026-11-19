"""Offline Shopify MCP contracts and hybrid routing; no external services."""
import copy
import asyncio
import json
import httpx
import pytest
from app.runtime import shopify_catalog as shopify, browser_search, discovery, policy, shopping_workflow, service
from app.runtime.schemas import Session, Fact, Action
from app.runtime.search_errors import SearchProviderError


def row(price=12500,variant="1",shop="10"):
    return {"id":"gid://shopify/p/model1","title":"Desk Lamp","url":"https://merchant.example/products/lamp",
        "description":{"plain":"Adjustable desk lamp"},"categories":[{"taxonomy":"merchant","value":"Lighting"}],
        "metadata":{"top_features":["waterproof"]},"variants":[{"id":"gid://shopify/ProductVariant/"+variant,
        "title":"Black","price":{"amount":price,"currency":"SGD"},"availability":{"available":True},
        "options":[{"name":"Color","label":"Black"}],"seller":{"id":"gid://shopify/Shop/"+shop,
        "name":"Example merchant","url":"https://merchant.example"},"checkout_url":"https://merchant.example/cart/1:1"}]}


def session(mode="hybrid"):
    return Session(search_provider=mode,mode="mock",brief={"category":Fact(value="Desk lamp"),"currency":Fact(value="SGD"),"budget":Fact(value="200",hard=True)})


def test_anonymous_and_allowlist(monkeypatch):
    monkeypatch.setenv("SHOPIFY_CLIENT_ID","");monkeypatch.setenv("SHOPIFY_CLIENT_SECRET","")
    assert shopify.headers()=={}
    with pytest.raises(ValueError):shopify.call("complete_checkout",{})
    monkeypatch.setenv("SHOPIFY_CLIENT_ID","partial")
    with pytest.raises(SearchProviderError) as exc:shopify.headers()
    assert exc.value.provider=="shopify_catalog" and exc.value.reason=="access"


def test_normalization_variant_minor_units_and_inferred_evidence():
    p,m=shopify.normalize(row())[0]
    assert p.price==125 and p.currency=="SGD"
    assert p.attributes==[] and p.inferred_attributes==["waterproof"]
    assert p.provider_ids["variant"].endswith("/1") and "/cart/" not in p.source_url
    assert not p.detail_checked and not m.verified_business
    assert shopify.normalize(row(variant="2"))[0][0].id!=p.id
    assert shopify.normalize(row(shop="11"))[0][0].id!=p.id


@pytest.mark.parametrize("mutation",["no_price","invalid_currency","bad_url","from_price","seller_mismatch"])
def test_bad_offers_not_imported(mutation):
    data=row()
    if mutation=="no_price":del data["variants"][0]["price"]
    if mutation=="invalid_currency":data["variants"][0]["price"]["currency"]="EUR"
    if mutation=="bad_url":data["url"]="http://localhost/lamp"
    if mutation=="from_price":data["price_range"]={"min":{"amount":100,"currency":"SGD"}};del data["variants"][0]["price"]
    if mutation=="seller_mismatch":data["variants"][0]["seller"]["url"]="https://other.example"
    assert shopify.normalize(data)==[]


def test_shopify_success_no_browser_and_detail_refresh(monkeypatch):
    calls=[]
    def call(name,catalog):
        calls.append((name,catalog))
        return {"products":[row()]} if name=="search_catalog" else {"product":row(13000)}
    monkeypatch.setattr(shopify,"call",call)
    monkeypatch.setattr(browser_search,"discover",lambda *_:pytest.fail("No browsing for Shopify success"))
    s=session()
    with discovery.budget():
        ids=discovery.discover(s)
        p=shopify.details(s,s.live_products[ids[0]])
    assert p.price==130 and p.detail_checked
    assert calls[0][1]["filters"]["price"]["max"]==20000
    assert calls[1][1]["id"]=="gid://shopify/ProductVariant/1"


@pytest.mark.parametrize("failed",[True,False])
def test_hybrid_fallback_once_and_shared_budget(monkeypatch,failed):
    calls=[]
    def initial(*_):
        calls.append("shopify")
        if failed:raise shopify.error("rate_limit")
        return []
    def fallback(s,q):
        calls.append("browser")
        p,m=shopify.normalize(row())[0];p.source="browser_use"
        s.live_products[p.id]=p;s.live_merchants[m.id]=m
        return [p.id]
    monkeypatch.setattr(shopify,"discover",initial);monkeypatch.setattr(browser_search,"discover",fallback)
    s=session()
    with discovery.budget():
        assert discovery.discover(s)
        with pytest.raises(ValueError):discovery.discover(s)
    assert calls==["shopify","browser"]
    if failed: assert json.loads(s.events[-1].detail)["provider"]=="shopify_catalog"


def test_stop_prevents_fallback(monkeypatch):
    from threading import Event
    from app.runtime.progress import cancellation,RequestStopped
    stop=Event()
    def initial(*_):stop.set();return []
    monkeypatch.setattr(shopify,"discover",initial)
    monkeypatch.setattr(browser_search,"discover",lambda *_:pytest.fail("Stopped request must not browse"))
    with cancellation(stop),discovery.budget():
        with pytest.raises(RequestStopped):discovery.discover(session())


def test_failure_plus_empty_is_unavailable_not_no_match(monkeypatch):
    monkeypatch.setattr(shopify,"discover",lambda *_:(_ for _ in ()).throw(shopify.error("unavailable")))
    monkeypatch.setattr(browser_search,"discover",lambda *_:[])
    with discovery.budget(),pytest.raises(SearchProviderError):discovery.discover(session())


def test_both_empty_is_no_match(monkeypatch):
    monkeypatch.setattr(shopify,"discover",lambda *_:[]);monkeypatch.setattr(browser_search,"discover",lambda *_:[])
    with discovery.budget(): assert discovery.discover(session())==[]


def test_http_error_diagnostics():
    response=httpx.Response(429,headers={"Retry-After":"7"},request=httpx.Request("POST",shopify.ENDPOINT))
    exc=shopify.classify(httpx.HTTPStatusError("SECRET",request=response.request,response=response))
    assert exc.reason=="rate_limit" and exc.retry_after==7 and "SECRET" not in str(exc)
    assert "credits" not in str(exc)


def test_default_and_old_session_compatibility(monkeypatch):
    monkeypatch.delenv("BEANY_SEARCH_PROVIDER",raising=False)
    assert service.create().search_provider=="hybrid"
    assert Session.model_validate({}).search_provider=="catalogue"
    assert Session.model_validate({"search_provider":"browser_use"}).search_provider=="browser_use"


def test_mcp_transport_contract(monkeypatch):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    import mcp
    import mcp.client.streamable_http as transport
    calls=[]
    @asynccontextmanager
    async def fake_transport(url,**kwargs):
        assert url==shopify.ENDPOINT and kwargs["headers"]=={}
        yield (None,None,None)
    class Client:
        def __init__(self,*_):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*_):pass
        async def initialize(self):calls.append("initialize")
        async def list_tools(self,**kwargs):return SimpleNamespace(tools=[SimpleNamespace(name="search_catalog")])
        async def send_request(self,request,result_type):
            name=request.root.params.name
            args=request.root.params.arguments
            calls.append(name)
            assert args["meta"]["ucp-agent"]["profile"]==shopify.PROFILE
            return result_type.model_validate({"structuredContent":{"products":[row()]}})
    monkeypatch.setattr(transport,"streamablehttp_client",fake_transport)
    monkeypatch.setattr(mcp,"ClientSession",Client)
    data=asyncio.run(shopify._call("search_catalog",{"query":"lamp"},{},shopify.PROFILE,10))
    assert data["products"] and calls==["initialize","search_catalog"]


def test_workflow_inspects_shopify_variant_and_keeps_policy(monkeypatch):
    monkeypatch.setattr(shopify,"call",lambda name,args:{"products":[row()]} if name=="search_catalog" else {"product":row()})
    monkeypatch.setattr(browser_search,"discover",lambda *_:pytest.fail("Unexpected fallback"))
    s=session()
    result=shopping_workflow.run_shopping(s)
    assert result.status=="proposed" and result.product.detail_checked
    service.propose(s,result.product,recommendations=result.candidates)
    assert s.proposals[-1].decision=="REVIEW" and not s.receipts
    assert s.proposals[-1].fingerprint==policy.fingerprint(s.proposals[-1])


def test_detail_failure_then_empty_fallback_remains_unavailable(monkeypatch):
    def call(name,args):
        if name=="search_catalog":return {"products":[row()]}
        raise shopify.error("unavailable")
    monkeypatch.setattr(shopify,"call",call)
    monkeypatch.setattr(browser_search,"discover",lambda *_:[])
    with pytest.raises(SearchProviderError):shopping_workflow.run_shopping(session())


def test_optional_auth_token_cached_without_exposing_secret(monkeypatch):
    monkeypatch.setenv("SHOPIFY_CLIENT_ID","client")
    monkeypatch.setenv("SHOPIFY_CLIENT_SECRET","secret")
    monkeypatch.setattr(shopify,"_token",("","",0))
    calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,json):
            calls.append(url)
            assert json["grant_type"]=="client_credentials"
            return httpx.Response(200,json={"access_token":"test-token"},request=httpx.Request("POST",url))
    monkeypatch.setattr(shopify.httpx,"Client",Client)
    assert shopify.headers()=={"Authorization":"Bearer test-token"}
    assert shopify.headers()=={"Authorization":"Bearer test-token"} and len(calls)==1


def test_mixed_provider_cart_keeps_simulated_checkout(monkeypatch):
    from app.runtime import cart
    from app.runtime.schemas import CartSelection, CartCheckout
    s=session()
    for index,source in enumerate(["shopify_catalog","browser_use"]):
        p,m=shopify.normalize(row(variant=str(index+1)))[0]
        p.source=source;p.detail_checked=True
        s.live_products[p.id]=p;s.live_merchants[m.id]=m
        service.propose(s,p,recommendations=[p])
        a=s.proposals[-1]
        cart.add(s,CartSelection(proposal_id=a.id,fingerprint=a.fingerprint))
    cart.checkout(s,CartCheckout(items=[CartSelection(proposal_id=i.action.id,fingerprint=i.action.fingerprint) for i in s.cart]))
    assert len(s.receipts)==2 and all(r.status=="simulated" for r in s.receipts)
