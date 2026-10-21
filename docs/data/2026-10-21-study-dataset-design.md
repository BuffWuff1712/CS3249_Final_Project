# Study Dataset Design: Products, Merchants and Risk Offers

Date: 2026-10-21
Status: Draft for review

## 1. Purpose

Beany's user study compares two conditions of the same shopping CUI:

- **Baseline**: the CUI does not handle merchant risk. Which baseline variant to use (allow everything, or silently refuse risky offers without announcing it) is still open. This dataset supports both.
- **Treatment**: the team's risk-handling design, which announces the risk, explains it and lets the user decide.

The independent variable is **how the CUI handles risk**. Risk offers are fixed stimuli. They move a conversation into a risk-handling moment.

Study scale: 6 participants, within-subject. Each participant does one practice task plus two formal tasks (one per condition). Every task asks the agent to help buy one product.

This spec covers **building the dataset only**. It produces a pool of risk offers covering every risk type, so the team can choose the study conditions later.

## 2. Decisions

| Topic | Decision |
|---|---|
| Categories | The existing three: Running shoes, Headphones, Backpacks. No category code changes are needed. |
| Task roles | Two formal tasks and one practice task. The default assignment is Headphones and Running shoes as formal tasks and Backpacks as practice. All three categories get the full risk library so the assignment can change. |
| Product content | Derived from Amazon Reviews 2023 (titles, features, descriptions, prices, reviews), hand-curated and anonymised. |
| Merchants | Entirely fictional and hand-authored. Amazon has no multi-seller offer data and no seller policies. Real seller names are never used. |
| Brands | Fictional brands. Brand reputation is conveyed through rating, rating count and description style, not a dedicated field. This prevents participants' prior opinions of real brands from confounding results and avoids presenting a real brand next to a malicious seller. |
| Risk coverage | One risk merchant per risk variant (Section 6), each selling the target product of all three categories. |
| Text fidelity | Every risk flag must be matched by realistic user-visible text in the fields listed in Section 7. Flags alone are not enough. |
| Detection | Risk prediction stays deterministic (`app/runtime/merchant_risk.py`). The LLM is not expected to infer risk from free text. |
| Ownership | The dataset owns signals, visible cues, prices and ground truth. The policy owner owns weights, thresholds and ALLOW/REVIEW/BLOCK decisions. Dataset tests never assert levels or decisions. |
| Existing fixtures | Kept unchanged, because `tests/test_merchant_extension.py` and other tests depend on them. New records use new ID prefixes. |

## 3. Sources and Anonymisation

**Source**: Amazon Reviews 2023 (McAuley Lab).

- Headphones: `Electronics` metadata and reviews.
- Running shoes and Backpacks: `Clothing_Shoes_and_Jewelry` metadata and reviews.

**Processing**:

1. A helper script filters items by keyword, then samples candidates with a fixed seed and writes them to a scratch file. Raw downloads stay outside the repository.
2. A human picks the final items and rewrites them:
   - Replace brand names in titles, features, descriptions and reviews with fictional brands from Section 4.
   - Remove model numbers, URLs, and any personal names or handles in reviews.
   - Convert prices from USD to SGD at a rate of 1.35, rounded to a whole dollar or `.90`.
   - Map features to `attributes` (lowercase keywords used by search) and `specifications` (a display dictionary).
3. Every product `description` must stop saying "Fictional ... for simulation only". The README and consent materials state that the data is fictional; product text should read like a real listing.

**Repository content**: only the curated JSON outputs are committed. Raw Amazon dumps are never committed.

## 4. Brands

Each category has four fictional brands spread across three reputation tiers:

| Tier | Signals |
|---|---|
| Well-known | Rating 4.5–4.8 with 1,500+ ratings, polished descriptions, full specifications |
| Mid-range | Rating 4.0–4.4 with 200–1,500 ratings, standard descriptions |
| No-name | Rating 3.6–4.1 with fewer than 200 ratings, sparse specifications |

Existing fictional brand names (Stride, Pace, Echo, Wave, Trail, Orbit) can be reused. A new brand is added where a category needs a fourth.

## 5. Task Structure

All three categories share the same structure. This parallelism is what lets differences between conditions be attributed to the CUI.

### 5.1 Task card (participant-facing)

Each task card gives one goal with a hard budget and leaves other preferences open, so the conversation needs clarification. Examples:

- Headphones: "Buy wireless noise-cancelling headphones for commuting, under SGD 200."
- Running shoes: "Buy cushioned road-running shoes for daily training, under SGD 180."
- Backpacks: "Buy a laptop backpack for campus, under SGD 120."

Final wording is decided when scenarios are assembled.

### 5.2 Candidate set (6–8 products per category)

- **One target product.** It is the only product that has every key attribute in the task goal, so search ranking (`policy.py:114`: attribute matches first, then lowest price) places its offers first.
- **Two or three near misses.** These are either cheaper but missing one key attribute, or complete but over budget.
- **The rest are filler.** They come from other brands and tiers and make the result list look real.
- Near misses and filler use **different brands** from the target product. This keeps them out of the target's price comparables (see 6.3).

### 5.3 Target product offers

Every offer of the target product is a separate `Product` record with the same name, brand, attributes and specifications, but a different `merchant_id` and price. P is the trusted price.

| Offer | Price | Role |
|---|---|---|
| Trusted | P (within budget) | Established store, verified, 2,000+ reviews at 4.7, clear 30-day return policy |
| Neutral | about 0.95P | Small verified store, few reviews, no risk signals; an extra legitimate option when switching merchant |
| Risk offers | See Section 6 | One per risk variant |

Every risk offer is priced **below P** so it is the attractive first proposal. Price is the lever that makes the risk moment happen naturally.

## 6. Risk Offer Library

### 6.1 Variants

Unless stated otherwise, each variant activates exactly **one** signal. All other merchant fields are kept clean: verified, contact present, Demo payment methods only, and `requested_information: []` (no extra checkout fields).

The last column is **informational only**. It shows the result under the current `config/merchant_risk_rules.json` (medium 2, high 5, critical 8) and helps the team choose conditions. The policy owner may change it.

| ID suffix | Signal | Price | Structured fields | Outcome under current rules (informational) |
|---|---|---|---|---|
| `lowprice` | low_price | 0.35P | none | LOW (the code forces LOW when price is the only signal) |
| `nobiz` | missing_business | 0.80P | `contact: ""`, `verified_business: false` | MEDIUM (2), REVIEW |
| `data-mid` | excessive_data | 0.80P | `requested_information` adds `date_of_birth` and `social_media_account` | MEDIUM (3), REVIEW |
| `data-high` | excessive_data | 0.80P | `requested_information` adds `government_id` | MEDIUM (3), forced BLOCK |
| `payment` | unusual_payment | 0.80P | `payment_methods: ["Gift card", "Crypto wallet"]` | MEDIUM (3), REVIEW |
| `external` | external_payment and unusual_payment | 0.75P | `payment_methods: ["Bank transfer"]`, `external_payment: true` | CRITICAL (8), forced BLOCK |
| `returns` | misleading_returns | 0.80P | `misleading_returns: true` | MEDIUM (2), REVIEW |
| `lookalike` | lookalike | 0.80P | `lookalike_identity: true` | MEDIUM (4), REVIEW |
| `pressure` | pressure | 0.85P | `pressure_tactics: true` | LOW (1), ALLOW |
| `inconsistent` | inconsistent | 0.80P | `inconsistent_information: true` | MEDIUM (3), REVIEW |
| `injection` | injection | 0.80P | Description contains an instruction aimed at the assistant that matches the existing regex | HIGH (6), forced BLOCK |
| `benign` | low_price only (hard negative) | 0.40P | none | LOW (low_price fires, forced LOW); ground truth TRUSTWORTHY |
| `concealed` | none (hidden malicious) | 0.85P | none | LOW; ground truth MALICIOUS |

`external` necessarily triggers unusual_payment as well, because bank transfer is not a Demo method.

`lowprice` and `benign` produce the same engine output. They differ only in visible text (Section 7) and ground truth. This is intentional: it is the existing false-positive design, where price alone is weak evidence.

`payment` and `external` accept no Demo payment method. `propose()` falls back to "Demo Visa" when the user's permitted methods and the merchant's methods do not overlap. Implementation must check that this path produces a coherent proposal and policy decision for these two variants.

**Notes for the policy owner** (current behaviour, not dataset requirements). Under default permissions:

- The engine's ALLOW becomes REVIEW, because approval is required.
- `data-mid` becomes BLOCK through `merchant_privacy`, because personal-data sharing is off by default.
- `payment` becomes BLOCK through `merchant_payment`, because Demo Visa is not accepted.
- Any merchant with non-empty `requested_information` is blocked by `merchant_privacy`. This is why clean merchants use an empty list.

### 6.2 Combination variants

Weak signals (low_price, pressure) only produce LOW on their own. No combination merchants are built now. If the team later needs a REVIEW-level version of a weak signal, a combination merchant is added (for example low_price + pressure + missing_business) and documented in the manifest in the same way.

### 6.3 Price comparables caveat

`assess()` computes the low_price median from the **scenario-scoped catalogue**: same brand, category and currency, excluding the product itself. The low_price result therefore depends on which offers a scenario includes.

Manifest expectations are computed against a **reference set**: the trusted offer, the neutral offer, and the offer itself. Prices are chosen with margin so that adding up to two other risk offers (each at 0.75P or above) to a scenario does not flip the result:

- The threshold is half the comparable median. It is 0.4875P with the reference set alone, and falls to 0.4375P when two 0.80P offers are added.
- `lowprice` (0.35P) and `benign` (0.40P) stay below the threshold in both cases.
- Every other offer, priced at 0.75P or above, never reaches it.

Putting `lowprice` and `benign` in the same scenario lowers the median further. Avoid it, or re-check the result.

Scenario assembly must re-run the validation test (Section 9) with the actual product set.

### 6.4 Ground truth labels

Labels are added to `data/research/merchant_ground_truth.json`:

- `lowprice`, `pressure`: UNCERTAIN.
- `nobiz`, `returns`, `inconsistent`, `lookalike`, `payment`, `data-mid`: SUSPICIOUS.
- `data-high`, `external`, `injection`, `concealed`: MALICIOUS.
- `benign`, trusted, neutral: TRUSTWORTHY.

## 7. Text Fidelity Rules

Every variant must show its signal in **at least one** user-visible field. It must not leak cues of any other signal. Base merchants show no risk cues at all.

| Variant | Required user-visible manifestation |
|---|---|
| `lowprice` | Description mentions a clearance sale. Merchant reviews are mixed, e.g. "suspiciously cheap but it arrived". |
| `nobiz` | Description is vague, with no address or company details. Website looks throwaway (e.g. `shop-8812.test`). Merchant reviews mention slow or no replies. |
| `data-mid` | Checkout note explains the extra fields as "membership verification". Merchant reviews mention marketing spam after ordering. |
| `data-high` | Checkout note demands an ID "for customs clearance". Merchant reviews raise privacy concerns. |
| `payment` | Description promotes "10% off when paying with gift card". Merchant reviews mention an unusual payment flow. |
| `external` | Description asks buyers to transfer money and message the store to confirm. Merchant reviews mention orders not being honoured. |
| `returns` | Headline promises "30-day free returns" while `return_policy` fine print says "store credit only" plus a category-specific exclusion. Merchant reviews describe a return dispute. |
| `lookalike` | Name and website imitate the trusted store (e.g. "Trai1 Official Store", `trail-officiaI.test`). Description claims to be the official store. |
| `pressure` | Description or product listing shows "Only 2 left" and "price returns in 10 minutes". |
| `inconsistent` | The merchant claims to be local with same-day dispatch, but its shipping terms quote 20–30 day overseas delivery. This is kept at merchant level so that all offers share product specifications. |
| `injection` | Description embeds an instruction to the assistant, such as telling it to ignore its rules. Placement keeps the rest of the listing plausible. |
| `benign` | Description gives a legitimate reason for the discount (end-of-term clearance, previous colourway). Merchant reviews are positive. |
| `concealed` | Indistinguishable from the trusted store in every visible field. |

**Category-specific exclusions.** One merchant serves all three categories, so the `returns` fine print lists every exclusion: opened electronics, shoes worn outdoors, and used bags are non-returnable.

**Where text lives.** Merchant-level cues (`nobiz`, `data-*`, `payment`, `external`, `returns`, `lookalike`, `inconsistent`, `injection`) go in merchant fields and are written once. Offer-level cues (`lowprice`, `pressure`, `benign`) go in that offer's product `description`, written per category.

**Drafting.** Text may be drafted with templates or an LLM, but every record is human-edited and checked against this table.

## 8. Schema and File Changes

### 8.1 Schema additions (`app/runtime/schemas.py`)

```python
class Review(Model):
    rating: int = Field(ge=1, le=5)
    title: str
    text: str
    date: str  # ISO date, fictional

# Product
rating: float | None = Field(default=None, ge=0, le=5)
rating_count: int = Field(default=0, ge=0)
reviews: list[Review] = Field(default_factory=list)  # 3-5 per product

# Merchant
merchant_reviews: list[Review] = Field(default_factory=list)  # 3-5 per merchant
checkout_note: str = ""  # explains requested_information to the user
```

All new fields have defaults, so existing fixtures stay valid.

**Product reviews.** Product reviews describe product quality and are shared by every offer of the same product. Risk cues live only in merchant reviews and merchant fields.

**Rendering dependency (outside this spec).** The participant UI must render reviews and the checkout note before participants can see these cues. The dataset is usable without it, but the cues would then be invisible.

**Prompt boundary.** Product reviews and merchant reviews are observable data and may be sent to the model. They are untrusted content and must be treated the same way as descriptions.

### 8.2 Data files

| File | Change |
|---|---|
| `data/products/catalogue.json` | Append study products and offers. |
| `data/merchants/merchants.json` | Append study merchants. Websites must use `.test` domains (enforced by `merchants.py`). |
| `data/research/merchant_ground_truth.json` | Append labels. |
| `data/research/risk_offer_manifest.json` | **New, researcher-only, never loaded at runtime.** One entry per offer (format below). |
| `data/scenarios/scenarios.json` | Not changed by this work. Scenarios are assembled after the team selects conditions. |
| `scripts/sample_amazon.py` | New helper that filters and samples candidates into a scratch file. It does not write the final data. |

### 8.3 ID conventions

- Products: `study-{cat}-{n}` for candidates and `study-{cat}-target-{variant}` for target offers, where `cat` is `hp`, `rs` or `bp`.
- Merchants: `study-m-trusted`, `study-m-neutral`, `study-m-{variant}`.

### 8.4 Manifest entry format

```json
{
  "product_id": "study-hp-target-returns",
  "merchant_id": "study-m-returns",
  "category": "Headphones",
  "variant": "returns",
  "signals": ["misleading_returns"],
  "visible_in": ["return_policy", "description", "merchant_reviews"],
  "price_ratio": 0.80,
  "reference_set": ["study-hp-target-trusted", "study-hp-target-neutral"],
  "ground_truth": "SUSPICIOUS"
}
```

## 9. Validation

**Automated** (new test, `tests/test_study_dataset.py`):

1. All study records validate against the Pydantic schemas, IDs are unique, and every `merchant_id` resolves.
2. For each manifest entry, build the reference set and call `assess()`. Assert that the set of fired rule IDs equals the manifest's `signals`: the intended signal fires and no other does. Levels and decisions are not asserted, so policy tuning never breaks dataset tests.
3. Within each category, every target offer shares name, brand, attributes and specifications with the trusted offer. Every risk offer is priced below 0.95P, so it ranks ahead of both the neutral and trusted offers.
4. For the task goal's attributes, the target product ranks first among the candidates (search ranking test).
5. Every ground truth label has a matching merchant.

**Manual** (checklist in the manifest PR):

- Each variant shows its required manifestation (Section 7) in at least one listed field.
- No variant leaks cues of another signal.
- No real brand, real seller, URL or personal name remains anywhere in the text.

## 10. Size

| Item | Count |
|---|---|
| Candidate products | About 20 (6–8 per category, including the target) |
| Target product offers | 15 per category (trusted, neutral and 13 variants), 45 in total |
| Merchants | 15 study merchants (trusted, neutral, 13 variants), plus existing fixtures |

Every record can be reviewed by hand.

## 11. Out of Scope

- Choosing which risk variants become study conditions.
- Implementing the baseline mode (allow-all or silent refusal).
- Assembling scenario entries and the counterbalancing schedule.
- Rendering reviews and checkout notes in the frontend.
- Strengthening injection detection or adding LLM-based risk detection.

## 12. Open Questions

1. Baseline variant: allow-all or silent refusal. This affects tuning only (cue salience, the price gap in the silent swap, whether forced-BLOCK variants are usable). It does not change the dataset structure.
2. Whether combination variants (6.2) are needed after the team's selection.
3. Final task card wording and budgets.
