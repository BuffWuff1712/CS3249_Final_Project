"""Metadata-only timing spans, correlated across cancellable worker threads."""
import json
import hashlib
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from time import perf_counter
from uuid import uuid4

logger = logging.getLogger("uvicorn.error")
_trace = ContextVar("timing_trace", default=None)
_parent = ContextVar("timing_parent", default=None)


def product_ref(product_id):
    """Stable opaque identifier; never expose provider-controlled identifiers."""
    return hashlib.sha256(str(product_id).encode()).hexdigest()[:12] if product_id else "-"


def diagnostic(event, **fields):
    """Call sites supply fixed event names and metadata only, never raw text."""
    trace = _trace.get()
    logger.info("diagnostic trace=%s span=%s event=%s data=%s",
                trace["id"] if trace else "-", _parent.get() or "-", event,
                json.dumps(fields, sort_keys=True))


@contextmanager
def timed(stage):
    """Use only developer-defined stage names; never pass user/provider text."""
    trace = _trace.get()
    root = trace is None
    token = None
    if root:
        trace = {"id": uuid4().hex[:12], "rows": [], "lock": Lock()}
        token = _trace.set(trace)
    span = uuid4().hex[:8]
    parent = _parent.get()
    parent_token = _parent.set(span)
    started = perf_counter()
    status, error_type = "ok", "none"
    logger.info("timing_start trace=%s span=%s parent=%s stage=%s", trace["id"], span, parent or "-", stage)
    try:
        yield
    except BaseException as exc:
        error_type = type(exc).__name__
        status = "cancelled" if error_type == "RequestStopped" else "error"
        raise
    finally:
        elapsed = perf_counter() - started
        logger.info("timing_end trace=%s span=%s stage=%s status=%s elapsed_s=%.3f error_type=%s",
                    trace["id"], span, stage, status, elapsed, error_type)
        with trace["lock"]:
            trace["rows"].append((stage, elapsed, span))
            rows = list(trace["rows"])
        _parent.reset(parent_token)
        if root:
            totals = {}
            for name, seconds, identifier in rows:
                if identifier == span:
                    continue
                item = totals.setdefault(name, {"stage": name, "calls": 0, "total_s": 0, "max_s": 0})
                item["calls"] += 1
                item["total_s"] += seconds
                item["max_s"] = max(item["max_s"], seconds)
            slowest = sorted(totals.values(), key=lambda item: item["total_s"], reverse=True)
            for item in slowest:
                item["total_s"] = round(item["total_s"], 3)
                item["max_s"] = round(item["max_s"], 3)
            logger.info("timing_summary trace=%s status=%s total_s=%.3f stages=%s",
                        trace["id"], status, elapsed, json.dumps(slowest))
            _trace.reset(token)


@contextmanager
def timed_lock(lock):
    with timed("storage.lock_wait"):
        lock.acquire()
    try:
        yield
    finally:
        lock.release()
