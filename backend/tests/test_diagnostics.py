import json
import logging

from fastapi.testclient import TestClient
from app.main import app
from app.runtime import service


def events(caplog):
    return [json.loads(r.message) for r in caplog.records if r.name == "uvicorn.error" and r.message.startswith("{")]


def test_request_logs_correlate_with_worker_logs_without_chat_text(caplog, monkeypatch):
    from app.runtime.diagnostics import log

    caplog.set_level(logging.INFO, logger="uvicorn.error")
    monkeypatch.setattr(service, "chat", lambda *_: log("test_worker"))
    client = TestClient(app)
    sid = client.post("/sessions").json()["id"]
    caplog.clear()
    response = client.post(f"/sessions/{sid}/messages", json={"text": "private-shopping-text"})
    rows = events(caplog)
    assert response.status_code == 200
    assert {r["event"] for r in rows} >= {"request_started", "test_worker", "request_finished"}
    assert {r["request_id"] for r in rows} == {response.headers["X-Request-ID"]}
    assert all(r["entry_point"] == "http" for r in rows)
    assert "private-shopping-text" not in caplog.text


def test_unexpected_error_is_logged_and_readable_across_cors(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    client = TestClient(app, raise_server_exceptions=False)
    sid = client.post("/sessions").json()["id"]

    def crash(*_):
        raise RuntimeError("private-secret-in-error")

    monkeypatch.setattr(service, "chat", crash)
    response = client.post(f"/sessions/{sid}/messages", json={"text": "hello"},
                           headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    failed = next(r for r in events(caplog) if r["event"] == "request_failed")
    assert failed["error_type"] == "RuntimeError" and failed["frames"]
    assert "private-secret-in-error" not in caplog.text + response.text


def test_handled_provider_error_has_request_reference(caplog, monkeypatch):
    from app.runtime.gateway import LLMError

    def fail(*_):
        raise LLMError("Browser Use search timed out")

    caplog.set_level(logging.INFO, logger="uvicorn.error")
    monkeypatch.setattr(service, "chat", fail)
    client = TestClient(app)
    sid = client.post("/sessions").json()["id"]
    response = client.post(f"/sessions/{sid}/messages", json={"text": "hello"})
    assert response.status_code == 503
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert any(r["event"] == "request_rejected" and r["error_type"] == "LLMError" for r in events(caplog))


def test_model_failure_logs_stage_without_payload_or_exception_text(caplog, monkeypatch):
    import pytest
    from types import SimpleNamespace
    from app.runtime import gateway
    from app.runtime.schemas import Fact

    def fail(**_):
        raise ValueError("private-model-output")

    caplog.set_level(logging.INFO, logger="uvicorn.error")
    config = gateway.Settings("private-key", "https://gateway.test/v1", "test", "responses", "schema", "")
    monkeypatch.setattr(gateway, "make_client", lambda _: SimpleNamespace(
        responses=SimpleNamespace(parse=fail), close=lambda: None))
    with pytest.raises(gateway.LLMError):
        gateway.structured_call(Fact, "private-instructions", {"private": "private-payload"}, config)
    failed = next(r for r in events(caplog) if r["event"] == "model_call_failed")
    assert failed["schema"] == "Fact" and failed["error_type"] == "ValueError"
    assert failed["duration_ms"] >= 0
    assert "private-" not in caplog.text
