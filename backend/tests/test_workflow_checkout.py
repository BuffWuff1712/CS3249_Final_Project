import pytest
pytest.importorskip('langgraph', reason='Optional legacy learning exercises')
"""Receipt safeguards and complete approval-to-checkout graph tests."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from langgraph.types import Command

from app.agent import CATALOGUE
from app.intent import ShoppingIntent
from app.models import Preferences, Proposal
from app.checkout import ReceiptStore, checkout_node
from app.workflow import build_workflow
from app.review import ReviewDecision, fingerprint


def approved_state():
    proposal = Proposal(id=str(uuid4()), product=CATALOGUE[0].model_copy(deep=True), status='approved')
    digest = fingerprint(proposal)
    return {
        'intent': ShoppingIntent(category='Headphones', maximum_price=100, currency='SGD'),
        'preferences': Preferences(),
        'proposal': proposal,
        'decision': ReviewDecision(proposal_id=proposal.id, action_fingerprint=digest, action='approve'),
        'action_fingerprint': digest,
        'violations': [], 'receipt': None, 'checkout_error': None,
    }


def test_new_receipt_contains_approved_action_snapshot():
    state, store = approved_state(), ReceiptStore()
    result = checkout_node(state, store)
    receipt = result['receipt']
    assert result['checkout_error'] is None
    assert receipt.status == 'simulated'
    assert receipt.proposal_id == state['proposal'].id
    assert receipt.action_fingerprint == state['action_fingerprint']
    assert receipt.product.id == 'p1'
    assert receipt.amount == 89 and receipt.currency == 'SGD'
    assert receipt.created_at.utcoffset().total_seconds() == 0
    assert len(store.receipts) == 1
    assert 'No real payment or order' in result['outcome']


def test_retry_returns_same_receipt_without_exposing_stored_copy():
    state, store = approved_state(), ReceiptStore()
    first = checkout_node(state, store)['receipt']
    second = checkout_node(state, store)['receipt']
    assert first == second
    assert first is not second
    assert len(store.receipts) == 1
    first.product.name = 'Changed first response'
    second.product.name = 'Changed retry response'
    saved = store.receipts[state['proposal'].id]
    assert saved.product.name == 'Everyday Quiet Headphones'
    state['proposal'].product.attributes.append('Changed original product')
    assert 'Changed original product' not in saved.product.attributes


def test_reused_id_for_changed_action_cannot_overwrite_receipt():
    state, store = approved_state(), ReceiptStore()
    original = checkout_node(state, store)['receipt']
    changed = state['proposal'].product.model_copy(update={'price': 90})
    state['proposal'] = state['proposal'].model_copy(update={'product': changed})
    state['action_fingerprint'] = fingerprint(state['proposal'])
    state['decision'] = state['decision'].model_copy(update={'action_fingerprint': state['action_fingerprint']})
    result = checkout_node(state, store)
    assert result['receipt'] is None and result['checkout_error']
    assert store.receipts[state['proposal'].id] == original


def test_retry_still_checks_policy_before_returning_receipt():
    state, store = approved_state(), ReceiptStore()
    original = checkout_node(state, store)['receipt']
    state['preferences'] = Preferences(budget=50)
    result = checkout_node(state, store)
    assert result['receipt'] is None and result['decision'] is None
    assert any(reason.startswith('Budget:') for reason in result['violations'])
    assert store.receipts[state['proposal'].id] == original


def test_concurrent_retries_create_only_one_receipt():
    state, store = approved_state(), ReceiptStore()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: checkout_node(state, store), range(16)))
    assert all(result['checkout_error'] is None for result in results)
    assert len({result['receipt'].id for result in results}) == 1
    assert len({result['receipt'].created_at for result in results}) == 1
    assert len(store.receipts) == 1


def start_checkout(preferences=None, maximum_price=100):
    store = ReceiptStore()
    graph = build_workflow(store)
    config = {'configurable': {'thread_id': str(uuid4())}}
    state = {
        'intent': ShoppingIntent(category='Headphones', maximum_price=maximum_price, currency='SGD'),
        'preferences': preferences if preferences is not None else Preferences(restricted_merchants=[]),
        'candidates': [], 'outcome': '', 'proposal': None, 'violations': [],
        'decision': None, 'action_fingerprint': None,
        'receipt': None, 'checkout_error': None,
    }
    result = graph.invoke(state, config=config)
    return graph, config, store, result


def resume_decision(paused, action='approve'):
    payload = paused['__interrupt__'][0].value
    return {
        'proposal_id': payload['proposal_id'],
        'action_fingerprint': payload['action_fingerprint'],
        'action': action,
    }


def test_graph_waits_for_approval_before_creating_receipt():
    graph, config, store, paused = start_checkout()
    assert paused['__interrupt__']
    assert paused['proposal'].status == 'pending'
    assert paused['decision'] is None and paused['receipt'] is None
    assert store.receipts == {}

    result = graph.invoke(Command(resume=resume_decision(paused)), config=config)
    assert result['proposal'].status == 'approved'
    assert result['receipt'].proposal_id == paused['proposal'].id
    assert result['receipt'].action_fingerprint == paused['action_fingerprint']
    assert result['receipt'].product.id == 'p4'
    assert result['receipt'].amount == 79
    assert result['checkout_error'] is None
    assert len(store.receipts) == 1
    assert not graph.get_state(config).next


def test_graph_rejection_ends_without_checkout():
    graph, config, store, paused = start_checkout()
    result = graph.invoke(Command(resume=resume_decision(paused, 'reject')), config=config)
    assert result['proposal'].status == 'rejected'
    assert result['receipt'] is None and store.receipts == {}
    assert result['checkout_error'] is None
    assert not graph.get_state(config).next


@pytest.mark.parametrize('preferences,maximum_price', [(Preferences(), 100), (None, 50)])
def test_graph_blocked_or_no_match_never_creates_receipt(preferences, maximum_price):
    graph, config, store, result = start_checkout(preferences, maximum_price)
    assert not result.get('__interrupt__')
    assert result['decision'] is None and result['receipt'] is None
    assert store.receipts == {}
    assert not graph.get_state(config).next


def test_graph_rechecks_lower_budget_after_pause():
    graph, config, store, paused = start_checkout()
    graph.update_state(config, {'preferences': Preferences(budget=50, restricted_merchants=[])}, as_node='prepare_review')
    result = graph.invoke(Command(resume=resume_decision(paused)), config=config)
    assert result['proposal'].status == 'pending'
    assert result['decision'] is None and result['receipt'] is None
    assert any(reason.startswith('Budget:') for reason in result['violations'])
    assert store.receipts == {}


@pytest.mark.parametrize('field', ['proposal_id', 'action_fingerprint'])
def test_graph_mismatched_approval_cannot_create_receipt(field):
    graph, config, store, paused = start_checkout()
    response = resume_decision(paused)
    response[field] = 'wrong-value'
    with pytest.raises(ValueError, match='Approval does not target correct action'):
        graph.invoke(Command(resume=response), config=config)
    assert store.receipts == {}


def test_graph_changed_product_rejects_old_approval():
    graph, config, store, paused = start_checkout()
    changed = paused['proposal'].product.model_copy(update={'price': 80})
    proposal = paused['proposal'].model_copy(update={'product': changed})
    graph.update_state(config, {'proposal': proposal}, as_node='prepare_review')
    with pytest.raises(ValueError, match='Changed actions require a new policy/review run'):
        graph.invoke(Command(resume=resume_decision(paused)), config=config)
    assert store.receipts == {}
