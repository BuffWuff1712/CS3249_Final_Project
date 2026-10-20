import hashlib, json
from pathlib import Path
from .schemas import Product, Rule
from .merchants import merchant_for
from .merchant_risk import assess, session_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config/policy.json").read_text(encoding="utf-8-sig"))
FIELDS = {
    "category",
    "usage",
    "budget",
    "currency",
    "preferred_brands",
    "excluded_brands",
    "size",
    "features",
    "merchants",
    "other",
}


def value(s, key, default=""):
    fact = s.brief.get(key)
    return fact.value if fact and fact.source != "unspecified" else default


def terms(text):
    return [x.strip().casefold() for x in text.split(",") if x.strip()]


def confirmed(s, key):
    return key in s.brief and s.brief[key].source == "confirmed"


def catalogue(s):
    products = [
        Product.model_validate(p)
        for p in json.loads(
            (ROOT / "data/products/catalogue.json").read_text(encoding="utf-8-sig")
        )
    ]
    for p in products:
        m = merchant_for(p)
        p.merchant = m.name
        p.trust = "established" if m.verified_business else "unverified"
    if s.scenario_id:
        scenario = json.loads(
            (ROOT / "data/scenarios/scenarios.json").read_text(encoding="utf-8-sig")
        )
        spec = next(x for x in scenario if x["id"] == s.scenario_id)
        if spec.get("merchant_ids"):
            products = [p for p in products if p.merchant_id in spec["merchant_ids"]]
        if spec.get("product_ids"):
            products = [p for p in products if p.id in spec["product_ids"]]
    return products


def search(s):
    products = []
    for p in catalogue(s):
        if (
            not p.stock
            or p.id in s.rejected_products
            or p.merchant_id in s.rejected_merchants
        ):
            continue
        if (
            value(s, "category")
            and p.category.casefold() != value(s, "category").casefold()
        ):
            continue
        if confirmed(s, "currency") and p.currency != value(s, "currency"):
            continue
        if (
            confirmed(s, "budget")
            and s.brief["budget"].hard
            and p.price > float(value(s, "budget"))
        ):
            continue
        if confirmed(s, "excluded_brands") and p.brand.casefold() in terms(
            value(s, "excluded_brands")
        ):
            continue
        if p.merchant.casefold() in [
            m.casefold() for m in s.permissions.restricted_merchants
        ]:
            continue
        if confirmed(s, "size") and p.sizes and value(s, "size") not in p.sizes:
            continue
        if (
            confirmed(s, "preferred_brands")
            and s.brief["preferred_brands"].hard
            and p.brand.casefold() not in terms(value(s, "preferred_brands"))
        ):
            continue
        if (
            confirmed(s, "features")
            and s.brief["features"].hard
            and any(
                t not in " ".join(p.attributes).casefold()
                for t in terms(value(s, "features"))
            )
        ):
            continue
        if (
            confirmed(s, "merchants")
            and s.brief["merchants"].hard
            and p.merchant.casefold() not in terms(value(s, "merchants"))
        ):
            continue
        products.append(p)

    def rank(p):
        score = sum(
            t in " ".join(p.attributes).casefold() for t in terms(value(s, "features"))
        )
        score += 2 * (p.brand.casefold() in terms(value(s, "preferred_brands")))
        score += (
            int(value(s, "usage").casefold() in " ".join(p.attributes).casefold())
            if value(s, "usage")
            else 0
        )
        return (-score, p.price, p.id)

    return sorted(products, key=rank)[: CONFIG["recommendation_limit"]]


def fingerprint(a):
    payload = {
        "product": a.product.model_dump(),
        "merchant": a.merchant_details.model_dump() if a.merchant_details else None,
        "risk_config": a.risk.config_hash if a.risk else None,
        "payment": a.payment_method,
        "sharing": a.shares_personal_data,
        "substitute": a.substitute,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def evaluate(s, a):
    rules = []

    def rule(id, decision, constraint, explanation):
        rules.append(
            Rule(
                triggering_action=f"Simulated checkout of {a.product.name} ({a.id})",
                rule_id=id,
                decision=decision,
                constraint=constraint,
                explanation=explanation,
                intervention=decision != "ALLOW",
            )
        )

    p = a.product
    try:
        merchant = merchant_for(p)
        if a.merchant_details is None or merchant != a.merchant_details:
            rule(
                "merchant_changed",
                "BLOCK",
                "merchant",
                "Merchant terms changed or are missing. Request a new proposal.",
            )
        a.risk = assess(p, merchant, catalogue(s), session_config(s))
        if a.risk.recommended_decision != "ALLOW":
            rule(
                "merchant_risk",
                a.risk.recommended_decision,
                "merchant_risk",
                a.risk.explanation,
            )
        if a.payment_method not in merchant.payment_methods:
            rule(
                "merchant_payment",
                "BLOCK",
                "payment",
                "This payment method is not accepted by the simulated merchant.",
            )
        if merchant.requested_information and not s.permissions.share_personal_data:
            rule(
                "merchant_privacy",
                "BLOCK",
                "share_personal_data",
                "This merchant requests information you have not permitted sharing: "
                + ", ".join(merchant.requested_information)
                + ".",
            )
    except (ValueError, OSError, KeyError, TypeError):
        a.risk = None
        rule(
            "risk_configuration",
            "BLOCK",
            "configuration",
            "Merchant risk data or configuration is invalid. Checkout is blocked until the researcher repairs it.",
        )
    if not p.stock:
        rule(
            "stock", "BLOCK", "availability", "This fictional product is out of stock."
        )
    if confirmed(s, "budget") and p.price > float(value(s, "budget")):
        rule(
            "budget",
            "BLOCK" if s.brief["budget"].hard else "REVIEW",
            "budget",
            "The price exceeds your "
            + ("hard limit." if s.brief["budget"].hard else "preferred budget."),
        )
    if confirmed(s, "currency") and p.currency != value(s, "currency"):
        rule(
            "currency",
            "BLOCK",
            "currency",
            "The currency differs from your confirmed currency.",
        )
    if confirmed(s, "excluded_brands") and p.brand.casefold() in terms(
        value(s, "excluded_brands")
    ):
        rule("brand", "BLOCK", "excluded_brands", "This brand is explicitly excluded.")
    if p.merchant.casefold() in [
        m.casefold() for m in s.permissions.restricted_merchants
    ]:
        rule(
            "merchant",
            "BLOCK",
            "restricted_merchants",
            "This fictional merchant is restricted by your settings.",
        )
    if a.payment_method not in s.permissions.payment_methods:
        rule(
            "payment",
            "BLOCK",
            "payment_methods",
            "This fictional payment method is not permitted.",
        )
    if a.shares_personal_data and not s.permissions.share_personal_data:
        rule(
            "data",
            "BLOCK",
            "share_personal_data",
            "Sharing personal data is not permitted.",
        )
    if a.substitute and not s.permissions.substitutions:
        rule(
            "substitution",
            "REVIEW",
            "substitutions",
            "This is a substitution; approve this specific alternative or refine your request.",
        )
    if confirmed(s, "category") and p.category != value(s, "category"):
        rule(
            "category",
            "REVIEW",
            "category",
            "This product differs from the requested category.",
        )
    if confirmed(s, "size") and p.sizes and value(s, "size") not in p.sizes:
        rule("size", "BLOCK", "size", "The requested size is unavailable.")
    if confirmed(s, "merchants") and p.merchant.casefold() not in terms(
        value(s, "merchants")
    ):
        rule(
            "preferred_merchant",
            "BLOCK" if s.brief["merchants"].hard else "REVIEW",
            "merchants",
            "This merchant differs from your preference.",
        )
    if (
        confirmed(s, "features")
        and s.brief["features"].hard
        and any(
            t not in " ".join(p.attributes).casefold()
            for t in terms(value(s, "features"))
        )
    ):
        rule("features", "BLOCK", "features", "A required feature is missing.")
    if (
        confirmed(s, "preferred_brands")
        and s.brief["preferred_brands"].hard
        and p.brand.casefold() not in terms(value(s, "preferred_brands"))
    ):
        rule(
            "required_brand",
            "BLOCK",
            "preferred_brands",
            "This brand does not meet your required brand constraint.",
        )
    if (
        confirmed(s, "usage")
        and s.brief["usage"].hard
        and value(s, "usage").casefold() not in " ".join(p.attributes).casefold()
    ):
        rule(
            "usage",
            "REVIEW",
            "usage",
            "Please verify suitability for your required usage.",
        )
    if confirmed(s, "other"):
        rule(
            "other",
            "REVIEW",
            "other",
            "Please check your additional requirements; these cannot be verified automatically.",
        )
    if CONFIG["review_missing_budget"] and not confirmed(s, "budget"):
        rule(
            "missing_budget",
            "REVIEW",
            "budget",
            "No spending limit is confirmed; review this price.",
        )
    if s.permissions.require_approval or s.permissions.autonomy == "guided":
        rule(
            "approval",
            "REVIEW",
            "require_approval",
            "Your settings require approval before simulated checkout.",
        )
    if CONFIG["review_unverified_merchants"] and p.trust == "unverified":
        rule(
            "trust",
            "REVIEW",
            "merchant_trust",
            "This simulated merchant has limited catalogue information.",
        )
    if not rules:
        rule(
            "within_limits",
            "ALLOW",
            "permissions",
            "All checked constraints and checkout permissions are satisfied.",
        )
    a.rules = rules
    a.decision = (
        "BLOCK"
        if any(r.decision == "BLOCK" for r in rules)
        else "REVIEW"
        if any(r.decision == "REVIEW" for r in rules)
        else "ALLOW"
    )
    return a
