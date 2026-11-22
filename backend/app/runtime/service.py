import json, os, re
from pathlib import Path
from .schemas import Session, Message, Event, Fact, Action, Receipt, Approval
from .policy import FIELDS, search, catalogue, evaluate, fingerprint, reasons
from .llm import OpenAIConversation, explain_outcome
from .merchants import merchant_for
from .merchant_risk import load_config, digest
from .shopping_workflow import run_shopping
from .shopping_tools import listed_spelling
from .risk_agent import review as review_listing
from .local_evidence import configured_detection, review_view
from .progress import step

from .timing import timed
llm = OpenAIConversation()
ELICITATION_PATH = Path(__file__).resolve().parents[2] / "config/elicitation.json"


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
    if field == "category":
        category = fact.value.strip()

        if not category:
            raise ValueError("Please enter a product category")

        fact.value = category


def edit(s, field, fact):
    validate_fact(field, fact)
    invalidate(s)
    if fact:
        fact.value = listed_spelling(s, field, fact.value)
        s.brief[field] = fact
    else:
        s.brief.pop(field, None)
    s.stage = "ready"
    event(s, "brief_edit", field)
    return s


def switches_category(s, changes, text):
    old = s.brief.get("category")
    return bool(old) and any(
        c.field == "category" and c.value and c.value.casefold() != old.value.casefold()
        and (c.source != "confirmed" or (c.evidence.strip() and c.evidence.casefold() in text.casefold()))
        for c in changes
    )


def reset_request(s):
    invalidate(s)
    s.task_start_message = max(0, len(s.messages) - 1)
    s.search_requested = False
    s.brief = {}
    s.clarification_asked = []
    s.clarification_answers = {}
    s.rejected_products = []
    s.rejected_merchants = []
    event(s, "brief_reset", "Started a new product request; cart and permissions retained")


def create(*, search_provider=None):
    from .browser_search import configured_provider, configured_replay
    s = Session(mode=os.getenv("BEANY_LLM_MODE", "openai"), search_provider=search_provider or configured_provider(),
                risk_detection=configured_detection())
    if s.search_provider == "browser_use":
        s.search_replay = configured_replay()
    config = load_config()
    s.experiment = {
        "profile": "standard",
        "risk_config": config.model_dump(),
        "config_hash": digest(config),
        "configuration_history": {
            digest(config): {"profile": "standard", "risk_config": config.model_dump()}
        },
    }
    message(
        s,
        "Hi, I’m Beany. Tell me what you’re shopping for, even if you’re unsure. We can compare fictional running shoes, headphones and backpacks. All purchases are simulated. You control the brief and permissions.",
    )
    if s.search_provider != "catalogue":
        s.messages[-1].text = "Hi, I’m Beany! Tell me what you’re shopping for, even if you’re unsure. I’ll help you find and compare options that fit your needs."
        if s.search_replay:
            s.messages[-1].text += " This session replays saved study listings rather than current store listings."
    event(s, "session_started", "Fresh shopping session")
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


@timed("recommendation.propose")
def propose(s, product=None, *, recommendations=None, **kwargs):
    invalidate(s)
    s.recommendations = search(s) if recommendations is None else recommendations
    if product is None:
        if not s.recommendations:
            s.stage = "no_match"
            message(
                s,
                "No products match these constraints. You can edit your brief or ask to explore alternatives; I have not relaxed your limits.",
            )
            event(s, "no_match", "No matching products")
            return
        product = s.recommendations[0]
    with step(f"Checking {product.name} and {product.merchant}…", "Checked seller terms, budget and permissions") as activity:
        merchant = merchant_for(product, s)
        if product.source in ("browser_use", "shopify_catalog"):
            # One cached agent review per snapshot; later policy rechecks reuse it.
            review_listing(s, product, merchant)
        elif s.risk_detection == "ai":
            # Local products are reviewed as the listing a shopper would read.
            review_listing(s, review_view(product, merchant), merchant)
        allowed = [
            m for m in s.permissions.payment_methods if m in merchant.payment_methods
        ]
        kwargs.setdefault("payment_method", allowed[0] if allowed else "Demo Visa")
        kwargs.setdefault("shares_personal_data", bool(merchant.requested_information))
        a = Action(
            product=product.model_copy(deep=True),
            merchant_details=merchant.model_copy(deep=True),
            **kwargs,
        )
        evaluate(s, a)
        a.fingerprint = fingerprint(a)
        s.proposals.append(a)
        event(s, "search", f"Compared {len(s.recommendations)} matches")
        event(s, "policy", json.dumps([r.model_dump() for r in a.rules]))
        event(
            s,
            "merchant_assessment",
            json.dumps(
                {
                    "proposal_id": a.id,
                    "product_id": a.product.id,
                    "merchant_id": a.product.merchant_id,
                    "risk": a.risk.model_dump() if a.risk else None,
                    "decision": a.decision,
                    "warning": reasons(a),
                }
            ),
        )
        activity["evidence"] = [product.name, merchant.name]
        activity["label"] += {"ALLOW": " · Within your limits", "REVIEW": " · Needs your approval", "BLOCK": " · Offer blocked"}[a.decision]
    s.stage = "blocked" if a.decision == "BLOCK" else "waiting_review"
    message(
        s,
        f"{product.name} costs {product.currency} {product.price:.2f}. "
        + reasons(a),
    )
    if a.decision != "BLOCK":
        message(s, "Use Select this offer to save this proposal, then Finish decision to explicitly confirm simulated checkout. Or use Add to cart to save items across searches and review them together in Cart. Nothing has been purchased." if s.experiment.get("shop_workspace") else "Would you like to add this to your cart or proceed to checkout? You can review your items before confirming simulated checkout.")
    if a.decision != "ALLOW":
        s.intervention_count += 1
        event(s, "intervention", a.decision)


@timed("conversation.process")
def chat(s, text):
    text = text.strip()
    if not text:
        raise ValueError("Please enter a message")
    elicitation = json.loads(ELICITATION_PATH.read_text(encoding="utf-8-sig"))
    with step("Reading your request…", "Read your request"):
        result = llm.interpret(s, text)  # Failure leaves persisted state unchanged.
    s.messages.append(Message(role="user", text=text))
    event(s, "user_message", "Message received")
    from .clarification import resume_uncertainty
    previous_search_requested = s.search_requested
    if result.search_control == "defer":
        s.search_requested = False
    elif result.search_control == "request" or result.intent in ("search", "alternative"):
        s.search_requested = True
    resume_uncertainty(s, result, text)
    if result.intent == "checkout":
        s.search_requested = False
        s.stage = "cart_review" if s.cart else "ready"
        s.suggestions = []
        if s.experiment.get("shop_workspace"):
            reply = ("Review the selected offer, then use Finish decision for explicit simulated checkout. Nothing has been purchased yet." if s.experiment["shop_workspace"].get("selected") else "Open Cart, then Review checkout to inspect saved items before Confirm simulated checkout. Nothing has been purchased yet.") if s.cart else "Select a current offer or Add to cart before checkout. No order or payment has been created."
        else:
            reply = "Ready when you are. Select Review cart and checkout below to check your items before confirming. Nothing has been purchased yet." if s.cart else "Your cart is empty. Tell me what you'd like to find first."
        message(s, reply)
        event(s, "cart_review_requested", "User requested checkout review; no purchase authorized")
        return s
    # Only an interpreted new task resets the brief; subtype wording is a refinement.
    if result.intent == "new_task":
        # An intent label alone must never erase a confirmed brief.
        from .preferences import grounded_change
        evidence = result.new_task_evidence.strip()
        grounded_family = any(c.field == "category" and c.value and c.source == "confirmed"
                              and grounded_change(s, c, text, allow_history=False)
                              for c in result.changes)
        if grounded_family and evidence and evidence.casefold() in text.casefold():
            reset_request(s)
            s.search_requested = result.search_control == "request"
            result.intent = "search" if s.search_requested else "respond"
        else:
            s.search_requested = previous_search_requested
            event(s, "protected_task", "New-task reset lacked grounded explicit evidence")
            message(s, "Are you starting a new shopping task, or changing the current one? Your existing preferences are still saved.")
            return s
    for change in result.changes:
        unknown_fields = {"product_type": "category", "budget": "budget", "features": "features"}
        if change.value is None and any(
            a.status == "unknown" and unknown_fields[a.field] == change.field
            for a in result.clarification_answers
        ):
            event(s, "protected_constraint", change.field)
            continue
        if change.field == "currency" and change.source == "confirmed" and change.value:
            aliases = {
                "USD": r"\bUSD\b|US\$|US dollars",
                "SGD": r"\bSGD\b|S\$|Singapore dollars",
            }
            if not re.search(aliases.get(change.value, r"(?!)"), text, re.I):
                change.source = "suggested"
                change.value = elicitation["default_currency"]
        old = s.brief.get(change.field)
        from .preferences import grounded_change, apply_change
        grounded = grounded_change(s, change, text, allow_history=result.intent != "new_task")
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
        fact = apply_change(old, change, fact)
        edit(s, change.field, fact)
        if old:
            event(s, "refine", change.field)
    if result.intent == "clarify" or (s.search_requested and result.intent in ("search", "alternative")):
        from .clarification import clarify_before_search
        type_was_missing = s.clarification_answers.get("product_type") == "missing"
        question = clarify_before_search(s, result, text)
        if question:
            if (result.intent != "clarify" or "category" in s.brief
                or any(a.field == "product_type" and a.status == "provided" for a in result.clarification_answers)
                or any(c.field == "category" for c in result.changes)):
                result.reply = question
            result.intent = "clarify"
            result.suggestions = ["I'm unsure about those; show me some options"]

    s.suggestions = result.suggestions[:4]
    event(s, "interpretation", result.model_dump_json())
    if result.intent == "cancel":
        invalidate(s)
        s.search_requested = False
        s.stage = "cancelled"
        event(s, "cancel", "Task cancelled")
        message(s, "Cancelled. No pending proposal can be approved.")
        return s
    if result.intent == "clarify":
        message(s, result.reply)
        s.clarification_count += 1
        s.stage = "clarifying"
        event(s, "clarification", "Question asked")
        return s
    if result.intent in ("respond", "explain") or not s.search_requested:
        message(s, result.reply)
        return s
    if result.intent == "alternative" and s.proposals:
        previous = s.proposals[-1]
        previous.status = (
            "rejected" if previous.status == "pending" else previous.status
        )
        s.rejected_products.append(previous.product.id)
        s.rejected_merchants.append(previous.product.merchant_id)
        event(s, "alternative", previous.id)
    if result.intent in ("search", "alternative") and "category" in s.brief:
        s.search_requested = False
        invalidate(s)
        from .search_errors import SearchProviderError, report_failure, USER_MESSAGE, ACTIONS
        try:
            outcome = run_shopping(s)
        except SearchProviderError as exc:
            report_failure(s, exc)
            s.stage = "ready"
            s.suggestions = []
            action = ACTIONS.get(exc.reason, ACTIONS["unknown"])
            message(s, USER_MESSAGE + " " + action)
            return s
        event(s, "shopping_result", outcome.model_dump_json())
        if outcome.status != "proposed":
            s.stage = "no_match" if outcome.status == "no_match" else "ready"
            message(s, (
                "No products match these constraints. You can refine your brief; I have not relaxed your limits."
                if outcome.status == "no_match" else
                "I couldn't complete the product comparison. No new proposal or checkout was created. You can retry or refine your brief."
            ))
            return s
        first_message = len(s.messages)
        propose(s, outcome.product, recommendations=outcome.candidates)
        with step("Preparing your recommendation…", "Prepared your recommendation"):
            explanation = explain_outcome(s)
            # One response per shopping turn, including the deterministic fallback.
            fallback = " ".join(m.text for m in s.messages[first_message:])
            del s.messages[first_message:]
            message(s, explanation or fallback)
        if type_was_missing and s.clarification_answers.get("product_type") == "unknown":
            s.messages[-1].text += f" You didn't name a specific type, so I searched {s.brief['category'].value}, the closest catalogue category. Tell me if you meant something else."
        if explanation:
            event(s, "outcome_explanation", "Explained verified shopping result")
        elif s.mode != "mock":
            event(
                s, "explanation_fallback", "Displayed deterministic policy explanation"
            )
    else:
        message(s, result.reply)
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
    if fingerprint(a) != a.fingerprint:
        raise ValueError(
            "Risk configuration or merchant terms changed. Request a new proposal."
        )
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
        s.rejected_merchants.append(a.product.merchant_id)
        s.stage = "rejected"
        message(s, "Rejected. Ask for an alternative or refine your brief.")
        s.suggestions = ["Find an alternative", "Cancel this task"]
    return s


def alternative(s):
    if s.proposals:
        previous = s.proposals[-1]
        if previous.status == "pending":
            previous.status = "rejected"
        s.rejected_products.append(previous.product.id)
        s.rejected_merchants.append(previous.product.merchant_id)
        event(s, "alternative", previous.id)
    propose(s)
