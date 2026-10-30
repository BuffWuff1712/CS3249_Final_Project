"""HTTP facade for the participant shopping workspace."""
from fastapi import APIRouter
from pydantic import Field
from .runtime import shop_workspace as shop, storage
from .runtime.schemas import Model, Fact, Permissions, CartSelection

router = APIRouter(prefix="/shop/sessions")


class Mutation(Model):
    revision: int = Field(ge=0)


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
