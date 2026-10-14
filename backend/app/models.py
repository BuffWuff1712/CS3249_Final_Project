from typing import Literal
from pydantic import BaseModel, Field


class Preferences(BaseModel):
    budget: float = Field(default=150, gt=0, le=100000)
    currency: Literal['SGD', 'USD'] = 'SGD'
    allowed_merchants: list[str] = Field(default_factory=lambda: ['Northstar', 'Everyday', 'Market Lane'])
    restricted_merchants: list[str] = Field(default_factory=lambda: ['Market Lane'])
    payment_methods: list[Literal['Demo Visa', 'Demo Wallet']] = Field(default_factory=lambda: ['Demo Visa'])
    substitutions: bool = False
    share_personal_data: bool = False
    autonomy: Literal['guided', 'balanced'] = 'guided'


class Product(BaseModel):
    id: str
    name: str
    price: float
    currency: Literal['SGD', 'USD'] = 'SGD'
    merchant: str
    category: str
    attributes: list[str]
    substitute: bool = False


class Message(BaseModel):
    role: Literal['assistant', 'user']
    text: str


class AuditEvent(BaseModel):
    id: str
    timestamp: str
    kind: str
    detail: str


class Proposal(BaseModel):
    id: str
    product: Product
    payment_method: str = 'Demo Visa'
    shares_personal_data: bool = False
    status: Literal['pending', 'approved', 'rejected', 'superseded'] = 'pending'
    violations: list[str] = Field(default_factory=list)
    explanation: str = ''


class Session(BaseModel):
    id: str
    preferences: Preferences = Field(default_factory=Preferences)
    messages: list[Message] = Field(default_factory=list)
    proposals: list[Proposal] = Field(default_factory=list)
    activity: list[str] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    scenario: Literal['normal', 'budget', 'substitution', 'merchant'] = 'normal'


class DecisionRequest(BaseModel):
    action: Literal['approve', 'reject', 'refine']
    note: str = Field(default='', max_length=2000)
