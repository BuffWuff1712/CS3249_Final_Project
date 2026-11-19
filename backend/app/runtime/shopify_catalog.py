"""Read-only Shopify Global Catalog MCP. No cart, checkout or account tools."""
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import time
from threading import Lock
from urllib.parse import urlparse
import httpx
from .schemas import Product, Merchant, Event, WebEvidence, now
from .search_errors import SearchProviderError
from .progress import cancellable_call, check_cancelled

ENDPOINT = "https://catalog.shopify.com/api/ucp/mcp"
PROFILE = "https://shopify.dev/ucp/agent-profiles/examples/2026-08-25/valid-with-capabilities.json"
ALLOWED = {"search_catalog", "lookup_catalog", "get_product"}
_token_lock = Lock()
_token = ("", "", 0.0)


def error(reason, **kw):
    return SearchProviderError(reason, provider="shopify_catalog", **kw)


def public_url(url):
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None,443):
        raise ValueError("Invalid public product URL")
    if "." not in p.hostname or p.hostname.endswith((".local", ".test")):
        raise ValueError("Not a public host")
    try:
        ipaddress.ip_address(p.hostname)
    except ValueError:
        return url
    raise ValueError("IP addresses are not merchant hosts")


def headers():
    global _token
    client_id = os.getenv("SHOPIFY_CLIENT_ID", "").strip()
    secret = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip()
    if not client_id and not secret:
        return {}  # Anonymous discovery is supported; never send a placeholder token.
    if not client_id or not secret:
        raise error("access")
    key = hashlib.sha256((client_id + secret).encode()).hexdigest()
    with _token_lock:
        if _token[0] != key or time.monotonic() >= _token[2]:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                response = client.post("https://api.shopify.com/auth/access_token", json={
                    "client_id":client_id,"client_secret":secret,"grant_type":"client_credentials"})
                response.raise_for_status()
                token = response.json()["access_token"]
                if not isinstance(token,str) or not token:
                    raise error("access")
                _token = (key,token,time.monotonic()+3000)
        return {"Authorization":"Bearer " + _token[1]}


def classify(exc):
    if isinstance(exc, SearchProviderError): return exc
    if isinstance(exc, BaseExceptionGroup):
        for child in exc.exceptions:
            result = classify(child)
            if result.reason != "invalid_output": return result
    if isinstance(exc, httpx.HTTPStatusError):
        status=exc.response.status_code
        retry=exc.response.headers.get("Retry-After", "")
        retry=int(retry) if retry.isdigit() and len(retry)<=8 else None
        reason="access" if status in (401,403) else "rate_limit" if status==429 else "timeout" if status in (408,504) else "unavailable" if status>=500 else "unknown"
        return error(reason,status=status,retry_after=retry)
    if isinstance(exc,(TimeoutError,httpx.TimeoutException)): return error("timeout")
    if isinstance(exc,httpx.RequestError): return error("unavailable")
    return error("invalid_output")


async def _call(name, catalog, auth_headers, profile, timeout):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import PaginatedRequestParams, ClientRequest, CallToolRequest, CallToolRequestParams, CallToolResult, ContentBlock
    from pydantic import Field
    class CatalogResult(CallToolResult):
        # Shopify returns structuredContent without the otherwise-required content array.
        content: list[ContentBlock] = Field(default_factory=list)
    async with asyncio.timeout(timeout):
        async with streamablehttp_client(ENDPOINT,headers=auth_headers,timeout=timeout,sse_read_timeout=timeout) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                check_cancelled()
                tools=await session.list_tools(params=PaginatedRequestParams(_meta={"ucp-agent":{"profile":profile}}))
                if name not in {tool.name for tool in tools.tools}:
                    raise error("access")
                check_cancelled()
                result=await session.send_request(ClientRequest(CallToolRequest(params=CallToolRequestParams(
                    name=name, arguments={"meta":{"ucp-agent":{"profile":profile}},"catalog":catalog}))), CatalogResult)
                if result.isError:
                    # Tool errors may contain private/raw details; never propagate their text.
                    raise error("failed_run")
                data=result.structuredContent
                if data is None:
                    data=next((json.loads(c.text) for c in result.content if c.type=="text"),None)
                if not isinstance(data,dict): raise error("invalid_output")
                return data


def call(name,catalog):
    if name not in ALLOWED: raise ValueError("Only catalog discovery tools are allowed")
    def work():
        try:
            profile=public_url(os.getenv("SHOPIFY_UCP_PROFILE_URL",PROFILE))
            timeout=float(os.getenv("SHOPIFY_TIMEOUT_SECONDS","30"))
            if not 5<=timeout<=120: raise ValueError("Invalid timeout")
            return asyncio.run(_call(name,catalog,headers(),profile,timeout))
        except Exception as exc:
            from .progress import RequestStopped
            if isinstance(exc,RequestStopped): raise
            raise classify(exc) from None
    return cancellable_call(work)


def context(session):
    currency=session.brief.get("currency")
    return {"address_country":os.getenv("SHOPIFY_MARKET_COUNTRY","SG"),
            "currency":currency.value if currency else "SGD"}


def normalize(row):
    """Each record is one seller/variant, never a product-level from-price."""
    products=[]
    if not isinstance(row,dict) or not isinstance(row.get("variants"),list):
        return products
    for variant in row.get("variants",[]):
        try:
            seller=variant["seller"]
            vid=variant["id"]; shop=seller["id"]
            if not vid.startswith("gid://shopify/ProductVariant/") or not shop.startswith("gid://shopify/Shop/"):
                continue
            url=public_url(variant.get("url") or row.get("url", ""))
            site=public_url(seller["url"])
            if urlparse(url).hostname != urlparse(site).hostname: continue
            # Never expose a returned checkout/cart permalink as a product link.
            if re.search(r"/(cart|checkout)(/|$)",urlparse(url).path): continue
            price=variant["price"]
            amount=price["amount"]
            if isinstance(amount,bool) or not isinstance(amount,int) or amount<=0 or price["currency"] not in ("SGD","USD"): continue
            if variant.get("requires",{}).get("selling_plan") or variant.get("requires",{}).get("components"): continue
            available=variant.get("availability",{}).get("available") is True
            options=variant.get("options",[])
            description=row.get("description",{})
            text=re.sub("<[^>]+>"," ",description.get("plain") or description.get("html",""))
            pid="shopify-"+hashlib.sha256((shop+vid).encode()).hexdigest()[:24]
            mid="shopify-"+hashlib.sha256(shop.encode()).hexdigest()[:16]
            category=next((c["value"] for c in row.get("categories",[]) if c.get("taxonomy")=="merchant"),"Unknown")
            inferred=[str(x) for x in row.get("metadata",{}).get("top_features",[])][:20]
            from .product_images import select_image
            img,alt=select_image(variant,row)
            p=Product(image_url=img,image_alt=alt,id=pid,name=row["title"]+" · "+variant.get("title",vid.rsplit("/",1)[-1]),
                category=category,brand="",price=amount/100,currency=price["currency"],merchant=seller["name"],merchant_id=mid,
                source="shopify_catalog",source_url=url,observed_at=now(),stock=available,trust="unverified",
                attributes=[],sizes=[],description=text[:2000],inferred_attributes=inferred,
                specifications={o["name"]:o["label"] for o in options},
                provider_ids={"product":row["id"],"variant":vid,"shop":shop},web_evidence=WebEvidence())
            m=Merchant(id=mid,name=seller["name"],website=site,description="Shopify catalog seller; identity and policies need review.",
                payment_methods=["Demo Visa","Demo Wallet"],return_policy="Unknown; check the merchant.",
                contact="",review_count=0,verified_business=False,requested_information=[])
            products.append((p,m))
        except (ValueError,TypeError,KeyError,AttributeError):
            continue
    return products


def discover(session,query=""):
    ctx=context(session)
    catalog={"query":"; ".join([query,*[k+": "+f.value for k,f in session.brief.items()]]),
             "context":ctx,"filters":{"available":True,"ships_to":{"country":ctx["address_country"]}},
             "pagination":{"limit":10}}
    budget=session.brief.get("budget")
    if budget and budget.hard:
        from decimal import Decimal
        catalog["filters"]["price"]={"max":int(Decimal(budget.value)*100)}
    data=call("search_catalog",catalog)
    if not isinstance(data.get("products"),list): raise error("invalid_output")
    ids=[]
    for row in data["products"]:
        for p,m in normalize(row):
            session.live_products[p.id]=p;session.live_merchants[m.id]=m
            if p.id not in ids: ids.append(p.id)
    if data["products"] and not ids: raise error("invalid_output")
    session.events.append(Event(kind="shopify_search",detail=json.dumps({"product_ids":ids})))
    return ids


def details(session,product):
    data=call("get_product",{"id":product.provider_ids["variant"],"context":context(session)})
    row=data.get("product")
    if not isinstance(row,dict): raise error("invalid_output")
    for fresh,merchant in normalize(row):
        if fresh.id==product.id and fresh.provider_ids["variant"]==product.provider_ids["variant"]:
            fresh.detail_checked=True
            session.live_products[fresh.id]=fresh;session.live_merchants[merchant.id]=merchant
            return fresh
    raise error("invalid_output")
