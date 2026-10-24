"""Authoritative contracts for the integrated Beany application."""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Fact(Model):
    value: str
    source: Literal["confirmed", "suggested", "unspecified"] = "confirmed"
    hard: bool = False


class Permissions(Model):
    require_approval: bool = True
    substitutions: bool = False
    share_personal_data: bool = False
    payment_methods: list[Literal["Demo Visa", "Demo Wallet"]] = Field(
        default_factory=lambda: ["Demo Visa"]
    )
    restricted_merchants: list[str] = Field(default_factory=list)
    autonomy: Literal["guided", "balanced"] = "guided"


class Review(Model):
    rating: int = Field(ge=1, le=5)
    title: str
    text: str
    date: str  # ISO date, fictional


class Merchant(Model):
    id: str
    name: str
    website: str
    description: str
    payment_methods: list[str]
    return_policy: str
    contact: str
    review_count: int = Field(ge=0)
    review_rating: float | None = Field(default=None, ge=0, le=5)
    verified_business: bool
    requested_information: list[str]
    external_payment: bool = False
    misleading_returns: bool = False
    lookalike_identity: bool = False
    pressure_tactics: bool = False
    inconsistent_information: bool = False
    merchant_reviews: list[Review] = Field(default_factory=list)
    checkout_note: str = ""


class RiskEvidence(Model):
    rule_id: str
    evidence: str
    weight: float


class RiskAssessment(Model):
    merchant_id: str
    level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    score: float
    evidence: list[RiskEvidence]
    recommended_decision: Literal["ALLOW", "REVIEW", "BLOCK"]
    explanation: str
    config_version: str
    config_hash: str


class Product(Model):
    source: Literal["catalogue", "browser_use"] = "catalogue"
    source_url: str = ""
    observed_at: str = ""
    id: str
    name: str
    category: str
    brand: str
    price: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal["SGD", "USD"] = "SGD"
    merchant: str
    merchant_id: str = ""
    specifications: dict[str, str] = Field(default_factory=dict)
    attributes: list[str]
    sizes: list[str] = Field(default_factory=list)
    stock: bool = True
    description: str
    trust: Literal["established", "unverified"] = "established"
    rating: float | None = Field(default=None, ge=0, le=5)
    rating_count: int = Field(default=0, ge=0)
    reviews: list[Review] = Field(default_factory=list)


class Rule(Model):
    triggering_action: str
    rule_id: str
    decision: Literal["ALLOW", "REVIEW", "BLOCK"]
    constraint: str
    explanation: str
    intervention: bool


class Action(Model):
    id: str = Field(default_factory=uid)
    product: Product
    merchant_details: Merchant | None = None
    risk: RiskAssessment | None = None
    payment_method: str = "Demo Visa"
    shares_personal_data: bool = False
    substitute: bool = False
    fingerprint: str = ""
    status: Literal["pending", "approved", "rejected", "superseded"] = "pending"
    rules: list[Rule] = Field(default_factory=list)
    decision: Literal["ALLOW", "REVIEW", "BLOCK"] = "REVIEW"


class Event(Model):
    id: str = Field(default_factory=uid)
    timestamp: str = Field(default_factory=now)
    kind: str
    detail: str


class Message(Model):
    role: Literal["user", "assistant"]
    text: str


class Receipt(Model):
    id: str = Field(default_factory=uid)
    proposal_id: str
    fingerprint: str
    product: Product
    timestamp: str = Field(default_factory=now)
    status: Literal["simulated"] = "simulated"


class Approval(Model):
    proposal_id: str
    fingerprint: str
    action: Literal["approve", "reject"]
    timestamp: str = Field(default_factory=now)


class CartItem(Model):
    action: Action
    brief: dict[str, Fact]
    added_at: str = Field(default_factory=now)


class CartSelection(Model):
    proposal_id: str
    fingerprint: str


class CartCheckout(Model):
    items: list[CartSelection] = Field(min_length=1, max_length=100)


class Session(Model):
    search_provider: Literal["catalogue", "browser_use"] = "catalogue"
    live_products: dict[str, Product] = Field(default_factory=dict)
    live_merchants: dict[str, Merchant] = Field(default_factory=dict)
    id: str = Field(default_factory=uid)
    participant: str = Field(default_factory=lambda: "P-" + uid()[:8])
    created_at: str = Field(default_factory=now)
    brief: dict[str, Fact] = Field(default_factory=dict)
    permissions: Permissions = Field(default_factory=Permissions)
    messages: list[Message] = Field(default_factory=list)
    recommendations: list[Product] = Field(default_factory=list)
    proposals: list[Action] = Field(default_factory=list)
    approvals: list[Approval] = Field(default_factory=list)
    receipts: list[Receipt] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    stage: str = "ready"
    suggestions: list[str] = Field(default_factory=list)
    scenario_id: str | None = None
    experiment: dict = Field(default_factory=dict)
    rejected_merchants: list[str] = Field(default_factory=list)
    rejected_products: list[str] = Field(default_factory=list)
    clarification_count: int = 0
    intervention_count: int = 0
    mode: str = "openai"
    cart: list[CartItem] = Field(default_factory=list)


class Change(Model):
    field: Literal[
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
    ]
    value: str | None
    source: Literal["confirmed", "suggested"]
    hard: bool
    evidence: str


class Interpretation(Model):
    reply: str = Field(
        min_length=1,
        description="Complete user-facing message, including one question when intent is clarify.",
    )
    changes: list[Change]
    intent: Literal["search", "clarify", "explain", "cancel", "new_task", "alternative", "checkout"]
    suggestions: list[str]


class Chat(Model):
    text: str = Field(min_length=1, max_length=2000)


class Decision(Model):
    action: Literal["approve", "reject"]
    fingerprint: str


class Edit(Model):
    field: str
    fact: Fact | None


class SessionView(Session):
    # Internal profile/config snapshots are persisted but never returned to participants.
    experiment: dict = Field(default_factory=dict, exclude=True)
