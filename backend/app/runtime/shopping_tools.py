"""Read-only catalogue tools. Query refinement never changes the user's brief."""

import re
from . import policy
from .merchants import merchant_for


def supported_categories(session):
    if session.search_provider == "browser_use" and not session.scenario_id:
        return []  # Open-ended public product search, not the study category list.
    return sorted({p.category for p in policy.catalogue(session)})


def search_products(session, query=""):
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


def get_product_details(session, product_id):
    product = next((p for p in policy.search(session, limit=None)
                    if p.id == product_id), None)
    if product is None:
        raise ValueError("Product is unavailable or outside the current constraints")
    return product, merchant_for(product, session)
