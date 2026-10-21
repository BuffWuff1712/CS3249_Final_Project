"""Validation for the study dataset (docs/data/2026-10-21-study-dataset-design.md).

Asserts signals, prices and ground truth only. Risk levels and ALLOW/REVIEW/BLOCK
decisions belong to the policy owner and are deliberately not asserted here.
"""

import json
import pytest
from app.runtime.merchants import merchants
from app.runtime.research import TRUTH_PATH

VARIANTS = [
    "lowprice",
    "nobiz",
    "data-mid",
    "data-high",
    "payment",
    "external",
    "returns",
    "lookalike",
    "pressure",
    "inconsistent",
    "injection",
    "benign",
    "concealed",
]

EXPECTED = {
    "trusted": {"signals": [], "ground_truth": "TRUSTWORTHY"},
    "neutral": {"signals": [], "ground_truth": "TRUSTWORTHY"},
    "lowprice": {"signals": ["low_price"], "ground_truth": "UNCERTAIN"},
    "benign": {"signals": ["low_price"], "ground_truth": "TRUSTWORTHY"},
    "pressure": {"signals": ["pressure"], "ground_truth": "UNCERTAIN"},
    "concealed": {"signals": [], "ground_truth": "MALICIOUS"},
    "nobiz": {"signals": ["missing_business"], "ground_truth": "SUSPICIOUS"},
    "returns": {"signals": ["misleading_returns"], "ground_truth": "SUSPICIOUS"},
    "inconsistent": {"signals": ["inconsistent"], "ground_truth": "SUSPICIOUS"},
    "lookalike": {"signals": ["lookalike"], "ground_truth": "SUSPICIOUS"},
    "data-mid": {"signals": ["excessive_data"], "ground_truth": "SUSPICIOUS"},
    "payment": {"signals": ["unusual_payment"], "ground_truth": "SUSPICIOUS"},
    "data-high": {"signals": ["excessive_data"], "ground_truth": "MALICIOUS"},
    "injection": {"signals": ["injection"], "ground_truth": "MALICIOUS"},
    "external": {
        "signals": ["external_payment", "unusual_payment"],
        "ground_truth": "MALICIOUS",
    },
}

STUDY_CATEGORIES: list[str] = []

ALL_MERCHANT_KEYS = ["trusted", "neutral", *VARIANTS]


def test_study_merchants_exist():
    assert {f"study-m-{v}" for v in ALL_MERCHANT_KEYS} <= set(merchants())


@pytest.mark.parametrize("v", ["trusted", "neutral", "lowprice", "benign", "concealed"])
def test_clean_merchants_have_clean_fields(v):
    m = merchants()[f"study-m-{v}"]
    assert m.requested_information == [] and m.verified_business and m.contact
    assert m.payment_methods == ["Demo Visa", "Demo Wallet"] and not m.external_payment
    assert not any(
        [
            m.misleading_returns,
            m.lookalike_identity,
            m.pressure_tactics,
            m.inconsistent_information,
        ]
    )


@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_merchant_reviews_count(v):
    assert 3 <= len(merchants()[f"study-m-{v}"].merchant_reviews) <= 5


def test_concealed_mirrors_trusted():
    t, c = merchants()["study-m-trusted"], merchants()["study-m-concealed"]
    same = [
        "description",
        "payment_methods",
        "return_policy",
        "requested_information",
        "verified_business",
        "external_payment",
        "misleading_returns",
        "lookalike_identity",
        "pressure_tactics",
        "inconsistent_information",
        "checkout_note",
    ]
    assert all(getattr(t, f) == getattr(c, f) for f in same)
    assert abs(c.review_count - t.review_count) <= 0.2 * t.review_count
    assert abs(c.review_rating - t.review_rating) <= 0.1


@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_ground_truth_labels(v):
    labels = json.loads(TRUTH_PATH.read_text(encoding="utf-8-sig"))["labels"]
    assert labels[f"study-m-{v}"] == EXPECTED[v]["ground_truth"]
