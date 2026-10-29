# CUI v2 delivery and verification

29 October 2026 · scenario `beany-cui-v3.0` · work continues on `feat/cui-v2-issues`

## Delivered behaviour

UI clarity follow-up: the purchase input now leads the page, with editable examples. The intent summary labels Buying, For, Spending limit and Most important; the default explanation labels intent, model choice, seller choice and trade-off. Every blocked offer encountered in the current seller comparison is shown in a red, explicitly scoped flag with its seller/price, evidence, consequence and recommended next action. The flag can explicitly select the current eligible alternative through the existing selection checks. Incomplete information and trade-offs remain amber. See the [full change inventory and pre-merge checklist](cui-v2-change-list.md).

The `/shop` journey now supports both headphones and running shoes with the same typed comparison and session transitions. A detailed request goes directly to a concise personalised recommendation; a vague request asks bounded questions and accepts browsing with visible assumptions. The ordinary completion path selects and finishes an offer without opening sources, changing permissions or invoking checkout.

Corrections update needs, selection and explanation atomically. The change explanation distinguishes a new priority, changed budget and explicit product request. A deliberately constrained SGD260 headphone task keeps Luma Air after switching to comfort and explains why. Only affected expanded trace steps are marked Updated. Editing leaves the old result labelled Previous and unselectable; a new current selection is required.

Seller changes preserve the exact product/variant. A failed seller change never silently chooses another model on retry; changing products is explicit. Outside-checkout gift-card demands are explained through the visible record, their consequence and a named selectable alternative. Clean small sellers and ordinary discounts remain viable. Unknown evidence remains unknown, with unavailable activity rather than fabricated verification.

Selection rechecks revision, offer ID and price. Refresh validates stored needs and seller intent, recomputes the result and restores only a matching current selection. Old scenario versions and invalid browser records cannot restore selection. Storage failure has a visible explanation. USD requests require an explicit SGD decision; no exchange conversion is implied. Unsupported requests clarify rather than map to another category.

## Acceptance map

| GitHub work | Implementation / evidence |
| --- | --- |
| #9 Expanded reasoning | Five needs/eligibility/product/seller/choice steps; source focus links, priority/budget/use-case/seller-preference editors, targeted Updated markers |
| #10 Honest activity | Labelled local plan, actual product/offer counts and completed/unavailable states; no timers, streaming claims or website visits |
| #11 Consequential correction | Changed and unchanged winners; concise causal update; stale offer/selection invalidation |
| #12 Tradeoffs and budget | Focused conflict question, exact ceiling enforcement, SGD180 no-match, explicit revision/recovery |
| #13 Seller identity | Product IDs represent fixed variants; seller-only comparison lock survives retry and refresh |
| #14 Merchant concerns | Visible gift-card cue, concrete consequence, clean ordinary-checkout alternative; price/history alone do not block |
| #15 Recovery | Missing return/review/payment evidence, comparison error result/retry, unsupported input and currency clarification; preserved needs/message |
| #16 Selection | Primary Select this offer, decision recap and Finish decision; no backend mutation, credentials or order |
| #17 Second category | Two fixed EU42/blue/new running-shoe models and six offers using the same components/state machine |
| #18 Mobile and keyboard | Desktop and Pixel 7 projects, extra 320px width, keyboard submission/disclosure/evidence focus/selection, overflow and page-error assertions |
| #19 Study plan | Fair full-package comparison, four counterbalanced sequences, proposed 16–24 participants, measures/scoring, confidence and comprehension, limits and data handling |
| #20 Final-demo preparation | Runnable build, frozen fixture version, reproducible demo script, 15-minute presentation outline, actual silent browser recordings and screenshots |

The actual narrated course recording, team rehearsal, checking historical claims against the original mid-project deck, and professor feedback remain team activities. The prepared silent test recordings verify the real interaction; they are not a completed narrated submission. Future study implementation #21–24 remains outside the final-demo gate and must precede participant recruitment.

## Verification

Commands use the repository's existing pytest, TypeScript, Next.js and Playwright tooling; no new runtime or testing dependency was added. Offline tests pin mock/catalogue mode and blank paid-service credentials.

- Backend regression: 430 passed, 5 existing skips, one upstream Starlette/httpx deprecation warning.
- Frontend typecheck and production build: pass.
- UI clarity follow-up production verification: `BEANY_E2E=1 npm run build` passed all ten pages using the existing isolated `.next-e2e` directory. A normal-output build hit a root-page prerender/build-manifest error while an existing Next.js server was active on port 3000 in this project. The isolated build avoids sharing its output; no checks were disabled and application code does not branch on this flag.
- Full Playwright suite: 90 passed across desktop Chromium and Pixel 7 projects (including the 320px keyboard/layout check and pure decision/state tests).
- Budget mutation: temporarily reversed the eligibility ceiling; the budget regression failed as expected. Restored the original source before the final suite. This confirms the test detects a genuinely broken guard.
- Runtime visual checks: actual screenshots of explanation/evidence and shoe selection on desktop and at 320px; browser tests assert no page errors and no horizontal overflow in those paths.
- Final screenshots: [headphone recommendation](verification/cui-v2/headphones-desktop.png), [consequential correction](verification/cui-v2/headphones-correction.png), [merchant concern](verification/cui-v2/merchant-caution.png), [shoe selection at 320px](verification/cui-v2/shoes-320px.png). Silent desktop/mobile WebM recordings are generated by `cui-recording.spec.ts` and retained in ignored test output; they are verification artifacts, not a narrated course submission.
- UI clarity checks: labelled intent and reasoning, computed red flag colour, exact risky offer/price, alternative selection and budget-editor recovery. Inspect the [red risk flag](verification/cui-v2/red-risk-flag-desktop.png) and [mobile purchase intent](verification/cui-v2/purchase-intent-mobile.png).
- The classic settings test was scoped to its application error because Next's route announcer is also an alert. The message, absence of Save permissions and enabled return action remain asserted; no checks were skipped or weakened.

## Review and boundaries

Reviewed the comparison/state changes for correctness, readability, architecture, security and performance. Key controls are shared input validation, local fixture-only comparisons, source-derived cautions, explicit revisions, recomputation at selection/restore, bounded persisted strings, and React's ordinary text rendering. Comparison and session modules remain small and synchronous; no general agent framework, new global store or live-service dependency was introduced.

Automated checks establish deterministic consistency and working browser interactions. They do not establish human comprehension, real-world merchant detection, fit, authenticity or security certification. The product is explicitly fictional and local. `/shop` has no participant analytics, GUI baseline or linked study assignments. The classic FastAPI, research, cart and receipt guards retain their independent behaviour.

## Files to start with

- `frontend/src/lib/shoppingFixtures.ts`: frozen scenario facts and version.
- `frontend/src/lib/shoppingScenario.ts`: budget eligibility, product/seller comparison, cautions and activity.
- `frontend/src/lib/shoppingSession.ts`: atomic transitions, invalidation and storage validation.
- `frontend/src/components/shopping/ShoppingWorkspace.tsx`: interface composition.
- `frontend/tests/decision.spec.ts`, `shopping-session.spec.ts`, `cui-journey.spec.ts`, `cui-recording.spec.ts`: focused logic, state, full journeys and recording.
- `docs/evaluation-guide.md`: proposed study and scoring.
- `docs/final-demo.md`: run instructions, demo script and timed presentation outline.
