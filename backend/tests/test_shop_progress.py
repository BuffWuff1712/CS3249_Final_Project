"""Real streaming observations arrive before the transactional result is saved."""
import asyncio
import json
from threading import Event
import pytest
from app import shop as api
from app.runtime import shop_workspace as shop, storage, service
from app.runtime.gateway import LLMError


def fresh():
    s = shop.create()
    storage.save(s)
    return s


def test_progress_arrives_while_model_is_still_working(monkeypatch):
    s = fresh()
    release = Event()
    interpret = service.llm.interpret
    def delayed(session, text):
        assert release.wait(5), "The client must receive progress before finishing the model call"
        return interpret(session, text)
    monkeypatch.setattr(service.llm, "interpret", delayed)
    response = api.message_stream(s.id, api.Message(revision=0, text="Find wireless headphones under $200"))
    async def read():
        first = json.loads(await anext(response.body_iterator))
        assert first["type"] == "activity" and first["activity"]["state"] == "running"
        assert first["activity"]["label"] == "Reading your request…"
        assert shop.meta(storage.load(s.id))["revision"] == 0
        release.set()
        return [json.loads(chunk) async for chunk in response.body_iterator]
    events = asyncio.run(read())
    result = next(e["view"] for e in events if e["type"] == "result")
    assert result["revision"] == 1 and result["current"]
    labels = [e["activity"]["label"] for e in events if e["type"] == "activity"]
    assert any("Found 4 matching offers" in label for label in labels)
    assert any("Needs your approval" in label for label in labels)
    assert any("Prepared your recommendation" in label for label in labels)
    assert not result["session"]["receipts"]
    assert storage.load(s.id).proposals[-1].fingerprint == result["current"]["fingerprint"]
    for row in result["history"]:
        assert not any("study-" in value or "site_reputation_" in value for step in row["activity"] for value in step["evidence"])


def test_stream_error_is_explicit_and_rolls_back(monkeypatch):
    s = fresh(); before = s.model_dump_json()
    def unavailable(*_):
        raise LLMError("Gateway unavailable")
    monkeypatch.setattr(service.llm, "interpret", unavailable)
    response = api.message_stream(s.id, api.Message(revision=0, text="Find headphones"))
    async def read():
        return [json.loads(chunk) async for chunk in response.body_iterator]
    events = asyncio.run(read())
    assert events[-1] == {"type": "error", "message": "Gateway unavailable"}
    assert any(e.get("activity", {}).get("state") == "unavailable" for e in events)
    assert not any(e["type"] == "result" for e in events)
    assert storage.load(s.id).model_dump_json() == before


def test_stale_stream_does_not_start_work_or_approve():
    s = fresh()
    response = api.compare_stream(s.id, api.Mutation(revision=9))
    async def read():
        return [json.loads(chunk) async for chunk in response.body_iterator]
    events = asyncio.run(read())
    assert len(events) == 1 and events[0]["type"] == "error"
    assert not storage.load(s.id).proposals and not storage.load(s.id).receipts
