"""Exercise real checkpoint/interrupt/resume behavior, without mocking policy."""
from uuid import uuid4

import pytest
from langgraph.types import Command

from app.intent import ShoppingIntent
from app.models import Preferences
from app.workflow_review import ReviewState, build_review_workflow


@pytest.fixture
def review_run():
    # A fresh saver per test prevents checkpoint leakage between tests.
    graph = build_review_workflow()
    config = {'configurable': {'thread_id': str(uuid4())}}
    return graph, config


def initial_state(preferences=None, maximum_price=100) -> ReviewState:
    return {
        'intent': ShoppingIntent(category='Headphones', maximum_price=maximum_price, currency='SGD'),
        'candidates': [],
        'outcome': '',
        'preferences': preferences if preferences is not None else Preferences(restricted_merchants=[]),
        'proposal': None,
        'violations': [],
        'decision': None,
        'action_fingerprint': None,
    }


def decision_for(result, action='approve'):
    # Respond to exactly the proposal displayed by the interrupt.
    payload = result['__interrupt__'][0].value
    return {
        'proposal_id': payload['proposal_id'],
        'action_fingerprint': payload['action_fingerprint'],
        'action': action,
    }


def test_passing_proposal_pauses_without_approval(review_run):
    graph, config = review_run
    result = graph.invoke(initial_state(), config=config)

    assert len(result['__interrupt__']) == 1
    assert result['proposal'].product.id == 'p4'
    assert result['proposal'].status == 'pending'
    assert result['decision'] is None
    payload = result['__interrupt__'][0].value
    assert payload['proposal_id'] == result['proposal'].id
    assert payload['action_fingerprint'] == result['action_fingerprint']
    assert payload['product']['id'] == 'p4'


def test_matching_approval_resumes_same_proposal(review_run):
    graph, config = review_run
    paused = graph.invoke(initial_state(), config=config)
    response = decision_for(paused)
    result = graph.invoke(Command(resume=response), config=config)

    assert not result.get('__interrupt__')
    assert not graph.get_state(config).next
    assert result['proposal'].id == paused['proposal'].id
    assert result['proposal'].status == 'approved'
    assert result['decision'].model_dump() == response
    assert result['violations'] == []
    assert 'No checkout occurred' in result['outcome']


def test_rejection_resumes_without_approval(review_run):
    graph, config = review_run
    paused = graph.invoke(initial_state(), config=config)
    response = decision_for(paused, action='reject')
    result = graph.invoke(Command(resume=response), config=config)

    assert not result.get('__interrupt__')
    assert not graph.get_state(config).next
    assert result['proposal'].id == paused['proposal'].id
    assert result['proposal'].status == 'rejected'
    assert result['decision'].model_dump() == response
    assert 'no checkout occurred' in result['outcome']


@pytest.mark.parametrize('field', ['proposal_id', 'action_fingerprint'])
def test_mismatched_approval_is_rejected(review_run, field):
    graph, config = review_run
    paused = graph.invoke(initial_state(), config=config)
    response = decision_for(paused)
    response[field] = 'wrong-value'

    with pytest.raises(ValueError, match='Approval does not target correct action'):
        graph.invoke(Command(resume=response), config=config)

    state = graph.get_state(config).values
    assert state['proposal'].status == 'pending'
    assert state['decision'] is None


def test_changed_product_invalidates_old_approval(review_run):
    graph, config = review_run
    paused = graph.invoke(initial_state(), config=config)
    response = decision_for(paused)
    proposal = paused['proposal']
    changed_product = proposal.product.model_copy(update={'price': 80.0})
    changed_proposal = proposal.model_copy(update={'product': changed_product})

    # Test-only checkpoint edit: preserve the old fingerprint to simulate a
    # changed action. Keep human_review as the next node; no production edit API.
    graph.update_state(config, {'proposal': changed_proposal}, as_node='prepare_review')

    with pytest.raises(ValueError, match='Changed actions require a new policy/review run'):
        graph.invoke(Command(resume=response), config=config)

    state = graph.get_state(config).values
    assert state['proposal'].status == 'pending'
    assert state['decision'] is None


def test_lower_budget_while_paused_blocks_approval(review_run):
    graph, config = review_run
    paused = graph.invoke(initial_state(), config=config)
    response = decision_for(paused)
    stricter_preferences = paused['preferences'].model_copy(update={'budget': 50.0})

    # This verifies the graph's policy recheck using updated checkpoint state.
    # It does not imply integration with a live preference database exists.
    graph.update_state(config, {'preferences': stricter_preferences}, as_node='prepare_review')
    result = graph.invoke(Command(resume=response), config=config)

    assert result['proposal'].status == 'pending'
    assert result['decision'] is None
    assert any(reason.startswith('Budget:') for reason in result['violations'])
    assert result['proposal'].violations == result['violations']
    assert 'Approval blocked:' in result['outcome']
    assert not result.get('__interrupt__')


def test_restricted_merchant_never_requests_approval(review_run):
    graph, config = review_run
    result = graph.invoke(initial_state(preferences=Preferences()), config=config)

    assert not result.get('__interrupt__')
    assert not graph.get_state(config).next
    assert result['proposal'].status == 'pending'
    assert result['decision'] is None
    assert any(reason.startswith('Merchant:') for reason in result['violations'])
    assert 'is blocked:' in result['outcome']


def test_no_match_never_requests_approval(review_run):
    graph, config = review_run
    result = graph.invoke(initial_state(maximum_price=50), config=config)

    assert not result.get('__interrupt__')
    assert not graph.get_state(config).next
    assert result['proposal'] is None
    assert result['decision'] is None
    assert result['violations'] == []
    assert result['outcome'] == 'No matching products found.'
