"""Participant workspace facade for the collaborative UI. Policy and checkout remain authoritative."""
import hashlib
import json
import re
from . import service, policy, cart
from .schemas import Action, Fact, SessionView
from .merchants import merchant_for, merchants
from .shopping_workflow import run_shopping

MAX_OFFERS = 120


def meta(s):
    if not s.experiment.get("shop_workspace"):
        raise ValueError("This session has not been opened in the shopping workspace.")
    return s.experiment["shop_workspace"]


def create():
    s = service.create()
    return adopt(s)


def adopt(s):
    if s.experiment.get("shop_workspace"):
        return s
    if s.proposals and s.proposals[-1].status == "pending" and any(item.action.id == s.proposals[-1].id for item in s.cart):
        s.proposals[-1].status = "superseded"
    s.experiment["shop_workspace"] = {"revision": 0, "history": [], "selected": None, "seller_preference": "longer returns"}
    return s


def model_key(product):
    identity = [product.name.casefold(), product.brand.casefold(), product.category.casefold(),
                product.currency, sorted(product.sizes), sorted(product.specifications.items())]
    if product.source == "browser_use":
        # No canonical cross-seller model/variant identifier is supplied by the live adapter.
        identity += [product.source_url, product.id]
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def preview(s):
    """Never call a model, mutate the original, or mint approval fingerprints here."""
    if not s.recommendations:
        return []
    offers = []
    context = s.model_copy(deep=True)
    records = s.live_merchants if s.search_provider == "browser_use" and not s.scenario_id else merchants()
    products = policy.catalogue(s)
    for p in policy.search(s, limit=None)[:MAX_OFFERS]:
        a = Action(id="", product=p, merchant_details=records[p.merchant_id])
        policy.evaluate(context, a, catalogue_snapshot=products, merchant_snapshot=records)
        offers.append({"product": p.model_dump(), "model_key": model_key(p),
                       "merchant": a.merchant_details.model_dump() if a.merchant_details else None,
                       "risk": a.risk.model_dump() if a.risk else None,
                       "decision": a.decision, "rules": [r.model_dump() for r in a.rules]})
    return offers


def view(s):
    state = meta(s)
    current = s.proposals[-1] if s.proposals and s.proposals[-1].status == "pending" else None
    current_error = ""
    if current:
        from .schemas import CartItem
        try:
            cart.checked_context(s, CartItem(action=current.model_copy(deep=True), brief=s.brief.copy()))
        except (ValueError, LookupError) as exc:
            current_error = str(exc)
    selected_id = state.get("selected")
    selected = next((item for item in s.cart if item.action.id == selected_id), None)
    selection_error = ""
    if selected:
        try:
            if current is None or current.id != selected.action.id or selected.brief != s.brief:
                raise ValueError("Your needs or current proposal changed. Compare and select again.")
            cart.checked_context(s, selected)
        except (ValueError, LookupError) as exc:
            selection_error = str(exc)
    # Only explicitly selected participant-facing state is exposed, never experiment labels.
    return {"session": SessionView.model_validate(s.model_dump()).model_dump(),
            "revision": state["revision"], "offers": preview(s),
            "current": current.model_dump() if current else None, "current_error": current_error,
            "current_model_key": model_key(current.product) if current else None,
            "selected": selected.action.model_dump() if selected else None,
            "selection_error": selection_error, "cart_review": cart.review(s),
            "seller_preference": state["seller_preference"], "history": friendly_history(s)}



def friendly_history(s):
    """Upgrade saved technical activity labels without rewriting saved sessions."""
    if not meta(s)["history"]:
        return []
    rows = []
    names = {p.id: f"{p.name} · {p.merchant}" for p in policy.catalogue(s)}
    for row in meta(s)["history"]:
        action = next((a for a in s.proposals if a.id == row["proposal_id"]), None)
        activity = []
        for original in row["activity"]:
            item = dict(original)
            count = len(item["evidence"])
            if item["id"] == "search":
                item["label"] = f"Found {count} matching offer{'s' if count != 1 else ''}"
                item["evidence"] = [names.get(value, value if " · " in value else "Previously compared offer") for value in item["evidence"]]
            elif item["id"] == "inspection":
                item["label"] = f"Checked {count} product{'s' if count != 1 else ''} and seller terms"
                item["evidence"] = [names.get(value, value if " · " in value else "Previously checked product") for value in item["evidence"]]
            elif item["id"] == "policy" and action:
                item["label"] = "Checked budget and permissions · " + {"ALLOW": "Within your limits", "REVIEW": "Needs your approval", "BLOCK": "Offer blocked"}[action.decision]
                item["evidence"] = [action.product.name]
            elif item["id"] == "risk" and action:
                item["label"] = "Checked seller concerns"
                item["evidence"] = [action.risk.explanation] if action.risk else []
            activity.append(item)
        rows.append({**row, "activity": activity})
    return rows

def clear_selection(s):
    state = meta(s)
    selected = state.get("selected")
    if selected:
        s.cart = [item for item in s.cart if item.action.id != selected]
    state["selected"] = None


def record(s, events_before, proposals_before):
    if len(s.proposals) <= proposals_before:
        return
    a = s.proposals[-1]
    activity = []
    searched, inspected = set(), set()
    for event in s.events[events_before:]:
        if event.kind == "shopping_tool":
            step = json.loads(event.detail)
            if step["action"] == "search_products":
                searched.update(p["id"] for p in step["products"])
            if step["action"] == "get_product_details":
                inspected.add(step["product"]["id"])
    if searched:
        activity.append({"id": "search", "label": f"Search returned {len(searched)} {'local catalogue' if s.search_provider == 'catalogue' else 'saved listing' if s.search_replay else 'web listing'} offers", "state": "completed", "evidence": sorted(searched)})
    if inspected:
        activity.append({"id": "inspection", "label": f"Inspected {len(inspected)} product records", "state": "completed", "evidence": sorted(inspected)})
    activity.append({"id": "policy", "label": f"Checked selected offer: {a.decision}", "state": "completed", "evidence": [a.product.id]})
    if a.risk:
        activity.append({"id": "risk", "label": f"Merchant assessment: {a.risk.level.lower()} predicted risk ({a.risk.basis})", "state": "completed", "evidence": [e.rule_id for e in a.risk.evidence]})
    meta(s)["history"] = [*meta(s)["history"], {"message_index": len(s.messages) - 1, "proposal_id": a.id, "activity": activity}][-30:]


def message(s, text):
    text = text.strip()
    if not text:
        raise ValueError("Please enter a message.")
    # A mentioned amount inside a denied edit is not authorization to weaken a hard limit.
    denied_budget = re.search(r"(?:don't|do not|never|not).{0,40}(?:increase|raise|remove|change|drop).{0,50}(?:budget|limit|SGD|USD|\$)", text, re.I) or re.search(r"(?:budget|limit).{0,20}(?:is not|isn't|not|never).{0,20}\d", text, re.I)
    denied_seller = re.search(r"(?:don't|do not|not).{0,25}(?:cheapest|lowest price)", text, re.I)
    if denied_budget or denied_seller:
        from .schemas import Message
        s.messages.append(Message(role="user", text=text))
        service.message(s, "I kept your current needs and selection. Please state the budget or seller preference you want to apply, or use the explicit needs and seller controls. A denied change does not authorize changing your limit.")
        s.suggestions = []
        service.event(s, "clarification", "Preserved constraints while clarifying a denied budget or seller change")
        return
    before = s.model_copy(deep=True)
    events, proposals = len(s.events), len(s.proposals)
    service.chat(s, text)
    # Read-only answers retain approval/selection. Any actual comparison, edit or cancellation does not.
    changed = s.brief != before.brief or len(s.proposals) != proposals or s.stage == "cancelled"
    if changed:
        clear_selection(s)
    record(s, events, proposals)


def edit(s, field, fact):
    clear_selection(s)
    service.edit(s, field, fact)
    service.message(s, f"{field.replace('_', ' ').capitalize()} {'updated' if fact else 'removed'}. Compare your current needs before selecting again.")


def merge_reply(s, start):
    """One response per completed explicit comparison, with activity before its facts."""
    from .schemas import Message
    replies = s.messages[start:]
    if replies:
        s.messages = s.messages[:start] + [Message(role="assistant", text=" ".join(message.text for message in replies))]


def compare(s):
    if not policy.value(s, "category"):
        raise ValueError("Choose a product category before comparing.")
    clear_selection(s)
    service.invalidate(s)
    events, proposals = len(s.events), len(s.proposals)
    outcome = run_shopping(s)
    if outcome.status != "proposed":
        s.stage = "no_match" if outcome.status == "no_match" else "ready"
        service.message(s, "No eligible offer was proposed. Your limits were kept. Refine your needs or retry the comparison.")
        return
    start = len(s.messages)
    service.propose(s, outcome.product, recommendations=outcome.candidates)
    merge_reply(s, start)
    record(s, events, proposals)


def propose(s, product_id):
    if not s.recommendations or not policy.value(s, "category"):
        raise ValueError("Compare your current needs before choosing a catalogue offer.")
    candidates = policy.search(s, limit=None)
    p = next((p for p in candidates if p.id == product_id), None)
    if p is None:
        raise ValueError("That offer is no longer eligible. Compare again.")
    context = s.model_copy(deep=True)
    checked = Action(product=p, merchant_details=merchant_for(p, context))
    policy.evaluate(context, checked)
    if checked.decision == "BLOCK":
        raise ValueError("This offer is blocked by the backend policy. " + " ".join(r.explanation for r in checked.rules if r.decision == "BLOCK"))
    clear_selection(s)
    events, proposals = len(s.events), len(s.proposals)
    start = len(s.messages)
    service.propose(s, p, recommendations=candidates)
    merge_reply(s, start)
    record(s, events, proposals)


def another_seller(s, preference=None):
    if not s.proposals:
        raise ValueError("Compare a product before choosing its seller.")
    current = s.proposals[-1]
    key = model_key(current.product)
    candidates = [o for o in preview(s) if o["model_key"] == key and o["decision"] != "BLOCK"
                  and (preference is not None or o["product"]["id"] != current.product.id)]
    if not candidates:
        raise ValueError("No other eligible seller for this exact model and variant fits your needs. Your current choice is unchanged.")
    if preference is not None:
        if preference not in ("longer returns", "lowest price"):
            raise ValueError("Choose longer returns or lowest price.")
        meta(s)["seller_preference"] = preference
    def rank(offer):
        days = re.search(r"\b(\d+)\s*[- ]?\s*days?\b", (offer["merchant"] or {}).get("return_policy", ""), re.I)
        period = int(days.group(1)) if days else -1
        price = offer["product"]["price"]
        return (price,) if meta(s)["seller_preference"] == "lowest price" else (-period, price)
    chosen = sorted(candidates, key=rank)[0]
    propose(s, chosen["product"]["id"])
    s.messages[-1].text += " Kept the exact product model and variant while comparing eligible sellers. Return terms are supplied catalogue claims; eligibility and exclusions still need review."


def select(s, proposal_id, fingerprint):
    if not s.proposals or s.proposals[-1].id != proposal_id:
        raise ValueError("Select only the current proposal.")
    clear_selection(s)
    from .schemas import CartSelection
    cart.add(s, CartSelection(proposal_id=proposal_id, fingerprint=fingerprint))
    meta(s)["selected"] = proposal_id
    s.messages[-1].text = "Offer selected. Review its terms and use Finish decision to explicitly confirm simulated checkout. No order, payment or receipt has been created."


def finish(s, proposal_id, fingerprint):
    from .schemas import CartCheckout, CartSelection
    state = meta(s)
    if state.get("selected") != proposal_id:
        # An exact repeated request may return its existing receipt, but never a different receipt.
        receipt = next((r for r in s.receipts if r.proposal_id == proposal_id and r.fingerprint == fingerprint), None)
        if receipt:
            return
        raise ValueError("Select this current offer and review it before finishing.")
    item = next((item for item in s.cart if item.action.id == proposal_id), None)
    if not item or item.brief != s.brief or not s.proposals or s.proposals[-1].id != proposal_id or s.proposals[-1].status != "pending":
        raise ValueError("Your needs or current proposal changed. Compare and select again.")
    cart.checkout(s, CartCheckout(items=[CartSelection(proposal_id=proposal_id, fingerprint=fingerprint)]))
    meta(s)["selected"] = None
    s.messages[-1].text = "Simulated checkout complete. The receipt is shown in this workspace. No real order or payment was created."


def permissions(s, value):
    clear_selection(s)
    service.invalidate(s)
    s.permissions = value
    s.stage = "ready"
    service.event(s, "permissions", "Permissions explicitly updated through controls")
    service.message(s, "Permissions saved. Pending proposals were cleared; compare again. Cart items retain their original needs and use current permissions at checkout.")


def cancel(s):
    clear_selection(s)
    service.invalidate(s)
    s.stage = "cancelled"
    service.event(s, "cancel", "Cancelled through explicit control")
    service.message(s, "Cancelled. No pending proposal can be approved. Saved cart items remain available for separate review.")
    s.suggestions = []


def reject(s, proposal_id, fingerprint):
    from .schemas import Decision
    if not s.proposals or s.proposals[-1].id != proposal_id:
        raise ValueError("Reject only the current proposal.")
    clear_selection(s)
    service.decide(s, proposal_id, Decision(action="reject", fingerprint=fingerprint))


def alternative(s):
    events, proposals = len(s.events), len(s.proposals)
    clear_selection(s)
    start = len(s.messages)
    service.alternative(s)
    merge_reply(s, start)
    record(s, events, proposals)


def add_cart(s, proposal_id, fingerprint):
    from .schemas import CartSelection
    if not s.proposals or s.proposals[-1].id != proposal_id:
        raise ValueError("Add only the current proposal.")
    cart.add(s, CartSelection(proposal_id=proposal_id, fingerprint=fingerprint))
    # Promote an ephemeral selection into a persistent original-brief cart entry.
    meta(s)["selected"] = None
    s.proposals[-1].status = "superseded"


def remove_cart(s, proposal_id):
    s.cart = [item for item in s.cart if item.action.id != proposal_id]
    if meta(s).get("selected") == proposal_id:
        meta(s)["selected"] = None
    service.event(s, "cart_removed", proposal_id)


def checkout_cart(s, items):
    cart.checkout(s, items)
    if meta(s).get("selected") not in {item.action.id for item in s.cart}:
        meta(s)["selected"] = None
