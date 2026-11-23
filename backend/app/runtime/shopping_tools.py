"""Read-only catalogue tools. Query refinement never changes the user's brief."""

from .timing import timed, diagnostic, product_ref
import re
from . import policy
from .merchants import merchant_for
from .progress import step


def supported_categories(session):
    if session.search_provider != "catalogue" and not session.scenario_id:
        if session.search_replay:
            from .browser_search import replay_categories
            return replay_categories(session.search_replay)
        return []  # Open-ended public product search, not the study category list.
    return sorted({p.category for p in policy.catalogue(session)})


def search_vocabulary(session):
    """Exact attribute and size spellings search matches literally, per category."""
    if session.search_provider != "catalogue" and not session.scenario_id:
        return {}  # Open web listings have no fixed vocabulary.
    vocab = {}
    for p in policy.catalogue(session):
        entry = vocab.setdefault(p.category, {"features": set(), "sizes": set()})
        entry["features"].update(p.attributes)
        entry["sizes"].update(p.sizes)
    return {c: {"features": sorted(v["features"]), "sizes": sorted(v["sizes"])} for c, v in sorted(vocab.items())}


def listed_spelling(session, field, value):
    """Rewrite only case, spaces, hyphens and an EU size prefix; never the meaning."""
    if field not in ("features", "size"):
        return value
    key = "features" if field == "features" else "sizes"
    listed = {term for entry in search_vocabulary(session).values() for term in entry[key]}
    squash = lambda text: re.sub(r"[\W_]+", "", text.casefold())

    def match(term):
        if term in listed:
            return term
        wanted = squash(term)
        if field == "size" and wanted.startswith("eu"):
            wanted = wanted[2:]
        found = {t for t in listed if squash(t) == wanted}
        return found.pop() if len(found) == 1 else term

    if field == "size":
        return match(value.strip())
    return ", ".join(match(term.strip()) for term in value.split(",") if term.strip())


def _search_products(session, query=""):
    if session.search_provider != "catalogue" and not session.scenario_id:
        from .discovery import discover
        ids = discover(session, query)
        return [p for p in policy.search(session, limit=None) if p.id in ids]
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
    return products


def recommendation_limit():
    return max(1, min(3, int(policy.CONFIG.get("recommendation_limit", 3))))


def candidate_key(product):
    # Group known variants of the same provider product; never infer model identity.
    if product.source == "shopify_catalog" and product.provider_ids.get("product"):
        return (product.source, product.provider_ids["product"])
    return (product.source_url, product.name.casefold(), product.brand.casefold(), product.category.casefold())


def candidate_rank(session, product):
    from .relevance import status
    features = " ".join(product.attributes).casefold()
    fit = sum(policy.has_feature(session, product, t) for t in policy.terms(policy.value(session, "features")))
    fit += 2 * (product.brand.casefold() in policy.terms(policy.value(session, "preferred_brands")))
    fit += int(bool(policy.value(session, "usage")) and policy.value(session, "usage").casefold() in features)
    information = sum(map(bool, [product.description, product.attributes, product.specifications, product.sizes]))
    return (status(session, product) == "mismatch", -fit, -information,
            product.currency, product.price, product.id)


def screen_candidate(session, product):
    """Single-product boundary: evidence/cache logic stays in the existing assessors."""
    from .schemas import Action, Event
    from .risk_agent import review
    from .relevance import status
    from .progress import check_cancelled
    import json
    product, merchant = get_product_details(session, product.id)
    session.events.append(Event(kind="shopping_tool", detail=json.dumps({
        "action": "get_product_details", "product": product.model_dump(), "merchant": merchant.model_dump()})))
    if product.source in ("browser_use", "shopify_catalog") and status(session, product) == "mismatch":
        return None
    if product.source in ("browser_use", "shopify_catalog"):
        review(session, product, merchant)
    elif session.risk_detection == "ai":
        from .local_evidence import review_view
        review(session, review_view(product, merchant), merchant)
    check_cancelled()
    allowed = [m for m in session.permissions.payment_methods if m in merchant.payment_methods]
    action = Action(product=product.model_copy(deep=True), merchant_details=merchant.model_copy(deep=True),
                    payment_method=allowed[0] if allowed else "Demo Visa",
                    shares_personal_data=bool(merchant.requested_information))
    policy.evaluate(session, action)
    diagnostic("shortlist.policy", product_ref=product_ref(product.id), decision=action.decision,
               blocking_rules=[r.rule_id for r in action.rules if r.decision == "BLOCK"])
    return product if action.decision != "BLOCK" else None


# INNOVATION: Bounded hybrid shortlist. Other chat shopping agents either render
# unverified cache cards instantly or make the user wait minutes with no visibility.
# Beany merges Shopify (MCP) and Browser Use results, deduplicates them, and inspects
# under a fixed budget, stopping at three distinct eligible products — one primary
# recommendation plus up to two alternatives — so verification stays bounded.
@timed("search.screen_and_rank")
def screen_candidates(session, ids):
    from .progress import check_cancelled
    from .search_errors import SearchProviderError, report_failure
    from .discovery import last_failure
    ranked = sorted((p for p in policy.search(session, limit=None) if p.id in ids),
                    key=lambda p: candidate_rank(session, p))
    # Remove exact duplicates first; retain different seller/variant evidence as fallback.
    unique = {}
    for p in ranked:
        key = p.model_dump_json(exclude={"id", "relevance", "relevance_binding"})
        unique.setdefault(key, p)
    budget = max(1, min(30, int(policy.CONFIG.get("screening_budget", 6))))
    checked, failures, inspected = [], [], 0
    accepted_models = set()
    diagnostic("shortlist.start", retrieved=len(ids), eligible_candidates=len(ranked),
               distinct_candidates=len(unique), screening_budget=budget, target=recommendation_limit())
    for product in unique.values():
        check_cancelled()
        if inspected >= budget or len(checked) >= recommendation_limit():
            break
        if candidate_key(product) in accepted_models:
            continue
        inspected += 1
        diagnostic("shortlist.inspect", product_ref=product_ref(product.id), source=product.source, index=inspected)
        try:
            result = screen_candidate(session, product)
            if result is not None:
                checked.append(result.model_copy(deep=True))
                accepted_models.add(candidate_key(result))
        except SearchProviderError as exc:
            failures.append(exc)
            report_failure(session, exc)
        except ValueError:
            diagnostic("shortlist.exclude", product_ref=product_ref(product.id), reason="details_no_longer_eligible")
    failure = failures[-1] if failures else last_failure()
    if not checked and failure:
        raise failure
    from .relevance import status
    checked.sort(key=lambda p: (p.source in ("browser_use", "shopify_catalog") and status(session, p) != "match", candidate_rank(session, p)))
    diagnostic("shortlist.result", retrieved=len(ids), inspected=inspected, returned=len(checked),
               products=[product_ref(p.id) for p in checked])
    return checked


@timed("product.inspect")
def _get_product_details(session, product_id):
    diagnostic("inspection.start", product_ref=product_ref(product_id))
    product = next((p for p in policy.search(session, limit=None)
                    if p.id == product_id), None)
    if product is None:
        raise ValueError("Product is unavailable or outside the current constraints")
    if product.source == "shopify_catalog" and not product.detail_checked:
        diagnostic("inspection.refresh", product_ref=product_ref(product_id), reason="details_not_checked")
        from .shopify_catalog import details
        product = details(session, product)
        if product.id not in {p.id for p in policy.search(session, limit=None)}:
            raise ValueError("Updated offer no longer meets your requirements")
    from .relevance import inspect
    product = inspect(session, product)
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
