from typing import TypedDict
from uuid import uuid4

from .catalogue import search_catalogue
from .intent import ShoppingIntent
from .models import Product, Preferences, Proposal
from .policy import evaluate

class ShoppingState(TypedDict):
    """Data passed between graph nodes."""

    intent: ShoppingIntent
    candidates: list[Product]
    outcome: str
    preferences: Preferences
    proposal: Proposal | None
    violations: list[str]


def search_node(state: ShoppingState) -> dict:
    """Search the catalogue using the structured intent."""

    intent = state['intent']
    products = search_catalogue(intent)

    # Return an update rather than mutating state directly.
    return {"candidates": products}


def propose_node(state: ShoppingState) -> dict:
    """Select the cheapest candidate and create a pending proposal."""

    candidates = state['candidates']

    if len(candidates) == 0:
        return {"proposal": None}

    selected = min(candidates, key=lambda product: (product.price, product.id))
    proposed_product = Proposal(id=str(uuid4()), product=selected)

    return {"proposal": proposed_product}



def check_policy_node(state: ShoppingState) -> dict:
    """Evaluate saved permissions without approving the proposal."""

    proposal, preferences = state['proposal'], state['preferences']
    if proposal is None:
        return {'violations': []}

    reasons = evaluate(proposal, preferences)

    # Keep the API-facing proposal and the graph's violation field consistent.
    checked_proposal = proposal.model_copy(update={'violations': reasons})
    return {'proposal': checked_proposal, 'violations': reasons}

def summarise_node(state: ShoppingState) -> dict:
    """Explain whether the proposed product passes policy; never approve it."""
    proposal, violations = state['proposal'], state['violations']

    if proposal is None:
        outcome = "No matching products found."
    elif violations:
        outcome = f"{proposal.product.name} is blocked: " + '; '.join(violations)
    else:
        outcome = f"{proposal.product.name} passes policy checks. Awaiting user approval."

    return {"outcome": outcome}