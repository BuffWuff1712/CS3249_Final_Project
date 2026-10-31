import asyncio
import json
from threading import Event

import pytest

from app import shop as api
from app.runtime import service, storage, shop_workspace as shop
from app.runtime.progress import cancellation, cancellable_call, RequestStopped
from app.runtime.schemas import Interpretation, ClarificationAnswer, Session


def test_broad_shoes_asks_all_then_accepts_uncertainty(monkeypatch):
    monkeypatch.setenv("BEANY_LLM_MODE", "mock")
    s = Session(mode="mock")
    service.chat(s, "I need shoes")
    assert s.stage == "clarifying" and not s.proposals
    assert set(s.clarification_asked) == {"product_type", "budget", "features"}
    assert s.brief["category"].source == "suggested"
    service.chat(s, "I'm unsure about those; show me some options")
    assert s.proposals and s.clarification_answers["product_type"] == "unknown"
    assert not s.receipts and "budget" not in s.brief


def test_partial_answer_does_not_skip_remaining_questions():
    s = Session(mode="mock")
    service.chat(s, "I need shoes")
    service.chat(s, "running shoes under $100")
    assert s.stage == "clarifying" and not s.proposals
    assert "features" in s.messages[-1].text and "your budget" not in s.messages[-1].text
    service.chat(s, "no preference")
    assert s.proposals and s.brief["budget"].value == "100"


def test_complete_request_searches_without_questions():
    s = Session(mode="mock")
    service.chat(s, "Find cushioned running shoes under $100")
    assert s.proposals and not s.clarification_asked


def test_greeting_does_not_resolve_questions_and_compare_cannot_bypass():
    s = shop.create()
    shop.message(s, "I need shoes")
    before = s.clarification_answers.copy()
    shop.message(s, "hello")
    assert before == s.clarification_answers and not s.proposals
    with pytest.raises(ValueError, match="questions"):
        shop.compare(s)


def test_ungrounded_skip_is_ignored(monkeypatch):
    s = Session(mode="mock")
    service.chat(s, "I need shoes")
    monkeypatch.setattr(service.llm, "interpret", lambda *_: Interpretation(
        intent="search", reply="Search", changes=[], suggestions=[],
        clarification_answers=[ClarificationAnswer(field=f, status="unknown", evidence="not in message")
                               for f in ("product_type", "budget", "features")]))
    service.chat(s, "What about options?")
    assert s.stage == "clarifying" and not s.proposals


def test_stop_returns_before_remote_call_and_discards_late_result(monkeypatch):
    s = shop.create(); storage.save(s)
    before = s.model_dump_json()
    entered, release, finished = Event(), Event(), Event()
    def remote():
        entered.set()
        assert release.wait(5)
        finished.set()
        return Interpretation(intent="respond", reply="Late reply", changes=[], suggestions=[])
    monkeypatch.setattr(service.llm, "interpret", lambda *_: cancellable_call(remote))
    request_id = "stop-test-request"
    response = api.message_stream(s.id, api.Message(revision=0, request_id=request_id, text="hello"))
    async def read():
        first = json.loads(await anext(response.body_iterator))
        assert first["type"] == "activity"
        assert entered.wait(2)
        assert api.stop_request(s.id, request_id)["stopped"]
        return [json.loads(chunk) async for chunk in response.body_iterator]
    try:
        events = asyncio.run(read())
        assert not finished.is_set()
        assert events[-1]["type"] == "error" and "Stopped" in events[-1]["message"]
        assert storage.load(s.id).model_dump_json() == before
    finally:
        release.set()
    assert finished.wait(2)
    assert storage.load(s.id).model_dump_json() == before
    assert not api.stop_request(s.id, request_id)["stopped"]


def test_stop_before_commit_rolls_back():
    s = shop.create(); storage.save(s)
    signal = Event()
    def work(session):
        service.message(session, "Must not be saved")
        signal.set()
    with pytest.raises(RequestStopped), cancellation(signal):
        api.mutate(s.id, api.Mutation(revision=0), work)
    assert len(storage.load(s.id).messages) == len(s.messages)
