# One shopping UI, full backend parity

Goal: replace the classic participant page only after the redesigned workspace exposes the existing backend capabilities. Preserve core backend policy, researcher routes and local fixtures. No paid provider calls during testing.

## 1. Backend parity
- [x] Honour the same configured catalogue/Browser Use provider and saved replay mode at session creation.
- [x] Restore/adopt saved classic sessions without losing brief, cart, receipts or permissions.
- [x] Add revision-checked permissions, cancel, reject/refine, general alternative and persistent multi-item cart controls.
- [x] Preserve ephemeral Select/Finish safeguards and separate persistent cart snapshots.
- [x] Support previews from either provider without model/network calls and without mixing catalogue products into live sessions.
- [x] Independently test provider, migration, stale state, permissions and atomic cart rules.

## 2. Redesigned frontend parity
- [x] Wire settings, cart, checkout and cross-session receipts to the active redesigned workspace.
- [x] Add explicit cancel, reject/refine, general alternative and Add to cart controls.
- [x] Preserve full hard/soft brief editing and display all saved needs.
- [x] Show complete local merchant and captured web evidence, source links, timestamps, payment/data-sharing and accurate provider/replay labels.
- [x] Preserve errors, drafts, request ordering, refresh and accessibility.

## 3. Replace and verify
- [x] Test all three local categories, permissions, reject/cancel/alternative, cart across searches, checkout, historical receipts and saved classic sessions.
- [x] Confirm local catalogue mode and no Browser Use calls. Existing provider compatibility is retained, with offline backend coverage only; skip the separate replay browser run per user preference.
- [x] Remove classic participant implementation; make / the new workspace and retain /shop compatibility.
- [x] Migrate obsolete UI assertions to equivalent new-interface tests; keep backend compatibility regression coverage.
- [x] Run backend/frontend tests, TypeScript, build, browser screenshots and desktop/mobile checks.
- [x] Independent adversarial review of final code, checklist and evidence; resolve actionable findings.
- [x] Leave local mock-mode app running and record results in plans/.

Do not commit or push this work without a further instruction. Prior uncommitted work is preserved.

Backend-section review: 12 independent offline parity cases passed (7.27s), including saved replay, study-session adoption, persistent cart, policy gates and atomic checkout. Source audit found no unresolved backend issue. Frontend completion remains gated on stable browser verification.

Frontend parity gate: 36 desktop/mobile local-backend journey cases passed before replacing the home page. Removed the classic page implementation and its unused Brief component; both / and /shop now render the single workspace. Full replacement coverage is recorded in shop-feature-parity-qa.md: 177 passes in the full run and the final 2-case cart rerun passed; TypeScript, build and independent final review passed.

Subsequent live-model check: user supplied a SoCLaaS key privately. Active preview now uses the configured real model with local catalogue and rules risk mode (Browser Use disabled). See `soclass-local-live-check.md` for the bounded real-model journey; the earlier offline result remains separate. Offline parity goal completed in approximately 27 minutes.
