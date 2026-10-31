import pytest
from app.runtime import llm, service
from app.runtime.schemas import Session, Fact, Interpretation, Change, ClarificationAnswer


def result(intent="search", changes=None, answers=None):
    return Interpretation(intent=intent, reply="I'll look for shoes. Let's get started.",
                          changes=changes or [], clarification_answers=answers or [], suggestions=[])


def test_repairs_ellipsized_evidence_once(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    s = Session(brief={"category": Fact(value="Running shoes"), "budget": Fact(value="200")})
    text = "ideally there is extra cushioning in the soles and it should be durable for both road and dirt"
    invalid = Change(field="features", value="cushioned", source="confirmed", hard=False,
                     evidence="extra cushioning... durable for both road and dirt")
    valid = invalid.model_copy(update={"evidence": "extra cushioning"})
    calls = []
    def call(schema, instructions, payload):
        calls.append(payload)
        return result(changes=[invalid if len(calls) == 1 else valid])
    monkeypatch.setattr(llm, "structured_call", call)
    parsed = llm.OpenAIConversation().interpret(s, text)
    assert len(calls) == 2 and calls[1]["validation_feedback"]
    assert parsed.changes[0].evidence == "extra cushioning"


def test_provided_category_without_change_triggers_repair(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    calls = []
    def call(*args):
        calls.append(args)
        return result("clarify", answers=[ClarificationAnswer(field="product_type", status="provided", evidence="running shoes")])
    monkeypatch.setattr(llm, "structured_call", call)
    s = Session()
    service.chat(s, "help me find running shoes")
    assert len(calls) == 2  # A malformed retry cannot create an unbounded loop.
    assert s.stage == "clarifying" and not s.proposals
    assert "type of product" in s.messages[-1].text
    assert "product_type" not in s.clarification_answers


@pytest.mark.parametrize("intent", ["respond", "search", "clarify"])
def test_unsure_resumes_pending_search_instead_of_only_promising(monkeypatch, intent):
    s = Session(mode="mock", stage="clarifying", brief={
        "category": Fact(value="Running shoes"), "budget": Fact(value="200", hard=True)},
        clarification_asked=["features"], clarification_answers={"product_type": "provided", "budget": "provided"})
    monkeypatch.setattr(service.llm, "interpret", lambda *_: result(intent))
    service.chat(s, "Im unsure")
    assert s.proposals
    assert any(e.kind == "shopping_tool" for e in s.events)
    assert s.messages[-1].text != "I'll look for shoes. Let's get started."


def test_unknown_does_not_remove_existing_features(monkeypatch):
    s = Session(mode="mock", brief={"category": Fact(value="Running shoes"),
        "budget": Fact(value="200", hard=True), "features": Fact(value="cushioned", hard=False)})
    monkeypatch.setattr(service.llm, "interpret", lambda *_: result(changes=[
        Change(field="features", value=None, source="confirmed", hard=False, evidence="Im unsure")],
        answers=[ClarificationAnswer(field="features", status="unknown", evidence="Im unsure")]))
    service.chat(s, "Im unsure")
    assert s.brief["features"].value == "cushioned"


def test_corrupt_old_readiness_flags_do_not_allow_fake_search(monkeypatch):
    s = Session(brief={"budget": Fact(value="200")}, clarification_asked=["budget", "features"],
                clarification_answers={"product_type": "provided", "budget": "provided", "features": "unknown"})
    monkeypatch.setattr(service.llm, "interpret", lambda *_: result())
    monkeypatch.setattr(service, "run_shopping", lambda *_: pytest.fail("No category to search"))
    service.chat(s, "Im unsure")
    assert s.stage == "clarifying" and "type of product" in s.messages[-1].text
