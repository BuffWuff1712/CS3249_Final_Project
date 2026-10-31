> Historical integration stage. Provider/session restrictions described here are superseded by `shop-feature-parity.md`; retain these results as the earlier checkpoint.

# Local-backend shopping integration QA

Verified 30 October 2026 on local branch `feat/shop-backend-integration`, based on `b44bff7`. No commit or push made for this work.

## Results

| Check | Result |
| --- | --- |
| Full backend regression | 620 passed, 4 skipped; one existing Starlette/httpx deprecation warning |
| Independent adversarial backend tests | 27 passed, included in full run |
| Full frontend regression | 170 passed on desktop/mobile; affected 22-case integration suite passed again after final receipt-layout fix |
| TypeScript | Passed |
| Next production build | Passed, all 10 pages generated |
| Whitespace validation | `git diff --check` passed |
| Desktop / 320px evidence | Inspected by implementer and independent reviewer; no horizontal overflow or clipped evidence |

Logs and persistent screenshots: `plans/verification/shop-backend-integration/`.

## Browser evidence

- `evidence-desktop.png`: 1280x900 test viewport. Stable chat and decision columns; expanded factual product and seller evidence.
- `evidence-mobile.png`: 320x900 full-page capture. Wrapped needs, specification labels/values, review and return evidence, distinct seller/model sections and disabled blocked controls.
- `manual-desktop.png`: independent manual browser journey through a real local-backend request, same-model change from Outlet Plus to City Goods, expanded sources.
- `manual-receipt.png`: manual Select then Finish and refresh; receipt persisted through backend session restore.

The automated journeys cover all three backend categories, vague clarification, needs edits, impossible budgets, questions preserving selection, exact-model sellers, site good/mid/poor tiers, blocked policy decisions, historical evidence, explicit selection/finish, refresh, failed request recovery and delayed-reset races. Keyboard Enter expands evidence; layout tests detect page errors and horizontal overflow.

## Changes to existing tests

Six browser specs that assumed the old four-product frontend fixture engine moved to `frontend/legacy-tests/` as reference. They are not active integrated-UI coverage. New `shop-backend.spec.ts` exercises actual FastAPI endpoints instead. Useful pure tests for the old engine remain, and their passes are not claimed as backend-connected shopping validation. The classic-interface merchant assertion now matches the existing hostname display instead of expecting the full URL scheme.

## Independent findings resolved

Corrected stale checkout metadata, classic-route mutation bypass, fresh-session arbitrary proposal, brief mismatch, repeated catalogue reads, reset draft race, denied-budget interpretation, mismatched checkout wording, and multiple-answer activity ordering. New adversarial regressions cover these cases. Final manual checkout also found the completed product mislabeled as a different model after the active proposal cleared; model alternatives now require an active recommendation. All 22 affected browser cases passed again after this fix, and the receipt screenshot was recaptured. Two browser selector errors and two outdated classic URL assertions in an earlier run were fixed; the final 170-test run is clean.

## Scope and limits

All verification uses local catalogue, mock LLM and rules risk mode, separate test/preview databases, and blank provider keys. No paid API, Browser Use or real checkout ran. Real model interpretation/quality remains unverified. Fictional website reputation and merchant-risk signals are presented as uncertain evidence, not fraud findings. Existing catalogue contents and classic session rules remain unchanged; classic mutation routes intentionally reject dedicated shop sessions to prevent bypassing their revision/selection safeguards.

Preview stays available at http://localhost:3200/shop with the isolated backend at http://127.0.0.1:8200. The preview uses `.next-preview`; build and Playwright outputs are separate. Screenshots are current-state verification, not pixel matching to an unchanged fixture recommendation.
