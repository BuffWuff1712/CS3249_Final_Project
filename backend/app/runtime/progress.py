"""Request-scoped public activity updates, never model reasoning or authority."""
from contextlib import contextmanager
from contextvars import ContextVar

_observer = ContextVar("shopping_progress", default=None)


@contextmanager
def observe(callback):
    token = _observer.set({"callback": callback, "next": 0})
    try:
        yield
    finally:
        _observer.reset(token)


@contextmanager
def step(label, completed=None):
    observer = _observer.get()
    data = {"id": "", "label": label, "state": "running", "evidence": []}
    if observer:
        observer["next"] += 1
        data["id"] = str(observer["next"])
        observer["callback"](dict(data))
    result = {"label": completed or label, "evidence": [], "state": "completed"}
    try:
        yield result
    except Exception:
        if observer:
            observer["callback"]({**data, "state": "unavailable", "label": "Could not finish: " + label.rstrip(".…")})
        raise
    else:
        if observer:
            observer["callback"]({**data, **result})
