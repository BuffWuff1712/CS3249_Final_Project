"""Request-scoped public activity updates, never model reasoning or authority."""
from contextlib import contextmanager
from contextvars import ContextVar

_observer = ContextVar("shopping_progress", default=None)
_cancellation = ContextVar("shopping_cancellation", default=None)


class RequestStopped(Exception):
    pass


def check_cancelled():
    signal = _cancellation.get()
    if signal is not None and signal.is_set():
        raise RequestStopped("Stopped this request. No new result was saved.")


@contextmanager
def cancellation(signal):
    token = _cancellation.set(signal)
    try:
        check_cancelled()
        yield
    finally:
        _cancellation.reset(token)


def cancellable_call(call):
    """Release the caller promptly; a remote call may finish but cannot mutate state."""
    check_cancelled()
    if _cancellation.get() is None:
        return call()
    from concurrent.futures import Future, TimeoutError
    from contextvars import copy_context
    from threading import Thread
    result = Future()
    context = copy_context()
    def run():
        try:
            result.set_result(context.run(call))
        except BaseException as exc:
            result.set_exception(exc)
    Thread(target=run, daemon=True).start()
    while True:
        check_cancelled()
        try:
            value = result.result(timeout=0.1)
            check_cancelled()
            return value
        except TimeoutError:
            if result.done():
                raise


@contextmanager
def observe(callback):
    token = _observer.set({"callback": callback, "next": 0})
    try:
        yield
    finally:
        _observer.reset(token)


@contextmanager
def step(label, completed=None):
    check_cancelled()
    observer = _observer.get()
    data = {"id": "", "label": label, "state": "running", "evidence": []}
    if observer:
        observer["next"] += 1
        data["id"] = str(observer["next"])
        observer["callback"](dict(data))
    result = {"label": completed or label, "evidence": [], "state": "completed"}
    try:
        yield result
        check_cancelled()
    except Exception:
        if observer:
            observer["callback"]({**data, "state": "unavailable", "label": "Could not finish: " + label.rstrip(".…")})
        raise
    else:
        if observer:
            observer["callback"]({**data, **result})
