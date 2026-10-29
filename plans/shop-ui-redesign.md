# Collaborative shopping UI

Goal: implement selected mockup 1 in `/shop`, preserve shopping safeguards, add evidence-based follow-ups, and verify visual fidelity and functionality through browser testing and independent review.

Work in this fresh checkout only. No paid APIs, real purchases, backend changes, fixture changes, or classic interface redesign. Tick items only with evidence. Reports and guidance live under `plans/`.

## Implementation

- [x] Save exact mockup 1: `verification/shop-ui/mockup-1.png` (first displayed image selected by user).
- [x] Install researched frontend-design and web-design-guidelines skills. Official upstream skills installed in `~/.codex/skills/`; skill installer returned success for both.
- [x] Build compact editable needs and two-column conversation/decision workspace.
- [x] Match reference typography, spacing, colours, icons, and hierarchy.
- [x] Preserve conversation history, clarification, and correction explanations.
- [x] Show factual comparison activity, evidence, and unknowns.
- [x] Distinguish current recommendation, alternative model, and excluded sellers.
- [x] Make seller-preference controls update and explain comparison.
- [x] Answer evidence questions about choice, alternatives, reviews, sellers, returns, and concerns.
- [x] Keep questions read-only and clarify ambiguous mixed requests.
- [x] Preserve budgets, exact-product seller changes, stale-selection and blocked-offer rules.
- [x] Preserve compatible saved sessions and validated refresh behaviour.
- [x] Implement mobile, keyboard, visible focus, and evidence navigation.
- [x] Keep all new task guidance and reports under `plans/`.

## Verification

- [x] Browser comparison with reference at matched normalized dimensions and recommendation state.
- [x] Inspect typography, layout, warnings, controls, and evidence presentation.
- [x] Exercise both categories through clarification, correction, seller change, selection, completion.
- [x] Exercise questions, conflicting priorities, budgets, unknowns, and unsupported requests.
- [x] Verify edits clear selection, blocked offers cannot be selected, and refresh is safe.
- [x] Desktop, mobile, 320px, keyboard, overflow, and console checks.
- [x] TypeScript, production build, full existing frontend tests, and meaningful new regressions.
- [x] Fix discovered issues and repeat affected checks; save `plans/design-qa.md`.

## Completion gate

- [x] Independent adversarial subagent audits implementation, checklist, screenshots, and tests.
- [x] Fix findings, rerun affected verification, and obtain clean re-review.
- [x] Leave local preview running and provide before/after evidence and test results.
- [x] Mark Codex goal complete only after all applicable checks pass.

## Evidence log

- Baseline: fresh `main` commit `c46edf4`; only pre-existing change is generated `frontend/next-env.d.ts` from development startup.
- Reference contains no product photography. Keep existing wordmark and use library icons; correct unsupported delivery/total-cost wording rather than copying invented claims.

- First regression pass: 138 frontend tests passed across desktop/mobile. TypeScript passed. New conversation source/state tests are included; additional collaboration browser tests are being verified.
- Visual iteration: first settled desktop capture showed wrapped needs and excess repetition. Compact strip and reduced repetition implemented; matched viewport captures retained for re-comparison.

- Second full acceptance pass: **166 passed** across desktop/mobile (`/tmp/beany-ui-acceptance-tests.log`), including legacy UI, source/readonly question, fixed-product, cap-scrolling and storage regressions.
- Browser evidence and equal-size comparison are indexed in `plans/design-qa.md`. Direct browser demonstrated both categories, review/return follow-ups without selection mutation, source focus, completion, and390/320px reflow with no console errors.
- Independent review found four issues, then one repeated-preference edge. Fixes and repeat regressions are present; final re-review, release tests and final build pending. Seller-preference/guard checkboxes remain pending until that last gate.

- Final stable-source release suite: **166 passed (1.4m)**; copied to `verification/shop-ui/frontend-tests.log`. Repeated seller preference tested in browser and pure regressions. Three independent adversarial probes passed; source re-review found no remaining actionable issue. Final production rebuild is running after the last helper fix.

- Final production rebuild passed after the repeated-criterion fix. `plans/design-qa.md` now records `final result: passed`; build/test logs and before/after captures are retained. Independent final source review is clean; final checklist audit requested before marking the goal complete. Local preview remains on http://localhost:3000/shop with matched headphones example.

- Final independent checklist audit: clean. Reviewer accounted for every implementation/verification item using source, screenshots,166 passing frontend tests, production build and3 independent probes. No missing scope items or unsupported completion claims. Codex goal marked complete after this review.
