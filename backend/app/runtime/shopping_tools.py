"""Read-only catalogue tools. Query refinement never changes the user's brief."""

import re
from . import policy
from .merchants import merchant_for
from .progress import step


def supported_categories(session):
    if session.search_provider == "browser_use" and not session.scenario_id:
        if session.search_replay:
            from .browser_search import replay_categories
            return replay_categories(session.search_replay)
        return []  # Open-ended public product search, not the study category list.
    return sorted({p.category for p in policy.catalogue(session)})


def _search_products(session, query=""):
    if session.search_provider == "browser_use" and not session.scenario_id:
        from .browser_search import discover
        ids = discover(session, query)
        return [p for p in policy.search(session, limit=None) if p.id in ids][:policy.CONFIG["recommendation_limit"]]
    # Apply every existing eligibility filter before optional keyword filtering.
    products = policy.search(session, limit=None)
    words = re.findall(r"\w+", query.casefold())
    if words:
        products = [
            p for p in products
            if all(word in " ".join([
                p.name, p.category, p.brand, *p.attributes,
                *p.specifications.values(),
            ]).casefold() for word in words)
        ]
    return products[:policy.CONFIG["recommendation_limit"]]


def _get_product_details(session, product_id):
    product = next((p for p in policy.search(session, limit=None)
                    if p.id == product_id), None)
    if product is None:
        raise ValueError("Product is unavailable or outside the current constraints")
    return product, merchant_for(product, session)


def search_products(session, query=""):
    source = "the local catalogue" if session.search_provider == "catalogue" else "saved listings" if session.search_replay else "product listings"
    with step(f"Searching {source}…") as activity:
        products = _search_products(session, query)
        activity["label"] = f"Found {len(products)} matching offer{'s' if len(products) != 1 else ''}"
        activity["evidence"] = [f"{p.name} · {p.merchant}" for p in products]
        return products


def get_product_details(session, product_id):
    with step("Checking product details and seller terms…") as activity:
        product, merchant = _get_product_details(session, product_id)
        activity["label"] = f"Checked {product.name} from {merchant.name}"
        activity["evidence"] = ["Product details", "Available reviews and return terms"]
        return product, merchant
