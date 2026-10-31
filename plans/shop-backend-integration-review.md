# Independent backend/UI integration review

Status: backend and frontend source review,170 browser regressions, fresh desktop/mobile screenshots and production build passed after corrections. Final whole-checklist audit passed.

## Method

Read the existing classic service, cart, policy, storage, LLM and site-risk contracts before the facade was written. Independently authored `backend/tests/test_shop_workspace.py` against the actual FastAPI `/shop/sessions` contract. Tests run with the repository's offline conftest: mock LLM, blank provider keys and temporary SQLite. A model-payload test replaces `structured_call` with a local capture function; it makes no model call. No implementation files were edited by this reviewer.

## Findings and rechecks

| Finding | Status and evidence |
| --- | --- |
| Preview repeatedly reparsed the catalogue/merchant registry per offer | Fixed by parent with request-local evaluation snapshots; no global stale cache. Original16-case run took96.29s. Corrected16-case run took10.81s. Cross-request product and merchant changes are explicitly tested. |
| Finished selection metadata retained an old proposal reference | Fixed by parent: `cart.checkout` replaces the session dictionary, so metadata must be looked up again after checkout before clearing selection. Regression passes. |
| A fresh workspace accepted a known catalogue product before any visible comparison | Fixed by parent with comparison/category preconditions. Regression passes. |
| Classic endpoint could change a shop session's hard budget without invalidating its selected cart snapshot | Fixed by parent. Classic mutation endpoints now reject shop-bound sessions; selected context is also checked against current brief and pending proposal. Independent tests verify brief/message/approve/cart-checkout isolation and rejection after unexpected stored brief changes. |
| Mock/fallback replies named Add to cart/Proceed to checkout rather than Select/Finish | Fixed by parent. Actual fallback responses and checkout-intent replies now use Select this offer / Finish decision. Independent assertions verify these labels and that chat checkout creates no receipt. |
| Explicit comparison/seller operations put factual answers before activity | Fixed by parent by merging each explicit comparison response before recording its message index. Independent API test checks compare, proposal and seller operations each append exactly one assistant answer and attach activity to its beginning. |
| A model could treat an amount inside a denied budget edit as grounded authorization | Fixed with a conservative shop-only clarification guard before interpreting denied budget/seller changes. Independently injected incorrect interpreter changes for an increase to SGD500 and budget removal; both preserve needs, cart and selection. This bounded guard is not claimed to solve unrestricted language understanding. |

Two initial failures were test-fixture corrections, not implementation defects: `audio-1` has valid alternative sellers, so a unique model is used for the no-seller case; changed-catalogue tests patch the cart module's imported alias as well as policy.catalogue.

## Covered acceptance boundaries

- Local catalogue is forced despite Browser Use environment settings; classic/live sessions cannot be restored as shop sessions.
- View/GET preview does not change persisted state, call the risk model, expose experiment metadata or mint approval fingerprints.
- Revision/fingerprint failures leave persisted state unchanged.
- Select saves selection only; Finish creates an exact receipt, repeated finishing does not duplicate it, and mismatched fingerprints fail.
- Read-only answers preserve needs/proposal/cart; edits and new comparisons clear selection while old receipts survive.
- External-payment/injection/sensitive-data offers are blocked and cannot be proposed through the facade.
- Seller changes preserve strict model identity and exclude knockoff variants; absence of an alternative leaves the current state unchanged.
- Website tiers and overall approval decisions are distinct; guided approval does not imply fraud.
- Completed history counts actual backend events and does not replay on read-only answers.
- AI GET previews use cached reviews or explicit rules fallback, without making a model request.
- Changed catalogue price or merchant terms are read again and prevent stale checkout.
- The real-model interpretation payload includes selected-offer context and correct /shop control labels without granting permissions.

## Verification result

`backend/.venv/bin/python -m pytest tests/test_shop_workspace.py -q --durations=5`: **27 passed in32.07s**. One existing Starlette/httpx deprecation warning remains. This rerun used fresh imports after the fixes; earlier failing invocations are not counted as passes. Source-level backend acceptance is complete, including the latest denied-edit and reply-order regressions.

## Frontend source review

A reset/draft race was found and fixed by the parent: fresh reset now clears the old draft at request start, preserving text typed while the response is pending. The delayed-create regression passed on desktop and mobile in the first full browser run.

Reviewed `ShoppingWorkspace`, `BackendNeedsSummary`, `BackendOffer`, `ComparisonActivity` and `shopBackend` against the facade contract. Generation/AbortController guards prevent late reset responses; mutation errors retain draft and pause actions until reload; only the server session ID is stored; transient restore failures do not silently create a new session. Current and historical proposals are distinct, old evidence has no selection action, and current/selected validation disables stale approval. Website reputation is separate from merchant risk/approval, assessment basis is explicit, and product/seller evidence admits missing or fictional sources. No further actionable frontend source issue was found after the draft and ordering fixes.

The first complete browser run produced **164 passes and four assertion failures**. Two restore-error failures were duplicate text locators (the visible alert and screen-reader status both reported the same error). Two classic evidence failures expected a full URL while the unchanged component intentionally displays the hostname. The corrected full rerun passed **170 tests in2.4m**, including both previously failing assertion cases, seller-change journeys and the newly added vague clarification case on desktop/mobile. Earlier failing attempts are not counted as passes. The seller-change journey passed for desktop and mobile. The vague clarification regression also passed in the corrected full run.

Full backend run evidence supplied by the parent: **617 passed, 4 skipped**, before the three newest adversarial cases. TypeScript check was clean, and the final production build completed successfully (Next15.5.27, all10 static pages generated). Browser and screenshot checks are complete. Latest full backend rerun passed **620 tests,4 skipped in70.50s** (one existing Starlette/httpx warning). The final checklist and QA report were reviewed against source, tests and screenshots. Running frontend3200/shop and backend8200/health each independently returnHTTP200. The final receipt-state correction passed its affected tests and visual recheck. No production/live-model usability or accuracy claim is made.

Visual spot check: independently viewed the fresh1280px desktop `backend-shop-evidence.png` emitted by the real-backend browser test. Header/needs strip remain compact, chat and decision occupy stable columns, the composer remains visible, and risk/approval/source language is explicit. Expanded source content continues in the scrollable right panel. Also independently viewed the fresh320px full-page mobile evidence capture: needs chips wrap2x2, chat/composer remain contained, specifications/returns/contact wrap safely, model/seller sections remain distinct and blocked controls remain disabled. No further actionable spacing or overflow defect was visible in either capture.

Persistent screenshots reviewed: `plans/verification/shop-backend-integration/evidence-desktop.png`, `evidence-mobile.png`, and `manual-desktop.png`. The manual capture shows an explicit City Goods offer with the older comparison retained and the current activity before its response. Code, offline regression and visual acceptance gates have no unresolved actionable finding. Final plan bookkeeping and running-preview confirmation remain with the parent.

Final receipt-state finding: after Finish, current proposal becomes null; the former purchased model was incorrectly presented under Other models as a Different model. Parent added a current-proposal guard to that section, plus a refreshed-receipt assertion. This is the correct boundary because model alternatives need a current comparison reference. The affected22-case browser rerun passed in1.1m, and the updated receipt capture was independently inspected: the receipt is retained and the false Other models section is absent. Final TypeScript and production build rerun both completed successfully after this last correction.

Checklist audit: every backend, frontend and verification item maps to implementation, offline tests and recorded screenshots. Dedicated preview URLs returnedHTTP200. No unimplemented checked item or remaining actionable source/UI issue was found. The manual screenshot captions describe implementer-driven checks; independent review was of the captures and API/source behavior.

## Final signoff

Independent review complete: no remaining actionable findings within scope. Backend620passed/4skipped, full frontend170passed, final affected22passed, independent adversarial27passed, TypeScript and production build succeeded. Checked all checklist items against code/evidence and verified the running isolated preview. Real paid-model behavior remains explicitly unverified; this acceptance covers local-data application integration and offline safeguards.
