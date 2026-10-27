import pytest
from app.runtime import service, cart
from app.runtime.schemas import Session, Fact, Change, Interpretation, CartSelection
from app.runtime.policy import catalogue


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    s = Session(mode="mock", brief={
        "category": Fact(value="Running shoes"), "budget": Fact(value="200", hard=True),
        "size": Fact(value="40"), "features": Fact(value="cushioned", hard=True),
    })
    service.propose(s, next(p for p in catalogue(s) if p.id == "shoe-1"))
    a = s.proposals[-1]
    cart.add(s, CartSelection(proposal_id=a.id, fingerprint=a.fingerprint))
    return s


@pytest.mark.parametrize("text", ["I'm looking for bags too", "those are shoes not bags"])
def test_mock_switch_keeps_cart_not_shoe_preferences(session, text):
    old_cart = session.cart[0].model_dump()
    permissions = session.permissions.model_dump()
    service.chat(session, text)
    assert session.brief["category"].value == "Backpacks"
    assert "budget" not in session.brief and "size" not in session.brief and "features" not in session.brief
    assert session.proposals[-1].product.category == "Backpacks"
    assert session.cart[0].model_dump() == old_cart
    assert session.permissions.model_dump() == permissions


def test_llm_new_task_resets_brief(session, monkeypatch):
    monkeypatch.setattr(service.llm, "interpret", lambda *_: Interpretation(
        reply="Let's find a backpack", intent="new_task", suggestions=[], changes=[
            Change(field="category", value="Backpacks", source="confirmed", hard=False, evidence="bags"),
            Change(field="budget", value="80", source="confirmed", hard=True, evidence="under 80"),
        ]))
    service.chat(session, "Find bags under 80")
    assert session.brief["budget"].value == "80" and "size" not in session.brief
    assert session.cart[0].brief["budget"].value == "200"


def test_same_product_refinement_keeps_constraints(session):
    service.chat(session, "Find cheaper options under $100")
    assert session.brief["category"].value == "Running shoes"
    assert session.brief["budget"].value == "100"
    assert session.brief["size"].value == "40"


def test_ungrounded_switch_does_not_clear_brief(session, monkeypatch):
    monkeypatch.setattr(service.llm, "interpret", lambda *_: Interpretation(
        reply="Explanation", intent="explain", suggestions=[], changes=[
            Change(field="category", value="Backpacks", source="confirmed", hard=False, evidence="not in message"),
        ]))
    service.chat(session, "Explain the current item")
    assert session.brief["category"].value == "Running shoes"
    assert session.brief["budget"].value == "200"


def test_same_category_new_task_only_carries_explicit_values(session, monkeypatch):
    monkeypatch.setattr(service.llm, "interpret", lambda *_: Interpretation(
        reply="Another pair", intent="new_task", suggestions=[], changes=[
            Change(field="category", value="Running shoes", source="confirmed", hard=False, evidence="shoes"),
            Change(field="budget", value="200", source="confirmed", hard=True, evidence="same budget"),
        ]))
    service.chat(session, "Find shoes for my brother with the same budget")
    assert session.brief["budget"].value == "200" and "size" not in session.brief
    assert len(session.cart) == 1
