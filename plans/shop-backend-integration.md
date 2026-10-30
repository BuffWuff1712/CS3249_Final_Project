> Historical integration stage. Provider/session restrictions described here are superseded by `shop-feature-parity.md`; retain these results as the earlier checkpoint.

# Connect /shop to the local-data backend

Goal: retain the collaborative shopping layout while making the existing backend authoritative for conversation, local products, risk, selection and simulated checkout. No live shopping or paid API calls during verification. Backend/model modes remain explicit; an offline test double is never presented as a real LLM.

## A. Backend contract and safeguards

- [x] Add a local-catalogue-only shopping session facade; do not reuse a classic live-search session.
- [x] Reuse backend conversation/shopping workflow, authoritative brief, proposals, policy and risk configuration.
- [x] Expose bounded policy previews for eligible local offers on copies, without model calls, mutating stored sessions or granting approval.
- [x] Distinguish model alternatives from sellers of the exact same model/variant using conservative product identity.
- [x] Provide explicit compare/propose/seller-preference operations; preserve all hard limits and show missing evidence as unknown.
- [x] Select through server cart validation and finish through explicit fingerprint-bound simulated checkout. Needs changes clear the workspace's selected item; read-only questions preserve it.
- [x] Record factual comparison activity from backend events; no fabricated timings or claimed review counts.
- [x] Keep classic routes, researcher-only labels, fixtures and existing policy decisions unchanged.
- [x] Independent review/test this section; resolve actionable findings.

## B. Frontend integration and details layout

- [x] Replace /shop's production use of fixture ranking, local intent parsing and timed presentation with backend session state.
- [x] Keep stable chat/needs/composer/decision layout; display the local catalogue and explicit backend mock/AI modes accurately.
- [x] Wire needs, suggestions, comparisons, same-model seller changes, selection and finish to the server.
- [x] Show server website reputation separately from overall risk and ALLOW/REVIEW/BLOCK. Include assessment basis and evidence without turning a poor site into an automatic block.
- [x] Present current offer, model alternatives, same-model offers and blocked offers distinctly using backend data.
- [x] Keep historical proposal evidence inspectable; prevent stale/out-of-order responses and stale selection after edits/reset.
- [x] Resume a dedicated server session on refresh, recover deleted sessions/errors, keep draft text on failures and never silently fall back to frontend fixtures.
- [x] Fix evidence-panel product headings, label/value spacing, review wrapping and responsive layout.
- [x] Independent review/test this section; resolve actionable findings.

## C. Verification and completion

- [x] Offline backend integration tests: local isolation, preview purity, website tiers, policy gates, stale fingerprints/terms, same-model switch, edits, reset, questions and checkout idempotency.
- [x] Replace obsolete fixture-specific /shop browser assertions with real-backend journeys covering equivalent safeguards; retain useful pure legacy tests as such.
- [x] Browser journeys for clarification, both original categories plus backend-supported backpack, preference changes, good/mid/poor websites, risk evidence, BLOCK, no matches, selection/finish and refresh.
- [x] Test unavailable backend, failed mutations, request/reset races, stale source evidence, keyboard and desktop/mobile/320px layout.
- [x] Run relevant backend/frontend regressions, TypeScript and production build. Keep all test providers offline.
- [x] Capture and inspect fresh screenshots; record QA under plans/.
- [x] Final adversarial subagent review of code, checklist and evidence; fix actionable issues and rerun affected checks.
- [x] Leave the local app running with local data and clearly labelled offline model mode; mark goal complete only after verified work is checked.

Implementation defaults: /shop uses a dedicated persisted backend session and local catalogue regardless of the classic provider setting. GET previews are deterministic, bounded and side-effect-free. Selecting an offer does not create a receipt; finishing is an explicit simulated checkout. Existing classic sessions and frontend-prototype saved data are not silently reinterpreted as new backend sessions. Validation will use a separate mock backend/database and blank provider keys; no paid real-model verification is claimed.

Section A evidence: independent backend facade suite passed 24 offline tests after fixes for candidate boundaries, classic-route bypass, current-brief validation, preview performance and checkout metadata. No actual model calls.

Final evidence: 620 backend tests passed (4 skipped), 170 frontend tests passed, TypeScript and production build passed. See `shop-backend-integration-qa.md`, persistent verification artifacts, and independent review report. Verification uses mock models only.
