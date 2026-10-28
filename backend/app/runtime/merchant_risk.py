"""Deterministic risk prediction from observable signals, not hidden labels."""

import hashlib, json, re
from statistics import median
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .schemas import Model, RiskAssessment, RiskEvidence

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/merchant_risk_rules.json"
RULES = {
    "low_price",
    "missing_business",
    "excessive_data",
    "unusual_payment",
    "external_payment",
    "misleading_returns",
    "lookalike",
    "pressure",
    "inconsistent",
    "injection",
}


class RiskConfig(Model):
    version: str = Field(min_length=1)
    weights: dict[str, float]
    medium: float = Field(gt=0, allow_inf_nan=False)
    high: float = Field(gt=0, allow_inf_nan=False)
    critical: float = Field(gt=0, allow_inf_nan=False)
    low_price_ratio: float = Field(gt=0, lt=1, allow_inf_nan=False)
    decisions: dict[str, Literal["ALLOW", "REVIEW", "BLOCK"]]
    explanation_detail: Literal["brief", "detailed"] = "detailed"

    @model_validator(mode="after")
    def coherent(self):
        import math

        if not self.medium < self.high < self.critical:
            raise ValueError("Thresholds must increase")
        if set(self.weights) != RULES or any(
            not math.isfinite(v) or v < 0 for v in self.weights.values()
        ):
            raise ValueError("All known weights must be finite and nonnegative")
        if set(self.decisions) != {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("All risk decisions required")
        return self


def load_config():
    return RiskConfig.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def digest(config):
    return hashlib.sha256(
        json.dumps(config.model_dump(), sort_keys=True).encode()
    ).hexdigest()


def session_config(s):
    # Invalid current config blocks checkout even when an older snapshot exists.
    current = load_config()
    return (
        RiskConfig.model_validate(s.experiment["risk_config"])
        if s.experiment.get("risk_config")
        else current
    )


INJECTION = re.compile(
    r"ignore.{0,60}(rules|instructions|preferences)|reveal.{0,30}(key|password)|disregard.{0,40}(policy|rules)|enable.{0,40}personal data",
    re.I,
)
SENSITIVE_REQUESTS = {"password", "bank_password", "card_number", "government_id"}


def safeguard_block(product, merchant):
    """Non-negotiable application safeguards, read from the record; no detector may tune them away."""
    return bool(
        merchant.external_payment
        or set(merchant.requested_information) & SENSITIVE_REQUESTS
        or INJECTION.search(merchant.description + " " + product.description)
    )


def assess(product, merchant, comparables, config):
    evidence = []

    def add(rule, text):
        evidence.append(
            RiskEvidence(rule_id=rule, evidence=text, weight=config.weights[rule])
        )

    cheap = low_price(product, comparables, config)
    if cheap:
        add("low_price", cheap)
    if not merchant.contact.strip() or not merchant.verified_business:
        add(
            "missing_business",
            "Business contact or verification information is incomplete in this simulated record.",
        )
    excessive = set(merchant.requested_information) - {
        "fictional_name",
        "fictional_delivery_address",
        "fictional_email",
    }
    if excessive:
        add(
            "excessive_data",
            "Checkout requests unrelated information: "
            + ", ".join(sorted(excessive))
            + ".",
        )
    if any(m not in ("Demo Visa", "Demo Wallet") for m in merchant.payment_methods):
        add(
            "unusual_payment",
            "Merchant lists an unsupported payment channel: "
            + ", ".join(merchant.payment_methods)
            + ".",
        )
    if merchant.external_payment:
        add(
            "external_payment",
            "Merchant requests payment outside the simulated checkout.",
        )
    for field, rule, text in [
        (
            "misleading_returns",
            "misleading_returns",
            "Return terms conflict with the advertised refund promise.",
        ),
        (
            "lookalike_identity",
            "lookalike",
            "Merchant identity resembles another business in the fixture.",
        ),
        ("pressure_tactics", "pressure", "The listing uses a high-pressure deadline."),
        (
            "inconsistent_information",
            "inconsistent",
            "Merchant and product information is inconsistent in the fixture.",
        ),
    ]:
        if getattr(merchant, field):
            add(rule, text)
    if INJECTION.search(merchant.description + " " + product.description):
        add(
            "injection",
            "The description contains instructions aimed at changing assistant behaviour; these are treated as untrusted content.",
        )
    # Non-negotiable application safeguards cannot be tuned away.
    return score(merchant, evidence, config, safeguard_block(product, merchant), "observable simulation signals")


def score(merchant, evidence, config, force_block, basis):
    total = sum(e.weight for e in evidence)
    level = (
        "CRITICAL"
        if total >= config.critical
        else "HIGH"
        if total >= config.high
        else "MEDIUM"
        if total >= config.medium
        else "LOW"
    )
    if evidence and all(e.rule_id == "low_price" for e in evidence):
        level = "LOW"
    decision = "BLOCK" if force_block else config.decisions[level]
    explanation = (
        f"{merchant.name}: {level.lower()} predicted risk from {basis}. "
        + (
            " ".join(e.evidence for e in evidence)
            if config.explanation_detail == "detailed"
            else f"{len(evidence)} signal(s) observed. "
        )
        + "This is an uncertain assessment, not proof of fraud."
        if evidence
        else f"No configured risk signals detected for {merchant.name}. This does not guarantee safety."
    )
    return RiskAssessment(
        merchant_id=merchant.id,
        level=level,
        score=total,
        evidence=evidence,
        recommended_decision=decision,
        explanation=explanation,
        config_version=config.version,
        config_hash=digest(config),
    )


def low_price(product, comparables, config):
    prices = [
        p.price
        for p in comparables
        if p.id != product.id
        and p.category == product.category
        and p.brand == product.brand
        and p.currency == product.currency
    ]
    if prices and product.price < median(prices) * config.low_price_ratio:
        return f"Price {product.price:.2f} is below {config.low_price_ratio:.0%} of the comparable-brand median {median(prices):.2f} {product.currency}. A discount alone does not establish wrongdoing."
    return None


def assess_live(product, merchant, comparables, config, review, force_block=False):
    """Score grounded agent findings for a web snapshot; blank page fields are never evidence."""
    evidence = [
        RiskEvidence(
            rule_id=f.rule_id,
            evidence=f"{f.reason} Observed: \u201c{f.quote}\u201d",
            weight=config.weights[f.rule_id],
        )
        for f in review.findings
    ]
    cheap = low_price(product, comparables, config)
    if cheap:
        evidence.append(
            RiskEvidence(rule_id="low_price", evidence=cheap + " Compared with other captured listings only.", weight=config.weights["low_price"])
        )
    force_block = force_block or any(e.rule_id in ("external_payment", "injection") for e in evidence)
    return score(merchant, evidence, config, force_block, "the captured listing details")
