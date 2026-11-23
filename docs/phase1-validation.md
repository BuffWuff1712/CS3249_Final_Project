# Beany Phase 1: deterministic discovery and conversational exploration

## Implementation

| Files | Responsibility |
| --- | --- |
| `backend/app/runtime/schemas.py` | Backward-compatible interpretation control and persisted pending-search flag. |
| `backend/app/runtime/llm.py`, `backend/config/prompts/dialogue.txt` | Retain the conversational model; distinguish exploration, deferral and requested searches. Give the model the pending-search flag. |
| `backend/app/runtime/service.py`, `clarification.py` | Apply grounded preferences independently of searching; preserve uncertainty and hard constraints; validate task resets; do not promote completed clarification automatically. |
| `backend/app/runtime/shopping_workflow.py` | Deterministic orchestration, audit events and snapshot revalidation. No ShoppingStep model calls. |
| `backend/app/runtime/shopping_tools.py` | Retrieve the candidate pool, cheap ranking/filtering, exact deduplication, bounded single-product screening and final ranking. |
| `backend/config/policy.json` | Output target 3; screening budget 6 total, independently configurable. Workflow output cannot exceed 3. |
| `backend/app/runtime/shop_workspace.py`, `backend/app/main.py` | Keep comparisons and product changes inside the saved shortlist; preserve it when rechecking permissions or selecting an offer. |
| Backend tests and `frontend/tests/shop-phase1.spec.ts` | Conversation, shortlist, cache, approval, snapshot, progress and browser regression coverage. |

Flow: interpret -> validate and save changes -> discuss/clarify OR authorized search ->
existing providers -> structured eligibility filters -> cheap ranking and exact deduplication ->
single-product details/relevance/risk -> Python policy -> rank up to three eligible distinct
products -> verify unchanged snapshots -> propose primary -> explain -> explicit review/approval ->
simulated checkout. No new framework, database migration, batching or reasoning-setting changes.

An exploratory turn can now save, add or remove preferences without initiating search.
A grounded edit invalidates stale recommendations and pending approvals. `search_control=defer`
clears pending search; `request` records the user's request. The model still chooses the intent.
A `clarify` result never becomes `search` simply because fields are complete. Existing uncertainty
handling resumes only an already-requested search. Task resets require both grounded product-family
changes and a literal switch quote. This is an extra guard, not a guarantee that a model cannot
misinterpret a quoted statement. Cart snapshots, receipts and permissions survive a task reset.

Every normal workflow recommendation is screened. A rejected/mismatched candidate does not consume
an output slot; screening continues within budget. Exact deduplication retains decision-relevant
evidence; different sellers/variants can still be screened if the preferred one fails. After a
product model is accepted, identified variants do not fill the other slots. Unknown relevance
retains review requirements. Failed assessments are not proof of safety. Existing cache bindings
and deterministic policy/fingerprint checks remain authoritative.

## Validation

- Full backend suite: **1,000 passed, 4 skipped**, 49.54 seconds.
- After final offline-deferral and changed-snapshot additions: **43 focused tests passed**,
  including both added tests and conversation/hybrid/workflow regressions.
- Final legacy-endpoint/API/runtime/Phase 1 regression subset: **54 passed**, after preserving
  the screened shortlist when selecting through the legacy endpoint.
- Frontend TypeScript check: passed.
- Frontend production build: passed.
- Playwright: **12 passed**, desktop and mobile, 56.5 seconds. Covers clarification,
  uncertainty, streaming progress/Stop, at most two alternatives, selection without purchase,
  and explicit simulated checkout.
- No live Qwen, Shopify or Browser Use calls were made.
- Existing test warnings: Starlette/httpx deprecation and a non-writable pytest cache directory.
  No unresolved test failures in the checks above. Four existing optional tests remain skipped.

Old planner-injection tests were replaced by deterministic sequencing/no-planner tests. Tests that
expected all catalogue sellers (including blocked entries) in the UI now check the screened shortlist.
Specific checkout/seller safety tests seed explicitly screened fixtures rather than depending on
which merchant wins ranking. Dataset inventory tests still test inventory independently of UI limits.

## Performance evidence and limits

The prior user-supplied trace is a real 344.035-second run. The revised controlled fixture uses seven
distinct desk lamps with deterministic provider/model stubs. It exercises the production conversation,
screening, policy, proposal and explanation boundaries; it is **not an equivalent live latency benchmark**
and does not reproduce the original product snapshots. No saved provider recording of that exact run
was available for replay.

| Metric | Prior real trace | Revised offline fixture |
| --- | ---: | ---: |
| End-to-end time | 344.035 s | 0.033 s with stubs; not comparable to live latency |
| Model invocations | 15 | 8 logical stub calls; 0 network calls |
| ShoppingStep invocations | 3 | 0 |
| Eligible offers retrieved | 7 | 7 synthetic offers |
| Products screened | 5 | 3 |
| Relevance model calls | 5 | 3 |
| Risk model calls | 5 | 3 |
| Recommendations | 5 | 3 |
| Total LLM request time | 334.536 s | Not measured; no live LLM |
| Token usage | Available per call in the supplied trace | Unavailable for stubs |
| First-screen assessment cache | 5 relevance + 5 risk misses | 3 relevance + 3 risk misses |
| Repeat unchanged screening | Selected-product cache hits in trace | 0 additional assessment/review model calls |

The fixture asserts one Interpretation, three Assessment, three Review and one OutcomeExplanation.
The selected-product proposal reuses its cached review. Running screening again uses cached
product assessments. Reproduce with:

```powershell
cd backend
.venv/Scripts/python.exe -m pytest tests/test_phase1.py::test_live_shape_single_product_calls_and_cache -q -s
```

Eight is not a universal call count: rejected candidates, extraction repair or invalid caches can
increase calls. The screening budget limits inspected candidates, not total conversation calls.
No proportional live speedup is claimed. Capture the same request against live providers separately
when authorized; compare `timing_summary`, `shortlist.start/result`, LLM call/token diagnostics and
cache events. Parent/child timings overlap and must not be added together.

## Phase 2 opportunities

Batch relevance and risk inputs behind `screen_candidate`, while retaining per-product evidence,
validation, cache bindings and independent policy results. Measure tokens, model latency and
partial-failure behavior before selecting a batch size. Phase 1 still assesses sequentially; model
latency can remain substantial. Hybrid discovery still queries both configured providers once.
The shortlist is the best within the bounded screened set, not the global best across all inventory.
Trade-off ranking uses grounded feature matches and information completeness; cross-provider model
identity is not always known, so some near-duplicates can remain. Model browsing is limited to the
screened shortlist rather than exposing unscreened inventory. For catalogue products, seller browsing
also lists the other eligible sellers of each shortlisted model; live listings stay limited to the
screened shortlist.
