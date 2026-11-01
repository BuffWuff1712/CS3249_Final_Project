# Shopping readability improvements

Goal: resolve all annotated readability issues without changing shopping decisions, policy rules or source data.

- [x] Add evidence-supported feature-match highlights and clearer battery presentation.
- [x] Add fractional stars with exact values, separate product/seller counts and unknown states.
- [x] Use consistent labelled, accessible risk and website-reputation badges.
- [x] Highlight unique concerns; remove duplicated risk explanations while retaining distinct restrictions and uncertainty.
- [x] Improve seller-table prices, status labels, concise actions and blocked reasons.
- [x] Visually verify the same Lion City summary, expanded risk evidence and seller table in the browser.
- [x] Check a narrow/mobile layout and relevant interactions without paid APIs.
- [x] Run relevant frontend checks and record results/screenshots; mark only verified work complete.

Before evidence: plans/readability-browser-audit.md and plans/verification/readability-browser-audit/.

## Results

- 18 relevant desktop/mobile cases passed in the final combined run: readability, compact comparison, clarification and progress flows.
- 2 additional desktop/mobile cases passed for replacing a risky merchant while retaining the brief.
- Production build and TypeScript passed. No backend or catalogue changes; no paid APIs or real purchases.
- Direct in-app browser inspection at desktop 1280x900 and mobile 320x900 verified feature chips, fractional stars, distinct website/risk/approval badges, one highlighted inconsistency concern, unbroken prices, short Compare/Current offer/Blocked labels and accessible source controls.
- Manually edited priorities to add wireless, recomputed the recommendation and returned to Lion City; both supported match chips appear.
- The mobile comparison heading was made full width after visual review. Mobile comparison actions now scroll the current user message/progress into view; the related regression passes.
- Test setup was adjusted for the newly pulled clarification requirements: existing generic requests explicitly state no feature preference. The backend itself was not loosened.

## Evidence

Before: `plans/verification/readability-browser-audit/`.
After: `plans/verification/readability-improvements/`:

1. `01-summary-desktop.png`: two matched feature chips, battery emphasis, exact fractional product/seller stars and coloured labelled assessments.
2. `02-risk-desktop.png`: one concern card with one uncertainty note; permission status remains separate.
3. `03-sellers-desktop.png`: full prices, compact badges and concise action labels.
4. `04-summary-mobile.png`: readable summary at 320px (captured before adding the second saved priority).
5. `05-sellers-mobile.png`: stacked mobile seller cards, full-width heading and expanded evidence.
6. `06-blocked-seller-desktop.png`: blocked offer retains its specific instruction-injection reason and disabled Compare control.

Source limits remain explicit: a listed battery duration is not automatically a confirmed fit for commuting; unknown ratings/assessments stay unknown; the generic inconsistency signal does not identify particular conflicting fields. The UI does not invent them.

Code changes are local and uncommitted. The local preview is running with mock conversation, local catalogue and an isolated audit database.
