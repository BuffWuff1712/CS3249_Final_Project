import hashlib
import json
from typing import Literal

from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict


from .models import Proposal
from .policy import evaluate
from .shopping_nodes import ShoppingState


class ReviewDecision(BaseModel):
    """Untrusted resume input: identify the exact action being reviewed."""

    model_config = ConfigDict(extra='forbid')
    proposal_id: str
    action_fingerprint: str
    action: Literal['approve', 'reject']


class ReviewState(ShoppingState):
    decision: ReviewDecision | None
    action_fingerprint: str | None


def fingerprint(proposal: Proposal) -> str:
    """Detect action changes; this hash is not authentication or authorization."""
    action = {
        'product': proposal.product.model_dump(mode='json'),
        'payment_method': proposal.payment_method,
        'shares_personal_data': proposal.shares_personal_data,
    }
    encoded = json.dumps(action, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def route_after_policy(state: ReviewState) -> Literal['summarise', 'prepare_review']:
    if state["proposal"] is None or state["violations"]:
        return "summarise"

    return "prepare_review"


def prepare_review_node(state: ReviewState) -> dict:
    """Checkpoint the action fingerprint BEFORE entering the interrupt node."""
    proposal = state['proposal']
    if proposal is None or state['violations']:
        raise ValueError('Only a policy-passing proposal may enter review')
    return {'action_fingerprint': fingerprint(proposal), 'decision': None}


def human_review_node(state: ReviewState) -> dict:
    """Pause, validate a specific decision, and record it without checkout."""
    proposal = state['proposal']
    if proposal is None or proposal.status != 'pending':
        raise ValueError('Review requires a pending proposal')
    if state['violations']:
        raise ValueError('A blocked proposal cannot be approved')

    if fingerprint(proposal) != state['action_fingerprint']:
        raise ValueError('Changed actions require a new policy/review run.')

    payload = {
        "question": 'Do you approve or reject the following purchase?',    
        "proposal_id": proposal.id,
        "action_fingerprint": state['action_fingerprint'],
        "product": proposal.product.model_dump(mode="json"),         
        "payment_method": proposal.payment_method,
        "shares_personal_data": proposal.shares_personal_data,
    }

    raw_decision = interrupt(payload)

    decision = ReviewDecision.model_validate(raw_decision)

    if (decision.proposal_id != proposal.id 
        or decision.action_fingerprint != state['action_fingerprint']):
        raise ValueError("Approval does not target correct action")

    if decision.action == 'reject':
        return {
            "decision": decision,
            "proposal": proposal.model_copy(update={"status": 'rejected'}),
            "outcome": 'Rejected; no checkout occurred'
        }
    
    if decision.action == 'approve':
        reasons = evaluate(proposal, state['preferences'])

        if reasons:
            return {
                "decision": None,
                "proposal": proposal.model_copy(
                    update={
                        "status": "pending",
                        "violations": reasons,
                    }
                ),
                "violations": reasons,
                "outcome": (
                    "Approval blocked: "
                    + "; ".join(reasons)
                    + ". No checkout occurred."
                ),
            }
        
        else:
            return {
                "decision": decision,
                "proposal": proposal.model_copy(
                    update={
                        "status": "approved",
                        "violations": [],
                    }
                ),
                "violations": [],
                "outcome": (
                    "Approval recorded. No checkout occurred."
                ),
            }