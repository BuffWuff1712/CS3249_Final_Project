import json
import httpx
import pytest
from app.runtime import service, llm, browser_search as browser, relevance, policy
from app.runtime.schemas import Session, Fact, Change, Interpretation, Message, Event
from app.runtime.preferences import apply_change, grounded_change
from app.runtime.search_errors import SearchProviderError, provider_reason, USER_MESSAGE
from app.runtime.shopping_workflow import ShoppingResult
from test_browser_search import listing, RUN


def change(field="features", value="over-ear", operation="add", **kw):
    return Change(field=field, value=value, operation=operation, source="confirmed", hard=False, evidence=value or "clear", **kw)


def test_add_remove_preserves_constraints():
    old = Fact(value="wireless, noise-cancelling", hard=True)
    c = change()
    result = apply_change(old, c, Fact(value=c.value))
    assert result.value == "wireless, noise-cancelling, over-ear" and result.hard
    assert apply_change(result, change(value="wireless", operation="remove"), None).value == "noise-cancelling, over-ear"
    assert apply_change(result, change(value="wired", operation="set"), Fact(value="wired")).value == "wired"


@pytest.mark.parametrize("category", ["Coffee machine", "Desk lamp", "Suitcase", "Halloween decorations"])
def test_arbitrary_category_reaches_search(monkeypatch, category):
    s = Session(search_provider="browser_use")
    interpretation = Interpretation(
        intent="search", reply="Searching", suggestions=[], changes=[
            change(field="category", value=category, operation="set"),
            change(field="budget", value="200", operation="set"),
            change(value="durable")])
    monkeypatch.setattr(service.llm, "interpret", lambda *_: interpretation)
    seen=[]
    monkeypatch.setattr(service, "run_shopping", lambda state: seen.append(state.brief.copy()) or ShoppingResult(status="no_match"))
    service.chat(s, category + " under 200 durable")
    assert len(seen)==1 and seen[0]["category"].value==category


def test_recover_missing_category_from_current_user_only(monkeypatch):
    s=Session(messages=[Message(role="user",text="wireless headphones"), Message(role="assistant",text="What style?")],
              brief={"features":Fact(value="wireless"), "budget":Fact(value="200")})
    c=change(field="category",value="headphones",operation="set",evidence_message_index=0)
    assert grounded_change(s,c,"over-ear")
    assert not grounded_change(s,c,"over-ear",allow_history=False)
    s.task_start_message=1
    assert not grounded_change(s,c,"over-ear")
    s.task_start_message=None
    s.events.append(Event(kind="brief_reset",detail="legacy reset"))
    assert not grounded_change(s,c,"over-ear")


def test_refinement_does_not_reset_budget(monkeypatch):
    s=Session(brief={"category":Fact(value="shoes"),"budget":Fact(value="200"),"features":Fact(value="cushioned")})
    monkeypatch.setattr(service.llm,"interpret",lambda *_: Interpretation(intent="search",reply="Search",suggestions=[],changes=[change(field="category",value="running shoes",operation="set")]))
    monkeypatch.setattr(service,"run_shopping",lambda *_: ShoppingResult(status="no_match"))
    service.chat(s,"running shoes")
    assert s.brief["budget"].value=="200" and s.brief["features"].value=="cushioned"


@pytest.mark.parametrize("status,data,reason",[(402,{},"unknown"),(401,{},"access"),(403,{},"access"),(429,{},"rate_limit"),(504,{},"timeout"),(503,{},"unavailable"),(400,{"error":{"code":"insufficient_credits"}},"credits"),(500,{"message":"credits maybe"},"unavailable")])
def test_provider_error_classification(monkeypatch,status,data,reason):
    monkeypatch.setenv("BROWSER_USE_API_KEY","secret")
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS","shop.example")
    calls=[]
    def handle(req):
        calls.append(req)
        return httpx.Response(status,json=data)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SearchProviderError) as caught:
            browser.run_task({},"",client=client)
    assert caught.value.reason==reason and len(calls)==1
    assert "secret" not in str(caught.value)


def test_failure_is_one_saved_response_not_no_match(monkeypatch,caplog):
    s=Session(search_provider="browser_use",brief={"category":Fact(value="lamp"),"budget":Fact(value="200"),"features":Fact(value="adjustable")})
    monkeypatch.setattr(service.llm,"interpret",lambda *_: Interpretation(intent="search",reply="Searching",changes=[],suggestions=[]))
    def fail(*_): raise SearchProviderError("credits",402,RUN)
    monkeypatch.setattr(service,"run_shopping",fail)
    service.chat(s,"Find a lamp")
    assert s.messages[-1].text==USER_MESSAGE and len(s.messages)==2
    assert s.brief["category"].value=="lamp" and s.stage=="ready" and not s.proposals
    assert s.events[-1].kind in ("search_failure","assistant_message")
    assert "top up" in caplog.text and "Find a lamp" not in caplog.text


@pytest.mark.parametrize("assessment",["match","mismatch","unknown"])
def test_relevance_bound_to_snapshot_and_request(monkeypatch,assessment):
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS","shop.example")
    monkeypatch.setattr(browser,"run_task",lambda *_:(RUN,browser.SearchOutput(products=[browser.Listing(**listing(observed_type="Desk lamp",type_evidence="Adjustable desk lamp"))])))
    s=Session(search_provider="browser_use",brief={"category":Fact(value="Lighting")})
    browser.discover(s,"")
    p=next(iter(s.live_products.values()))
    assert p.category=="Desk lamp"  # Never assigned Lighting from request.
    monkeypatch.setenv("BEANY_LLM_MODE","openai")
    from app.runtime import gateway
    monkeypatch.setattr(gateway,"structured_call",lambda *_:relevance.Assessment(status=assessment,evidence="Adjustable desk lamp"))
    relevance.inspect(s,p)
    assert relevance.status(s,p)==assessment
    assert (p in policy.search(s)) == (assessment!="mismatch")
    s.brief["category"]=Fact(value="Coffee machine")
    assert relevance.status(s,p)=="unknown"
    p.price=26
    assert relevance.status(s,p)=="unknown"


def test_unquoted_assessment_cannot_confirm_match(monkeypatch):
    from app.runtime.schemas import Product
    p=Product(id="x",name="Lamp",category="Lamp",brand="X",price=20,merchant="X",attributes=[],description="Lamp",source="browser_use")
    s=Session(search_provider="browser_use")
    from app.runtime import gateway
    monkeypatch.setenv("BEANY_LLM_MODE","openai")
    monkeypatch.setattr(gateway,"structured_call",lambda *_:relevance.Assessment(status="match",evidence="invented"))
    relevance.inspect(s,p)
    assert relevance.status(s,p)=="unknown"


def test_stream_provider_failure_commits_chat_and_unavailable_progress(monkeypatch):
    import asyncio
    from app import shop as api
    from app.runtime import shop_workspace, storage
    s=shop_workspace.create()
    s.search_provider="browser_use"
    s.brief={"category":Fact(value="Desk lamp"),"budget":Fact(value="200"),"features":Fact(value="adjustable")}
    storage.save(s)
    monkeypatch.setattr(service.llm,"interpret",lambda *_: Interpretation(intent="search",reply="Search",changes=[],suggestions=[]))
    def fail(*_): raise SearchProviderError("credits",402)
    monkeypatch.setattr(browser,"run_task",fail)
    response=api.message_stream(s.id,api.Message(revision=0,text="Find my lamp"))
    async def read(): return [json.loads(chunk) async for chunk in response.body_iterator]
    events=asyncio.run(read())
    assert not any(e["type"]=="error" for e in events)
    assert any(e.get("activity",{}).get("state")=="unavailable" for e in events)
    view=next(e["view"] for e in events if e["type"]=="result")
    assert view["revision"]==1 and view["current"] is None
    saved=storage.load(s.id)
    assert saved.messages[-1].text==USER_MESSAGE and saved.brief["category"].value=="Desk lamp"


@pytest.mark.parametrize("mode,reason",[("failed","failed_run"),("invalid","invalid_output"),("network","unavailable"),("timeout","timeout")])
def test_transport_and_run_failure_reasons(monkeypatch,mode,reason):
    monkeypatch.setenv("BROWSER_USE_API_KEY","secret")
    monkeypatch.setenv("BROWSER_USE_ALLOWED_DOMAINS","shop.example")
    def handler(req):
        if mode=="network": raise httpx.ConnectError("secret",request=req)
        if mode=="timeout": raise httpx.ReadTimeout("secret",request=req)
        if req.method=="POST": return httpx.Response(200,json={"id":RUN})
        return httpx.Response(200,json={"status":"failed"} if mode=="failed" else {"status":"completed","output":{"bad":"secret"}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SearchProviderError) as caught: browser.run_task({},"",client=client)
    assert caught.value.reason==reason and "secret" not in str(caught.value)


def test_unsure_retains_valid_recovered_family(monkeypatch):
    s=Session(stage="clarifying",messages=[Message(role="user",text="Find a coffee machine")],
              brief={"budget":Fact(value="200")},clarification_asked=["product_type","features"])
    c=change(field="category",value="coffee machine",operation="set",evidence_message_index=0)
    monkeypatch.setattr(service.llm,"interpret",lambda *_:Interpretation(intent="search",reply="Search",changes=[c],suggestions=[]))
    calls=[]
    monkeypatch.setattr(service,"run_shopping",lambda state:calls.append(state.brief.copy()) or ShoppingResult(status="no_match"))
    service.chat(s,"Im unsure")
    assert calls and calls[0]["category"].value=="coffee machine"
