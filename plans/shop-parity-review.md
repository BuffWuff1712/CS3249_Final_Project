# Independent shopping-UI parity review

## Initial inventory

The classic root page and related pages were inspected against the backend facade and redesigned workspace. The work must preserve these participant-visible capabilities before root-page replacement:

| Capability | Initial gap |
| --- | --- |
| Configured catalogue / Browser Use / replay | New session and client validation forced catalogue; live previews looked up local merchants only |
| Living brief | All fields present, but new editor forced hard budget and lacked the classic hard/soft control |
| Explicit authority | New UI lacked permission controls: approval, substitution, data sharing, payments, restricted merchants and autonomy |
| Task control | Explicit Cancel and fingerprint-bound Reject/Refine needed; chat interpretation alone is insufficient for authority controls |
| Cart | Classic supported multiple saved offers, per-item brief snapshots, removal, review and explicit batch checkout; new UI supported one ephemeral selection only |
| Receipts | Current session receipt shown, but previous-session history used old storage keys and was not linked from new UI |
| Live evidence | Source URL/time, captured seller/contact/policy/payment/privacy/AI-directed details and source links missing from new evidence component |
| Local evidence | Verification indicator, merchant review aggregate counts, requested information, checkout note and action payment/data-sharing details missing |
| Research | Research tools and hidden labels must stay separate; participant UI must never reveal ground truth |
| Replacement | Root and old navigation can only be retired after the above are implemented and tested; saved sessions/receipts require deliberate compatibility handling |

## Review protocol

Use only mock model responses, catalogue data or offline saved Browser Use replay with blank provider keys. Test provider configuration, preview purity, revisions, permission invalidation, exact fingerprints, blocked offers, cart snapshots and receipts. Do not claim real Browser Use or model quality was verified. Review implementation and browser evidence again after changes. No completion claim at this inventory stage.

## Independent backend checks (implementation in progress)

Added `backend/tests/test_shop_parity.py` with independent adversarial cases. First ten passed in 108.19 seconds under concurrent CPU load. This included the real saved Browser Use replay adapter through the new facade and simulated cart checkout, with the paid `run_task` function replaced by a failing sentinel. No live API was called.

Findings reported and corrected so far:

- Unsupported `carted` proposal status would fail response validation; use supported `superseded` on original proposal while retaining pending cart snapshot.
- Adopted research sessions initially blocked authorized researcher mutations; researcher-only mutation path now keeps auth, preserves private metadata and advances workspace revision.
- Cart and settings initially resolved the active browser session differently from the workspace; consistency fix is required and under review.
- Single-offer checkout instructions initially pointed persistent-cart users at a missing Finish control; control descriptions and checkout response now distinguish the two paths.

A further classic-cart adoption regression was added after finding a saved classic cart offer could be reclassified as an ephemeral selection. Final pass and signoff remain pending implementation, browser checks and final source review.

## Second adversarial round

All **12 independent backend parity tests passed in 7.27 seconds** after the implementation fixes, using fresh imports and offline environment pins. Earlier passing ten-test run predates the last two regressions; the 12-case pass includes them.

Further findings resolved:

- First adoption now supersedes an already-carted classic proposal, preventing an original saved cart item from being reclassified as an ephemeral selection and deleted on a later needs edit.
- Blocked/stale current offers disable Select/Add only; Reject, Change needs and general alternatives remain available subject to backend validation.
- Active-session resolution is consistent across workspace, settings and cart; research-created sessions clear the older workspace pointer. Settings forms remount with revision after reload.
- Soft budgets display as Target, while hard budgets retain Up to.
- Completed single-offer choices no longer appear as different-model alternatives.

Reviewed catalogue performance change: merchant registry is read once per `policy.catalogue` invocation, with no global cache. Later requests still read fresh merchant data. GET previews and cart validation remain policy-authoritative and model-call-free.

Independent source acceptance for `/shop` parity is complete with no remaining actionable finding at this stage. Final root-page replacement, stable frontend/full backend/build runs and current browser evidence still need verification before whole-task signoff.

## Replacement and browser regression migration

The stable `/shop` parity gate passed **36 browser cases** before the classic root implementation was removed. Root `/` and compatibility `/shop` now render the same `ShoppingWorkspace`; the unused classic `Brief` component was removed. Permission/cart/history pages remain as shared backend-connected feature pages, not a second shopping engine.

Independent review of the final source additions found no further actionable issues: composer restores Enter-to-send and Shift+Enter/IME safeguards, activity is derived from actual backend events/stage, and Browser Use alternatives are labelled as other listings with uncertain model/variant identity.

Migrated the seven classic-root shopping scenarios and three merchant reputation rendering scenarios to the replacement UI. Coverage retains hard/soft needs, simulated approval/receipt persistence, vague-request correction/cancellation, research hard block and CSV, keyboard/error recovery, public-versus-research evidence, and risky merchant replacement. Added blocked-offer Reject/Refine/Alternative checks and Enter/Shift+Enter behaviour. Reputation display tests use an explicitly patched saved-cart response; they do not claim source validation.

Full regression and final screenshot/build results remain pending; do not interpret this source review as the final completion signoff.

## Final verification evidence reviewed

- Full backend regression: **632 passed, 4 skipped**, one existing Starlette/httpx deprecation warning, 59.90 seconds.
- Full frontend regression: **177 passed, one 30-second cart-journey deadline, two skipped replay cases**. The affected cart journey had reached two receipts; cold development-page compilation consumed the aggregate deadline. Its timeout alone was increased to 60 seconds, and the desktop/mobile rerun passed **2/2 in 24.2 seconds**. The deadline adjustment changed test configuration only; production code was unchanged.
- Migrated shopping and merchant-reputation scenarios passed on desktop and mobile, including blocked rejection, keyboard submission, retained draft/error recovery and research evidence isolation.
- Viewed persistent `home-desktop.png`, `home-evidence.png` and `home-320px.png`: new navigation and controls are present, currency is explicit, evidence wraps safely, blocked offers remain distinct and disabled, and the small-screen page has no horizontal overflow. Long vertical seller detail is visible and scrollable.
- TypeScript check passed.

The user subsequently narrowed testing to local fictional catalogue products. Separate Browser Use replay **browser** testing was removed from scope and its new browser spec was removed. Existing backend provider compatibility remains covered offline; no live Browser Use or real model-quality verification is claimed. The final build/checklist/QA handoff still needs confirmation before final signoff.

## Final signoff

Independent review is complete. No unresolved actionable implementation or UI regression remains within the user's local-catalogue scope.

Confirmed final production build success and clean TypeScript output. Confirmed the preview home page returns HTTP 200 and the isolated backend health reports mock mode. Confirmed private `.env`, preview build artifacts and the E2E SQLite database remain ignored by Git. `git diff --check` passes.

Every implementation and verification checklist item is supported by code, the 12 independent tests, full backend results, applicable frontend checks, the affected cart rerun, or inspected current screenshots. Remaining final verification/review/running-preview boxes can be checked based on this evidence. The old and new home pages have been replaced by one participant workspace; existing supporting feature pages use that workspace's backend session. No real SoCLaaS quality or live Browser Use validation is claimed.
