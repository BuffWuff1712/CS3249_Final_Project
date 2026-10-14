from uuid import UUID

from app.intent import ShoppingIntent
from app.models import Preferences
from app.shopping_nodes import ShoppingState, search_node, propose_node, check_policy_node, summarise_node


def run_workflow(category='Headphones', maximum_price=100, preferences=None):
    state: ShoppingState = {
        'intent': ShoppingIntent(category=category, maximum_price=maximum_price, currency='SGD'),
        'candidates': [],
        'outcome': '',
        'preferences': preferences if preferences is not None else Preferences(),
        'proposal': None,
        # Ensure the policy node replaces old reasons, including on no-match runs.
        'violations': ['stale reason'],
    }
    # Test extracted nodes without creating a second graph builder.
    for node in (search_node, propose_node, check_policy_node, summarise_node):
        state.update(node(state))
    return state


def test_cheapest_headphones_blocked_by_merchant_restriction():
    result = run_workflow()
    proposal = result['proposal']
    assert proposal.product.id == 'p4'
    assert UUID(proposal.id).version == 4
    assert proposal.status == 'pending'
    assert len(result['violations']) == 1
    assert result['violations'][0].startswith('Merchant:')
    assert proposal.violations == result['violations']
    assert 'is blocked:' in result['outcome']


def test_no_match_has_no_proposal_and_clears_violations():
    result = run_workflow(maximum_price=50)
    assert result['proposal'] is None
    assert result['violations'] == []
    assert result['outcome'] == 'No matching products found.'


def test_earbuds_blocked_by_current_catalogue_substitute_flag():
    # The fixed substitute flag is a mock catalogue limitation, not intent reasoning.
    result = run_workflow(category='Earbuds')
    assert result['proposal'].product.id == 'p3'
    assert result['proposal'].status == 'pending'
    assert len(result['violations']) == 1
    assert result['violations'][0].startswith('Substitution:')
    assert 'is blocked:' in result['outcome']


def test_merchant_absent_from_both_lists_is_still_blocked():
    prefs = Preferences(allowed_merchants=['Northstar', 'Everyday'], restricted_merchants=[])
    result = run_workflow(preferences=prefs)
    assert result['proposal'].product.id == 'p4'
    assert any(reason.startswith('Merchant:') for reason in result['violations'])


def test_policy_pass_is_not_user_approval():
    result = run_workflow(preferences=Preferences(restricted_merchants=[]))
    assert result['proposal'].product.id == 'p4'
    assert result['violations'] == []
    assert result['proposal'].violations == []
    assert result['proposal'].status == 'pending'
    assert 'Awaiting user approval.' in result['outcome']
