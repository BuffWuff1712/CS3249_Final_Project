import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError
from pydantic import BaseModel

from app.runtime import gateway, llm
from app.runtime.schemas import Fact, Interpretation, Message, Session


class Answer(BaseModel):
    reply: str


@pytest.mark.parametrize("fails", [False, True])
def test_call_logs_metadata_only_and_sends_schema_once(monkeypatch, caplog, fails):
    captured = {}
    closed = []
    def create(**kwargs):
        captured.update(kwargs)
        if fails:
            raise APITimeoutError(request=httpx.Request("POST", "https://private.example"))
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="stop", message=SimpleNamespace(content='{"reply":"private answer"}')
        )])
    monkeypatch.setattr(gateway, "make_client", lambda _: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        close=lambda: closed.append(True),
    ))
    config = gateway.Settings("secret-key", "https://private.example", "model", "chat", "json", "", 75)
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        if fails:
            with pytest.raises(gateway.LLMError, match="timed out"):
                gateway.structured_call(Answer, "private instructions", {"text": "private message"}, config)
        else:
            assert gateway.structured_call(Answer, "private instructions", {"text": "private message"}, config).reply == "private answer"
    instructions = captured["messages"][0]["content"]
    assert instructions.count('"title":"Answer"') == 1
    assert "stage=Answer" in caplog.text and "elapsed_s=" in caplog.text
    assert f"status={'error' if fails else 'ok'}" in caplog.text
    for private in ("secret-key", "private.example", "private instructions", "private message", "private answer"):
        assert private not in caplog.text
    assert closed == [True]


@pytest.mark.parametrize("value", ["nan", "inf", "0", "601", "nope"])
def test_invalid_timeout_rejected(monkeypatch, value):
    for name, setting in {"OPENAI_API_KEY": "test", "OPENAI_BASE_URL": "https://test.example",
                          "OPENAI_MODEL": "model", "OPENAI_API_MODE": "chat",
                          "OPENAI_STRUCTURED_MODE": "json", "OPENAI_TIMEOUT_SECONDS": value}.items():
        monkeypatch.setenv(name, setting)
    with pytest.raises(gateway.LLMError, match="OPENAI_TIMEOUT_SECONDS"):
        gateway.Settings.load()


def test_timeout_reaches_both_clients(monkeypatch):
    import openai
    captured = {}
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: captured.update(kwargs))
    gateway.make_client(gateway.Settings("test", "https://test.example", "model", "chat", "json", "", 75))
    try:
        assert captured["timeout"] == 75
        assert captured["http_client"].timeout.read == 75
        assert captured["max_retries"] == 0
    finally:
        captured["http_client"].close()


def test_context_keeps_recent_text_and_durable_brief(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    s = Session(brief={"budget": Fact(value="50", source="confirmed", hard=True)})
    s.messages = [Message(role="user" if i % 2 == 0 else "assistant", text=f"turn {i}") for i in range(24)]
    captured = {}
    def call(schema, instructions, payload):
        captured.update(payload)
        return Interpretation(intent="respond", reply="Hi!", changes=[], suggestions=[])
    monkeypatch.setattr(llm, "structured_call", call)
    llm.OpenAIConversation().interpret(s, "hello")
    assert captured["history"] == [{"role": m.role, "text": m.text} for m in s.messages[-20:]]
    assert captured["brief"]["budget"] == s.brief["budget"].model_dump()
    assert len(s.messages) == 24
