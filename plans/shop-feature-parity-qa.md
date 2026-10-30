# Replacement shopping UI: feature parity and QA

The participant home page and `/shop` now render the same `ShoppingWorkspace`. The old home-page implementation and unused `Brief` component have been removed. Existing cart, checkout, settings, receipts and researcher pages remain as supporting workflows, connected to the active workspace session. No commit or push was made for this task.

## Feature mapping

| Existing backend feature | New interface |
| --- | --- |
| Configured catalogue / Browser Use / saved replay | Session creation calls the same service configuration; accurate provider/replay disclosure |
| Conversation, clarification, correction, explanation | Existing backend chat workflow, with real request status and factual completion activity |
| All brief fields and hard/preferred constraints | Needs editor, full saved-needs disclosure and Target versus Up to budget labels |
| Merchant risk, website reputation and policy rules | Current and historical evidence, distinct risk/site/policy labels, BLOCK prevents selection/checkout |
| Captured web listing evidence | Shared merchant evidence displays source/capture time, seller, returns, warranty, shipping, payment/data concerns and source links |
| Explicit permissions | Settings retains all original permission controls; revision checks and selection invalidation |
| Reject, refine, alternative, cancel | Dedicated controls; blocked offers can still be rejected or refined |
| Multi-item cart | Add to cart preserves original brief per item; remove/review/atomic simulated checkout use the original backend cart operations |
| Single-offer selection | Select/Finish retained as an additional explicit path; temporary selection is separate from saved cart items |
| Receipt history | Saved session history retained across fresh sessions, including earlier classic sessions |
| Existing saved and study sessions | Explicit idempotent adoption preserves products, needs, permissions, cart, receipts and research metadata; hidden labels remain protected |
| Research configuration, triggers, observations and exports | Existing authorized routes remain functional after adoption and advance workspace revision |
| Shopping oversight and keyboard input | Actual backend stage/events disclosure; Enter sends, Shift+Enter adds newline, IME and repeated keys are guarded |

General alternative-merchant search uses the same shared service operation as the compatibility API. Exact-model seller controls remain more conservative for Browser Use: the adapter has no canonical cross-seller variant identity, so separate live URLs are labelled other listings instead of claiming identical/different models.

## Verification evidence

- Independent adversarial backend suite: 12 passed, including actual saved listing replay with paid run_task disabled, classic-cart adoption, researcher authorization/revisions, current permissions, stale state and atomic multi-item checkout.
- Full backend regression: 632 passed, 4 skipped, one existing Starlette/httpx deprecation warning, 59.90 seconds.
- Before replacing the old home page: 36 desktop/mobile local-data journeys passed. Full replacement regression is recorded below when complete. The separate replay browser run was cancelled at the user's request to keep the app and browser testing on local mock products.
- Manual browser: visited the new default home page on the isolated preview, restored existing history, started a fresh session, sent a local search with Enter and expanded product evidence. Persistent captures are under `plans/verification/shop-feature-parity/`.

Earlier development runs included selector failures and timing failures while source changes were being applied; those attempts were stopped and are not counted as passes. The final stable parity gate passed after fixes, deferred full-list rendering and request-local catalogue I/O reduction. No global catalogue cache was introduced; subsequent requests still read changed records.

## Limits and running preview

Testing uses local fictional products, mock LLM, rules risk mode and separate databases. Optional Browser Use compatibility has offline backend tests only; the app and browser tests stay on the catalogue, and the planned separate replay browser run was cancelled. Real SoCLaaS model behavior remains unverified. No paid calls, real orders or payments occurred. Existing backend provider and model settings remain available and were not overwritten in the private .env.

Local preview: http://localhost:3200/ (backend http://127.0.0.1:8200). `/shop` is a compatible address for the same interface. The isolated preview continues in mock/catalogue/rules mode.

## Final replacement test results

- Full frontend run: 177 passed, one desktop cart test reached its 30-second whole-journey deadline, two planned replay browser cases skipped. Its trace showed two receipts created and all steps succeeding until the final history assertion ran out of total time. No application assertion failed. Only this multi-page test received a 60-second total budget to include cold Next development compilation; individual assertion deadlines were unchanged.
- Final affected cart run: both desktop/mobile cases passed in 24.2 seconds. Combined with the full run, all 178 applicable frontend checks have passed; no claim is made that the first full run was entirely green.
- The separate replay browser spec and its configuration switch were removed at the user's request. Active browser tests always use local catalogue, mock LLM, rules risk mode and blank provider keys.
- Desktop screenshots and `home-320px.png` were inspected: navigation wraps, controls remain accessible, product/merchant evidence wraps, blocked offers remain disabled, and no horizontal clipping was visible. Chat retains its own scroll area. A long risk explanation is preserved from backend output; no recommendation quality claim is inferred from the mock model.

TypeScript and the Next production build passed after the final cart test/configuration changes. `git diff --check` passed. The isolated preview remains running on ports 3200/8200. User is adding a SoCLaaS key privately; actual-model testing is a separate next step and is not claimed by this offline completion.

Independent final review signed off with no actionable findings. The offline parity goal is complete. Subsequent user request: privately add SoCLaaS credentials and validate the real model with the same local catalogue; that live-model check is tracked separately in this folder and does not retroactively change the offline evidence.

Subsequent live-model check: user supplied a SoCLaaS key privately. Active preview now uses the configured real model with local catalogue and rules risk mode (Browser Use disabled). See `soclass-local-live-check.md` for the bounded real-model journey; the earlier offline result remains separate. Offline parity goal completed in approximately 27 minutes.
