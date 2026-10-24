"""Cart entries retain their original shopping brief, but use current permissions."""
from . import service
from .schemas import CartItem, Approval
from .policy import catalogue, evaluate, fingerprint


def checked_context(session, item):
    context = session.model_copy(deep=True)
    context.brief = {k: v.model_copy(deep=True) for k, v in item.brief.items()}
    action = item.action.model_copy(deep=True)
    current = next((p for p in catalogue(context) if p.id == action.product.id), None)
    if current is None or current != action.product:
        raise ValueError("Product details changed. Remove this item and search again.")
    evaluate(context, action)
    if fingerprint(action) != item.action.fingerprint:
        raise ValueError("Merchant terms or policy changed. Remove this item and search again.")
    if action.decision == "BLOCK":
        raise ValueError(" ".join(r.explanation for r in action.rules if r.decision == "BLOCK"))
    return context, action


def add(session, selection):
    existing = next((i for i in session.cart if i.action.id == selection.proposal_id), None)
    if existing:
        if existing.action.fingerprint != selection.fingerprint:
            raise ValueError("Proposal changed")
        return
    action = next((a for a in session.proposals if a.id == selection.proposal_id), None)
    if not action or action.status != "pending" or action.fingerprint != selection.fingerprint:
        raise ValueError("Request a current proposal before adding to cart")
    if fingerprint(action) != selection.fingerprint:
        raise ValueError("Proposal changed")
    item = CartItem(action=action.model_copy(deep=True), brief=session.brief.copy())
    checked_context(session, item)
    session.cart.append(item.model_copy(deep=True))
    session.stage = "ready"
    service.event(session, "cart_added", action.id)
    service.message(session, f"Added {action.product.name} to your cart! Tell me what else you'd like to find, or let me know when you're ready to check out.")


def review(session):
    rows = []
    for item in session.cart:
        error = ""
        action = item.action
        try:
            _, action = checked_context(session, item)
        except ValueError as exc:
            error = str(exc)
        rows.append({"action": action.model_dump(), "error": error})
    return rows


def checkout(session, selection):
    ids = [i.proposal_id for i in selection.items]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate checkout item")
    # Work on a copy: a failure on any line leaves all receipts and approvals unchanged.
    working = session.model_copy(deep=True)
    for chosen in selection.items:
        receipt = next((r for r in working.receipts if r.proposal_id == chosen.proposal_id), None)
        if receipt:
            if receipt.fingerprint != chosen.fingerprint:
                raise ValueError("Receipt action mismatch")
            continue
        item = next((i for i in working.cart if i.action.id == chosen.proposal_id), None)
        if not item or item.action.fingerprint != chosen.fingerprint:
            raise ValueError("Cart changed. Review it again before checkout.")
        context, action = checked_context(working, item)
        context.approvals.append(Approval(proposal_id=action.id, fingerprint=chosen.fingerprint, action="approve"))
        service.event(context, "approve", action.id)
        service.checkout(context, action)
        working.approvals = context.approvals
        working.receipts = context.receipts
        working.events = context.events
        for original in working.proposals:
            if original.id == action.id:
                original.status = "approved"
        service.event(working, "cart_checkout", action.id)
    working.cart = [i for i in working.cart if i.action.id not in ids]
    if working.proposals and working.proposals[-1].id in ids:
        working.stage = "completed"
    service.message(working, "Simulated checkout complete. Your receipts are in Purchase history. No real order or payment was made.")
    session.__dict__.update(working.__dict__)
