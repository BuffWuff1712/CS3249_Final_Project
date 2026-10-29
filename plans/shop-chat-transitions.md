# Stable chat and staged comparisons

Checkpoint: `dce8dae` (`feat: add collaborative shopping workspace and evidence answers`) on local `main`. No push. The checkpoint excludes credentials, databases, dependencies, build output and private logs.

Goal: build on the checkpoint to provide a stable `/shop` chat layout and a two-second staged local comparison, preserving shopping safeguards and passing browser, functional and independent review.

## Implementation

- [x] Commit the reviewed existing redesign and verify excluded files.
- [x] Create Codex goal and this checklist.
- [x] Keep chat frame, needs strip, composer and decision-panel structure stable across empty/pending/result states.
- [x] Replace the hero welcome with an assistant greeting in the conversation.
- [x] Show user message immediately; withhold new reply/result during the staged reveal.
- [x] Reveal needs at about 400ms, model summary at 1000ms, seller summary at 1600ms, and result at 2000ms.
- [x] Use 300ms for clarification and read-only evidence replies without comparison steps.
- [x] Derive steps from actual local records; handle unavailable/no-match/error outcomes honestly.
- [x] Disable stale selection and submission/preference/selection actions while presenting; keep draft typing/reset available.
- [x] Cancel timers on reset/unmount, reject old ticks, restore validated results without replay.
- [x] Respect reduced motion and preserve backend/domain shopping rules.

## Verification and completion

- [x] Pure presentation tests: timing, readonly/clarification/no-match, busy guards, reset and restore.
- [x] Browser-controlled timing tests: immediate message, staged summaries/result, stable coordinates and stale selection.
- [x] Verify reset during every phase, refresh, draft preservation, keyboard and live status.
- [x] Inspect initial/pending/final states on desktop, mobile and 320px with no overflow/console errors.
- [x] Run full frontend regressions, TypeScript and production build.
- [x] Independent adversarial subagent review; fix actionable findings and repeat affected checks.
- [x] Record final visual QA and evidence in `plans/` and audit all checkboxes.
- [x] Create separate verified transition commit and leave local preview running.
- [x] Mark goal complete after final review.

No paid APIs, real web search, real orders, backend changes or fictional-fixture edits. Transient presentation state is not persisted; authoritative state keeps the existing persistence/validation contract.

Evidence: [transition QA](chat-transitions-qa.md), scoped source diff and presentation/browser regression suites. All 204 unique regression cases are verified across the broad run and corrected-file rerun (exact results in QA); TypeScript and production build passed. The separate transition commit is in local Git, the preview is running, and the Codex goal is complete. Nothing was pushed.
