import pytest

from app.runtime import cart, service
from app.runtime.schemas import CartSelection, Change, Fact, Interpretation, Session


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    s = Session(mode="mock", brief={
        "category": Fact(value="Headphones", source="confirmed"),
        "budget": Fact(value="200", source="confirmed", hard=True),
    })
    service.propose(s)
    return s


@pytest.mark.parametrize("text", ["Hello", "hi", "Hey!", "Thanks"])
@pytest.mark.parametrize("carted", [False, True])
def test_small_talk_preserves_shopping_state(session, monkeypatch, text, carted):
    if carted:
        a = session.proposals[-1]
        cart.add(session, CartSelection(proposal_id=a.id, fingerprint=a.fingerprint))
    before = session.model_dump(exclude={"messages", "events"})
    def unexpected_search(*args):
        pytest.fail("Conversation must not search")
    monkeypatch.setattr(service, "run_shopping", unexpected_search)
    service.chat(session, text)
    assert session.model_dump(exclude={"messages", "events"}) == before
    assert "require approval" not in session.messages[-1].text
    assert session.events[-1].kind == "interpretation"


@pytest.mark.parametrize("intent", ["respond", "explain"])
def test_conversation_uses_reply_and_ignores_proposed_edits(session, monkeypatch, intent):
    before = session.model_dump(exclude={"messages", "events"})
    monkeypatch.setattr(service.llm, "interpret", lambda *_: Interpretation(
        intent=intent, reply="You can review your items before confirming simulated checkout.",
        changes=[Change(field="budget", value="500", source="confirmed", hard=True, evidence="500")],
        suggestions=[],
    ))
    service.chat(session, "Explain how a budget of 500 works")
    assert session.messages[-1].text == "You can review your items before confirming simulated checkout."
    assert session.model_dump(exclude={"messages", "events"}) == before


def test_greeting_with_shopping_request_still_searches(session):
    service.chat(session, "Hi, find backpacks under $100")
    assert session.brief["category"].value == "Backpacks"
    assert session.proposals[-1].product.category == "Backpacks"


def test_explain_does_not_reuse_superseded_proposal(session):
    service.invalidate(session)
    service.chat(session, "Explain")
    assert session.messages[-1].text == "What would you like me to explain?"
