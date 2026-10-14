"""Interactive structured-intent demo: python -m app.run_workflow.

This runs the graph directly; Beany's HTTP backend still uses its mock agent.
"""
import argparse
import json
import math
from uuid import uuid4

from langgraph.types import Command

from .checkout import CheckoutState, ReceiptStore
from .intent import ShoppingIntent
from .models import Preferences
from .workflow import build_workflow


def main(argv=None):
    parser = argparse.ArgumentParser(description='Beany simulated shopping workflow')
    parser.add_argument('--category', choices=['Headphones', 'Earbuds'], default='Headphones')
    parser.add_argument('--maximum-price', type=float, default=100)
    parser.add_argument('--currency', choices=['SGD', 'USD'], default='SGD')
    parser.add_argument('--allow-market-lane', action='store_true',
                        help='Explicit demo permission to reach review for the cheapest headphones')
    args = parser.parse_args(argv)
    if args.maximum_price <= 0 or not math.isfinite(args.maximum_price):
        parser.error('--maximum-price must be a positive finite number')

    preferences = Preferences()
    if args.allow_market_lane:
        preferences = preferences.model_copy(update={'restricted_merchants': []})
    store = ReceiptStore()
    workflow = build_workflow(store)
    config = {'configurable': {'thread_id': str(uuid4())}}
    initial_state: CheckoutState = {
        'intent': ShoppingIntent(category=args.category, maximum_price=args.maximum_price, currency=args.currency),
        'preferences': preferences,
        'candidates': [], 'proposal': None, 'violations': [], 'outcome': '',
        'decision': None, 'action_fingerprint': None,
        'receipt': None, 'checkout_error': None,
    }
    print('Fictional catalogue. Simulated checkout only. Data is held in memory.')
    result = workflow.invoke(initial_state, config=config)
    if not result.get('__interrupt__'):
        print(result['outcome'])
        return

    payload = result['__interrupt__'][0].value
    print(json.dumps(payload, indent=2))
    while True:
        try:
            action = input('Approve or reject? ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print('\nCancelled. No decision recorded and no checkout occurred.')
            return
        if action in ('approve', 'reject'):
            break
        print('Please type approve or reject.')

    result = workflow.invoke(Command(resume={
        'proposal_id': payload['proposal_id'],
        'action_fingerprint': payload['action_fingerprint'],
        'action': action,
    }), config=config)
    print(result['outcome'])
    proposal, decision, receipt = result['proposal'], result['decision'], result['receipt']
    print('Proposal status:', proposal.status if proposal else None)
    print('Decision:', decision.model_dump() if decision else None)
    print('Checkout error:', result['checkout_error'])
    print('Receipt:', json.dumps(receipt.model_dump(mode='json'), indent=2) if receipt else None)


if __name__ == '__main__':
    main()
