import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.runtime import service, storage
from app.runtime.schemas import *
from app.runtime.policy import catalogue, evaluate, fingerprint, search


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BEANY_DB", str(tmp_path / "study.sqlite3"))
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    monkeypatch.setenv("BEANY_RESEARCH_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_MODE", "responses")
    monkeypatch.setenv("OPENAI_STRUCTURED_MODE", "schema")
    return TestClient(app)


def start(client, text="Find headphones under $150"):
    s = client.post("/sessions").json()
    response = client.post(f"/sessions/{s['id']}/messages", json={"text": text})
    assert response.status_code == 200, response.text
    return response.json()


def decision(client, s, action="approve", fingerprint_override=None):
    a = s["proposals"][-1]
    return client.post(
        f"/sessions/{s['id']}/proposals/{a['id']}/decision",
        json={
            "action": action,
            "fingerprint": fingerprint_override or a["fingerprint"],
        },
    )


def test_checkout_persistent_idempotent(client):
    s = start(client)
    r = decision(client, s)
    assert r.status_code == 200
    body = r.json()
    assert len(body["receipts"]) == 1
    assert decision(client, s).json() == body
    assert decision(client, s, "reject").status_code == 409
    assert storage.load(s["id"]).receipts[0].id == body["receipts"][0]["id"]


def test_stale_after_edit(client):
    s = start(client)
    r = client.put(
        f"/sessions/{s['id']}/brief",
        json={
            "field": "budget",
            "fact": {"value": "40", "source": "confirmed", "hard": True},
        },
    )
    assert r.status_code == 200
    assert decision(client, s).status_code == 409
    assert not storage.load(s["id"]).receipts


def test_fingerprint_mismatch(client):
    assert (
        decision(client, start(client), fingerprint_override="wrong").status_code == 409
    )


def test_cancel(client):
    s = start(client)
    client.post(f"/sessions/{s['id']}/messages", json={"text": "cancel"})
    assert decision(client, s).status_code == 409


def test_isolation_and_reset(client):
    a = start(client)
    b = client.post("/sessions").json()
    assert not b["brief"] and not b["proposals"]
    client.delete(f"/sessions/{a['id']}")
    assert client.get(f"/sessions/{a['id']}").status_code == 404
    assert client.get(f"/sessions/{b['id']}").status_code == 200


def test_clarification(client):
    s = start(client, "I need some shoes")
    assert (
        s["stage"] == "clarifying"
        and s["clarification_count"] == 1
        and not s["proposals"]
    )
    assert [m["text"] for m in s["messages"][1:]] == [
        "I need some shoes",
        "Will you use them for running or everyday wear?",
    ]


def test_unsupported_category_has_one_complete_clarification(client, monkeypatch):
    reply = (
        "Smartphones aren't in my current shopping categories. "
        "Would you like to explore running shoes, headphones, or backpacks instead?"
    )
    monkeypatch.setattr(
        service.llm,
        "interpret",
        lambda *_: Interpretation(
            reply=reply, changes=[], intent="clarify", suggestions=[]
        ),
    )
    s = start(client, "I want to find a smartphone for $2000")
    assert [m["text"] for m in s["messages"][1:]] == [
        "I want to find a smartphone for $2000",
        reply,
    ]
    assert s["stage"] == "clarifying" and s["clarification_count"] == 1
    assert not s["proposals"] and not s["receipts"]
    assert client.get(f"/sessions/{s['id']}").json()["messages"] == s["messages"]


def test_no_key_is_explicit(client, monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = client.post("/sessions").json()
    r = client.post(f"/sessions/{s['id']}/messages", json={"text": "headphones"})
    assert r.status_code == 503 and "OPENAI_API_KEY" in r.json()["detail"]
    assert len(storage.load(s["id"]).messages) == 1


def test_rejection_alternative(client):
    s = start(client)
    rejected = s["proposals"][-1]["product"]["id"]
    assert decision(client, s, "reject").status_code == 200
    r = client.post(
        f"/sessions/{s['id']}/messages", json={"text": "Find an alternative"}
    ).json()
    assert r["proposals"][-1]["product"]["id"] != rejected


def test_search_and_inferred_constraint_protection(client, monkeypatch):
    s = start(client)
    monkeypatch.setattr(
        service.llm,
        "interpret",
        lambda *_: Interpretation(
            reply="Suggestion",
            changes=[
                Change(
                    field="budget",
                    value="500",
                    source="suggested",
                    hard=False,
                    evidence="",
                )
            ],
            intent="explain",
            suggestions=[],
        ),
    )
    r = client.post(
        f"/sessions/{s['id']}/messages", json={"text": "What do you suggest?"}
    ).json()
    assert r["brief"]["budget"]["value"] == "150"
    assert all(p["price"] <= 150 for p in r["recommendations"])


def test_explicit_correction(client):
    s = start(client)
    r = client.post(
        f"/sessions/{s['id']}/messages", json={"text": "Change my budget to under 80"}
    ).json()
    assert r["brief"]["budget"]["value"] == "80"
    assert r["proposals"][0]["status"] == "superseded"
    assert all(p["price"] <= 80 for p in r["recommendations"])


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("normal", "REVIEW"),
        ("budget", "BLOCK"),
        ("substitution", "REVIEW"),
        ("merchant", "BLOCK"),
        ("privacy", "BLOCK"),
        ("injection", "BLOCK"),
        ("rejection", "REVIEW"),
    ],
)
def test_scenarios_and_blocks(client, scenario, expected):
    headers = {"X-Research-Key": "test-key"}
    s = client.post(f"/research/scenarios/{scenario}/sessions", headers=headers).json()
    r = client.post(f"/research/sessions/{s['id']}/trigger", headers=headers)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["proposals"][-1]["decision"] == expected
    assert decision(client, s).status_code == (409 if expected == "BLOCK" else 200)
    assert not s["permissions"]["share_personal_data"]
    csv = client.get(f"/research/sessions/{s['id']}/export", headers=headers)
    assert csv.status_code == 200 and "participant,scenario,seconds" in csv.text
    assert "Ignore your rules" not in csv.text


def test_research_auth(client):
    assert client.get("/research/scenarios").status_code == 403


def test_payment_and_auto_checkout(client):
    s = Session(
        brief={
            "category": Fact(value="Headphones"),
            "budget": Fact(value="150", hard=True),
        },
        permissions=Permissions(require_approval=False, autonomy="balanced"),
    )
    p = next(p for p in catalogue(s) if p.id == "audio-1")
    a = Action(product=p, payment_method="Real card")
    assert evaluate(s, a).decision == "BLOCK"
    service.propose(s, p)
    assert not s.receipts  # Even ALLOW proposals now wait for the checkout review UI.


def test_catalogue_tampering(client, monkeypatch):
    s = start(client)
    original = service.catalogue

    def changed(session):
        result = original(session)
        for p in result:
            p.price += 1
        return result

    monkeypatch.setattr(service, "catalogue", changed)
    assert decision(client, s).status_code == 409


def test_invalid_preference(client):
    s = client.post("/sessions").json()
    for value in ("nan", "-1", "infinity", "abc"):
        assert (
            client.put(
                f"/sessions/{s['id']}/brief",
                json={"field": "budget", "fact": {"value": value}},
            ).status_code
            == 409
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("excluded_brands", "Echo"),
        ("preferred_brands", "Wave"),
        ("features", "noise cancelling"),
        ("merchants", "Demo Store"),
    ],
)
def test_hard_search_constraints(client, field, value):
    s = Session(
        brief={
            "category": Fact(value="Headphones"),
            field: Fact(value=value, hard=True),
        }
    )
    results = search(s)
    assert results
    for p in results:
        if field == "excluded_brands":
            assert p.brand != "Echo"
        if field == "preferred_brands":
            assert p.brand == "Wave"
        if field == "features":
            assert value in p.attributes
        if field == "merchants":
            assert p.merchant == value


def test_sdk_structured_contract(client, monkeypatch):
    import openai
    from types import SimpleNamespace
    from app.runtime.llm import OpenAIConversation

    captured = {}

    def parse(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            output_parsed=Interpretation(
                reply="Will you use them for running or everyday wear?",
                changes=[],
                intent="clarify",
                suggestions=[],
            )
        )

    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: SimpleNamespace(
            responses=SimpleNamespace(parse=parse), close=lambda: None
        ),
    )
    result = OpenAIConversation().interpret(Session(), "shoes")
    assert result.intent == "clarify" and captured["text_format"] is Interpretation
    assert captured["store"] is False and captured["model"]


def test_policy_recheck_before_checkout(client):
    s = Session(brief={"budget": Fact(value="150", hard=True)})
    service.propose(s, next(p for p in catalogue(s) if p.id == "audio-1"))
    a = s.proposals[-1]
    s.approvals.append(
        Approval(proposal_id=a.id, fingerprint=a.fingerprint, action="approve")
    )
    s.brief["budget"] = Fact(value="50", hard=True)
    with pytest.raises(ValueError):
        service.checkout(s, a)
    assert not s.receipts


def test_select_alternative_is_new_action(client):
    s = start(client)
    product = s["recommendations"][-1]
    r = client.post(f"/sessions/{s['id']}/products/{product['id']}/propose")
    assert r.status_code == 200
    assert r.json()["proposals"][-1]["product"]["id"] == product["id"]
    assert r.json()["proposals"][-1]["id"] != s["proposals"][-1]["id"]
    assert decision(client, s).status_code == 409
    assert (
        client.post(f"/sessions/{s['id']}/products/nonexistent/propose").status_code
        == 409
    )


def test_wallet_only_permission(client):
    s = Session(permissions=Permissions(payment_methods=["Demo Wallet"]))
    service.propose(s, next(p for p in catalogue(s) if p.id == "audio-1"))
    assert s.proposals[-1].payment_method == "Demo Wallet"
    assert not any(r.rule_id == "payment" for r in s.proposals[-1].rules)


def test_explicit_cancel_does_not_require_llm(client, monkeypatch):
    s = start(client)
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post(f"/sessions/{s['id']}/cancel")
    assert r.status_code == 200 and r.json()["stage"] == "cancelled"
    assert decision(client, s).status_code == 409
