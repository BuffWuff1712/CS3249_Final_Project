# Independent UI/UX and deployment readiness review

Reviewed commit `4e9aef2` on 29 October 2026. Read-only review: no implementation changes, no paid APIs, no real purchases.

## Verdict

The desktop design is a coherent, credible **interaction prototype**: editable needs, a stable chat frame, compact progress, a distinct current offer/alternative, and explicit risk/evidence language work together well. It is not yet ready for an unmoderated public release. The independent probes found real intent mistakes, and the fresh browser audit found two important layout/flow weaknesses. Passing the existing regression suite is not sufficient to establish release readiness.

| Target | Verdict |
| --- | --- |
| Controlled class/team demonstration of fictional shopping | Suitable with the supported inputs and an explicit prototype introduction; fix the priority findings before calling it robust |
| Public self-service demo | Fix the intent errors, result-pane scrolling, narrow-screen composer and deployment entry/navigation first |
| Production shopping assistant with LLM/live search | Not ready: `/shop` is still deterministic fictional data, and the live backend/security/operational path is outside this UI's verified contract |

## Method and limits

Independently inspected the current source, session parsing/persistence, presentation reducer, evidence controls, route/API configuration and relevant tests. Ran fresh source-level reducer probes using the repository's TypeScript compiler, without changing tracked files. Inspected the primary audit's fresh saved screenshots `00` through `09` under `plans/verification/deployment-audit/`; these were captured during this review, not inherited QA artifacts. Browser geometry values below came from the primary audit's current browser run; the intent probe outputs were independently reproduced in this review.

No real-device soft keyboard, screen reader, Safari/Firefox, authentication/penetration, production host, live model or live shopping test was completed. This is not a complete accessibility or security certification.

## Ranked findings

| Rank | Severity | Finding and evidence | Required change |
| --- | --- | --- | --- |
| 1 | P1 | **Negated budget instructions change the hard spending limit.** Starting with headphones/SGD300, `I do not want to increase my budget to SGD500` sets budget to500 and clears selection. `I do not want to remove my budget` removes it. Independent reducer probes reproduced both; the primary browser reproduced the first in [05-negated-budget](verification/deployment-audit/05-negated-budget.jpg). Amount extraction and budget removal ignore negation: `frontend/src/lib/purchaseIntent.ts:36`–44 and73. | Preserve the existing amount when a change is denied or ambiguous; ask for confirmation/clarification rather than treating any mentioned amount or removal phrase as a command. Add adversarial tests for negated increase, decrease, removal and quoted/example amounts. |
| 2 | P1 | **Seller preference can be reversed by a natural correction.** `I don't want the cheapest seller; longer returns matter more` sets `sellerPreference=lowest price`, changes Northline Audio to Everyday Sound and clears selection. `sellerPreferenceFrom` returns the first positive keyword match regardless of negation or the explicit later priority: `frontend/src/lib/purchaseIntent.ts:10`–12. | Parse negated versus affirmed seller preferences, or ask which preference to apply when the input is mixed. Test the actual selected merchant and return period, not just response text. |
| 3 | P2 | **The current recommendation stays above the visible decision pane after a new comparison.** Selection scrolls the decision pane to the selected-offer section. A subsequent comparison preserves that scroll offset; at1280×800 the primary audit measured scrollTop382 and current recommendation top about-173. [05](verification/deployment-audit/05-negated-budget.jpg) shows only the alternative/excluded offer on the right after the update. `frontend/src/components/shopping/ShoppingWorkspace.tsx:61`–63 scrolls selection into view, but the persistent decision section at104 has no new-result scroll reset. | When a new comparison completes, bring its current-match heading into the decision viewport, without stealing focus from the composer. Preserve normal manual scrolling for read-only answers. Add select→correct→new-result geometry regression. |
| 4 | P2 | **Initial narrow-screen input requires extra page scrolling.** At320×800, Send was at y857.5–901.5 and the composer began at y764.5. [06-mobile-start](verification/deployment-audit/06-mobile-start.jpg) shows the input starting below a tall needs/jump-link area. The page is scrollable, so the controls are reachable; this is a usability weakness, not an inaccessible-control claim. The min420px conversation in `frontend/src/components/shopping/shopping.css:270` combines with the stacked needs and page scrolling. [07-mobile-result](verification/deployment-audit/07-mobile-result.jpg) shows the long stacked outcome. | Reduce/collapse the needs overview on narrow screens and keep the composer readily reachable. Validate with a real soft keyboard and a short viewport; verify page and inner-chat scrolling do not compete. |
| 5 | P2 | **Clarification and change explanations are repeated.** [02-clarification](verification/deployment-audit/02-clarification.jpg) repeats the same question in an assistant bubble and the blue choice panel. [05](verification/deployment-audit/05-negated-budget.jpg) repeats the unchanged-winner explanation in a bubble and a second blue block. Rendering at `frontend/src/components/shopping/ShoppingWorkspace.tsx:91`,98–99 creates the duplication. | Attach response choices directly beneath the assistant question, and show a correction explanation once. Keep any separate status short rather than copying the complete answer. |
| 6 | P2 | **Historical evidence links disappear after another answer.** Links render only for `message.id === latestReply?.id` and resolve only against the current decision (`ShoppingWorkspace.tsx:65`–66,92). The new activity snapshots remain in older turns, but their original evidence controls vanish after a follow-up; a category change can make old sources unavailable altogether. | Keep each comparison's inspectable evidence associated with its history entry, or explicitly label historical records and provide a bounded historical-source view. Do not route an old claim to a newer decision's source by accident. |

P1 findings violate the user's stated intent inside a fictional demo; no real charge/order occurred. Existing explicit selection and blocked-offer guards are still valuable, but do not excuse an incorrectly raised interpreted budget.

## Deployment gates separate from visual polish

1. **Choose a public entry route.** `/shop` is frontend-only, but `/` boots the classic backend and the visible Classic simulation link navigates there (`ShoppingWorkspace.tsx:69`, `frontend/src/app/page.tsx:39`–55). Its API defaults to the visitor's `http://localhost:8000` (`frontend/src/lib/beany.ts:122`). A frontend-only deployment must point visitors at `/shop` and handle the classic link/root, or configure/deploy the backend and CORS. An ordinary frontend build alone does not prove the visible whole-site navigation works publicly.
2. **Do not expose a paid-provider classic backend without abuse controls.** Session creation and message endpoints in `backend/app/main.py:101`–124 have no authentication dependency; the app setup at26–32 adds CORS but no request quotas/rate limiting. The research endpoints have a separate key guard, which does not protect ordinary chat. If that backend is public with paid credentials, add appropriate access, cost and rate limits. This is a conditional gate for the backend-connected product, not a requirement for the self-contained fictional `/shop` demo.
3. **Validate the real deployment.** Check production start, HTTPS/domain, public entry/navigation, refresh/storage behaviour and error reporting on the target host. No host has been assessed in this review. Client-only local storage is not account-level history or a cross-device product.
4. **Keep the product claim accurate.** The staged two-second checks are local presentation pacing. Production live search must report actual provider progress/failures rather than inheriting this timed sequence as proof of real work. Current fictional disclosures should remain until integration is real.

## Strengths supported by current evidence

- [01-start](verification/deployment-audit/01-start.jpg), [03-progress](verification/deployment-audit/03-progress.jpg) and [04-recommendation](verification/deployment-audit/04-recommendation.jpg) show a consistent desktop frame and readable hierarchy. The compact scale is an improvement over a disappearing hero and large repeated checklist.
- Current match, alternative, price, seller and the selection control are visually distinct. Red blocked-offer treatment has explanatory text, not colour alone.
- [08-completion](verification/deployment-audit/08-completion.jpg) confirms a shoe selection can reach a clearly labelled simulated completion. [09-evidence-followup](verification/deployment-audit/09-evidence-followup.jpg) shows a follow-up answer that distinguishes one supplied excerpt from312 aggregate reviews and avoids a fit guarantee. The primary browser audit reported no console warnings/errors in these flows.
- Factual local-record language, unknown evidence and subjective comfort/fit caveats avoid implying verified real-world safety.
- The pure state and source review show explicit selection revalidation, immediate invalidation when needs change, bounded history validation, old-tick rejection and reset/unmount cleanup. Read-only questions keep selection and needs unchanged.
- Native buttons/details, labels, live status and reduced-motion overrides provide a useful accessibility baseline. Their presence does not prove full assistive-technology usability.

## Secondary polish and compatibility notes

- Enter inside the textarea inserts a newline; tests demonstrate Tab→Enter on Send, not a conventional Enter-to-send/Shift+Enter-to-newline chat pattern (`PurchaseComposer.tsx:13`–16). Decide and document the intended keyboard convention.
- Older saved sessions remain valid, but lack the new optional comparison snapshots. [00-restored-legacy](verification/deployment-audit/00-restored-legacy.jpg) shows no inline checks or comparison narrative until a fresh comparison records them. This is a known compatibility limitation, not data loss; make the upgrade behaviour clear or offer a fresh-comparison action.
- At320px, some needs text is deliberately truncated. Full accessible edit labels are present, but visual recognition and readability still need real-user testing.
- Source-level validation rejects unrecognized stored evidence IDs. It does not turn browser-local historical text into independently trusted server evidence; retain that boundary for future live integration.

## Recommended order

1. Fix and test negated/ambiguous budget and seller-preference interpretation.
2. Correct the new-result decision-pane scroll and reduce duplicated prompts/answers.
3. Improve narrow-screen composer access and test actual mobile keyboard behaviour.
4. Retain historical evidence access; define public entry/hosting and scope the classic backend separately.
5. Recheck the full critical journeys on the production host and run a small usability session with people who did not build the app.

No source fixes were made as part of this review. The release verdict should remain conditional until the actionable findings are fixed and the affected journeys are rerun.
