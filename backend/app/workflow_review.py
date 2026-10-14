import hashlib
import json
from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict

from .intent import ShoppingIntent
from .models import Preferences, Proposal
from .policy import evaluate
from .workflow import (
    ShoppingState,
    check_policy_node,
    propose_node,
    search_node,
    summarise_node,
)


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


def build_review_workflow():
    builder = StateGraph(ReviewState)
    builder.add_node('search', search_node)
    builder.add_node('propose', propose_node)
    builder.add_node('check_policy', check_policy_node)
    builder.add_node('summarise', summarise_node)
    builder.add_node('prepare_review', prepare_review_node)
    builder.add_node('human_review', human_review_node)

    builder.add_edge(START, 'search')
    builder.add_edge('search', 'propose')
    builder.add_edge('propose', 'check_policy')


    builder.add_conditional_edges(
        'check_policy', route_after_policy,
        {'summarise': 'summarise', 'prepare_review': 'prepare_review'}
    )

    builder.add_edge('prepare_review', 'human_review')
    builder.add_edge('human_review', END)
    builder.add_edge('summarise', END)

    return builder.compile(checkpointer=InMemorySaver())


def main():
    workflow = build_review_workflow()
    config = {'configurable': {'thread_id': str(uuid4())}}
    initial_state: ReviewState = {
        'intent': ShoppingIntent(category='Headphones', maximum_price=100, currency='SGD'),
        'candidates': [],
        'outcome': '',
        'preferences': Preferences(restricted_merchants=[]),
        'proposal': None,
        'violations': [],
        'decision': None,
        'action_fingerprint': None,
    }

    result = workflow.invoke(initial_state, config=config)

    # Completed runs may omit __interrupt__; avoid calling len(None).
    if not result.get('__interrupt__'):
        print(result["outcome"])
        return

    payload = result['__interrupt__'][0].value
    print(json.dumps(payload, indent=2))

    while True:
        try:
            approval_decision = input('Approve or reject? ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print('\nReview cancelled. No decision recorded; no checkout occurred.')
            return
        if approval_decision in ('approve', 'reject'):
            break
        print('Please type approve or reject.')

    resume_data = {
        'proposal_id': payload['proposal_id'],
        'action_fingerprint': payload['action_fingerprint'],
        'action': approval_decision,
    }

    # Resume the same checkpoint using the same graph instance and thread ID.
    resumed = workflow.invoke(Command(resume=resume_data), config=config)
    print(resumed['outcome'])
    decision = resumed['decision']
    print('Decision:', decision.model_dump() if decision is not None else None)
    proposal = resumed['proposal']
    print('Proposal status:', proposal.status if proposal is not None else None)


if __name__ == '__main__':
    main()
