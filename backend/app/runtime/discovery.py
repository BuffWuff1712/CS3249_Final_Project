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


def last_failure():
    state = _state.get()
    return state["failures"][-1] if state and state["failures"] else None


# Live snapshots are blocked at checkout after 30 minutes; leave time to decide after a reuse.
REUSE_SECONDS = 25 * 60
# Needs sent to the providers that a reused pool must already cover, value for value.
SAME = ("category", "currency", "other")
# Optional needs: removing one is a local filter change, adding or changing one needs a new search.
OPTIONAL = ("usage", "size")


def listed(fact):
    return {t.strip().casefold() for t in fact.value.split(",") if t.strip()} if fact else set()


def same(a, b):
    return (a.value.strip().casefold() if a else "") == (b.value.strip().casefold() if b else "")


def covered(old, new):
    """True when the old search already looked for everything the new needs could want."""
    if any(not same(old.get(k), new.get(k)) for k in SAME):
        return False
    if any(new.get(k) and not same(old.get(k), new.get(k)) for k in OPTIONAL):
        return False
    # Fewer features, brands or merchants narrows nothing the providers were asked for.
    if any(not listed(new.get(k)) <= listed(old.get(k)) for k in ("features", "preferred_brands", "merchants")):
        return False
    # Brands excluded at search time were never fetched, so un-excluding one needs a new search.
    if not listed(old.get("excluded_brands")) <= listed(new.get("excluded_brands")):
        return False
    before, after = old.get("budget"), new.get("budget")
    if before:
        if not after:
            return False
        try:
            if float(after.value) > float(before.value):
                return False
        except ValueError:
            return False
        # A hard budget capped the search; a preferred one may want offers above it.
        if before.hard and not after.hard:
            return False
    return True


def reusable(session):
    """Listing ids from the last live search when only local filtering changed, else None."""
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
        if eligible:
            return eligible
        # An empty reuse is never a no-match: search again for the new needs.
    state = _state.get()
    from . import browser_search, shopify_catalog, policy
    from .schemas import LiveFetch, now
    # Timed from the start: the earliest snapshot in the pool sets how long it stays reusable.
    asked, started = {k: v.model_copy() for k, v in session.brief.items()}, now()
    providers = ["shopify_catalog", "browser_use"] if session.search_provider == "hybrid" else [session.search_provider]
    if state["calls"] + len(providers) > 2:
        raise ValueError("Discovery budget exhausted")

    from .feature_check import ensure, required

    def run_provider(provider):
        adapter = shopify_catalog if provider == "shopify_catalog" else browser_search
        label = ("Searching Shopify-verified merchants..." if provider == "shopify_catalog"
                 else "Deep-checking retailers for seller trust signals (up to 2 minutes)...")
        with step(label):
            return adapter.discover(session, query)

    def eligible_from(found):
        # Paraphrased required features are checked first, or Shopify offers that meet them would
        # look ineligible and trigger the minutes-long Browser Use call. Cached verdicts are not re-asked.
        if found and required(session):
            with step("Checking your required features...", "Checked your required features"):
                ensure(session, sorted(found))
        return [p.id for p in policy.search(session, limit=None) if p.id in found]

    ids, eligible = set(), []
    # Hybrid runs Shopify first and calls Browser Use only when Shopify gives no offer that fits.
    for provider in providers:
        check_cancelled()
        state["calls"] += 1
        try:
            ids.update(run_provider(provider))
        except SearchProviderError as exc:
            remember_failure(exc)
            report_failure(session, exc)
        eligible = eligible_from(ids)
        # Stop only on an offer that meets every must-have: one whose listing never mentions a
        # required feature is kept for review but is not a reason to skip the next source.
        if any(not policy.unstated_features(session, session.live_products[i]) for i in eligible):
            break
    check_cancelled()
    # A partial search (one provider failed) is never reused: the next search starts over.
    session.live_fetch = None if state["failures"] else LiveFetch(
        provider=session.search_provider, brief=asked, product_ids=sorted(ids),
        rejected=len(session.rejected_products), at=started)
    if not eligible and state["failures"]:
        raise state["failures"][-1]
    return eligible
