"""Bounded discovery: Shopify first; Browser Use only when Shopify returns no eligible offers."""
from contextvars import ContextVar
from contextlib import contextmanager
from .progress import check_cancelled, step
from .search_errors import SearchProviderError, report_failure

_state = ContextVar("discovery_budget", default=None)

@contextmanager
def budget():
    token = _state.set({"calls": 0, "failures": []})
    try:
        yield
    finally:
        _state.reset(token)


def remember_failure(exc):
    state = _state.get()
    if state is not None:
        state["failures"].append(exc)


def can_fallback(session):
    # Hybrid already queries both providers on its first search.
    return False


def last_failure():
    state = _state.get()
    return state["failures"][-1] if state and state["failures"] else None


def discover(session, query=""):
    if _state.get() is None:
        with budget():
            return discover(session, query)
    state = _state.get()
    from . import browser_search, shopify_catalog, policy
    providers = ["shopify_catalog", "browser_use"] if session.search_provider == "hybrid" else [session.search_provider]
    if state["calls"] + len(providers) > 2:
        raise ValueError("Discovery budget exhausted")

    def run_provider(index, provider):
        adapter = shopify_catalog if provider == "shopify_catalog" else browser_search
        label = ("Searching Shopify-verified merchants..." if provider == "shopify_catalog"
                 else "Deep-checking retailers for seller trust signals (up to 2 minutes)...")
        with step(label):
            return adapter.discover(session, query)

    def eligible_from(ids):
        return [p.id for p in policy.search(session, limit=None) if p.id in ids]

    ids = set()
    # Hybrid is documented as "Shopify first, Browser Use fallback". Run them sequentially:
    # if Shopify gives eligible results, skip the minutes-long Browser Use call.
    for index, provider in enumerate(providers):
        check_cancelled()
        state["calls"] += 1
        try:
            ids.update(run_provider(index, provider))
        except SearchProviderError as exc:
            remember_failure(exc)
            report_failure(session, exc)
        if eligible_from(ids):
            break

    check_cancelled()
    eligible = eligible_from(ids)
    if not eligible and state["failures"]:
        raise state["failures"][-1]
    return eligible
