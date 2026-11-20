"""Deterministic, bounded discovery and screening; never authorizes checkout."""
import json
from typing import Literal
from .timing import timed, diagnostic
from .schemas import Model, Field, Product, Event
from .shopping_tools import search_products, screen_candidates
from .progress import check_cancelled


class ShoppingResult(Model):
    status: Literal["proposed", "no_match", "stopped"]
    product: Product | None = None
    candidates: list[Product] = Field(default_factory=list)


def search_query(session):
    # Catalogue matching uses literal AND terms; its structured filters already use the brief.
    if session.search_provider == "catalogue" or session.scenario_id or session.search_replay:
        return ""
    return "; ".join(f"{key}: {fact.value}" for key, fact in session.brief.items()
                     if fact.source == "confirmed")


@timed("search.workflow")
def run_shopping(session):
    from .discovery import budget
    with budget():
        check_cancelled()
        query = search_query(session)
        candidates = search_products(session, query)
        check_cancelled()
        session.events.append(Event(kind="shopping_tool", detail=json.dumps({
            "action": "search_products", "query": query,
            "products": [{"id": p.id, "name": p.name, "price": p.price, "currency": p.currency,
                          "attributes": p.attributes, "merchant": p.merchant} for p in candidates]})))
        candidates = screen_candidates(session, [p.id for p in candidates])
        check_cancelled()
        if not candidates:
            return ShoppingResult(status="no_match")
        # Recheck snapshots without asking the model to inspect the same item again.
        from . import policy
        current = {p.id: p for p in policy.catalogue(session)}
        if any(current.get(p.id) != p for p in candidates):
            diagnostic("workflow.result", status="stopped", reason="snapshot_changed", planner_calls=0)
            return ShoppingResult(status="stopped")
        selected = candidates[0]
        session.events.append(Event(kind="shopping_tool", detail=json.dumps({
            "action": "propose", "product_id": selected.id})))
        diagnostic("workflow.result", status="proposed", recommendations=len(candidates), planner_calls=0)
        return ShoppingResult(status="proposed", product=selected, candidates=candidates)
