from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .models import Product
from .policy import evaluate
from .review import (
    ReviewState,
    fingerprint
)


class SimulatedReceipt(BaseModel):
    """A snapshot of a fictional purchase; never a real payment confirmation."""
    model_config = ConfigDict(extra='forbid')

    id: str
    proposal_id: str
    action_fingerprint: str
    product: Product
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal['SGD', 'USD']
    created_at: datetime
    status: Literal['simulated'] = 'simulated'


class CheckoutState(ReviewState):
    receipt: SimulatedReceipt | None
    checkout_error: str | None


class ReceiptStore:
    """Share one instance across retries; restart loses all receipts.

    The lock groups lookup and insertion for this single-process exercise.
    Use a SQLite transaction and unique proposal key in the persistence stage.
    """
    def __init__(self):
        self.receipts: dict[str, SimulatedReceipt] = {}
        self.lock = Lock()


def checkout_node(state: CheckoutState, store: ReceiptStore) -> dict:
    """Validate and record a simulated checkout, including on duplicate calls."""
    proposal = state['proposal']
    decision = state['decision']

    # Guard this node itself, even when invoked without graph routing.
    error = None
    if proposal is None or decision is None:
        error = 'Missing proposal or decision'
    elif proposal.status != 'approved':
        error = 'Proposal has not been approved'
    elif decision.action != 'approve':
        error = 'Decision does not approve checkout'
    elif decision.proposal_id != proposal.id:
        error = 'Decision targets a different proposal'
    elif not (
        decision.action_fingerprint
        == state['action_fingerprint']
        == fingerprint(proposal)
    ):
        error = 'Approved action has changed or its fingerprint does not match'

    if error is not None:
        return {
            'receipt': None,
            'checkout_error': error,
            'outcome': f'Checkout blocked: {error}. No checkout occurred.',
        }


    # Recheck saved permissions and request constraints before receipt lookup.
    # This standalone graph uses a preferences snapshot. Later integration must
    # supply the latest server-owned preferences before executing checkout.

    reasons = evaluate(proposal, state['preferences'])
    intentions = state['intent']

    if proposal.product.category != intentions.category:
        reasons.append("Category asked for differs from chosen category")
    if proposal.product.currency != intentions.currency:
        reasons.append("Currency asked for differs from chosen currency")
    if intentions.maximum_price is not None:
        if proposal.product.price > intentions.maximum_price:
            reasons.append("Product price exceeds max limit")

    if reasons:
        error = '; '.join(reasons)
        return {
            'decision': None,
            'proposal': proposal.model_copy(update={
                'status': 'pending',
                'violations': reasons,
            }),
            'violations': reasons,
            'receipt': None,
            'checkout_error': error,
            'outcome': f'Checkout blocked: {error}. No checkout occurred.',
        }

    # Keep lookup and insertion under the same lock to prevent duplicate receipts.
    with store.lock:
        existing = store.receipts.get(proposal.id)

        if existing is not None:
            if existing.action_fingerprint != state['action_fingerprint']:
                error = "Approved action has changed or its fingerprint does not match"
                return {
                    "receipt": None,
                    "checkout_error": error,
                    "outcome": f"Checkout blocked: {error}. No checkout occurred.",
                }

            return {
                "receipt": existing.model_copy(deep=True),
                "checkout_error": None,
                "outcome": "Existing simulated receipt returned. No new purchase created.",
            }

        else:
            receipt = SimulatedReceipt(
                id=str(uuid4()),
                proposal_id=proposal.id,
                action_fingerprint=fingerprint(proposal),
                product=proposal.product.model_copy(deep=True),
                amount=proposal.product.price,
                currency=proposal.product.currency,
                created_at=datetime.now(timezone.utc),
                status="simulated",
            )
            # Store a separate copy so callers cannot mutate the saved receipt.
            store.receipts[proposal.id] = receipt.model_copy(deep=True)

            return {
                "receipt": receipt,
                "checkout_error": None,
                "outcome": "Simulated checkout completed. No real payment or order was created."
            }


def route_after_human_review(state: ReviewState) -> Literal['approved', 'not_approved']:
    if (state["proposal"] is not None
        and state["proposal"].status == "approved"
        and state["decision"] is not None
        and state["decision"].action == "approve"
        and len(state["violations"]) == 0):
        return "approved"

    return "not_approved"
