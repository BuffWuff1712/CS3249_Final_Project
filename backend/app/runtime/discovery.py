"""Bounded discovery: hybrid searches each source once, without automatic retries."""
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
    ids = set()
    for index, provider in enumerate(providers):
        check_cancelled()
        state["calls"] += 1
        adapter = shopify_catalog if provider == "shopify_catalog" else browser_search
        try:
            with step("Searching product listings..." if index == 0 else "Searching more stores..."):
                ids.update(adapter.discover(session, query))
        except SearchProviderError as exc:
            remember_failure(exc)
            report_failure(session, exc)
    check_cancelled()
    eligible = [p.id for p in policy.search(session, limit=None) if p.id in ids]
    if not eligible and state["failures"]:
        raise state["failures"][-1]
    return eligible
