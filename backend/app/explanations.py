from .models import Proposal


def explain(proposal: Proposal) -> str:
    if proposal.violations:
        return 'This proposed selection differs from your boundaries. Approval is blocked until you refine the selection or explicitly update your permissions. No purchase will be made.'
    return 'This selection fits your current boundaries. Approve records a simulated decision only; no payment or order is created.'
