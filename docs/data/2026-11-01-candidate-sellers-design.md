# Candidate Sellers and Demo Scenario

Date: 2026-11-01
Status: Implemented
Related: [study dataset design](2026-10-21-study-dataset-design.md), [website reputation design](2026-10-29-website-reputation-design.md)

## 1. Goal

When a user corrects their needs during a demonstration, the recommendation moves from the study target to another product. Today every candidate product (`study-{cat}-1` onward) has one seller, the trusted store, so after a correction the user sees no risk at all.

This change gives nine existing candidates additional sellers drawn from the existing study merchants: a clean small store plus low-to-medium risk stores, and one high-risk store per category. A new conversation-driven `demo` scenario shows only study data, so a demonstration can run one flow: state a need, see the target's risky sellers, correct the need, and see the new product's sellers, including risky ones.

### Out of scope

- Statements of priority such as "battery life matters most" when the brief otherwise stays the same. Search weights every feature equally, and the assistant chooses among the top results. Changing that belongs to the policy owner.
- Free sessions without a scenario. They keep the original fixtures mixed in.
- New product models, new merchants, merchant records, ground-truth labels and the site registry. All stay unchanged.
- Existing scenarios. None of them gains the new offers, so the user study is unaffected.
- The `/shop` frontend, which is teammate-owned.

### Decisions taken in review

| Topic | Decision |
|---|---|
| Kind of correction | Only corrections that change the needs themselves (features, usage or budget). |
| Product variety | Existing candidates are enough. No new models. |
| Sellers | Existing study merchants only. Each chosen candidate gets `neutral`, two low-to-medium risk stores, and in one candidate per category a high-risk store. |
| Excluded variants | `lowprice` and `benign` (their `low_price` signal needs a stable same-brand median), `lookalike` (its merchant flag claims a knockoff, which a genuine candidate is not), `concealed` (not requested). |
| Prices | Candidate price times the variant's existing ratio, so a risky seller is cheaper than the trusted one, as for the target. |
| Entry point | A `demo` scenario that lists every study product, opened from `/research`. |
| IDs | `study-{cat}-{n}-{variant}`, so every study-wide check also covers the new offers. |

## 2. Seller Assignment

The trusted offer of each candidate (`study-{cat}-{n}`) stays as it is. Prices round down to the nearest `.9`, the same rule the target offers use.

| Candidate | Correction it serves | New offers (variant: price SGD) |
|---|---|---|
| `study-hp-2` Brio Air 60, 36.9 | No noise cancelling needed; foldable with long battery | neutral 34.9, pressure 30.9, returns 28.9 |
| `study-hp-3` Kestrel Studio Air, 44.9 | For video calls; needs a microphone | neutral 41.9, site-mid 32.9, payment 35.9, **external** 32.9 |
| `study-hp-1` Corvo Fold ANC, 256.9 | Foldable noise-cancelling; budget raised to 300 | neutral 243.9, nobiz 204.9, site-bad 204.9 |
| `study-rs-2` Summit Ridge Trail, 79.9 | Trail running | neutral 75.9, pressure 67.9, inconsistent 63.9, **injection** 63.9 |
| `study-rs-4` Tread Road Daily, 65.9 | Lightweight road shoe; cushioning not needed | neutral 61.9, site-mid 48.9, returns 51.9 |
| `study-rs-1` Arro Lift Neutral, 237.9 | Responsive cushioned road shoe; budget raised to 250 | neutral 225.9, nobiz 189.9, site-fake 189.9 |
| `study-bp-4` Nomad Cabin 40, 67.9 | Travel, carry-on | neutral 63.9, pressure 56.9, data-mid 53.9, **data-high** 53.9 |
| `study-bp-2` Fennec Dash 15, 40.9 | Lighter laptop backpack | neutral 37.9, site-mid 29.9, nobiz 31.9 |
| `study-bp-1` Nomad Roller 19, 128.9 | Rolling laptop bag; budget raised to 150 | neutral 121.9, returns 102.9, payment 102.9 |

That is 30 new offers: 9 `neutral` and 21 risk offers. Bold marks the high-risk store in each category.

`site-fake` sits on Arro Lift Neutral because its original trusted offer is also sold by Northline Outfitters, whose name `site-fake` copies on an imitation domain.

### 2.1 Low-price safety

`low_price` compares an offer with the median of other offers of the same brand, category and currency, and fires below 50% of it. With all 30 offers added, a full computation over every study product shows that `low_price` fires only on the existing target `lowprice` and `benign` offers. The nearest case is Kestrel: the new Studio Air offers keep the brand median near 42, so Flat S2 at 37.9 stays well above the threshold.

## 3. Record Format

Each new offer in `backend/data/products/catalogue.json`:

- `id`: `study-{cat}-{n}-{variant}`, for example `study-hp-2-neutral`. The test helper `candidates()` uses `fullmatch` on `study-{cat}-\d+`, so it does not pick these up.
- Equal to the candidate's trusted offer: `name`, `brand`, `category`, `currency`, `attributes`, `specifications`, `sizes`, `rating`, `rating_count`, `description`, `stock`. Equal fields keep `/shop` grouping the offers under the candidate's model (its `model_key`) and leave its comparison table unchanged.
- Different: `merchant_id` (`study-m-{variant}`), `price` (section 2) and `reviews`.
- `reviews`: two product reviews, built like the target's review pool but smaller. Call the candidate's three existing reviews A, B and C, in stored order, and write two new reviews D and E per candidate (18 new reviews in all). Offers take pairs in section 2 order: (A, D), (B, E), (C, D), (A, E); a family with three new offers uses the first three pairs. Each new offer then shares exactly one review with the trusted offer and at most one with any sibling, and no two offers show the same reviews. D and E are about the product only and consistent with its specifications.
- `merchant` and `trust` are display fields, filled in from the merchant record at load time, as for every other study offer.

Risk cues stay in merchant fields only. Every signal used here comes from the merchant record or its website, so each new risk offer fires its variant's signals unchanged.

## 4. Manifest and Replay

`backend/data/research/risk_offer_manifest.json` gains one entry per risk offer (21 entries; total 69). `neutral` offers get no entry, as now. The fields follow the existing entries:

| Field | Value |
|---|---|
| `product_id` | The new offer ID |
| `merchant_id` | `study-m-{variant}` |
| `category` | The candidate's category |
| `variant` | The variant key |
| `signals` | The variant's signals, as in the study dataset design |
| `visible_in` | Copied from the same variant's target entry in that category |
| `price_ratio` | The variant's ratio |
| `reference_set` | `[study-{cat}-{n}, study-{cat}-{n}-neutral]` |
| `ground_truth` | The variant's label |

After the data change, `python -m scripts.build_replay_fixture` regenerates `backend/data/replay/study_listings.json`, which then includes the new offers.

## 5. Demo Scenario

A new entry at the end of `backend/data/scenarios/scenarios.json`:

| Field | Value |
|---|---|
| `id` | `demo` |
| `name` | `Demonstration (study data)` |
| `scenario_type` | `demonstration` |
| `category` | `Headphones, Running shoes, Backpacks` |
| `context` | An opening message telling the user to describe what they want to buy, and that every product and store is fictional |
| `user_goal` | Buy headphones, running shoes or a backpack, then change the needs once |
| `system_goal` | Surface each proposed seller's risk and keep the user in control after a correction |
| `initial_brief`, `permissions`, `action` | `{}` |
| `trigger_product` | `null` (conversation-driven) |
| `product_ids` | Every `study-*` product ID |
| `expected_decision` | `REVIEW` |

Other required fields (`requirements`, `expected_intervention`, `expected_outcome`, `success_criteria`, `failure_criteria`, `ground_truth_reference`, `observable_indicators_reference`) carry short descriptive text, or `null` where no single offer applies.

The scenario lists products explicitly, as the data README requires for study scenarios. A test keeps the list equal to every study product, so it cannot go stale.

To demonstrate: on `/research`, start a `demo` session and open the participant interface. The scenario's catalogue contains only study data, so the interpreter's feature vocabulary has one spelling per feature (for example `noise-cancelling`).

## 6. Expected Behaviour

Search ranks by feature matches, then by price, and recommends four offers. Run over the demo scope:

| Brief (soft features, hard budget) | Top four, in order |
|---|---|
| Headphones: wireless, noise-cancelling; 200 | target lowprice, benign, site-mid, external |
| Running shoes: cushioned, road; 180 | target lowprice, benign, external, site-mid |
| Backpacks: laptop, water-resistant; 120 | target lowprice, benign, external, site-mid |
| Headphones: wireless, foldable, long-battery; 200 | `hp-2` returns, pressure, neutral, trusted |
| Headphones: wireless, microphone; 200 | `hp-3` external, site-mid, payment, neutral |
| Headphones: wireless, noise-cancelling, foldable; 300 | `hp-1` nobiz, site-bad, neutral, trusted |
| Running shoes: trail; 180 | `rs-2` inconsistent, injection, pressure, neutral |
| Running shoes: road, lightweight; 180 | `rs-4` site-mid, returns, neutral, trusted |
| Running shoes: cushioned, road, responsive; 250 | `rs-1` nobiz, site-fake, neutral, trusted |
| Backpacks: travel; 120 | `bp-4` data-high, data-mid, pressure, neutral |
| Backpacks: laptop, lightweight; 120 | `bp-2` site-mid, nobiz, neutral, trusted |
| Backpacks: laptop, water-resistant, rolling; 150 | `bp-1` payment, returns, neutral, trusted |

The default goals still surface only the target, so the new offers hide none of its risky sellers. After every correction, the corrected product's sellers fill the top four with a risky seller first. Equal prices fall back to ID order, which puts the high-risk store first for `hp-3` and `bp-4`. Those are blocked by policy, which demonstrates a block. The assistant chooses which of the four to propose, so a live run can propose a different one.

## 7. Tests

Additions to `backend/tests/test_study_dataset.py`, driven by one assignment constant that mirrors section 2:

1. Every offer in the table exists, has `merchant_id` `study-m-{variant}`, and equals its candidate's trusted offer on the shared fields of section 3.
2. Each price is within 0.03 of `candidate price × ratio` and below the trusted price.
3. Each new offer's two reviews follow the pairing in section 3: one of the trusted offer's reviews and one of the candidate's two new reviews. Within one candidate's offers, any two share at most one review.
4. Each risk offer has a manifest entry whose fields match section 4, and whose signals equal what `assess()` fires in its reference set. The manifest total is 69.
5. In category and catalogue scope, each new offer fires exactly its variant's signals. `test_candidates_fire_no_signals` keeps covering the original candidates under the new price spread.
6. In the `demo` scope, each default goal's top four are target offers, and each correction in section 6 ranks an offer of its candidate first.
7. The `demo` scenario lists exactly every `study-*` product. No other scenario lists a new offer.
8. All existing tests pass unchanged, including `test_only_target_meets_goal_within_budget`, the existing manifest checks, and the replay fixture check.

## 8. Documentation

- `backend/data/README.md`: in "Study dataset at a glance", add the candidate sellers, the assignment rule and the excluded variants; describe the `demo` scenario under "Building a study scenario".
- `docs/configuration-guide.md`: a paragraph on the `demo` scenario next to the `site-reputation` paragraph.
- This design and its implementation plan in `docs/data/`.

## 9. Known Limitations

- Priority statements ("matters most") still add a feature with equal weight, so they may not change the recommendation (section 1).
- The `/shop` seller table labels offers by merchant name only, so the trusted and `site-fake` offers of Arro Lift Neutral both read "Northline Outfitters". Showing the domain is a change for the `/shop` owner.
- The demo scope contains all 18 target offers, so research reports for `demo` sessions mix many variants. `demo` sessions are for demonstration, not for analysis.
