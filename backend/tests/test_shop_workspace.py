"""Adversarial offline checks for the backend-connected /shop boundary."""
import copy
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.runtime import shop_workspace as shop, storage, service, policy, risk_agent, cart

client = TestClient(app)


def create():
    response = client.post("/shop/sessions", json={})
    assert response.status_code == 200, response.text
    return response.json()


def change(view, path, body=None, method="POST", status=200):
    response = client.request(method, f"/shop/sessions/{view['session']['id']}/{path}",
                              json={"revision": view["revision"], **(body or {})})
    assert response.status_code == status, response.text[:1200]
    return response.json()


def searched():
    return change(create(), "messages", {"text": "Find headphones under $200"})


def proposed(product_id="study-hp-target-trusted"):
    return change(searched(), "propose", {"product_id": product_id})


def selection(view):
    action = view["current"]
    return {"proposal_id": action["id"], "fingerprint": action["fingerprint"]}


def test_create_honours_configured_provider_and_requires_workspace_adoption(monkeypatch):
    monkeypatch.setenv("BEANY_SEARCH_PROVIDER", "browser_use")
    monkeypatch.setenv("BROWSER_USE_REPLAY", "data/replay/study_listings.json")
    view = create()
    assert view["session"]["search_provider"] == "browser_use"
    assert view["session"]["search_replay"] == "data/replay/study_listings.json"
    assert view["offers"] == [] and view["current"] is None
    assert "experiment" not in view["session"]
    ordinary = service.create(search_provider="catalogue")
    storage.save(ordinary)
    assert client.get(f"/shop/sessions/{ordinary.id}").status_code == 409
    assert client.post(f"/shop/sessions/{ordinary.id}/adopt", json={}).status_code == 200


def test_previews_and_get_are_pure_no_model_calls_or_approval_tokens(monkeypatch):
    view = proposed()
    session = storage.load(view["session"]["id"])
    before = session.model_dump_json()
    monkeypatch.setattr(risk_agent, "review", lambda *_: pytest.fail("GET must never review with model"))
    previews = shop.preview(session)
    assert previews and session.model_dump_json() == before
    assert all("fingerprint" not in offer and "id" not in offer for offer in previews)
    response = client.get(f"/shop/sessions/{session.id}")
    assert response.status_code == 200
    assert storage.load(session.id).model_dump_json() == before
    assert "experiment" not in response.json()["session"]


def test_stale_revision_and_tampered_fingerprint_are_atomic():
    view = proposed()
    sid = view["session"]["id"]
    before = storage.load(sid).model_dump_json()
    change(view, "select", selection(view) | {"fingerprint": "wrong"}, status=409)
    assert storage.load(sid).model_dump_json() == before
    response = client.post(f"/shop/sessions/{sid}/select", json={"revision": view["revision"] - 1, **selection(view)})
    assert response.status_code == 409
    assert storage.load(sid).model_dump_json() == before


def test_select_is_not_checkout_and_finish_is_bound_and_idempotent():
    view = proposed()
    chosen = selection(view)
    change(view, "finish", chosen, status=409)
    view = change(view, "select", chosen)
    assert view["selected"]["id"] == chosen["proposal_id"]
    assert view["session"]["receipts"] == [] and view["session"]["approvals"] == []
    view = change(view, "finish", chosen)
    assert view["selected"] is None
    assert len(view["session"]["receipts"]) == 1
    assert view["session"]["receipts"][0]["proposal_id"] == chosen["proposal_id"]
    again = change(view, "finish", chosen)
    assert len(again["session"]["receipts"]) == 1
    change(again, "finish", chosen | {"fingerprint": "other"}, status=409)


def test_readonly_answer_keeps_selection_but_edits_remove_it():
    view = proposed()
    chosen = selection(view)
    view = change(view, "select", chosen)
    before = copy.deepcopy(view)
    view = change(view, "messages", {"text": "Explain this offer"})
    for key in ("brief", "permissions", "cart", "proposals"):
        assert view["session"][key] == before["session"][key]
    assert view["selected"] == before["selected"]
    view = change(view, "brief", {"field": "budget", "fact": {"value": "100", "source": "confirmed", "hard": True}}, method="PUT")
    assert view["selected"] is None and not view["session"]["cart"]
    assert view["current"] is None and not view["offers"]
    change(view, "finish", chosen, status=409)


def test_new_search_clears_selection_and_preserves_receipts():
    view = proposed()
    chosen = selection(view)
    view = change(change(view, "select", chosen), "finish", chosen)
    receipt = view["session"]["receipts"][0]
    view = change(view, "messages", {"text": "Find running shoes under $200"})
    assert view["selected"] is None
    assert view["session"]["receipts"] == [receipt]
    assert view["session"]["brief"]["category"]["value"] == "Running shoes"


@pytest.mark.parametrize("product_id", ["study-hp-target-external", "study-hp-target-injection", "study-hp-target-data-high"])
def test_blocked_previews_cannot_be_proposed_or_selected(product_id):
    view = searched()
    offer = next(offer for offer in view["offers"] if offer["product"]["id"] == product_id)
    assert offer["decision"] == "BLOCK"
    before = storage.load(view["session"]["id"]).model_dump_json()
    change(view, "propose", {"product_id": product_id}, status=409)
    assert storage.load(view["session"]["id"]).model_dump_json() == before


def test_same_model_seller_change_keeps_identity_and_excludes_knockoff():
    view = proposed()
    key = view["current_model_key"]
    view = change(view, "seller", {"preference": "lowest price"})
    assert view["current_model_key"] == key
    assert view["current"]["product"]["id"] != "study-hp-target-lookalike"
    assert view["current"]["decision"] != "BLOCK"
    old_id = view["current"]["product"]["id"]
    view = change(view, "seller")
    assert view["current_model_key"] == key and view["current"]["product"]["id"] != old_id


def test_no_same_model_seller_leaves_current_choice_unchanged():
    view = proposed("audio-2")
    sid = view["session"]["id"]
    before = storage.load(sid).model_dump_json()
    change(view, "seller", status=409)
    assert storage.load(sid).model_dump_json() == before


def test_site_tiers_and_policy_are_distinct():
    offers = {offer["product"]["id"]: offer for offer in searched()["offers"]}
    for suffix, tier in (("trusted", "good"), ("site-mid", "mid"), ("site-bad", "poor"), ("site-fake", "poor")):
        offer = offers[f"study-hp-target-{suffix}"]
        assert offer["merchant"]["site"]["tier"] == tier
        assert offer["decision"] == "REVIEW"
    assert offers["study-hp-target-site-mid"]["risk"]["recommended_decision"] == "ALLOW"
    assert offers["study-hp-target-site-bad"]["risk"]["recommended_decision"] == "REVIEW"


def test_history_is_backend_activity_not_fixed_frontend_counts():
    view = searched()
    assert len(view["history"]) == 1
    row = view["history"][0]
    assert row["proposal_id"] == view["current"]["id"]
    assert row["message_index"] == len(view["session"]["messages"]) - 1
    activity = {step["id"]: step for step in row["activity"]}
    assert len(activity["search"]["evidence"]) == 4
    assert len(activity["inspection"]["evidence"]) == 1
    assert all(step["state"] == "completed" for step in activity.values())
    explained = change(view, "messages", {"text": "Explain this offer"})
    assert explained["history"] == view["history"]


def test_selected_offer_detects_changed_catalogue_before_finish(monkeypatch):
    view = proposed()
    chosen = selection(view)
    view = change(view, "select", chosen)
    original = policy.catalogue
    def changed(session):
        return [p.model_copy(update={"price": p.price + 1}) if p.id == view["current"]["product"]["id"] else p for p in original(session)]
    monkeypatch.setattr(policy, "catalogue", changed)
    monkeypatch.setattr(cart, "catalogue", changed)
    restored = client.get(f"/shop/sessions/{view['session']['id']}").json()
    assert restored["selection_error"]
    change(restored, "finish", chosen, status=409)
    assert not storage.load(view["session"]["id"]).receipts


def test_offers_cannot_be_proposed_before_a_comparison():
    view = create()
    change(view, "propose", {"product_id": "study-hp-target-trusted"}, status=409)


def test_completed_selection_metadata_is_cleared():
    view = proposed()
    chosen = selection(view)
    finished = change(change(view, "select", chosen), "finish", chosen)
    assert shop.meta(storage.load(finished["session"]["id"]))["selected"] is None


def test_ai_preview_uses_cached_review_or_honest_rules_fallback_without_model_calls(monkeypatch):
    monkeypatch.setenv("BEANY_RISK_DETECTION", "ai")
    view = searched()
    sid = view["session"]["id"]
    saved = storage.load(sid)
    before = saved.model_dump_json()
    monkeypatch.setattr(service, "review_listing", lambda *_: pytest.fail("GET must not call a risk model"))
    restored = client.get(f"/shop/sessions/{sid}")
    assert restored.status_code == 200
    offers = restored.json()["offers"]
    selected = next(offer for offer in offers if offer["product"]["id"] == view["current"]["product"]["id"])
    assert selected["risk"]["basis"] == "ai"
    assert any(offer["risk"]["basis"] == "rules_fallback" for offer in offers if offer["risk"])
    assert storage.load(sid).model_dump_json() == before


def test_merchant_changes_are_read_on_next_request_and_block_old_checkout(monkeypatch):
    from app.runtime import merchants as merchants_module
    view = proposed()
    chosen = selection(view)
    view = change(view, "select", chosen)
    records = merchants_module.merchants()
    merchant_id = view["current"]["product"]["merchant_id"]
    records[merchant_id] = records[merchant_id].model_copy(update={"return_policy": "7-day returns only"})
    monkeypatch.setattr(merchants_module, "merchants", lambda: records)
    monkeypatch.setattr(shop, "merchants", lambda: records)
    restored = client.get(f"/shop/sessions/{view['session']['id']}").json()
    offer = next(offer for offer in restored["offers"] if offer["product"]["id"] == view["current"]["product"]["id"])
    assert offer["merchant"]["return_policy"] == "7-day returns only"
    assert restored["selection_error"]
    change(restored, "finish", chosen, status=409)
    assert not storage.load(view["session"]["id"]).receipts


def test_shop_fallback_replies_use_controls_that_exist():
    view = searched()
    reply = view["session"]["messages"][-1]["text"].casefold()
    assert "add this to your cart" not in reply and "proceed to checkout" not in reply
    assert "select this offer" in reply
    chosen = selection(view)
    # The first search offer is not blocked in this fixture; selection is separate from checkout.
    view = change(view, "select", chosen)
    view = change(view, "messages", {"text": "checkout"})
    reply = view["session"]["messages"][-1]["text"].casefold()
    assert "finish decision" in reply and "review cart and checkout" not in reply
    assert view["session"]["receipts"] == []


@pytest.mark.parametrize("text", ["I do not want to increase my budget to SGD500", "I do not want to remove my budget"])
def test_offline_negated_budget_reply_preserves_the_server_selection(text):
    view = proposed()
    view = change(view, "select", selection(view))
    before = copy.deepcopy(view)
    view = change(view, "messages", {"text": text})
    assert view["session"]["brief"] == before["session"]["brief"]
    assert view["selected"] == before["selected"]
    assert view["session"]["cart"] == before["session"]["cart"]


def test_workspace_model_payload_contains_selected_offer_and_correct_control_labels(monkeypatch):
    from app.runtime import llm
    from app.runtime.schemas import Interpretation
    view = proposed()
    view = change(view, "select", selection(view))
    session = storage.load(view["session"]["id"])
    calls = []
    def capture(schema, prompt, payload):
        calls.append(payload)
        return Interpretation(reply="Supplied evidence only", changes=[], intent="explain", suggestions=[])
    monkeypatch.setattr(llm, "structured_call", capture)
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    llm.OpenAIConversation().interpret(session, "Why this seller?")
    assert calls[0]["selected_offer"]["id"] == view["selected"]["id"]
    assert "Select this offer" in calls[0]["checkout_ui"] and "Finish decision" in calls[0]["checkout_ui"]
    assert calls[0]["permissions_read_only"] == session.permissions.model_dump()


def test_classic_routes_cannot_mutate_or_checkout_a_shop_session():
    view = proposed()
    chosen = selection(view)
    view = change(view, "select", chosen)
    sid = view["session"]["id"]
    before = storage.load(sid).model_dump_json()
    cases = [
        ("PUT", f"/sessions/{sid}/brief", {"field": "budget", "fact": {"value": "100", "source": "confirmed", "hard": True}}),
        ("POST", f"/sessions/{sid}/messages", {"text": "Find running shoes under $50"}),
        ("POST", f"/sessions/{sid}/proposals/{chosen['proposal_id']}/decision", {"action": "approve", "fingerprint": chosen["fingerprint"]}),
        ("POST", f"/sessions/{sid}/cart/checkout", {"items": [chosen]}),
    ]
    for method, path, body in cases:
        response = client.request(method, path, json=body)
        assert response.status_code == 409, response.text[:1000]
        assert storage.load(sid).model_dump_json() == before
    assert client.get(f"/sessions/{sid}").status_code == 200


def test_unexpected_stored_brief_change_invalidates_a_shop_selection():
    from app.runtime.schemas import Fact
    view = proposed()
    chosen = selection(view)
    view = change(view, "select", chosen)
    sid = view["session"]["id"]
    stored = storage.load(sid)
    stored.brief["budget"] = Fact(value="100", source="confirmed", hard=True)
    storage.save(stored)
    current = client.get(f"/shop/sessions/{sid}").json()
    assert current["selection_error"]
    change(current, "finish", chosen, status=409)
    assert not storage.load(sid).receipts


def test_explicit_comparisons_attach_activity_before_the_whole_assistant_answer():
    view = searched()
    for path, body in (("propose", {"product_id": "study-hp-target-trusted"}),
                       ("seller", {"preference": "lowest price"}), ("compare", {})):
        previous_count = len(view["session"]["messages"])
        view = change(view, path, body)
        replies = view["session"]["messages"][previous_count:]
        assert len(replies) == 1 and replies[0]["role"] == "assistant"
        assert view["history"][-1]["message_index"] == previous_count
        assert view["history"][-1]["proposal_id"] == view["current"]["id"]


@pytest.mark.parametrize("text,new_value,evidence", [
    ("I do not want to increase my budget to SGD500", "500", "SGD500"),
    ("I don't want to remove my budget", None, "remove my budget"),
])
def test_negated_budget_edit_cannot_be_applied_by_a_wrong_model_interpretation(monkeypatch, text, new_value, evidence):
    from app.runtime import llm
    from app.runtime.schemas import Interpretation, Change
    view = proposed()
    view = change(view, "select", selection(view))
    before = copy.deepcopy(view)
    wrong = Interpretation(reply="I changed your budget", intent="clarify", suggestions=[], changes=[
        Change(field="budget", value=new_value, source="confirmed", hard=True, evidence=evidence)])
    monkeypatch.setattr(service.llm, "interpret", lambda *_: wrong)
    view = change(view, "messages", {"text": text})
    assert view["session"]["brief"] == before["session"]["brief"]
    assert view["selected"] == before["selected"]
    assert view["session"]["cart"] == before["session"]["cart"]
