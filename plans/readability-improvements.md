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

Readability changes were committed locally as `7e2380a`. The local preview is running with mock conversation, local catalogue and an isolated audit database.

## Follow-up: duplicate cancellation control

Removed the bottom idle Cancel shopping task control, retaining the suggested Cancel this task action and Stop during active requests. Updated affected cancellation selectors. The existing reject/alternative/cancellation journey passed on desktop and mobile (2 cases). This follow-up is included in the subsequent UI-polish commit.

## Follow-up: budget match highlights

Added price/budget to the same match area, including offers with no feature preferences. Confirmed hard limits and preferred targets use distinct wording. Equal-to-limit offers count as within budget; above-budget and different-currency offers receive explanatory text rather than a positive match chip. Missing, invalid or unconfirmed budgets do not produce a match. The needs strip's existing SGD currency default is explicitly labelled “currency assumed” unless currency is confirmed.

Regression: 6 desktop/mobile readability cases passed, including nine budget presentation states (within, equal, preferred, above, currency mismatch, assumed currency, suggested budget, invalid and missing), alongside existing rating/evidence/selection checks. These UI edge states use controlled saved-brief fixtures; backend policy was not changed.

## Follow-up: compact assessment presentation

Added consistent list/battery/scales icons, grouped assessment badges above one About these checks info box, and removed the payment/data-sharing summary line at the user’s request. Policy decisions, source details and restrictions remain unchanged. TypeScript and whitespace checks passed before commit.

## Follow-up: concerns visible by default

Product review concerns remain separate from seller/listing concerns. Unique seller/listing evidence now appears directly below the assessment badges, without opening a dropdown. Additional shopping checks appear under More assessment details only when present; full product/seller sources remain available in the existing source disclosure. Six desktop/mobile readability cases and TypeScript passed, including a check that the inconsistency concern is visible once without opening details. This follow-up is included in the subsequent visible-concerns commit.
