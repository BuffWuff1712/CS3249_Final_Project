import json, os
from .schemas import Session, Message, Event, Fact, Action, Receipt, Approval
from .policy import FIELDS, search, catalogue, evaluate, fingerprint
from .llm import OpenAIConversation, explain_outcome

llm = OpenAIConversation()


def event(s, kind, detail):
    s.events.append(Event(kind=kind, detail=detail))


def message(s, text):
    s.messages.append(Message(role="assistant", text=text))


def invalidate(s):
    for a in s.proposals:
        if a.status == "pending":
            a.status = "superseded"
    s.recommendations = []


def validate_fact(field, fact):
    if field not in FIELDS:
        raise ValueError("Unknown brief field")
    if fact is None:
        return
    if len(fact.value) > 500:
        raise ValueError("Preference is too long")
    if field == "budget":
        import math

        try:
            amount = float(fact.value)
        except ValueError:
            raise ValueError("Budget must be a positive number")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Budget must be a positive number")
    if field == "currency" and fact.value not in ("SGD", "USD"):
        raise ValueError("Currency must be SGD or USD")
    if field == "category" and fact.value not in (
        "Running shoes",
        "Headphones",
        "Backpacks",
    ):
        raise ValueError("Choose Running shoes, Headphones or Backpacks")


def edit(s, field, fact):
    validate_fact(field, fact)
    invalidate(s)
    if fact:
        s.brief[field] = fact
    else:
        s.brief.pop(field, None)
    s.stage = "ready"
    event(s, "brief_edit", field)
    return s


def create():
    s = Session(mode=os.getenv("BEANY_LLM_MODE", "openai"))
    message(
        s,
        "Hi, I’m Beany. Tell me what you’re shopping for, even if you’re unsure. We can compare fictional running shoes, headphones and backpacks. All purchases are simulated. You control the brief and permissions.",
    )
    event(s, "session_started", "Fresh fictional participant session")
    return s


def checkout(s, a):
    existing = next((r for r in s.receipts if r.proposal_id == a.id), None)
    if existing:
        if existing.fingerprint != fingerprint(a):
            raise ValueError("Receipt action mismatch")
        return
    if a.status != "pending":
        raise ValueError("Only a current pending action can be checked out")
    evaluate(s, a)
    approval = next(
        (
            x
            for x in s.approvals
            if x.proposal_id == a.id
            and x.action == "approve"
            and x.fingerprint == fingerprint(a)
        ),
        None,
    )
    if (
        a.fingerprint != fingerprint(a)
        or a.decision == "BLOCK"
        or (a.decision == "REVIEW" and approval is None)
    ):
        raise ValueError("Checkout is not authorized")
    a.status = "approved"
    s.receipts.append(
        Receipt(
            proposal_id=a.id,
            fingerprint=a.fingerprint,
            product=a.product.model_copy(deep=True),
        )
    )
    s.stage = "completed"
    event(s, "simulated_checkout", a.id)
    message(s, "Simulated checkout complete. No real order or payment was created.")


def propose(s, product=None, **kwargs):
    invalidate(s)
    s.recommendations = search(s)
    if product is None:
        if not s.recommendations:
            s.stage = "no_match"
            message(
                s,
                "No fictional products match these constraints. You can edit your brief or ask to explore alternatives; I have not relaxed your limits.",
            )
            event(s, "no_match", "No matching products")
            return
        product = s.recommendations[0]
    kwargs.setdefault("payment_method", s.permissions.payment_methods[0] if s.permissions.payment_methods else "Demo Visa")
    a = Action(product=product.model_copy(deep=True), **kwargs)
    a.fingerprint = fingerprint(a)
    evaluate(s, a)
    s.proposals.append(a)
    event(s, "search", f"Compared {len(s.recommendations)} matches")
    event(s, "policy", json.dumps([r.model_dump() for r in a.rules]))
    s.stage = "blocked" if a.decision == "BLOCK" else "waiting_review"
    message(
        s,
        f"{product.name} costs {product.currency} {product.price:.2f}. "
        + " ".join(r.explanation for r in a.rules),
    )
    if a.decision == "ALLOW":
        checkout(s, a)
    else:
        s.intervention_count += 1
        event(s, "intervention", a.decision)


def chat(s, text):
    text = text.strip()
    if not text:
        raise ValueError("Please enter a message")
    result = llm.interpret(s, text)  # Failure leaves persisted state unchanged.
    s.messages.append(Message(role="user", text=text))
    event(s, "user_message", "Message received")
    if result.intent == "new_task":
        invalidate(s)
        s.brief = {}
        s.rejected_products = []
    for change in result.changes:
        old = s.brief.get(change.field)
        grounded = (
            bool(change.evidence.strip())
            and change.evidence.casefold() in text.casefold()
        )
        if change.source == "confirmed" and not grounded:
            event(s, "unverified_change", change.field)
            continue
        if old and old.source == "confirmed" and change.source != "confirmed":
            event(s, "protected_constraint", change.field)
            continue
        fact = (
            Fact(value=change.value, source=change.source, hard=change.hard)
            if change.value is not None
            else None
        )
        if fact is None and change.source != "confirmed":
            continue
        edit(s, change.field, fact)
        if old:
            event(s, "refine", change.field)
    s.suggestions = result.suggestions[:4]
    message(s, result.reply)
    event(s, "interpretation", result.model_dump_json())
    if result.intent == "cancel":
        invalidate(s)
        s.stage = "cancelled"
        event(s, "cancel", "Task cancelled")
        message(s, "Cancelled. No pending proposal can be approved.")
        return s
    if result.question and result.intent == "clarify":
        s.clarification_count += 1
        s.stage = "clarifying"
        message(s, result.question)
        event(s, "clarification", "Question asked")
        return s
    if result.intent == "explain":
        if s.proposals:
            message(s, " ".join(r.explanation for r in s.proposals[-1].rules))
        return s
    if result.intent == "alternative" and s.proposals:
        s.rejected_products.append(s.proposals[-1].product.id)
    if "category" in s.brief:
        propose(s)
        explanation = explain_outcome(s)
        if explanation:
            message(s, explanation)
        elif s.mode != "mock":
            event(
                s, "explanation_fallback", "Displayed deterministic policy explanation"
            )
    return s


def decide(s, pid, request):
    a = next((a for a in s.proposals if a.id == pid), None)
    if a is None:
        raise LookupError("Proposal not found")
    if request.fingerprint != a.fingerprint or fingerprint(a) != a.fingerprint:
        raise ValueError("Product details changed. Request a new proposal.")
    prior = next((x for x in s.approvals if x.proposal_id == pid), None)
    if prior:
        if prior.action != request.action:
            raise ValueError("This decision is already resolved")
        return s
    if a.status != "pending":
        raise ValueError("This proposal is no longer current")
    # Re-read catalogue so price/availability edits cannot retain an old approval.
    current = next((p for p in catalogue(s) if p.id == a.product.id), None)
    if current is None or current != a.product:
        raise ValueError("Catalogue changed. Request a fresh proposal.")
    evaluate(s, a)
    if request.action == "approve" and a.decision == "BLOCK":
        raise ValueError(
            "Hard-blocked action. Explicitly change the relevant constraint and request a new proposal."
        )
    s.approvals.append(
        Approval(proposal_id=pid, fingerprint=a.fingerprint, action=request.action)
    )
    event(s, request.action, pid)
    if request.action == "approve":
        checkout(s, a)
    else:
        a.status = "rejected"
        s.rejected_products.append(a.product.id)
        s.stage = "rejected"
        message(s, "Rejected. Ask for an alternative or refine your brief.")
        s.suggestions = ["Find an alternative", "Cancel this task"]
    return s
