"""Deterministic permissions; agent output never grants authority."""
from .models import Preferences, Proposal


def evaluate(proposal: Proposal, prefs: Preferences) -> list[str]:
    p = proposal.product
    reasons = []
    if p.currency != prefs.currency:
        reasons.append(f'Currency: product is priced in {p.currency}, but your boundary is {prefs.currency}. No exchange rate is assumed.')
    if p.price > prefs.budget:
        reasons.append(f'Budget: {p.currency} {p.price:.2f} exceeds your {prefs.currency} {prefs.budget:.2f} limit.')
    if p.merchant in prefs.restricted_merchants or p.merchant not in prefs.allowed_merchants:
        reasons.append(f'Merchant: {p.merchant} is restricted or absent from your allowed list.')
    if p.substitute and not prefs.substitutions:
        reasons.append('Substitution: earbuds replace the requested headphones; substitutions are disabled.')
    if proposal.payment_method not in prefs.payment_methods:
        reasons.append(f'Payment: {proposal.payment_method} is not permitted.')
    if proposal.shares_personal_data and not prefs.share_personal_data:
        reasons.append('Privacy: this proposal would share personal data without permission.')
    return reasons
