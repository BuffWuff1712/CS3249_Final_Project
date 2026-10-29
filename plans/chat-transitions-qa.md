# Chat transition QA

Final result: passed. Browser/functionality checks, corrected-source regression coverage, TypeScript and production build pass. The separate local transition commit is saved, the preview remains running, and the Codex goal is complete.

## Scope and reference

Checkpoint `dce8dae` preserves the completed redesign. This change follows the approved transition plan: the initial and completed states share a chat frame, needs strip, composer and decision panel. It intentionally replaces the old large welcome section and adds local presentation pacing. It does not add a search service.

Visual references:
- Original [mockup 1](verification/shop-ui/mockup-1.png), preserved unchanged.
- [Original mockup and current result](verification/chat-transitions/mockup-final-comparison.png). Both show Echo Quiet, Northline Audio, SGD289; the original image is fitted into a 744×529 panel, so this comparison is qualitative rather than a pixel match. Persistent scroll panes, explicit evidence caveats and the classic navigation label are intentional existing/product constraints.
- [Initial, pending and result together](verification/chat-transitions/desktop-states-comparison.png). Three screenshots at 1487×1058 CSS pixels, each scaled equally to 744×529. Original full-resolution files remain beside the comparison.

## Findings and fixes

| Issue | Fix | Verification |
| --- | --- | --- |
| P2: empty needs strip shrank to its content width because shared `main` aligned children at the start | Stretch the scoped shopping workspace children | Initial/pending/final captures; controlled browser width assertion |
| P1: opening the needs form on a 1280×600 desktop squeezed the chat to 16px and pushed its composer below the usable frame | Let the shell grow while the editor is open; reserve at least 420px for each workspace pane | Independent repeat: chat 284px inside a 420px conversation; short-screen regression |
| P1: follow-up auto-scroll went below the new answer to older comparison activity | Position the newest turn or current progress at the chat viewport start | Independent repeat at 390×844: answer top -0.25px rounding, answer 242px, region 312px; geometric regression |
| Test synchronization: two old tests used needs-strip visibility as proof that comparison had completed | Wait for the current recommendation before editing; preserve the production busy guard | Corrected full `cui.spec.ts` file: 10 passed |

## Required visual surfaces

| Surface | Assessment |
| --- | --- |
| Fonts and hierarchy | Existing font family, navy headings, body sizing and weight are retained. The oversized disappearing hero is now a normal assistant turn. Full-resolution desktop and 320px captures checked for wrapping. |
| Spacing and layout | Desktop uses the same two columns and pinned composer before and after submission. The needs placeholders reserve the final chip/status heights. Mobile stacks the decision after a bounded, internally scrolling chat. Expanded desktop editing deliberately permits page scrolling. |
| Colours and tokens | Existing pale-blue canvas, white cards, navy text, blue action and red blocked-offer tokens retained. Loading and disabled controls remain distinguishable. |
| Asset fidelity | Existing Phosphor icons and brand typography retained; typing uses the library dots icon. No raster product imagery or generated replacement assets added. |
| Copy and content | Progress states explicitly describe fictional local records and no visited websites. Model/seller counts come from actual comparison activity. No-match and unavailable records do not gain invented seller checks. Evidence/comfort/return limitations retained. |

Focused inspection used full-resolution initial/pending/final desktop images and narrow/mobile screenshots in addition to combined comparisons; the reduced triptych alone was not used to judge small text.

The accessibility pass also checked the relevant [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md): semantic controls, labels, focus, status announcements, reduced motion and overflow. This is a scoped UI review, not a comprehensive assistive-technology certification.

## Behaviour and accessibility

- Comparison timings: interpreted needs 400ms, model activity 1000ms, applicable seller/eligibility activity 1600ms, final result 2000ms.
- Clarification and read-only evidence answers: 300ms; no comparison replay.
- User message is immediate. Draft typing and reset remain available; submit/edit/selection/preference actions are guarded while busy.
- Existing result state is computed once and saved through the existing domain validator. Refresh restores it without replaying transient timers.
- Reset/restore reject old ticks; effect cleanup clears timer handles on replacement/unmount.
- Keyboard Tab→Enter submission checked in the in-app browser at 320px and in automated reduced-motion tests. A polite, atomic status announces stages and the final answer. No animation under reduced motion.
- Independent mobile checks: 390×844 and 320×740; primary browser checked 390×844 and 320×900, desktop 1487×1058. No horizontal overflow; no console warnings/errors in the primary browser capture.
- Both headphones and shoes exercised through real UI controls using fictional local data. No paid calls or purchases.

## Evidence

[Desktop initial](verification/chat-transitions/desktop-initial.jpg) · [Pending](verification/chat-transitions/desktop-pending.jpg) · [Final](verification/chat-transitions/desktop-final.jpg)

[Mobile initial](verification/chat-transitions/mobile-initial.jpg) · [Mobile pending](verification/chat-transitions/mobile-pending.jpg) · [Mobile final full page](verification/chat-transitions/mobile-final-full.jpg) · [Mobile follow-up](verification/chat-transitions/mobile-followup.jpg)

[320px initial](verification/chat-transitions/narrow-initial.jpg) · [320px pending](verification/chat-transitions/narrow-pending.jpg) · [320px final](verification/chat-transitions/narrow-final.jpg)

## Test ledger

- Pure presentation suite: 11 cases passed; projects execute each pure case on desktop/mobile in the full run.
- Initial controlled timing batch: 14 passed.
- First full run: 198 passed, 2 failed due to the old needs-strip synchronization assumption above. Fixed the assumption, not the guard.
- Final broader frontend run: 202 passed, 2 failed (7.1 minutes). Its test collection occurred just before the synchronization edit, so it retained the old completion assumption.
- Corrected-source rerun of the entire affected `cui.spec.ts` file: 10 passed (1.2 minutes), including both previously failing desktop/mobile cases. Together these runs verify all 204 unique regression cases; this is not a claim of one 204-pass invocation.
- TypeScript: passed (`npm run typecheck`).
- Production build: passed (`BEANY_E2E=1 npm run build`, exit 0), including lint/type validation and static generation for all 10 routes. `.next-e2e` isolated the build from the running `.next` preview.
- Independent review: both actionable findings fixed and independently rechecked; final test/build ledger audit passed. See [independent review](chat-transitions-independent-review.md).

The app preview remains at http://localhost:3000/shop. Backend APIs, fixtures, domain reducers and shopping rules are unchanged. Private environment files, databases, dependencies and build/test scratch output remain ignored.
