"""HTTP facade for the participant shopping workspace."""
from fastapi import APIRouter
from pydantic import Field
from .runtime import shop_workspace as shop, storage
from .runtime.schemas import Model, Fact, Permissions, CartSelection
from threading import Event, RLock
from uuid import uuid4
from .runtime.progress import cancellation, check_cancelled, RequestStopped

# Independent of the database lock: Stop must work while a model call is pending.
_runs_lock = RLock()
_runs = {}

router = APIRouter(prefix="/shop/sessions")


class Mutation(Model):
    revision: int = Field(ge=0)
    request_id: str | None = Field(default=None, min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9-]+$")


class Message(Mutation):
    text: str = Field(min_length=1, max_length=2000)


class Edit(Mutation):
    field: str
    fact: Fact | None


class Offer(Mutation):
    product_id: str


class Preference(Mutation):
    preference: str | None = None


class Selection(Mutation):
    proposal_id: str
    fingerprint: str


def mutate(sid, body, work):
    with storage.lock:
        s = storage.load(sid)
        state = shop.meta(s)
        if body.revision != state["revision"]:
            raise ValueError("This workspace changed. Refresh its state before trying again.")
        work(s)
        shop.meta(s)["revision"] += 1
        response = shop.view(s)
        with _runs_lock:
            check_cancelled()
            storage.save(s)
        return response


@router.post("")
def create():
    with storage.lock:
        s = shop.create()
        storage.save(s)
        return shop.view(s)


@router.get("/{sid}")
def read(sid: str):
    with storage.lock:
        return shop.view(storage.load(sid))


@router.post("/{sid}/messages")
def message(sid: str, body: Message):
    return mutate(sid, body, lambda s: shop.message(s, body.text))


@router.put("/{sid}/brief")
def edit(sid: str, body: Edit):
    return mutate(sid, body, lambda s: shop.edit(s, body.field, body.fact))


@router.post("/{sid}/compare")
def compare(sid: str, body: Mutation):
    return mutate(sid, body, shop.compare)


@router.post("/{sid}/propose")
def propose(sid: str, body: Offer):
    return mutate(sid, body, lambda s: shop.propose(s, body.product_id))


@router.post("/{sid}/seller")
def seller(sid: str, body: Preference):
    return mutate(sid, body, lambda s: shop.another_seller(s, body.preference))


@router.post("/{sid}/select")
def select(sid: str, body: Selection):
    return mutate(sid, body, lambda s: shop.select(s, body.proposal_id, body.fingerprint))


@router.post("/{sid}/finish")
def finish(sid: str, body: Selection):
    return mutate(sid, body, lambda s: shop.finish(s, body.proposal_id, body.fingerprint))


class PermissionMutation(Mutation):
    permissions: Permissions


class CheckoutMutation(Mutation):
    items: list[CartSelection] = Field(min_length=1)


@router.post('/{sid}/adopt')
def adopt(sid: str):
    with storage.lock:
        s = storage.load(sid)
        shop.adopt(s)
        response = shop.view(s)
        storage.save(s)
        return response


@router.put('/{sid}/permissions')
def permissions(sid: str, body: PermissionMutation):
    return mutate(sid, body, lambda s: shop.permissions(s, body.permissions))


@router.post('/{sid}/cancel')
def cancel(sid: str, body: Mutation):
    return mutate(sid, body, shop.cancel)


@router.post('/{sid}/reject')
def reject(sid: str, body: Selection):
    return mutate(sid, body, lambda s: shop.reject(s, body.proposal_id, body.fingerprint))


@router.post('/{sid}/alternative')
def alternative(sid: str, body: Mutation):
    return mutate(sid, body, shop.alternative)


@router.post('/{sid}/cart')
def add_cart(sid: str, body: Selection):
    return mutate(sid, body, lambda s: shop.add_cart(s, body.proposal_id, body.fingerprint))


@router.delete('/{sid}/cart/{pid}')
def remove_cart(sid: str, pid: str, body: Mutation):
    return mutate(sid, body, lambda s: shop.remove_cart(s, pid))


@router.post('/{sid}/cart/checkout')
def checkout(sid: str, body: CheckoutMutation):
    from .runtime.schemas import CartCheckout
    return mutate(sid, body, lambda s: shop.checkout_cart(s, CartCheckout(items=body.items)))


@router.post('/{sid}/stop/{request_id}')
def stop_request(sid: str, request_id: str):
    with _runs_lock:
        signal = _runs.get((sid, request_id))
        if signal is not None:
            signal.set()
    return {"stopped": signal is not None}


def stream_mutation(sid, body, work):
    """Stream observations from the real operation; commit once using the usual lock."""
    import json
    import logging
    from queue import Queue, Empty
    from threading import Thread, Event
    from fastapi.responses import StreamingResponse
    from .runtime.progress import observe
    from .runtime.gateway import LLMError

    updates = Queue()
    disconnected = Event()
    cancelled = Event()
    key = (sid, body.request_id or uuid4().hex)
    with _runs_lock:
        if key in _runs:
            raise ValueError("Request is already running")
        _runs[key] = cancelled

    def publish(event):
        if not disconnected.is_set():
            updates.put(event)

    def run():
        try:
            with cancellation(cancelled), observe(lambda activity: publish({"type": "activity", "activity": activity})):
                result = mutate(sid, body, work)
            publish({"type": "result", "view": result})
        except RequestStopped as exc:
            publish({"type": "error", "message": str(exc)})
        except (ValueError, LookupError, LLMError) as exc:
            publish({"type": "error", "message": str(exc)})
        except Exception:
            logging.getLogger(__name__).exception("Shopping stream failed")
            publish({"type": "error", "message": "The request could not finish. Reload the workspace before trying again."})
        finally:
            with _runs_lock:
                _runs.pop(key, None)
            updates.put(None)

    def events():
        Thread(target=run, daemon=True).start()
        try:
            while True:
                try:
                    update = updates.get(timeout=5)
                except Empty:
                    update = {"type": "ping"}
                if update is None:
                    return
                yield json.dumps(update) + "\n"
        finally:
            # A committed result is never undone; the client reloads after stopping.
            cancelled.set()
            disconnected.set()

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post('/{sid}/messages/stream')
def message_stream(sid: str, body: Message):
    return stream_mutation(sid, body, lambda s: shop.message(s, body.text))


@router.post('/{sid}/compare/stream')
def compare_stream(sid: str, body: Mutation):
    return stream_mutation(sid, body, shop.compare)


@router.post('/{sid}/propose/stream')
def propose_stream(sid: str, body: Offer):
    return stream_mutation(sid, body, lambda s: shop.propose(s, body.product_id))


@router.post('/{sid}/seller/stream')
def seller_stream(sid: str, body: Preference):
    return stream_mutation(sid, body, lambda s: shop.another_seller(s, body.preference))


@router.post('/{sid}/alternative/stream')
def alternative_stream(sid: str, body: Mutation):
    return stream_mutation(sid, body, shop.alternative)
