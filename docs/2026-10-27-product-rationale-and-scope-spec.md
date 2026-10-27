# Product Rationale and Scope

Beany product and change specification

27 October 2026 | CS3249 final project | Baseline commit `13e124f`

## 1 Product rationale

Consumer shopping agents can reduce the work of searching several websites and synthesising product information, but they also make decisions that users cannot easily inspect. A recommendation is difficult to trust when the user cannot verify what the agent understood, which sources it considered or why one merchant deserves more caution than another.

Beany addresses this gap through two connected capabilities: clarifying purchase intent and surfacing source trust signals and merchant risk indicators. Users should be able to see their needs represented accurately, correct that representation, inspect evidence and decide whether a recommendation is appropriate. Success means informed and calibrated reliance: accepting useful assistance while recognising uncertainty and rejecting unsuitable offers. Simply increasing trust, acceptance or purchase intent would be an inadequate goal.

The intended user is a consumer who wants research assistance for a considered purchase, particularly when unfamiliar with products or sellers. Purchases above $200 motivated the discussion because errors may matter more at that level; the threshold is a motivating example, not an eligibility rule. For the Singapore demonstration, all selected task prices and budgets must explicitly use SGD. Any claim about an above-$200 population requires its original currency and source to be established separately.

A conventional comparison site illustrates the design opportunity: a person can inspect sellers, prices and reviews, but must still determine which option fits their needs and how to interpret unfamiliar merchants. The meeting's kakaku.com example provides this design analogy. Beany should preserve access to the underlying information while helping users interpret its relevance.

The final scope is consumer product discovery, evaluation and human decision support. Earlier agent-to-agent purchasing and delegated transaction framing should be retired from the product story. The user remains in control at the decision and checkout boundary. Real payments and real orders are outside this build; existing checkout and receipts are explicitly simulated.

## 2 Scope and decisions

### Required final build

- Purchase intent clarification for meaningful ambiguities, with an explicit option to browse when the user is unsure.
- A visible, editable purchase brief containing category, budget, currency, use case and preferences, with provenance and hard versus soft distinctions.
- A result-side recap of the current brief and a clear explanation of important matches, mismatches and tradeoffs.
- Raw source signals per offer: product and seller ratings with counts, merchant identity indicators, returns and a comparable price reference when available.
- Evidence-backed merchant risk communication that distinguishes observed signals, missing information and uncertainty.
- A visible activity explanation of actual searches, inspections and assessments, presented before the result recommendation.
- A controlled synthetic catalogue with trustworthy, unfamiliar, suspicious and ambiguous merchants, plus headphones and one existing second category for the demo.
- A specified comparison baseline and full-system condition, with study metadata requirements and a proposed survey and interview plan. Implementation of the baseline is required before recruitment, not to present the final study plan.
- A working submitted system and a 15-minute presentation covering rationale, changes, demo and study design. Study results are not required.

### Proposed enhancements

A user-priority ranking, a Most recommended for you banner and richer side-by-side merchant offers are proposed design improvements. The meeting did not confirm the banner as mandatory. The minimum build must still explain fit and tradeoffs; a banner should be added only when its ranking rule and evidence are defensible. Real-time activity streaming is preferred if feasible; a truthful completed activity record with a clearly labelled advance search plan is the smaller fallback.

### Exclusions

Real payments, automatic purchasing, shipping, agent-to-agent commerce, general scam or phishing detection, website-security infrastructure, large-scale live crawling, production authentication and additional product categories are outside the final-build critical path. A retailer allowlist can illustrate familiarity but must not imply that every marketplace seller is trustworthy. Small merchants must not be rejected solely because they are unfamiliar.

## 3 Existing foundation and capability map

The integrated runtime is `backend/app/main.py` and `backend/app/runtime/`; older top-level backend modules are retained exercises. The active frontend uses `frontend/src/lib/beany.ts`, not the older `contracts.ts` and `api.ts` contracts. Current storage is SQLite snapshots under a single-worker mutation lock. The current stack is FastAPI, Pydantic, Python, Next.js, React and TypeScript.

| Module | Current foundation | Change responsibility | Depends on |
| --- | --- | --- | --- |
| purchase-intent | Fact extraction and editable Brief | Readiness, correction, priorities and tradeoff confirmation | None |
| source-evidence | Product, Merchant and synthetic records | Exact product identity, evidence references and visible review data | None |
| offer-evaluation | Search ranking and merchant risk rules | Match reasons, comparable prices and scoped alternatives | purchase-intent, source-evidence |
| shopping-activity | Tool and policy audit events | Safe activity projection and optional live progress | offer-evaluation |
| study-conditions | Research endpoints, profiles and CSV | Baseline, full-system condition, assignments and task outcomes | purchase-intent, source-evidence, offer-evaluation, shopping-activity |
| final-demonstration | Current UI and documentation | Curated tasks, recording and presentation narrative | purchase-intent, offer-evaluation, shopping-activity |

Build order for the final demo: repair existing controls; establish intent and evidence contracts; integrate evaluation and activity; freeze scenarios and presentation. Implement study conditions before participant recruitment. Modules describe responsibilities, not a requirement to create six services or packages.

## 4 Purchase intent requirements

### PI01 Clarify only decision-changing ambiguity

For headphones, ask about intended use and a spending range when these are missing and affect recommendations. Once those are known, ask about a decisive preference only if it would distinguish suitable options. Ask one question at a time; explain its purpose briefly. Accept I do not know, Any is fine and Show options as legitimate answers, recording an explicit flexible state rather than looping.

Replace the current unconditional category-plus-budget shortcut with a deterministic readiness decision that considers unresolved required fields and the user's explicit request to browse. Specific inputs such as Wireless noise-cancelling headphones for commuting, under SGD300, comfort first should search directly. If the user declines a budget, show prices for comparison and avoid claiming they are affordable.

Acceptance: a fresh bare headphones request asks a relevant question before calling search. A fully specified request searches without redundant questioning. A skipped question is not converted into a confirmed preference. Existing confirmed limits survive follow-up questions and corrections.

### PI02 Make the brief reliable and editable

Retain confirmed, suggested and unspecified provenance. Add an explicit flexibility or declined marker where needed rather than overloading unspecified. Store purchase priorities as an ordered list of preference identifiers; a hard flag records eligibility, while priority records relative importance among preferences. Currency must be visible; bare $ may suggest SGD but must not be represented as an explicit currency confirmation.

Fix the field selector so value and hard state change together. A saved edit increments the brief revision, supersedes pending recommendations and clearly marks the need to compare again. Reuse the existing quote-based extraction guard, while acknowledging that a matching quote does not prove correct interpretation.

Acceptance: changing from a hard budget to a soft feature preserves each field's own setting. Changing a preference cannot leave an old result labelled current. The user can correct or remove a stored value and see the updated brief after refresh. For simplicity, brief edits need not occur while a comparison request is running, but must become available again after completion or cancellation.

### PI03 Negotiate tradeoffs explicitly

When no item satisfies all hard constraints, show the conflict and ask which constraint the user wants to revise. Never relax it automatically. When several eligible products satisfy different soft preferences, show the tradeoff and ask which matters most. A hard constraint and an important preference must not be treated as the same concept.

Use the selected product categories in examples: These headphones prioritise noise cancellation but the other pair is lighter. Which matters more for your commute? Avoid adding laptop support merely to reproduce the meeting anecdote.

Acceptance: impossible budgets produce a no-match explanation; options above that limit are clearly labelled exploratory and cannot become eligible until the user changes the limit. Priority changes alter the fit explanation and, if enabled, ranking. Unknown or unstructured requirements remain visibly unverified.

### PI04 Close the understanding loop

Before the recommendation, render a concise deterministic recap: You wanted headphones for commuting, up to SGD300, prioritising comfort. Suggested values must be identified as assumptions. Show which criteria the proposal meets and which it does not. Generated prose may improve readability but must not supply facts absent from structured results.

Acceptance: manual edits immediately affect the next recap; missing criteria are not described as satisfied; users can navigate from the recap to edit the brief.

## 5 Source evidence and offer evaluation requirements

### SE01 Separate product identity from merchant offers

Add `product_group_id` and `variant_key` to each offer. Existing IDs remain offer identifiers. Product model, configuration, condition and included accessories determine comparability; do not group by brand alone. Migrate existing fixtures and replay mappings deliberately, retaining compatibility defaults for old saved sessions or requiring an explicit fresh session.

A same-product merchant change filters by both new keys. If no eligible seller remains, say so and offer a separately named Find a different product action. Display at least two comparable offers in the selected demo case.

Acceptance: changing merchants preserves the product variant and current brief. Comparisons never mix different models, currencies or conditions. A fresh proposal is required after any material offer change.

### SE02 Show observable information before conclusions

Extend the active frontend types with product rating, rating count and reviews, plus merchant reviews and checkout note. Each result should show price and currency, seller name, product rating and count, and seller rating and count. Keep product satisfaction distinct from seller reputation. Expandable details contain specifications, review excerpts, returns, merchant contact and source evidence.

Each signal has an origin: simulated catalogue record, replayed snapshot or live snapshot. Fictional `.test` merchant websites are displayed as fixture identifiers, not opened as working stores. Live sources retain captured time and actual source links. Badge copy must say what was checked, such as Listed in the demo retailer registry; it must not imply independent certification.

Acceptance: the user can locate the evidence for every displayed warning. Missing ratings display Unknown rather than zero. Review excerpts and specifications already present in the backend are visible in the full interface and raw baseline details. Unfamiliar merchants remain selectable when there is no policy violation.

### OE01 Explain merchant risk with traceable evidence

Preserve the existing deterministic rules and separation of researcher labels from participant data. For simulated rules, connect each signal to authored visible text or structured source fields. Move diagnostic annotation booleans out of planner and participant projections. Do not describe fixture flags as evidence of automated discovery on arbitrary websites.

Use three layers: observation, implication and limitation. Example: Seller record lists 12 reviews; this offers less reputation evidence than 2,000 reviews; review quantity alone does not establish trustworthiness. A suspicious signal is not proof of fraud, and no configured signal is not a safety guarantee. Do not invent a third-party certification, SSL check or external reputation check.

Acceptance: benign discounts and clean unfamiliar merchants remain in the task pool. Hidden malicious labels never appear in participant APIs, UI or model payloads. Concealed-risk fixtures demonstrate an observability limit; they must not be used to claim that users should have detected information unavailable to them.

### OE02 Use a defensible price reference

Compute a median only from other offers with the same product group, variant and currency. Return reference count, merchant identities, included offer IDs, median and percentage difference. Deduplicate duplicated offers and exclude incompatible bundles or conditions. If the reference set is insufficient, show Insufficient comparable prices. Do not silently compare against an entire brand.

For the demonstration, freeze a reference set containing at least two other independent sellers. Example: SGD210 versus a median of SGD300 across two comparable offers; 30 percent lower. A low price alone should prompt inspection, not establish fraud or force a high-risk classification.

### OE03 Keep fit and merchant caution distinct

Compute deterministic match reasons and mismatch reasons for eligible products. Use hard constraints for eligibility, confirmed preference priorities for fit, and price as a disclosed tie-breaker. Keep merchant caution visible as a separate dimension. A cheap risky merchant must not become an unexplained best recommendation.

If the optional banner is implemented, select it with a documented rule: exclude blocked offers, prefer offers with fewer observed merchant concerns, then compare fit and price. State the scope, such as Best fit among these six offers, and disclose the caution tradeoff. The planner's selected offer and banner must agree. No percentage match score should appear without a defined calculation.

Acceptance: identical inputs produce stable fit reasons in catalogue mode; hard-budget violations cannot be top eligible recommendations; priority changes are reflected; the banner never implies that all websites or all products were checked.

## 6 Visible shopping activity

Call this feature Shopping activity or What Beany checked. It is an explanation of observable actions, not a model's private chain of thought. Never ask the model to invent a narrative of checks or expose raw interpretations, hidden prompts, credentials or researcher annotations.

Before results, show the planned checks as planned: matching the confirmed brief, inspecting selected offers, reviewing available seller evidence and comparing prices. When checks finish, replace these with event-backed statements using separate counts: Found six eligible offers, Inspected three offers, Assessed one proposed merchant. Show Not checked, Unavailable or Failed when appropriate. A catalogue search must not be described as visiting multiple websites.

For the smaller implementation, retain the synchronous endpoint, show a clearly labelled plan while pending, then render the completed activity record above the recommendation from the returned safe events. It must not animate fabricated completions. This satisfies truthful process disclosure but does not provide live progress.

For live progress, add a run ID and an additive run endpoint returning an accepted run, plus a read-only status or event endpoint. Emit safe events into a per-run thread-safe buffer while the existing worker performs the search; event reads must not acquire the long-running session mutation lock. Persist the authoritative session only on successful completion. Bound event retention and include sequence numbers for reconnection. Keep brief edits disabled during the run unless revision-aware cancellation and stale-result rejection are implemented. A disconnected viewer must never duplicate a run or create a proposal twice.

Acceptance: results appear after their relevant activity explanation; every completed claim has a tool or rule event; search, inspection and assessment counts differ when appropriate; provider errors remain visible; refreshing shows completed activity; no raw diagnostic JSON is shown to participants. Choose the synchronous fallback before adding a job queue or replacing storage solely for the demonstration.

## 7 Data and API changes

Extend existing Pydantic models and mirror the active TypeScript contracts. Proposed additions are contracts to implement, not current fields.

| Contract | Required fields or behaviour |
| --- | --- |
| Purchase brief | Existing facts, explicit flexible status, ordered priorities and revision |
| Offer identity | Existing offer ID, product group, variant, source mode and evidence references |
| Recommendation explanation | Brief revision, matched criteria, unmet criteria, ranking basis and comparison scope |
| Evidence item | Stable ID, offer or merchant ID, field path, source text or value, source kind and capture time when applicable |
| Price comparison | Reference offer IDs, reference count, currency, median and percentage difference |
| Activity item | Run ID, sequence, action, status, time, actual count and safe evidence references |
| Study assignment | Shared pseudonymous study participant ID, session ID, condition, task, order and frozen versions |
| Task outcome | Task start and finish, selected offer, criteria assessment, confidence response and completion status |

Condition and source versions are server assigned. Expose only the presentation condition needed by the UI; retain hidden labels and diagnostic fields behind research authentication. Add an allowlisted participant response model rather than relying on CSS to hide scores and annotations in the baseline.

Keep the existing chat, brief and proposal routes for compatibility. Add explicit study start, task completion and choice-recording contracts, with the exact route names fixed during implementation. If the live activity option is selected, use separate run and event routes; do not pretend the current chat response streams. Validate all identifiers server-side, reject stale brief revisions and preserve current approval and fingerprint checks on simulated checkout paths.

## 8 Mock catalogue and demonstration tasks

Reuse the existing 81 offers, 23 merchant records and 62 study offers. Restrict each task to a frozen subset through existing scenario product IDs and merchant IDs. Without curation, numerous deliberately discounted variants of one target can crowd the recommendation limit and make the task artificial.

Use headphones and running shoes as the recommended two categories because they already have fixtures; backpacks can remain supported without appearing in the final demo. Each task should include five to seven plausible choices, at least two merchants for the same target product, one unfamiliar but clean small merchant, one concrete suspicious cue and one benign discount. Keep review counts, ratings, policies and specifications internally consistent. Validate scenario restrictions before recording.

Recommended high-stakes task revision: create a headphones subset with a stated SGD350 ceiling and comparable target offers around SGD260 to SGD320. Add a cheaper suspicious offer with visible, inspectable evidence. These are proposed fictional values and require fixture updates; existing target prices must not be described as already above SGD200. If time is limited, retain current prices and narrow the evaluation claim instead.

Do not rebuild an Amazon sampling pipeline or depend on live browsing for the final demonstration. Synthetic product and merchant evidence is sufficient. Freeze catalogue version, scenario IDs, prompt version, ranking and risk configuration, and selected model. Clearly distinguish a mock product database from mock conversation mode: realistic study dialogue can use the configured LLM with fictional products; offline regex responses are a test double.

## 9 User study design

### Research questions

RQ1: Does the full system improve users' ability to verify and correct the system's understanding of their purchase needs?

RQ2: Does the full system improve users' understanding of source evidence and their ability to identify observable merchant concerns without unnecessarily rejecting unfamiliar or discounted sellers?

RQ3: How does the full system affect decision confidence, perceived control, effort and calibrated reliance compared with a conventional comparison interface?

### Conditions and causal claim

Condition A is a comparison interface with ordinary filters, product cards and expandable raw specifications, review information and merchant terms. It has no conversational intent clarification, extracted brief, agent fit explanation, activity narrative or synthesised risk labels. Users interpret the evidence themselves.

Condition B is the full Beany experience: purchase intent clarification, editable brief, tradeoff handling, evidence signals, merchant cautions, activity and recommendation rationale. Include the banner only if it is implemented and frozen before the study.

Both conditions use the same task instructions, source records, available offers, hard restrictions and selection endpoint. Raw information is accessible in both. The intervention is assistance in interpreting and organising that information. Keep final choice separate from simulated checkout so a backend block does not reveal the intended answer before measuring a participant's decision. No real payment occurs in either condition.

This is one manipulated factor with two levels: interface package A or B. Intent clarification and risk communication are components of that package. Surveys and interviews can probe them separately, but the study cannot identify their independent causal effects without a factorial or ablation design. Do not claim otherwise.

### Proposed procedure

Use a within-participant design with two matched category tasks. As a feasible course plan, propose 16 to 24 adult participants with some online-shopping experience, allocated evenly across four sequences: A headphones then B shoes; B headphones then A shoes; A shoes then B headphones; B shoes then A headphones. This is a feasibility target, not a powered sample-size claim. Professor review precedes recruitment.

Obtain consent, explain fictional listings and model processing, assign a shared pseudonymous participant ID, and provide the first task. Allow independent exploration and clarification. Record the participant's final choice and its reason, then collect the post-task survey. Repeat for the other condition and category, followed by a short comparative interview and debrief. Use fresh sessions linked to the same study participant. Do not reveal hidden merchant labels during tasks.

### Measures and rationale

| Method | Measure | Why it is needed |
| --- | --- | --- |
| Task outcomes | Hard-constraint compliance; fit with stated priorities; recognition of visible concerns | Tests decision quality beyond subjective trust |
| Interaction logs | Task duration, corrections, clarification turns, evidence opens, merchant changes and final choice | Shows actual use, effort and recovery behaviour |
| Post-task survey | Understanding, control, confidence, effort and trust calibration on consistent response scales | Supports paired quantitative comparison of experience |
| Semi-structured interview | Why a signal mattered, whether the brief felt accurate, tradeoffs and unmet needs | Explains mechanisms and failures that ratings cannot reveal |

Example probes: Could you tell what the system believed you wanted? Which source evidence changed your choice? Did you reject a small store because of missing information or a concrete concern? What would you need before spending your own money? Exact questionnaire wording can remain in the protocol rather than the presentation slides.

Predefine scoring from task criteria and participant-accessible evidence. Concealed malicious merchants with no distinguishing visible evidence cannot count as avoidable user errors. Keep synthetic detector accuracy in a separate diagnostic report. Do not label more rejection or higher trust as success by itself.

### Analysis and limitations

Predefine primary outcomes as purchase-intent comprehension and correct interpretation of observable merchant evidence. Report paired differences with uncertainty intervals and descriptive distributions; choose a paired test appropriate to the scale and sample before collection. Account for category and order in interpretation. Code interviews for brief accuracy, evidence usefulness, overload, negotiation and reliance, with a second coder checking a subset when feasible.

The convenience sample, small study, synthetic sources, category differences, novelty and bundled treatment limit generalisation. Counterbalancing reduces order effects but cannot eliminate learning. The study does not establish real-world fraud detection or purchasing behaviour. The final presentation reports the proposed method and rationale; it must not invent results. Pilot and red-team activities belong to Assignment 2 and should not appear as final-presentation sections.

## 10 Implementation changes and verification

P0 means required for feedback alignment before final recording. P1 means useful after the required path works. Study means required before participant recruitment, while its design must be documented for the final presentation. The table is a proposed delivery order; it does not claim implementation is complete.

| Order | Priority | Change and files | Acceptance and verification |
| --- | --- | --- | --- |
| 1 | P0 | Repair brief state in `frontend/src/components/Brief.tsx` | Switch between hard and soft fields without changing either unintentionally; add a focused UI regression |
| 2 | P0 | Purchase intent readiness in `schemas.py`, `service.py`, `llm.py`, dialogue prompt and elicitation config | Bare headphones clarifies; specific requests search; skip and correction paths preserve facts; backend workflow tests |
| 3 | P0 | Review and evidence contracts in runtime schemas, `frontend/src/lib/beany.ts`, `MerchantDetails.tsx`, product UI | Product and seller data remain distinct and inspectable; missing values shown; typecheck and browser checks |
| 4 | P0 | Offer group and variant data in catalogue, replay fixture, schemas and merchant alternative path | Same-product alternatives preserve variant; low-price reference contains correct offers; fixture and risk tests |
| 5 | P0 | Priorities, tradeoff state and result recap in runtime policy and brief/result UI | No silent relaxation; mismatches and priority changes explained; tests for no-match and conflicting preferences |
| 6 | P0 | Safe completed activity projection in workflow, service and main page | Actual actions and counts render above result; no fake completed work or private traces; workflow and UI tests |
| 7 | P1 | Live activity option in run routes and dedicated UI | Pending events are observable without waiting for the mutation lock; replay/reconnect has no duplicate actions |
| 8 | Study | A/B assignment and baseline view in research runtime, endpoints, participant UI and exports | Same raw offers available; baseline omits assistance at response boundary; paired IDs, task outcomes and condition persist |
| 9 | P0 | Curate two scenarios and update `docs/evaluation-guide.md`, README and architecture | Dataset and versions frozen; two complete flows; payment exclusion and current behaviour consistent |
| 10 | P1 | Recommendation banner and richer merchant comparison | Ranking rule is documented and deterministic; selected proposal and banner agree; caution remains visible |
| 11 | P0 | Final recording and presentation materials | Working system submitted; 15-minute story covers goals, changes, demo and study design without results |

Use existing naming and module boundaries: snake_case Python, Pydantic validation, typed React props and ordinary JSON fixture records. Extend focused helpers rather than introducing another agent framework. A representative existing style is `Fact(value=change.value, source=change.source, hard=change.hard)`; new priority and evidence fields should receive equivalent explicit types rather than unstructured dictionaries crossing API boundaries.

Run from `backend`: `.venv/bin/python -m pytest -q -p no:cacheprovider`. Run from `frontend`: `npm run typecheck`, `npm run build` and `npm run test:e2e`. Development commands are `.venv/bin/python -m uvicorn app.main:app --reload --port 8000` from `backend`, and `npm run dev` from `frontend`. Preserve test isolation from local credentials; explicitly pin catalogue search, blank live-search credentials and replay settings in browser-test servers before broader tests.

Backend tests cover readiness, grounding, revisions, priorities, exact-product comparisons, safe response projections and condition-aware exports. Browser tests cover editing, disclosure, baseline versus full treatment, keyboard access, mobile layout and progress failure states. Use frozen synthetic fixtures for reproducibility. Live-model evaluation is separately reviewed and must never run implicitly in the offline suite.

Always preserve hard limits, hidden-label isolation, explicit final approval, deterministic fallback facts and test isolation. Never commit keys or participant data, weaken checks to make demonstrations pass, invent completed checks or claim real-world certification. Escalate genuine product-scope decisions such as real payment, live-source dependency or extra categories before implementation. Existing research and local-study deployment limits remain in force; production hardening is not a prerequisite for this course prototype.

## 11 Demonstration and presentation

Recommended allocation totals 15 minutes: rationale and two pillars, 2 minutes; changes since the mid-project version and why, 2 minutes; system demo, 5 minutes; study design and rationale, 4 minutes; limits and close, 2 minutes. Validate the historical mid-project claims against the actual deck before presenting them; repository state alone does not establish what was shown then.

Headphones flow: start ambiguously, answer one useful clarification, inspect and correct the brief, see the actual shopping activity, compare two sellers for the same product, inspect a caution and select the better-supported offer. The result recap must reflect the correction. End at a user decision; if shown, checkout is visibly simulated.

Running-shoes flow: state conflicting preferences, inspect the fit tradeoff, choose a priority, revise the brief and compare again. Keep a clean small merchant and a benign discount visible so the system does not imply that only large retailers are acceptable.

A recording can present these complete working flows. It must show actual application behaviour; edited or fabricated interactions are not a substitute for the submitted system. Record only after the scenario data and build are frozen. Provide run instructions, required environment placeholders and the chosen source mode with the submission.

## 12 Completion criteria and decision register

The required final build is complete when both demo tasks run from a fresh session; intent can be clarified and corrected; each result recaps the current brief; users can inspect product, seller and price evidence; risk statements point to observable information; activity matches actual work; and alternatives preserve product identity. The final presentation includes the complete study design without claiming results. Simulated checkout must remain explicitly user controlled with no real payment.

Before recruitment, also implement the baseline and full-system conditions with controlled data, and anonymous task exports containing condition, versions and paired participant identity. This second readiness gate does not expand the presentation's plan-only requirement.

Decisions to settle before implementation: adopt the proposed two categories or retain backpacks as the second task; choose the above-SGD200 fixture revision or narrow the evaluated population; choose completed activity or live progress; decide whether the optional banner fits the remaining time; confirm recruitment feasibility and professor review. Recommended defaults are headphones plus running shoes, an above-SGD200 headphones subset, truthful completed activity first, banner after core acceptance, and a 16 to 24 participant counterbalanced proposal. These are recommendations, not meeting agreements.

## 13 Evidence and traceability

The accompanying `2026-10-27-codebase-review.md` records findings F01 to F10 and verification results. PI01 to PI04 address F01, F02 and F07; source and offer requirements address F05, F06 and F08; activity addresses F03; study conditions address F04; data curation addresses F09; scope and presentation documentation address F10.

The supplied meeting feedback is the requirements source for the narrowed scope, two pillars, mock-data acceptance, A/B evaluation and presentation constraints. The asserted Polymarket transaction statistic and attributed Zuckerberg remark are not needed to justify this specification. They should be omitted from presentation evidence unless the team obtains the original sources, wording, date and context. Do not present a prediction-market probability as an observed transaction share.
