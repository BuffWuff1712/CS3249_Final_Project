# Compact shopping summaries and comparisons

Implemented 30 October 2026, building on the agreed decision-panel layout review.

- [x] Replace the long current-offer description with listed features, key specifications, returns and separate product/seller review facts.
- [x] Keep material review concerns, website reputation, merchant assessment and approval requirements visible; retain full source text under evidence controls.
- [x] Compare products in a two-product table, with an alternative picker and explicit unknown values.
- [x] Compare sellers of the same model in a separate table, including the current offer, complete return terms, website reputation, merchant risk and blocked/approval status.
- [x] Keep blocked-offer selection disabled, source details expandable, and existing selection, cart and simulated checkout controls intact.
- [x] Render assistant bullet lists and bold labels safely as React text; preserve saved answers and keep simple greetings conversational.
- [x] Update recommendation/evidence prompts to request concise points and a relevant next step without dropping material concerns.
- [x] Verify desktop and 320px layouts, source expansion, unsafe markup handling and simulated checkout.
- [x] Run regression tests, TypeScript and production build.

## Verification

- Backend: 635 passed, 4 skipped. Existing Starlette/httpx deprecation warning only.
- Affected frontend suite: 38 passed across desktop/mobile (backend workspace, parity, streamed progress and initial compact-view cases).
- Final compact-view suite after adding visible list markers and the noise-control row: 6 passed across desktop/mobile.
- TypeScript and production build passed.
- Browser assertions cover blocked Compare controls, current seller identification, full return terms, review concern, distinct product/seller ratings, HTML treated as text, no horizontal page overflow and simulated receipt completion.
- Desktop and mobile screenshots were inspected. On mobile the comparison becomes labelled stacked rows; long source details stay behind disclosures. The decision column remains scrollable on desktop.
- All automated runs used the local catalogue and mock model/rules configuration. No paid model or Browser Use calls were made for this verification. Live model compliance with the revised wording prompt was not tested.
- No API schemas, catalogue fixtures, policy rules, cart or approval logic changed. Existing assistant answers are reformatted without changing their words; new model answers are instructed to use concise bullet points.

## Screenshots

Saved under `plans/verification/compact-shopping/`:

- `compact-comparison-desktop.png` and `compact-comparison-mobile.png`: default catalogue comparison, blocked seller evidence expanded.
- `lumen-summary-tables-desktop.png` and `lumen-summary-tables-mobile.png`: Lumen summary with its supplied review concern and return terms.
- `lumen-model-comparison-desktop.png` and `lumen-model-comparison-mobile.png`: product-table view.

The earlier layout review and its before screenshots are retained in `plans/decision-panel-layout-review.md` and `plans/verification/decision-panel-review/`.

## Follow-up: comparison interactions and empty page space

Checkpoint before application changes: `4573c99` (`test: cover product picker and seller comparison interactions`). The earlier full UI implementation remains at `13b84ae`.

- [x] Exercise one enabled seller-table Compare action: same Lumen model, new seller, previous selection cleared.
- [x] Change the alternative picker and click product Compare: table follows picker and recommendation changes to the chosen model.
- [x] Explain blocked offers inline using the actual backend BLOCK rules. Replace technical policy label with “Unavailable under your shopping rules”; render privacy field names in plain language.
- [x] Reproduce and fix desktop blank space. At 1470×735, document height previously reached 1492px while the app frame was 735px. Absolutely positioned accessibility labels lacked containing blocks inside the scroll panels. Positioning those panels relatively retains the labels inside the intended scroll area; final document-height assertion passes at <=736px.
- [x] Verify the changed interaction and layout cases on desktop/mobile: 4 passed. Existing selection, checkout, follow-up, needs edit, seller preference, rejection, cancellation, cart and permissions cases had passed in the prior regression batch; they were not unnecessarily rerun.

Screenshots: `plans/verification/comparison-interactions/desktop.png` and `mobile.png`. Checks use local mock catalogue/model, with no paid provider requests. UI fixes are included in the follow-up commit with conversational Compare actions.

## Conversational Compare actions

- [x] Show the clicked product and seller immediately as a user message; persist that message on the backend so refresh keeps it once.
- [x] Keep real streamed checks visible for at least 900ms before revealing an instant local result. Slow operations receive no extra delay after that window. No invented process steps or extra search/API calls.
- [x] Keep selection disabled during presentation; preserve the composer draft; cancel the presentation timer on reset/unmount through the existing abort signal and generation guard.
- [x] Verify the Compare conversation on desktop: 1 passed in the final focused run. Screenshot review of the initial run caught scrolling to an older completed step; the selector now targets only the current live progress, and the repeated check asserts that both the user message and real steps are in the viewport. The test clicked a real eligible same-model seller, saw its user message and real checks while the old assistant count remained unchanged, then saw the new answer; it also verified draft preservation, selection disabling and a single persisted user message after refresh.

Screenshot: `plans/verification/comparison-interactions/compare-progress.png`. This test used the mock model and local catalogue, with no paid APIs.
