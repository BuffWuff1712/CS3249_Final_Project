# Beany CUI v2 delivery plan

Tasks are tracked in GitHub Issues. This file is an ordered index; acceptance criteria, verification and dependencies live in the linked issues.

Tracking issue and complete PRD: [#3](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/3).

Publication verified: 21 open task issues plus the tracking issue.

## Architecture and scope decisions

- Make personalised decision reasoning explicit while preserving convenience.
- Use consistent mock scenario state; live APIs and new production infrastructure are not prerequisites.
- Keep supporting evidence optional, hard limits intact and final selection under user control.
- Baseline, assignments, instrumentation and exports are later study-readiness work, not final-presentation blockers.

## Implementation pass — 29 October 2026

Continue the existing CUI work on `feat/cui-v2-issues`. Keep the generated `frontend/next-env.d.ts` outside implementation commits.

1. Corrections and conflicts (#11–12): atomic typed state, explicit no-match and unchanged-winner explanations, strict budgets, and input recovery. Verify focused browser and decision tests.
2. Seller choice and completion (#13–16): exact variant identity, observable cautions, optional sources, selection invalidation and validated refresh persistence. Verify a complete decision without opening evidence.
3. Shared second category and explanation (#9–10, #17–18): running-shoes negotiation, source-linked decision steps, truthful completed activity, keyboard and narrow-screen checks.
4. Study and demo preparation (#19–20): update run instructions, write the protocol, scoring rubric, reproducible demo script and presentation outline. No invented participant results.
5. Final checkpoint: backend regression suite, frontend typecheck/build, full desktop/mobile Playwright suite, screenshots/console inspection and code review. Record exact evidence before marking work complete.

Implementation and verification: #9–19 are implemented/documented locally. Final checks: 430 backend tests passed with five existing skips; 82 Playwright checks passed across desktop/mobile; typecheck and production build passed. The budget-guard mutation was caught and restored. Source/acceptance details and screenshots are in [`docs/cui-v2-delivery.md`](../docs/cui-v2-delivery.md).

#20 has a runnable system, silent recordings, a reproducible demo script and timed presentation notes. Team narration/rehearsal, historical-deck validation and the final course submission remain human deliverables. #21–24 remain the separate pre-recruitment gate. GitHub issue states are not changed by this local implementation record.

## Final demo and study plan

- [#4 Fix hard-constraint state when switching brief fields](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/4) — S · 2 files.
- [#5 Show one personalised headphone recommendation from a mock scenario](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/5) — M · 4–5 files.
- [#6 Replace the long default brief with a compact editable needs summary](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/6) — M · 3–4 files.
- [#7 Ask only decision-changing purchase clarification questions](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/7) — M · 3–5 files.
- [#8 Add optional comparison and source evidence to the recommendation](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/8) — M · 3–5 files.
- [#9 Show how the recommendation follows from needs and evidence](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/9) — M · 3–4 files.
- [#10 Show honest comparison progress from represented scenario actions](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/10) — M · 3 files.
- [#11 Make priority corrections update the choice and its explanation](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/11) — M · 4–5 files.
- [#12 Negotiate material tradeoffs without relaxing hard limits](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/12) — M · 3–4 files.
- [#13 Change seller while preserving the selected product variant](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/13) — M · 3–4 files.
- [#14 Show actionable merchant cautions without penalising clean small sellers](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/14) — M · 3–4 files.
- [#15 Recover clearly when source evidence or an input is unavailable](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/15) — M · 3–4 files.
- [#16 Let users select an offer without mandatory evidence review or checkout](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/16) — M · 3–4 files.
- [#17 Reuse the CUI journey for a curated running-shoes scenario](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/17) — M · 2–4 files.
- [#18 Verify the CUI flow on mobile and with keyboard navigation](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/18) — M · 2–4 files.
- [#19 Write the A/B study protocol for convenience and justified trust](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/19) — S · 1–2 documentation files.
- [#20 Prepare the working demo and 15-minute final presentation](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/20) — M · 2–3 documentation/artifact files.

## Before future participant recruitment

- [#21 Build a fair comparison-GUI baseline for the future study](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/21) — M · 3–5 files.
- [#22 Persist study condition assignments and linked participant sessions](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/22) — M · 3–5 files.
- [#23 Record minimal task outcomes and verification burden for both conditions](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/23) — M · 3–5 files.
- [#24 Export anonymised condition-aware study task results](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/24) — S · 2–3 files.

## Checkpoints

- First recommendation and evidence: [#4](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/4), [#5](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/5), [#6](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/6), [#8](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/8).
- Reasoning and conversational repair: [#7](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/7), [#9](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/9), [#10](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/10), [#11](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/11), [#12](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/12).
- Seller choice and completion: [#13](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/13), [#14](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/14), [#15](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/15), [#16](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/16).
- Final demonstration: [#17](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/17), [#18](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/18), [#19](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/19), [#20](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/20).
- Later study readiness: [#21](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/21), [#22](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/22), [#23](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/23), [#24](https://github.com/BuffWuff1712/CS3249_Final_Project/issues/24).

## Risks and controls

- Generic reassurance can replace reasoning: require comparative explanations linked to current facts and evidence.
- Detail can erase time savings: normal completion must not require opening every source.
- Mock branches can drift: verify correction, no-match and unavailable-evidence paths against a shared decision record.
- Study claims can exceed the design: evaluate the whole package and measure effort and comprehension together.

## Publication record

The original prepared scope is in `docs/github-issues/cui-v2-issue-plan.json`. Verified publication URLs are in `docs/github-issues/cui-v2-publication.json`; their saved open states describe publication time. GitHub status is the task source of truth. That initial publication did not change application code; the implementation pass above records subsequent delivery.
