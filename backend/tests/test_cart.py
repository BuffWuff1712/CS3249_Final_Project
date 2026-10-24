import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.runtime import service, cart
from app.runtime.schemas import Session, Fact, CartSelection, CartCheckout
from app.runtime.policy import catalogue


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    s = Session(mode="mock", brief={"category": Fact(value="Headphones"), "budget": Fact(value="150", hard=True)})
    service.propose(s, next(p for p in catalogue(s) if p.id == "audio-1"))
    return s


def select(s):
    a = s.proposals[-1]
    return CartSelection(proposal_id=a.id, fingerprint=a.fingerprint)


def test_add_persists_without_purchasing_and_survives_search(session):
    chosen = select(session)
    cart.add(session, chosen)
    cart.add(session, chosen)
    service.edit(session, "category", Fact(value="Backpacks"))
    assert len(session.cart) == 1 and not session.receipts
    cart.checkout(session, CartCheckout(items=[chosen]))
    assert len(session.receipts) == 1 and not session.cart
    cart.checkout(session, CartCheckout(items=[chosen]))
    assert len(session.receipts) == 1


def test_rechecks_permissions(session):
    chosen = select(session)
    cart.add(session, chosen)
    session.permissions.restricted_merchants = [session.proposals[-1].product.merchant]
    assert cart.review(session)[0]["error"]
    with pytest.raises(ValueError):
        cart.checkout(session, CartCheckout(items=[chosen]))
    assert not session.receipts and not session.approvals


def test_checkout_chat_only_invites_review(session):
    cart.add(session, select(session))
    service.chat(session, "I'm ready to check out")
    assert session.stage == "cart_review"
    assert not session.receipts and not session.approvals
    assert "Review cart and checkout" in session.messages[-1].text


def test_checkout_multiple_categories_together(session):
    first = select(session)
    cart.add(session, first)
    service.edit(session, "category", Fact(value="Backpacks"))
    product = next(p for p in catalogue(session) if p.category == "Backpacks" and p.merchant_id == "demo-store" and p.price <= 150)
    service.propose(session, product)
    second = select(session)
    cart.add(session, second)
    cart.checkout(session, CartCheckout(items=[first, second]))
    assert len(session.receipts) == 2 and not session.cart
    assert {r.product.category for r in session.receipts} == {"Headphones", "Backpacks"}


def test_atomic_and_fingerprint_bound(session):
    chosen = select(session)
    cart.add(session, chosen)
    with pytest.raises(ValueError):
        cart.checkout(session, CartCheckout(items=[chosen, CartSelection(proposal_id="invented", fingerprint="x")]))
    assert not session.receipts and len(session.cart) == 1
    with pytest.raises(ValueError):
        cart.checkout(session, CartCheckout(items=[chosen.model_copy(update={"fingerprint": "wrong"})]))


def test_changed_catalogue_rejected(session, monkeypatch):
    chosen = select(session)
    cart.add(session, chosen)
    original = cart.catalogue
    def changed(s):
        ps = original(s)
        for p in ps: p.price += 1
        return ps
    monkeypatch.setattr(cart, "catalogue", changed)
    with pytest.raises(ValueError): cart.checkout(session, CartCheckout(items=[chosen]))
    assert not session.receipts


def test_blocked_cannot_be_added(session):
    p = next(p for p in catalogue(session) if p.id == "offer-injection")
    service.propose(session, p)
    with pytest.raises(ValueError): cart.add(session, select(session))
    assert not session.cart


def test_api_persistence_and_isolation(session, tmp_path, monkeypatch):
    from app.runtime import storage
    monkeypatch.setenv("BEANY_DB", str(tmp_path / "cart.sqlite3"))
    storage.save(session)
    client = TestClient(app)
    chosen = select(session)
    url = f"/sessions/{session.id}/cart"
    assert client.post(url, json=chosen.model_dump()).status_code == 200
    assert len(client.get(f"/sessions/{session.id}").json()["cart"]) == 1
    other = client.post("/sessions").json()
    assert client.post(f"/sessions/{other['id']}/cart/checkout", json={"items": [chosen.model_dump()]}).status_code == 409
    assert client.post(url + "/checkout", json={"items": [chosen.model_dump()]}).status_code == 200
    assert len(storage.load(session.id).receipts) == 1
