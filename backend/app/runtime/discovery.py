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
# List needs compare as sets: "a, b" and "B, a" ask for the same thing.
LIST_NEEDS = ("features", "preferred_brands", "excluded_brands", "merchants")


def normalized(key, fact):
    if fact is None:
        return None
    text = fact.value.strip().casefold()
    if key in LIST_NEEDS:
        return frozenset(part.strip() for part in text.split(",") if part.strip())
    return text


def same(a, b, key=""):
    return normalized(key, a) == normalized(key, b)


def same_needs(old, new):
    """Same value and must-have flag for every need, ignoring case, spacing and list order."""
    return all(same(old.get(k), new.get(k), k) and bool(old.get(k) and old[k].hard) == bool(new.get(k) and new[k].hard)
               for k in set(old) | set(new))


def narrows(old, new):
    """True when every changed need can only remove listings from the batch fetched for old.

    A lower or newly added budget and more excluded brands narrow. Anything else (a higher or
    removed budget, added or removed features, a new usage, size, preferred brand, seller,
    category or currency) asks for listings the last search was never run for."""
    for key in set(old) | set(new):
        a, b = old.get(key), new.get(key)
        if same(a, b, key):
            continue
        if key == "budget" and b is not None:
            if a is None:
                continue
            try:
                if float(b.value) <= float(a.value):
                    continue
            except ValueError:
                pass
            return False
        if key == "excluded_brands" and b is not None and normalized(key, b) >= (normalized(key, a) or frozenset()):
            continue
        return False
    return True


# INNOVATION: Search reuse on narrowing edits. Other chat shopping agents re-fire a
# fresh web search every turn even when the user is only tightening the filter. Beany
# rechecks the last search's listings when an edit only narrows them (a lower or new
# budget, a newly excluded brand) or only switches a need between must-have and
# preferred, so refinement is instant instead of another paid Browser Use run. Any edit that asks
# for listings the last search never looked for (a higher or removed budget, added or
# removed features, a new usage, size, brand, category or currency) searches again, as
# does asking again with unchanged needs, fewer than three listings still qualifying,
# or a batch older than 25 minutes.
def reusable(session):
    """Listing ids of the current batch, refiltered after an edit that only narrows it."""
    from datetime import datetime, timezone
    fetch = session.live_fetch
    if fetch is None or session.search_replay or fetch.provider != session.search_provider:
        return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(fetch.at)).total_seconds()
    if not 0 <= age <= REUSE_SECONDS:
        return None
    # Unchanged needs mean the user is asking for a fresh search, even after rejecting an
    # offer: "search again" or "find something else" must not show the same batch again.
    if same_needs(fetch.brief, session.brief):
        return None
    if not narrows(fetch.brief, session.brief):
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
