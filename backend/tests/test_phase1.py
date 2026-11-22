"""Phase 1 contracts: structured conversation, bounded screening, no paid calls."""
import json
from threading import Event as Signal
import pytest
from app.runtime import service, shopping_workflow as workflow, shopping_tools as tools, policy, shop_workspace
from app.runtime.schemas import Session, Fact, Interpretation, Change
from app.runtime.progress import cancellation, RequestStopped


def interpretation(intent="respond", changes=None, control="unchanged", **kwargs):
    return Interpretation(intent=intent, reply="Let's work out what you need.", changes=changes or [],
                          suggestions=[], search_control=control, **kwargs)


def change(field, value, operation="set"):
    return Change(field=field, value=value, evidence=value or "remove", source="confirmed", hard=True, operation=operation)


def test_exploration_saves_adds_removes_then_searches(monkeypatch):
    s = Session(mode="mock")
    turns = [interpretation(changes=[change("category", "Headphones")], control="defer"),
             interpretation(changes=[change("budget", "200")]),
             interpretation(changes=[change("features", "wireless")]),
             interpretation(changes=[change("features", "lightweight", "add")]),
             interpretation(changes=[change("features", "wireless", "remove")]),
             interpretation("search", control="request")]
    calls = []
    monkeypatch.setattr(service.llm, "interpret", lambda *_: turns.pop(0))
    monkeypatch.setattr(service, "run_shopping", lambda s: calls.append(s.brief.copy()) or workflow.ShoppingResult(status="no_match"))
    for text in ["Headphones; don't search yet", "200", "wireless", "lightweight", "remove wireless"]:
        service.chat(s, text)
        assert not calls and not s.proposals
    assert s.brief["features"].value == "lightweight" and s.brief["features"].hard
    service.chat(s, "Okay now show options")
    assert len(calls) == 1 and calls[0]["budget"].value == "200"


def test_complete_clarification_is_not_automatic_search(monkeypatch):
    s = Session(search_requested=True, brief={k: Fact(value=v) for k,v in
                {"category":"Headphones", "budget":"200", "features":"wireless"}.items()})
    monkeypatch.setattr(service.llm, "interpret", lambda *_: interpretation("clarify"))
    monkeypatch.setattr(service, "run_shopping", lambda *_: pytest.fail("Clarify is not search"))
    service.chat(s, "What is wireless?")
    assert s.stage == "clarifying" and not s.proposals


def test_deferral_overrides_search_label_and_uncertainty(monkeypatch):
    s = Session(search_requested=True, stage="clarifying", clarification_asked=["features"],
                brief={"category":Fact(value="Headphones"), "budget":Fact(value="200")})
    monkeypatch.setattr(service.llm, "interpret", lambda *_: interpretation("search", control="defer"))
    monkeypatch.setattr(service, "run_shopping", lambda *_: pytest.fail("Explicit deferral wins"))
    service.chat(s, "Im unsure")
    assert not s.search_requested and not s.proposals


def test_ungrounded_new_task_does_not_destroy_brief(monkeypatch):
    s = Session(brief={"category":Fact(value="Headphones"),"budget":Fact(value="200",hard=True)})
    before = s.brief.copy()
    monkeypatch.setattr(service.llm, "interpret", lambda *_: interpretation("new_task", changes=[change("category","Shoes")]))
    service.chat(s, "Tell me more")
    assert s.brief == before and not s.proposals


def test_change_invalidates_pending_without_search(monkeypatch):
    s = Session(mode="mock",brief={"category":Fact(value="Headphones"),"budget":Fact(value="200")})
    service.propose(s)
    old = s.proposals[-1]
    monkeypatch.setattr(service.llm, "interpret", lambda *_: interpretation(changes=[change("budget","100")],control="defer"))
    monkeypatch.setattr(service,"run_shopping",lambda *_: pytest.fail("No search"))
    service.chat(s,"Set budget 100; don't search")
    assert old.status == "superseded" and not s.recommendations and not s.receipts


def test_cancellation_stops_before_discovery(monkeypatch):
    signal=Signal();signal.set()
    monkeypatch.setattr(workflow,"search_products",lambda *_: pytest.fail("Cancelled"))
    with pytest.raises(RequestStopped), cancellation(signal):
        workflow.run_shopping(Session())


def test_screening_skips_bad_candidates_and_caps_output(monkeypatch):
    s=Session(mode="mock",brief={"category":Fact(value="Headphones")})
    base=policy.search(s,limit=None)[0]
    products=[base.model_copy(update={"id":str(i),"name":f"Model {i}","price":float(i),"description":"same"}) for i in range(9)]
    products.insert(1,products[0].model_copy(update={"id":"duplicate"}))
    monkeypatch.setattr(policy,"search",lambda *_ ,**kw:products)
    inspected=[]
    def inspect(s,p):
        inspected.append(p.id)
        return None if p.id in ("0","1") else p
    monkeypatch.setattr(tools,"screen_candidate",inspect)
    found=tools.screen_candidates(s,[p.id for p in products])
    assert [p.id for p in found]==["2","3","4"]
    assert inspected==["0","1","2","3","4"] and "duplicate" not in inspected
    monkeypatch.setitem(policy.CONFIG,"screening_budget",3)
    assert len(tools.screen_candidates(s,[p.id for p in products]))==1
    shop_workspace.adopt(s);s.recommendations=found
    assert len(shop_workspace.current_candidates(s))==3


def test_query_only_uses_confirmed_preferences():
    s=Session(search_provider="hybrid",brief={"category":Fact(value="Lamps"),"features":Fact(value="adjustable"),
                "budget":Fact(value="100",source="suggested")})
    assert workflow.search_query(s)=="category: Lamps; features: adjustable"


def test_live_shape_single_product_calls_and_cache(monkeypatch, caplog):
    from collections import Counter
    from time import perf_counter
    import logging
    from app.runtime import gateway, llm, risk_agent, shopify_catalog
    from test_shopify_catalog import row
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    s=Session(mode="openai",search_provider="shopify_catalog")
    for i in range(7):
        p,m=shopify_catalog.normalize(row(variant=str(i)))[0]
        p.provider_ids["product"] += str(i)
        p.name=f"Desk lamp {i}"
        p.attributes=["adjustable"]
        p.detail_checked=True
        s.live_products[p.id]=p;s.live_merchants[m.id]=m
    counts=Counter()
    def call(schema,*_):
        counts[schema.__name__]+=1
        if schema.__name__=="Interpretation":
            return interpretation("search",[change("category","Desk lamp"),change("budget","200"),change("features","adjustable")],"request")
        if schema.__name__=="Assessment":return schema(status="match",evidence="Desk lamp")
        if schema.__name__=="Review":return schema(findings=[])
        if schema.__name__=="OutcomeExplanation":return schema(explanation="Here are three options to review. Checkout is simulated.")
        pytest.fail(f"Unexpected LLM schema: {schema.__name__}")
    monkeypatch.setattr(gateway,"structured_call",call)
    monkeypatch.setattr(llm,"structured_call",call)
    monkeypatch.setattr(risk_agent,"structured_call",call)
    monkeypatch.setattr(workflow,"search_products",lambda *_:list(s.live_products.values()))
    caplog.set_level(logging.INFO,logger="uvicorn.error")
    start=perf_counter();service.chat(s,"Desk lamp under 200 with adjustable lighting");elapsed=perf_counter()-start
    assert counts=={"Interpretation":1,"Assessment":3,"Review":3,"OutcomeExplanation":1}
    assert len(s.recommendations)==3 and s.proposals[-1].decision=="REVIEW" and not s.receipts
    before=counts.copy();workflow.run_shopping(s)
    assert counts==before
    assert '"cache": "hit"' in caplog.text
    print(json.dumps({"fixture":"seven distinct lamps, offline model stubs", "latency_s":round(elapsed,4),
                      "model_stub_calls":dict(counts),"retrieved":7,"inspected":3,"returned":3,
                      "repeat_new_assessments":0,"tokens":None,"live_llm_time_s":None}))


def test_offline_mock_understands_explicit_deferral(monkeypatch):
    s=Session(mode="mock")
    monkeypatch.setattr(service,"run_shopping",lambda *_:pytest.fail("Deferred"))
    service.chat(s,"Headphones under 200, wireless; don't search yet")
    assert s.brief["category"].value=="Headphones" and not s.search_requested
    assert not s.proposals


def test_changed_snapshot_stops_without_proposal(monkeypatch):
    s=Session(mode="mock",brief={"category":Fact(value="Headphones")})
    product=policy.search(s,limit=None)[0]
    monkeypatch.setattr(workflow,"search_products",lambda *_:[product])
    monkeypatch.setattr(workflow,"screen_candidates",lambda *_:[product.model_copy(update={"price":product.price+1})])
    outcome=workflow.run_shopping(s)
    assert outcome.status=="stopped" and not outcome.candidates and outcome.product is None
