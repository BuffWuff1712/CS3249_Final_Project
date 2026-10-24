import json
from copy import deepcopy
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.runtime import service, storage, merchant_risk, merchants, research, gateway
from app.runtime.schemas import Session, Fact, Permissions, Action, Decision
from app.runtime.policy import catalogue, evaluate, fingerprint


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BEANY_DB", str(tmp_path / "study.sqlite3"))
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    monkeypatch.setenv("BEANY_RESEARCH_KEY", "study-secret")
    return TestClient(app)


HEADERS = {"X-Research-Key": "study-secret"}


def scenario(client, id):
    s = client.post(f"/research/scenarios/{id}/sessions", headers=HEADERS).json()
    response = client.post(f"/research/sessions/{s['id']}/trigger", headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def test_ground_truth_is_not_in_participant_state_or_prompt(client, monkeypatch):
    s = scenario(client, "risk-h")
    assert "experiment" not in s
    assert "MALICIOUS" not in json.dumps(s) and "ground_truth" not in json.dumps(s)
    report = client.get(
        f"/research/sessions/{s['id']}/risk-report", headers=HEADERS
    ).json()
    assert report["rows"][0]["ground_truth"] == "MALICIOUS"
    assert report["rows"][0]["predicted_risk"] == "LOW"
    assert report["metrics"]["fn"] == 1
    from app.runtime.llm import OpenAIConversation, Interpretation

    captured = {}

    def fake(schema, instructions, payload):
        captured.update(payload)
        return Interpretation(
            reply="Explanation",
            changes=[],
            intent="explain",
            suggestions=[],
        )

    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    monkeypatch.setattr("app.runtime.llm.structured_call", fake)
    OpenAIConversation().interpret(storage.load(s["id"]), "Explain this merchant")
    assert "MALICIOUS" not in json.dumps(captured) and "experiment" not in captured


@pytest.mark.parametrize("endpoint", ["risk-report", "risk-export"])
def test_research_access_required(client, endpoint):
    s = scenario(client, "risk-a")
    assert client.get(f"/research/sessions/{s['id']}/{endpoint}").status_code == 403
    assert (
        client.put(
            f"/research/sessions/{s['id']}/configuration",
            json={"profile_id": "concise"},
        ).status_code
        == 403
    )


def test_risk_engine_never_reads_truth(client, monkeypatch):
    monkeypatch.setattr(research, "TRUTH_PATH", None)
    s = scenario(client, "risk-b")
    assert s["proposals"][-1]["risk"]["level"] == "HIGH"


@pytest.mark.parametrize(
    "id,decision",
    [
        ("risk-a", "REVIEW"),
        ("risk-b", "REVIEW"),
        ("risk-c", "BLOCK"),
        ("risk-d", "BLOCK"),
        ("risk-e", "REVIEW"),
        ("risk-f", "BLOCK"),
        ("risk-g", "REVIEW"),
        ("risk-h", "REVIEW"),
        ("risk-i", "REVIEW"),
    ],
)
def test_risk_scenarios(client, id, decision):
    s = scenario(client, id)
    a = s["proposals"][-1]
    assert a["decision"] == decision
    response = client.post(
        f"/sessions/{s['id']}/proposals/{a['id']}/decision",
        json={"action": "approve", "fingerprint": a["fingerprint"]},
    )
    assert response.status_code == (409 if decision == "BLOCK" else 200)
    assert not s["permissions"]["share_personal_data"]


def test_low_price_alone_is_not_high_risk(client):
    s = scenario(client, "risk-g")
    risk = s["proposals"][-1]["risk"]
    assert risk["level"] == "LOW"
    assert [e["rule_id"] for e in risk["evidence"]] == ["low_price"]
    assert risk["recommended_decision"] == "ALLOW"


def test_thresholds_change_outcomes_but_mandatory_blocks_survive(client):
    s = scenario(client, "risk-b")
    original = s["proposals"][-1]
    config = merchant_risk.load_config().model_dump()
    config.update(medium=20, high=30, critical=40)
    r = client.put(
        f"/research/sessions/{s['id']}/configuration",
        headers=HEADERS,
        json={"profile_id": "concise", "risk_config": config},
    )
    assert r.status_code == 200 and r.json()["proposals"][-1]["status"] == "superseded"
    r = client.post(f"/research/sessions/{s['id']}/trigger", headers=HEADERS).json()
    assert r["proposals"][-1]["risk"]["level"] == "LOW"
    assert r["proposals"][-1]["risk"]["config_hash"] != original["risk"]["config_hash"]
    for id in ("risk-c", "risk-d", "risk-f"):
        s = scenario(client, id)
        config["weights"] = {k: 0 for k in config["weights"]}
        config["decisions"] = {k: "ALLOW" for k in config["decisions"]}
        client.put(
            f"/research/sessions/{s['id']}/configuration",
            headers=HEADERS,
            json={"risk_config": config},
        )
        result = client.post(
            f"/research/sessions/{s['id']}/trigger", headers=HEADERS
        ).json()
        assert result["proposals"][-1]["decision"] == "BLOCK"


def test_invalid_config_fails_closed(client, tmp_path, monkeypatch):
    s = scenario(client, "risk-a")
    a = s["proposals"][-1]
    path = tmp_path / "broken.json"
    path.write_text("{broken")
    monkeypatch.setattr(merchant_risk, "CONFIG_PATH", path)
    result = client.post(
        f"/sessions/{s['id']}/proposals/{a['id']}/decision",
        json={"action": "approve", "fingerprint": a["fingerprint"]},
    )
    assert result.status_code == 409 and not storage.load(s["id"]).receipts


def test_merchant_change_invalidates_approval(client, tmp_path, monkeypatch):
    s = scenario(client, "risk-a")
    a = s["proposals"][-1]
    data = json.loads(merchants.MERCHANT_PATH.read_text())
    data[0]["requested_information"] = ["fictional_email"]
    path = tmp_path / "merchants.json"
    path.write_text(json.dumps(data))
    monkeypatch.setattr(merchants, "MERCHANT_PATH", path)
    result = client.post(
        f"/sessions/{s['id']}/proposals/{a['id']}/decision",
        json={"action": "approve", "fingerprint": a["fingerprint"]},
    )
    assert result.status_code == 409


def test_rejection_alternative_preserves_constraints_and_avoids_merchant(client):
    s = scenario(client, "risk-i")
    a = s["proposals"][-1]
    r = client.post(f"/sessions/{s['id']}/alternative").json()
    assert (
        r["brief"] == s["brief"]
        and r["proposals"][-1]["product"]["merchant_id"] != a["product"]["merchant_id"]
    )
    assert r["proposals"][-2]["status"] == "rejected"


def test_research_observations_and_export(client):
    s = scenario(client, "risk-b")
    a = s["proposals"][-1]
    r = client.put(
        f"/research/sessions/{s['id']}/observation",
        headers=HEADERS,
        json={
            "proposal_id": a["id"],
            "understood": True,
            "responded_appropriately": False,
        },
    )
    assert r.status_code == 200 and "experiment" not in r.json()
    report = client.get(
        f"/research/sessions/{s['id']}/risk-report", headers=HEADERS
    ).json()
    assert report["rows"][0]["understood"] is True and report["metrics"]["tp"] == 1
    csv = client.get(f"/research/sessions/{s['id']}/risk-export", headers=HEADERS).text
    assert "SUSPICIOUS" in csv and "configuration_hash" in csv
    anon = client.get(f"/research/sessions/{s['id']}/export", headers=HEADERS).text
    assert "SUSPICIOUS" not in anon


def test_metrics():
    rows = [
        {"ground_truth": a, "predicted_risk": p}
        for a, p in [
            ("MALICIOUS", "HIGH"),
            ("TRUSTWORTHY", "HIGH"),
            ("UNCERTAIN", "LOW"),
            ("MALICIOUS", "LOW"),
        ]
    ]
    result = research.evaluate_rows(rows)
    assert [result[k] for k in ("tp", "fp", "tn", "fn")] == [1, 1, 1, 1]
    assert result["precision"] == result["recall"] == 0.5


@pytest.fixture
def gateway_env(monkeypatch):
    for k, v in {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_BASE_URL": "https://nus-gateway.test/v1",
        "OPENAI_MODEL": "selected-model",
        "OPENAI_API_MODE": "responses",
        "OPENAI_STRUCTURED_MODE": "schema",
        "OPENAI_REASONING_EFFORT": "",
    }.items():
        monkeypatch.setenv(k, v)


@pytest.mark.parametrize(
    "api,mode",
    [("responses", "schema"), ("chat", "schema"), ("chat", "json"), ("chat", "text")],
)
def test_gateway_modes_use_exact_endpoint_model(gateway_env, monkeypatch, api, mode):
    import openai
    from app.check_gateway import Ping

    captured = {}
    calls = []

    def result(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            output_parsed=Ping(status="ok"),
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        parsed=Ping(status="ok"), content='{"status":"ok"}'
                    ),
                )
            ],
        )

    def factory(**kwargs):
        captured.update(kwargs)
        kwargs["http_client"].close()
        return SimpleNamespace(
            responses=SimpleNamespace(parse=result),
            chat=SimpleNamespace(
                completions=SimpleNamespace(parse=result, create=result)
            ),
            close=lambda: None,
        )

    monkeypatch.setattr(openai, "OpenAI", factory)
    monkeypatch.setenv("OPENAI_API_MODE", api)
    monkeypatch.setenv("OPENAI_STRUCTURED_MODE", mode)
    assert gateway.structured_call(Ping, "Return JSON", {}).status == "ok"
    assert (
        captured["base_url"] == "https://nus-gateway.test/v1"
        and captured["api_key"] == "test-key"
    )
    assert len(calls) == 1 and calls[0]["model"] == "selected-model"


def test_invalid_output_no_fallback(gateway_env, monkeypatch):
    from app.check_gateway import Ping

    calls = []

    def parse(**kw):
        calls.append(kw)
        return SimpleNamespace(output_parsed=None)

    monkeypatch.setattr(
        gateway,
        "make_client",
        lambda *_: SimpleNamespace(
            responses=SimpleNamespace(parse=parse), close=lambda: None
        ),
    )
    with pytest.raises(gateway.LLMError, match="malformed"):
        gateway.structured_call(Ping, "test", {})
    assert len(calls) == 1


@pytest.mark.parametrize("status", [401, 403, 404, 429, 503])
def test_gateway_errors_no_fallback(gateway_env, monkeypatch, status):
    from openai import APIStatusError
    from app.check_gateway import Ping

    calls = []

    def parse(**kw):
        calls.append(kw)
        raise APIStatusError(
            "secret upstream body",
            response=httpx.Response(
                status,
                request=httpx.Request("POST", "https://nus-gateway.test/v1/responses"),
            ),
            body={"secret": "hidden"},
        )

    monkeypatch.setattr(
        gateway,
        "make_client",
        lambda *_: SimpleNamespace(
            responses=SimpleNamespace(parse=parse), close=lambda: None
        ),
    )
    with pytest.raises(gateway.LLMError) as exc:
        gateway.structured_call(Ping, "test", {})
    assert (
        "hidden" not in str(exc.value)
        and "secret" not in str(exc.value)
        and len(calls) == 1
    )


def test_thresholds_can_change_actual_review_to_allow(client, tmp_path, monkeypatch):
    data = json.loads(merchants.MERCHANT_PATH.read_text())
    data[0]["pressure_tactics"] = True
    data[0]["inconsistent_information"] = True
    path = tmp_path / "merchants.json"
    path.write_text(json.dumps(data))
    monkeypatch.setattr(merchants, "MERCHANT_PATH", path)
    s = Session(
        brief={"budget": Fact(value="150", hard=True)},
        permissions=Permissions(require_approval=False, autonomy="balanced"),
    )
    product = next(p for p in catalogue(s) if p.id == "audio-1")
    service.propose(s, product)
    assert s.proposals[-1].decision == "REVIEW" and not s.receipts
    cfg = merchant_risk.load_config().model_dump()
    cfg.update(medium=20, high=30, critical=40)
    research.configure(
        s,
        research.ExperimentUpdate(
            risk_config=merchant_risk.RiskConfig.model_validate(cfg)
        ),
    )
    service.propose(s, product)
    assert s.proposals[-1].decision == "ALLOW" and not s.receipts


def test_ambiguous_dollar_does_not_confirm_usd(client, monkeypatch):
    from app.runtime.schemas import Interpretation, Change

    s = service.create()
    monkeypatch.setattr(
        service.llm,
        "interpret",
        lambda *_: Interpretation(
            reply="A question",
            changes=[
                Change(
                    field="category",
                    value="Headphones",
                    source="confirmed",
                    hard=False,
                    evidence="headphones",
                ),
                Change(
                    field="budget",
                    value="150",
                    source="confirmed",
                    hard=True,
                    evidence="$150",
                ),
                Change(
                    field="currency",
                    value="USD",
                    source="confirmed",
                    hard=False,
                    evidence="$150",
                ),
            ],
            intent="clarify",
            suggestions=[],
        ),
    )
    service.chat(s, "Find headphones under $150")
    assert (
        s.brief["currency"].value == "SGD" and s.brief["currency"].source == "suggested"
    )
    assert s.proposals and s.clarification_count == 0


def test_low_price_alone_cannot_become_high_with_weight_change(client):
    s = Session()
    p = next(p for p in catalogue(s) if p.id == "offer-benign")
    m = merchants.merchant_for(p)
    cfg = merchant_risk.load_config()
    cfg.weights["low_price"] = 100
    assert merchant_risk.assess(p, m, catalogue(s), cfg).level == "LOW"
