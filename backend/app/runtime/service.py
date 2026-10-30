import json, os, re
from pathlib import Path
from .schemas import Session, Message, Event, Fact, Action, Receipt, Approval
from .policy import FIELDS, search, catalogue, evaluate, fingerprint
from .llm import OpenAIConversation, explain_outcome
from .merchants import merchant_for
from .merchant_risk import load_config, digest
from .shopping_workflow import run_shopping
from .risk_agent import review as review_listing
from .local_evidence import configured_detection, review_view
from .progress import step

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
        s.brief[field] = fact
    else:
        s.brief.pop(field, None)
    s.stage = "ready"
    event(s, "brief_edit", field)
    return s


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
    if s.search_provider == "browser_use":
        s.messages[-1].text = "Hi, I’m Beany. Tell me what you’re shopping for. I can search public product listings using Browser Use. Prices and merchant details need review; checkout here is always simulated."
        if s.search_replay:
            s.messages[-1].text = "Hi, I’m Beany. Tell me what you’re shopping for. This session replays saved study listings instead of searching the web. Prices and merchant details need review; checkout here is always simulated."
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
        if product.source == "browser_use":
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
                    "warning": " ".join(r.explanation for r in a.rules),
                }
            ),
        )
        activity["evidence"] = [product.name, merchant.name]
        activity["label"] += {"ALLOW": " · Within your limits", "REVIEW": " · Needs your approval", "BLOCK": " · Offer blocked"}[a.decision]
    s.stage = "blocked" if a.decision == "BLOCK" else "waiting_review"
    message(
        s,
        f"{product.name} costs {product.currency} {product.price:.2f}. "
        + " ".join(r.explanation for r in a.rules),
    )
    if a.decision != "BLOCK":
        message(s, "Use Select this offer to save this proposal, then Finish decision to explicitly confirm simulated checkout. Or use Add to cart to save items across searches and review them together in Cart. Nothing has been purchased." if s.experiment.get("shop_workspace") else "Would you like to add this to your cart or proceed to checkout? You can review your items before confirming simulated checkout.")
    if a.decision != "ALLOW":
        s.intervention_count += 1
        event(s, "intervention", a.decision)


def chat(s, text):
    text = text.strip()
    if not text:
        raise ValueError("Please enter a message")
    elicitation = json.loads(ELICITATION_PATH.read_text(encoding="utf-8-sig"))
    with step("Reading your request…", "Read your request"):
        result = llm.interpret(s, text)  # Failure leaves persisted state unchanged.
    s.messages.append(Message(role="user", text=text))
    event(s, "user_message", "Message received")
    if result.intent in ("respond", "explain"):
        # Conversation cannot edit the brief, invalidate a proposal, or authorize checkout.
        # The interpreter has current proposal facts; keep its answer to this question
        # instead of replacing it with rules from an unrelated historical proposal.
        event(s, "interpretation", result.model_dump_json())
        message(s, result.reply)
        return s
    if result.intent == "checkout":
        s.stage = "cart_review" if s.cart else "ready"
        s.suggestions = []
        if s.experiment.get("shop_workspace"):
            reply = ("Review the selected offer, then use Finish decision for explicit simulated checkout. Nothing has been purchased yet." if s.experiment["shop_workspace"].get("selected") else "Open Cart, then Review checkout to inspect saved items before Confirm simulated checkout. Nothing has been purchased yet.") if s.cart else "Select a current offer or Add to cart before checkout. No order or payment has been created."
        else:
            reply = "Ready when you are. Select Review cart and checkout below to check your items before confirming. Nothing has been purchased yet." if s.cart else "Your cart is empty. Tell me what you'd like to find first."
        message(s, reply)
        event(s, "cart_review_requested", "User requested checkout review; no purchase authorized")
        return s
    # The interpreter decides whether this is a new task, including within one category.
    if result.intent == "new_task":
        invalidate(s)
        s.brief = {}
        s.rejected_products = []
        s.rejected_merchants = []
        event(s, "brief_reset", "Started a new product request; cart and permissions retained")
    for change in result.changes:
        if change.field == "currency" and change.source == "confirmed" and change.value:
            aliases = {
                "USD": r"\bUSD\b|US\$|US dollars",
                "SGD": r"\bSGD\b|S\$|Singapore dollars",
            }
            if not re.search(aliases.get(change.value, r"(?!)"), text, re.I):
                change.source = "suggested"
                change.value = elicitation["default_currency"]
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
    if (
        result.intent == "clarify"
        and elicitation["skip_optional_questions_when_ready"]
        and all(
            k in s.brief and s.brief[k].source == "confirmed"
            for k in elicitation["ready_fields"]
        )
    ):
        result.intent = "search"
        result.reply = "I have enough information to compare catalogue options. You can refine your brief at any time."
    s.suggestions = result.suggestions[:4]
    event(s, "interpretation", result.model_dump_json())
    if result.intent == "cancel":
        invalidate(s)
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
    if result.intent == "alternative" and s.proposals:
        previous = s.proposals[-1]
        previous.status = (
            "rejected" if previous.status == "pending" else previous.status
        )
        s.rejected_products.append(previous.product.id)
        s.rejected_merchants.append(previous.product.merchant_id)
        event(s, "alternative", previous.id)
    if "category" in s.brief:
        invalidate(s)
        outcome = run_shopping(s)
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
