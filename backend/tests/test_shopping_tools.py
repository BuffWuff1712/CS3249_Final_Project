"""Offline checks for the shopping boundary, tool loop and service integration."""
import json
import pytest
from app.runtime import service, shopping_workflow as workflow
from app.runtime.schemas import Session, Fact, Interpretation, Decision
from app.runtime.shopping_tools import search_products, get_product_details


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    return Session(mode="mock", brief={
        "category": Fact(value="Headphones"),
        "budget": Fact(value="150", hard=True),
    })


def steps(*items):
    pending = iter(items)
    return lambda *_: next(pending)


def step(action, query="", product_id=""):
    return workflow.ShoppingStep(action=action, query=query, product_id=product_id)


def test_tools_preserve_constraints_and_exclusions(session):
    before = session.model_dump()
    found = search_products(session)
    assert found and all(p.price <= 150 for p in found)
    assert session.model_dump() == before
    session.rejected_merchants.append(found[0].merchant_id)
    assert all(p.merchant_id != found[0].merchant_id for p in search_products(session))
    with pytest.raises(ValueError):
        get_product_details(session, found[0].id)


def test_refinement_inspection_then_proposal(session):
    p = search_products(session)[0]
    before = session.brief.copy()
    result = workflow.run_shopping(session, steps(
        step("search_products", "nonexistentkeyword"),
        step("search_products"),
        step("get_product_details", product_id=p.id),
        step("propose", product_id=p.id),
    ))
    assert result.product.id == p.id and result.status == "proposed"
    assert session.brief == before and not session.receipts and not session.proposals
    assert [json.loads(e.detail)["action"] for e in session.events] == [
        "search_products", "search_products", "get_product_details", "propose"]


@pytest.mark.parametrize("action", ["propose", "get_product_details"])
def test_cannot_invent_or_skip_search(session, action):
    result = workflow.run_shopping(session, steps(step(action, product_id="audio-1")))
    assert result.status == "stopped" and result.product is None


def test_cannot_propose_without_inspection(session):
    p = search_products(session)[0]
    result = workflow.run_shopping(session, steps(
        step("search_products"), step("propose", product_id=p.id)))
    assert result.product is None


def test_search_budget(session):
    calls = []
    def repeat(*_):
        calls.append(1)
        return step("search_products")
    assert workflow.run_shopping(session, repeat).status == "stopped"
    assert len(calls) == 3


def test_step_budget(session):
    p = search_products(session)[0]
    calls = []
    def repeat(*_):
        calls.append(1)
        return step("search_products") if len(calls) == 1 else step(
            "get_product_details", product_id=p.id)
    assert workflow.run_shopping(session, repeat).status == "stopped"
    assert len(calls) == workflow.MAX_STEPS


def test_unavailable_model_does_not_fallback_to_selection(session):
    def unavailable(*_):
        raise workflow.LLMError("provider failure")
    assert workflow.run_shopping(session, unavailable).product is None
    assert not session.receipts


def test_no_match_does_not_relax_budget(session):
    session.brief["budget"] = Fact(value="0.01", hard=True)
    result = workflow.run_shopping(session)
    assert result.status == "no_match" and session.brief["budget"].value == "0.01"


def test_chat_one_reply_policy_and_exact_approval(session):
    service.chat(session, "Find headphones under $150; no feature preference")
    assert len([m for m in session.messages if m.role == "assistant"]) == 1
    assert session.proposals and not session.receipts
    a = session.proposals[-1]
    assert a.rules and a.fingerprint and a.decision in ("REVIEW", "BLOCK")
    assert any(e.kind == "shopping_tool" for e in session.events)


def test_failed_run_invalidates_previous_proposal(session, monkeypatch):
    service.chat(session, "Find headphones under $150; no feature preference")
    old = session.proposals[-1]
    monkeypatch.setattr(service.llm, "interpret", lambda *_: Interpretation(
        reply="Searching", changes=[], intent="search", suggestions=[]))
    monkeypatch.setattr(workflow, "choose_step", lambda *_: step("propose", product_id="invented"))
    service.chat(session, "Try again")
    assert old.status == "superseded" and not session.receipts
    assert len(session.proposals) == 1 and session.stage == "ready"


def test_planner_payload_excludes_hidden_research_labels(session, monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    session.experiment = {"secret_label": "MALICIOUS"}
    captured = {}
    def fake(schema, instructions, payload):
        captured.update(payload)
        return step("stop")
    monkeypatch.setattr(workflow, "structured_call", fake)
    workflow.choose_step(session, [])
    assert "MALICIOUS" not in json.dumps(captured)
    assert set(captured) == {"brief", "tool_results", "steps_remaining"}


def test_injection_offer_still_blocked_after_agent_selection(session, monkeypatch):
    session.scenario_id = "risk-f"
    assert "offer-injection" in {p.id for p in search_products(session)}
    monkeypatch.setattr(workflow, "choose_step", steps(
        step("search_products"),
        step("get_product_details", product_id="offer-injection"),
        step("propose", product_id="offer-injection"),
    ))
    service.chat(session, "Find headphones under $150; no feature preference")
    a = session.proposals[-1]
    assert a.decision == "BLOCK" and session.stage == "blocked"
    with pytest.raises(ValueError):
        service.decide(session, a.id, Decision(action="approve", fingerprint=a.fingerprint))
    assert not session.receipts
    with pytest.raises(ValueError):
        get_product_details(session, "study-hp-target-trusted")


def test_search_vocabulary_lists_catalogue_spellings(session):
    from app.runtime.shopping_tools import search_vocabulary
    vocab = search_vocabulary(session)
    assert set(vocab) == {"Backpacks", "Headphones", "Running shoes"}
    assert "noise-cancelling" in vocab["Headphones"]["features"]
    assert "water-resistant" in vocab["Backpacks"]["features"]
    assert "42" in vocab["Running shoes"]["sizes"] and not vocab["Headphones"]["sizes"]


def test_search_vocabulary_follows_scenario_scope(session):
    from app.runtime.shopping_tools import search_vocabulary
    session.scenario_id = "site-reputation"
    vocab = search_vocabulary(session)
    assert set(vocab) == {"Headphones"}
    assert "study" not in vocab["Headphones"]["features"]  # Old-fixture tag outside the scenario.


def test_search_vocabulary_is_empty_for_open_web_search(session):
    from app.runtime.shopping_tools import search_vocabulary
    session.search_provider = "browser_use"
    assert search_vocabulary(session) == {}


def test_interpreter_receives_search_vocabulary(session, monkeypatch):
    from app.runtime import llm
    from app.runtime.shopping_tools import search_vocabulary
    captured = {}
    def fake(schema, prompt, payload):
        captured.update(payload, prompt=prompt)
        return Interpretation(reply="Which budget?", changes=[], intent="clarify", suggestions=[])
    monkeypatch.setattr(llm, "structured_call", fake)
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    llm.OpenAIConversation().interpret(session, "noise cancelling headphones")
    assert captured["search_vocabulary"] == search_vocabulary(session)
    assert "search_vocabulary" in captured["prompt"]


def test_edit_maps_feature_spelling_to_listed_vocabulary(session):
    session.scenario_id = "site-reputation"
    service.edit(session, "features", Fact(value="Noise Cancelling, wireless, university", source="confirmed", hard=True))
    assert session.brief["features"].value == "noise-cancelling, wireless, university"
    assert session.brief["features"].hard  # Only spelling changes; strength is untouched.


def test_edit_keeps_a_spelling_that_is_already_listed(session):
    # The unscoped catalogue lists both spellings; an exact listing is never rewritten.
    service.edit(session, "features", Fact(value="noise cancelling", source="confirmed"))
    assert session.brief["features"].value == "noise cancelling"


def test_edit_strips_eu_prefix_from_listed_sizes(session):
    for typed, saved in [("EU 42", "42"), ("eu42", "42"), ("42", "42"), ("US 9", "US 9")]:
        service.edit(session, "size", Fact(value=typed, source="confirmed", hard=True))
        assert session.brief["size"].value == saved


def test_edit_leaves_open_web_terms_unchanged(session):
    session.search_provider = "browser_use"
    service.edit(session, "features", Fact(value="Noise Cancelling", source="confirmed"))
    assert session.brief["features"].value == "Noise Cancelling"
