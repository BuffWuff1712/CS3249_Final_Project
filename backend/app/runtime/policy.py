import hashlib, json
from pathlib import Path
from .schemas import Product, Rule, Event
from .merchants import merchant_for, merchants
from .merchant_risk import assess, assess_live, safeguard_block, session_config
from .risk_agent import snapshot
from .local_evidence import review_view

from .timing import timed
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


def live(s, p):
    return p.source in ("browser_use", "shopify_catalog") and not s.search_replay


KEY_PREFIX = {"feature": "", "size": "size: ", "usage": "use: "}


def needs(s):
    """(kind, term, cache key) for each need the model may settle in a live listing.

    Preferred needs are checked too, so a listing that clearly meets one is shown as meeting it;
    only must-have needs ever exclude an offer or add a review rule."""
    out = []
    if confirmed(s, "features"):
        out += [("feature", t, t) for t in terms(value(s, "features"))]
    for kind, field in (("size", "size"), ("usage", "usage")):
        term = value(s, field).strip().casefold()
        if confirmed(s, field) and term:
            out.append((kind, term, KEY_PREFIX[kind] + term))
    return out


def need_rule(s, p, kind, term):
    """Rules only: True met, False clearly not, None undecided (a live listing then asks the model)."""
    from .feature_match import met, listing_text, size_rule
    if kind == "size":
        if not p.sizes:
            return None if live(s, p) else True
        found = size_rule(term, p.sizes)
        return found if found is not None or live(s, p) else False
    if live(s, p):
        return True if met(term, listing_text(p)) else None
    return term in " ".join(p.attributes).casefold()


def status(s, p, kind, term):
    """met, absent, unstated (the model found no mention) or unknown (nothing settled it)."""
    found = need_rule(s, p, kind, term)
    if found is not None:
        return "met" if found else "absent"
    verdict = s.feature_checks.get(p.id, {}).get(KEY_PREFIX[kind] + term) if live(s, p) else None
    return verdict.status if verdict else "unknown"


def has_feature(s, p, term):
    return status(s, p, "feature", term) == "met"


def unstated_features(s, p):
    """Required features a live listing neither shows nor contradicts, per the model check."""
    return [t for t in terms(value(s, "features")) if status(s, p, "feature", t) == "unstated"]


def missing_features(s, p):
    """Features that disqualify: contradicted, or never confirmed by rules or the model."""
    return [t for t in terms(value(s, "features")) if status(s, p, "feature", t) in ("absent", "unknown")]


def size_status(s, p):
    return status(s, p, "size", value(s, "size").strip().casefold()) if confirmed(s, "size") and value(s, "size").strip() else None


def usage_met(s, p):
    return bool(value(s, "usage").strip()) and status(s, p, "usage", value(s, "usage").strip().casefold()) == "met"


def brand_match(s, p, field):
    """True if the offer is one of these brands, False if clearly not, None if its brand is not shown."""
    from .feature_match import brand_rule
    found = [brand_rule(t, p) for t in terms(value(s, field))]
    return True if True in found else None if None in found else False


def merchant_match(p, names):
    from .feature_match import merchant_rule
    return any(merchant_rule(n, p) for n in names if n.strip())


def feature_fit(s, p):
    """Per requested need: met, absent, unstated (model found no mention) or unknown."""
    from .schemas import FeatureFit
    checks = s.feature_checks.get(p.id, {}) if live(s, p) else {}
    out = []
    if confirmed(s, "features"):
        for t in terms(value(s, "features")):
            st = status(s, p, "feature", t)
            # A curated catalogue attribute list not naming a feature is no evidence the product lacks it.
            st = "unknown" if st == "absent" and not live(s, p) else st
            found = checks.get(t)
            out.append(FeatureFit(feature=t, status=st, quote=found.quote if found and found.status == st else ""))
    for kind, field in (("size", "size"), ("usage", "usage")):
        term = value(s, field).strip()
        if confirmed(s, field) and term:
            st = status(s, p, kind, term.casefold())
            found = checks.get(KEY_PREFIX[kind] + term.casefold())
            out.append(FeatureFit(kind=kind, feature=term, status=st,
                                  quote=found.quote if found and found.status == st else ""))
    if confirmed(s, "preferred_brands"):
        found = brand_match(s, p, "preferred_brands")
        out.append(FeatureFit(kind="brand", feature=value(s, "preferred_brands"),
                              status="met" if found else "unknown" if found is None else "absent"))
    if confirmed(s, "merchants"):
        out.append(FeatureFit(kind="merchant", feature=value(s, "merchants"),
                              status="met" if merchant_match(p, terms(value(s, "merchants"))) else "absent"))
    return out


def confirmed(s, key):
    return key in s.brief and s.brief[key].source == "confirmed"


def catalogue(s):
    if s.search_provider != "catalogue" and not s.scenario_id:
        return list(s.live_products.values())
    products = [
        Product.model_validate(p)
        for p in json.loads(
            (ROOT / "data/products/catalogue.json").read_text(encoding="utf-8-sig")
        )
    ]
    records = merchants()
    for p in products:
        m = records.get(p.merchant_id)
        if m is None:
            raise ValueError("Unknown merchant: request a fresh catalogue proposal")
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


def search(s, *, limit=CONFIG["recommendation_limit"]):
    products = []
    for p in catalogue(s):
        if (
            not p.stock
            or p.id in s.rejected_products
            or p.merchant_id in s.rejected_merchants
        ):
            continue
        if (
            not (p.source in ("browser_use", "shopify_catalog") and not s.search_replay)
            and value(s, "category")
            and p.category.casefold() != value(s, "category").casefold()
        ):
            continue
        if p.source in ("browser_use", "shopify_catalog") and not s.search_replay:
            from .relevance import status
            if status(s, p) == "mismatch":
                continue
        if confirmed(s, "currency") and p.currency != value(s, "currency"):
            continue
        if (
            confirmed(s, "budget")
            and s.brief["budget"].hard
            and p.price > float(value(s, "budget"))
        ):
            continue
        if confirmed(s, "excluded_brands") and brand_match(s, p, "excluded_brands"):
            continue
        if merchant_match(p, s.permissions.restricted_merchants):
            continue
        if size_status(s, p) == "absent" and s.brief["size"].hard:
            continue
        if (
            confirmed(s, "preferred_brands")
            and s.brief["preferred_brands"].hard
            and brand_match(s, p, "preferred_brands") is False
        ):
            continue
        if (
            confirmed(s, "features")
            and s.brief["features"].hard
            and missing_features(s, p)
        ):
            continue
        if (
            confirmed(s, "merchants")
            and s.brief["merchants"].hard
            and not merchant_match(p, terms(value(s, "merchants")))
        ):
            continue
        products.append(p)

    def rank(p):
        score = sum(has_feature(s, p, t) for t in terms(value(s, "features")))
        score += 2 * bool(confirmed(s, "preferred_brands") and brand_match(s, p, "preferred_brands"))
        score += int(usage_met(s, p))
        return (-score, p.price, p.id)

    ranked = sorted(products, key=rank)
    return ranked if limit is None else ranked[:limit]


def fingerprint(a):
    payload = {
        "product": a.product.model_dump(exclude={"image_url", "image_alt"}),
        "merchant": a.merchant_details.model_dump() if a.merchant_details else None,
        "risk_config": a.risk.config_hash if a.risk else None,
        "payment": a.payment_method,
        "sharing": a.shares_personal_data,
        "substitute": a.substitute,
    }
    for key in ("observed_type", "type_evidence", "relevance_binding", "relevance", "provider_ids", "inferred_attributes", "detail_checked", "selling_points", "policy_links", "rating_scope", "list_price", "availability_note", "product_rating_text", "seller_rating_text", "review_excerpts"):
        if payload["product"].get(key) in ("", "unknown", None, {}, [], False):
            payload["product"].pop(key, None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@timed("policy.evaluate")
def evaluate(s, a, *, catalogue_snapshot=None, merchant_snapshot=None):
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
        merchant = merchant_for(p, s) if merchant_snapshot is None else merchant_snapshot[p.merchant_id]
        if a.merchant_details is None or merchant != a.merchant_details:
            rule(
                "merchant_changed",
                "BLOCK",
                "merchant",
                "Merchant terms changed or are missing. Request a new proposal.",
            )
        if p.source in ("browser_use", "shopify_catalog"):
            import re
            from datetime import datetime, timezone
            config = session_config(s)  # Invalid policy configuration still blocks.
            cached = s.live_risk.get(p.id)
            if cached and cached.snapshot == snapshot(p):
                a.risk = assess_live(p, merchant, (catalogue(s) if catalogue_snapshot is None else catalogue_snapshot), config, cached)
                a.risk.basis = "ai"
            else:
                a.risk = None
                rule("risk_review_unavailable", "REVIEW", "merchant_risk",
                     "Automated risk review of this listing is unavailable. Check the seller, returns and payment terms on the source page yourself.")
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(p.observed_at)).total_seconds()
            rule("live_snapshot", "BLOCK" if age > 1800 or age < 0 else "REVIEW", "source",
                 "This is an unverified web snapshot, not a merchant safety assessment. Prices and stock may change. Refresh searches older than 30 minutes. Checkout is simulated only.")
            if re.search(r"ignore.{0,60}(rules|instructions|preferences)|reveal.{0,30}(key|password)|disregard.{0,40}(policy|rules)|enable.{0,40}personal data", p.description, re.I):
                rule("injection", "BLOCK", "source", "The listing contains instructions aimed at changing assistant behaviour. Choose another listing.")
        elif s.risk_detection == "ai":
            # AI is primary for local products; the rules engine is the fallback.
            view = review_view(p, merchant)
            cached = s.live_risk.get(p.id)
            if cached and cached.snapshot == snapshot(view):
                # The record's safeguards still hard-block whatever the model reported.
                a.risk = assess_live(view, merchant, (catalogue(s) if catalogue_snapshot is None else catalogue_snapshot), session_config(s), cached,
                                     force_block=safeguard_block(p, merchant))
                a.risk.basis = "ai"
            else:
                a.risk = assess(p, merchant, (catalogue(s) if catalogue_snapshot is None else catalogue_snapshot), session_config(s))
                a.risk.basis = "rules_fallback"
                if not any(e.kind == "risk_agent_fallback" and e.detail == p.id for e in s.events):
                    s.events.append(Event(kind="risk_agent_fallback", detail=p.id))
        else:
            a.risk = assess(p, merchant, (catalogue(s) if catalogue_snapshot is None else catalogue_snapshot), session_config(s))
        if a.risk and a.risk.recommended_decision != "ALLOW":
            # The rule states the consequence; the assessment itself stays in a.risk.
            level = a.risk.level.lower()
            if a.risk.recommended_decision == "REVIEW":
                consequence = f"Seller risk is estimated {level}, so this offer needs your review before simulated checkout."
            elif session_config(s).decisions[a.risk.level] == "BLOCK":
                consequence = f"Seller risk is estimated {level}, so this offer is blocked."
            else:
                consequence = "The seller shows a signal that always blocks checkout, so this offer is blocked."
            rule(
                "merchant_risk",
                a.risk.recommended_decision,
                "merchant_risk",
                consequence,
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
    if p.source == "shopify_catalog" and not p.detail_checked:
        rule("variant_unresolved", "BLOCK", "variant", "Inspect this seller and variant before simulated checkout.")
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
    if confirmed(s, "excluded_brands") and brand_match(s, p, "excluded_brands"):
        rule("brand", "BLOCK", "excluded_brands", "This brand is explicitly excluded.")
    if merchant_match(p, s.permissions.restricted_merchants):
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
    if p.source in ("browser_use", "shopify_catalog") and not s.search_replay:
        from .relevance import status
        relevance = status(s, p)
        if relevance != "match":
            rule("product_relevance", "BLOCK" if relevance == "mismatch" else "REVIEW", "category",
                 "This listing is not the requested product." if relevance == "mismatch" else "The listing’s fit to your request needs your review.")
    elif confirmed(s, "category") and p.category != value(s, "category"):
        rule(
            "category",
            "REVIEW",
            "category",
            "This product differs from the requested category.",
        )
    size = size_status(s, p)
    if size == "absent":
        rule("size", "BLOCK" if s.brief["size"].hard else "REVIEW", "size", "The requested size is unavailable.")
    elif size in ("unstated", "unknown") and (p.sizes or live(s, p)):
        rule("size_unconfirmed", "REVIEW", "size",
             f"The listing doesn't confirm size {value(s, 'size')}. Check the size options on the source page.")
    if confirmed(s, "merchants") and not merchant_match(p, terms(value(s, "merchants"))):
        rule(
            "preferred_merchant",
            "BLOCK" if s.brief["merchants"].hard else "REVIEW",
            "merchants",
            "This merchant differs from your preference.",
        )
    if (
        confirmed(s, "features")
        and s.brief["features"].hard
        and missing_features(s, p)
    ):
        rule("features", "BLOCK", "features", "A required feature is missing.")
    if confirmed(s, "features") and s.brief["features"].hard and unstated_features(s, p):
        rule("features_unconfirmed", "REVIEW", "features",
             f"The listing doesn't mention {', '.join(unstated_features(s, p))}. Check the source page yourself.")
    if confirmed(s, "preferred_brands") and s.brief["preferred_brands"].hard:
        brand = brand_match(s, p, "preferred_brands")
        if brand is False:
            rule("required_brand", "BLOCK", "preferred_brands",
                 "This brand does not meet your required brand constraint.")
        elif brand is None:
            rule("brand_unconfirmed", "REVIEW", "preferred_brands",
                 "The listing doesn't show its brand. Check it on the source page.")
    if (
        confirmed(s, "usage")
        and s.brief["usage"].hard
        and not usage_met(s, p)
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
    a.feature_fit = feature_fit(s, p)
    a.decision = (
        "BLOCK"
        if any(r.decision == "BLOCK" for r in rules)
        else "REVIEW"
        if any(r.decision == "REVIEW" for r in rules)
        else "ALLOW"
    )
    return a


def reasons(a, decision=None):
    """User-facing rule text, with the seller assessment after its consequence."""
    parts = []
    for r in a.rules:
        if decision and r.decision != decision:
            continue
        parts.append(r.explanation)
        if r.rule_id == "merchant_risk" and a.risk:
            parts.append(a.risk.explanation)
    return " ".join(parts)
