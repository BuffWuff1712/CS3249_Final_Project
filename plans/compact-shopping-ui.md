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
