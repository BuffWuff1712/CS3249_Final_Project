# Suggested reply review

Verified in the running browser on 1 November 2026. No implementation changes.

Environment: localhost:3200, local catalogue, mock conversation model, rules-based risk checks. This does not validate SoCLaaS response quality.

Each button was tested once from a fresh session using: "Find wireless noise-cancelling headphones under SGD200 for my commute."

Baseline: Lumen Hush ANC, Bargain Depot SG, SGD62.90.

| Button | Browser result | Assessment and proposed change |
| --- | --- | --- |
| Show me some options | Repeated Lumen Hush ANC at SGD62.90 and the same generic checkout instructions. | Does not meaningfully answer the request for options. Present a small shortlist with differences and link/open the relevant comparison. |
| Find an alternative | Changed to Campus Corner Clearance, same Lumen Hush ANC model, SGD70.90. Reply named only model and price, followed by generic checkout instructions. | Functional seller change, but ambiguous intent and weak explanation. Distinguish another seller from another model, and explain the changed seller, SGD8 price increase and relevant evidence. |
| Cancel this task | Replied "Cancelled. No pending proposal can be approved." Activity showed cancelled; no Select this offer button remained. Cancel this task was still visible. | Cancellation works, but suggested replies remain stale. Replace them with a clear next action such as Start a new search; use friendlier cancellation wording. |

Code confirms all three suggestions submit ordinary chat messages. The mock interpreter returns the same static suggestions every time. The service saves suggestions before handling cancellation and does not clear them. Alternative handling excludes the previous offer and merchant, so it can return the same model from another seller.

Browser console: no error entries returned after the checks.

Screenshots: `verification/suggestion-buttons/01-options.png`, `02-alternative.png`, `03-cancel.png`.

## Fixes and verification

- Show options now uses checked offers to list up to three distinct models with price, seller, listed features, return terms and approval status. It preserves needs, the current proposal and selection. Blocked offers are excluded.
- Find an alternative now proposes a different model, names the previous offer and price difference where currencies match, and reports the new features and policy results. It keeps needs and clears the previous selection for review. If no other selectable model exists, it keeps the current offer and explains the limitation.
- Cancellation now uses the existing explicit cancellation operation, clears suggestions and directs the user to Start fresh. Saved independent cart items remain available.
- Exact UI shortcuts are handled by the workspace using supplied facts in both mock and configured-model sessions; these actions do not require extra model calls. Other chat still uses the existing interpreter.
- Browser regression: `shop-suggestions.spec.ts`, desktop, three tests passed. Each suggestion clicked once from the same fresh headphone baseline, after selecting the offer. Verified user messages, unchanged brief, options preserving selection, alternative model identity/budget/policy, cancellation clearing proposal/selection/suggestions, and zero receipts.
- Backend workspace/parity regressions: 39 passed. Updated an outdated comparison-message assertion to include the existing user action message and verify activity attaches to the assistant reply.
- TypeScript check passed. Tests used local catalogue data and mock conversation; no paid API calls.
- Result screenshots: `verification/suggestion-buttons-fixed/options.png`, `alternative.png`, `cancel.png`.
