"""Provider routing with a shared per-turn discovery budget."""
from contextvars import ContextVar
from contextlib import contextmanager
from .progress import check_cancelled, step
from .search_errors import SearchProviderError, report_failure

_state=ContextVar("discovery_budget",default=None)

@contextmanager
def budget():
    token=_state.set({"calls":0,"browser":False,"failures":[]})
    try: yield
    finally: _state.reset(token)


def remember_failure(exc):
    state = _state.get()
    if state is not None:
        state["failures"].append(exc)


def can_fallback(session):
    state=_state.get()
    return session.search_provider=="hybrid" and state is not None and state["calls"]<2 and not state["browser"]


def discover(session,query=""):
    if _state.get() is None:
        with budget(): return discover(session,query)
    state=_state.get()
    provider=session.search_provider
    if provider=="hybrid": provider="shopify_catalog" if state["calls"]==0 else "browser_use"
    if state["calls"]>=2 or (session.search_provider=="hybrid" and provider=="browser_use" and state["browser"]):
        raise ValueError("Discovery budget exhausted")
    check_cancelled()
    state["calls"]+=1
    if provider=="browser_use": state["browser"]=True
    from . import browser_search, shopify_catalog, policy
    adapter=shopify_catalog if provider=="shopify_catalog" else browser_search
    label="Searching Shopify products…" if provider=="shopify_catalog" else "Searching retailer websites with Browser Use…"
    try:
        with step(label):
            ids=adapter.discover(session,query)
        eligible=[p.id for p in policy.search(session,limit=None) if p.id in ids]
        if eligible: return eligible
    except SearchProviderError as exc:
        state["failures"].append(exc)
        if not can_fallback(session): raise
        report_failure(session,exc)
    if can_fallback(session):
        with step("Trying Browser Use because Shopify did not supply eligible offers…", "Used Browser Use fallback"):
            return discover(session,query)
    if state["failures"]:
        raise state["failures"][-1]  # An incomplete search is not proof of no matches.
    return []
