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


# Live snapshots are blocked at checkout after 30 minutes; leave time to decide after a reuse.
REUSE_SECONDS = 25 * 60
# A recheck of the current batch must leave at least this many eligible listings (a full shortlist).
REUSE_MINIMUM = 3
# Needs that define what the providers searched for: changing one needs a new search.
SAME = ("category", "currency")


def same(a, b):
    return (a.value.strip().casefold() if a else "") == (b.value.strip().casefold() if b else "")


def covered(old, new):
    """True when the current batch was fetched for the same product and currency."""
    return all(same(old.get(k), new.get(k)) for k in SAME)


# INNOVATION: Search reuse on refining edits. Other chat shopping agents re-fire a
# fresh web search every turn even when the user is only adjusting the filter. Beany
# rechecks the last search's listings against the edited brief whenever the product
# category and currency are unchanged (a new budget, added or removed features, an
# excluded brand, a rejected offer), so refinement is instant instead of another paid
# Browser Use run. It searches again when the category or currency changes, fewer
# than three listings still qualify, the batch is older than 25 minutes, or the needs
# are unchanged (the user is asking for a fresh search).
def reusable(session):
    """Listing ids of the current batch, refiltered after any edit that keeps product and currency."""
    from datetime import datetime, timezone
    fetch = session.live_fetch
    if fetch is None or session.search_replay or fetch.provider != session.search_provider:
        return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(fetch.at)).total_seconds()
    if not 0 <= age <= REUSE_SECONDS:
        return None
    # Unchanged needs and no rejected offer means the user is asking for a fresh search.
    if fetch.brief == session.brief and len(session.rejected_products) <= fetch.rejected:
        return None
    if not covered(fetch.brief, session.brief):
        return None
    ids = [i for i in fetch.product_ids if i in session.live_products]
    return ids or None


def reuse(session, ids):
    import json
    from . import policy
    from .schemas import Event
    from .feature_check import ensure
    with step("Rechecking the listings already found...", "Rechecked the listings already found"):
        ensure(session, ids)
        eligible = [p.id for p in policy.search(session, limit=None) if p.id in set(ids)]
    session.events.append(Event(kind="search_reuse", detail=json.dumps({
        "fetched_at": session.live_fetch.at, "product_ids": ids, "eligible": eligible})))
    return eligible


def discover(session, query=""):
    if _state.get() is None:
        with budget():
            return discover(session, query)
    pooled = reusable(session)
    if pooled is not None:
        eligible = reuse(session, pooled)
        # The batch is enough only when it still fills the shortlist; otherwise search again.
        if len(eligible) >= REUSE_MINIMUM:
            # The batch now answers these needs: asking again without changing them is a fresh search.
            session.live_fetch.brief = {k: v.model_copy() for k, v in session.brief.items()}
            session.live_fetch.rejected = len(session.rejected_products)
            return eligible
    state = _state.get()
    from . import browser_search, shopify_catalog, policy
    from .schemas import LiveFetch, now
    # Timed from the start: the earliest snapshot in the pool sets how long it stays reusable.
    asked, started = {k: v.model_copy() for k, v in session.brief.items()}, now()
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
    # The new batch replaces the old one, even after a partial failure: its listings were fetched
    # for the current needs. An empty batch is never reused.
    session.live_fetch = LiveFetch(
        provider=session.search_provider, brief=asked, product_ids=sorted(ids),
        rejected=len(session.rejected_products), at=started) if ids else None
    from .feature_check import ensure, required
    if required(session):
        with step("Checking your required features...", "Checked your required features"):
            ensure(session, sorted(ids))
    eligible = [p.id for p in policy.search(session, limit=None) if p.id in ids]
    if not eligible and state["failures"]:
        raise state["failures"][-1]
    return eligible
