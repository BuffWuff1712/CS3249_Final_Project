# Beany final demo and presentation

Prepared 29 October 2026 · scenario `beany-cui-v3.0`

## Run the submitted build

For the CUI demo only, no backend, API key or browser-search credential is required:

```sh
cd frontend
npm install
npm run build
npm run start
```

Open `http://localhost:3000/shop`. The root route is the older backend-connected simulation; use `/shop` for this recording. For development use `npm run dev`. `Start fresh` resets only this CUI's local decision; it does not delete classic backend sessions or receipts.

The fixture version is defined in `frontend/src/lib/shoppingFixtures.ts` and displayed in the interface. Record the tested commit with `git rev-parse HEAD` after committing. Freeze that commit, package lock and fixtures for recording/submission. All products, reviews and seller records are fictional, and selection creates no order/payment. The interpreter recognises a bounded set of needs; do not describe it as a general live shopping agent.

## Working demonstration script

Use real application actions and keep the default sources collapsed unless the script calls for them. No fabricated screen, fake completed check or timed research animation is required.

### Headphones: goal, reasoning, correction, seller and selection

1. Start fresh. Enter: `Headphones for my daily train commute, under SGD300. Noise cancellation matters more than weight.`
2. Show Echo Quiet at SGD289 from Northline Audio. Read the four concise reasons: priority and ceiling; comparison with Luma Air; the editable longer-returns tie-breaker; 45g weight compromise.
3. Open `How I reached this recommendation`, follow one evidence link and show product review count separately from seller review count. Optional evidence is available, but the normal selection flow does not require it.
4. Enter: `Actually, comfort matters more`. Show Luma Air at SGD279, the short change explanation, current needs and only the affected trace steps marked Updated. Comfort remains subjective.
5. Enter: `Keep the product but find another seller`. Show the same Luma Air variant at SGD259 from Everyday Sound, with its own 14-day terms and seller evidence.
6. Select the offer with sources collapsed; show the recap. Change the budget to SGD180 and show selection invalidation and the no-match explanation. Restore SGD300 explicitly.
7. For the concern example start fresh with the initial reference request, then enter: `Find the cheapest Echo Quiet offer`. Show SoundRush's gift-card/outside-checkout concern and the recommended clean Everyday Sound offer at SGD269. Explain that small review history and a benign discount alone are not blocks.
8. Select the clean offer and `Finish decision`. No checkout, credentials or real order are involved.

### Running shoes: material conflict and reuse

1. Start fresh. Enter: `Running shoes for daily road runs, under SGD200. Cushioning and light weight are equally important.`
2. Show the focused priority question; choose `Cushioning first`. Stride Cloud at SGD179 from Northline Running wins, with 65g extra weight per shoe as the compromise.
3. Enter: `Actually, light weight matters more`. Show Pace Light at SGD169 and the updated reason. The scenario's size/colour/condition remain EU42/blue/new.
4. Enter: `Keep the product but find another seller`. Show Pace Light from Everyday Run at SGD149. Select and finish, leaving evidence optional.

### Short boundary checks for rehearsal

- Bare `headphones` → useful use-case question → `Show options`; no budget is invented.
- Headphones for commuting under SGD260, noise cancellation first → Luma Air; change to comfort → same winner with a concrete explanation and unchanged SGD260 ceiling.
- USD300 request → explicit SGD clarification; choosing `Use SGD` uses the same numeric amount with permission, without claiming an exchange conversion.
- `Find a laptop instead` → supported-category clarification; never map the laptop to a headphone recommendation.
- Inspect the SoundRush source → unknown return policy remains unknown; the UI does not claim verified authenticity.
- With Luma Air at SGD259 under SGD260, request another seller → no eligible other seller; retry keeps the product fixed, while a different-product search is an explicit separate action.
- Refresh a selected offer → restores that exact eligible offer; edit a need → selection clears. Start fresh → no selection survives.

## Fifteen-minute presentation outline and speaker notes

| Time | Slide / live segment | Concrete message |
| --- | --- | --- |
| 0:00–1:00 | 1. The purchase decision | A consumer can express a situation more easily than technical filters. The design goal is useful delegation with understandable decisions. |
| 1:00–2:00 | 2. Trust and convenience | Reading every source defeats delegation; an unexplained recommendation is hard to assess. Success requires both lower effort and comprehension. |
| 2:00–3:00 | 3. What the CUI makes visible | Show needs → eligible models → product comparison → seller comparison → choice. Explain observed facts versus agent tie-breakers. |
| 3:00–4:00 | 4. Changes and boundaries | Show the implemented compact summary, optional evidence and consequential correction. Verify any “since mid-project” claims against the actual historical deck before using them. Explain fictional fixtures, local interpreter and simulated selection. |
| 4:00–7:30 | 5. Headphones live demo | Specific request; concise reasons; correction; same-product seller switch; visible concern; informed selection. Use the script above. |
| 7:30–9:00 | 6. Second task and hard boundary | Running shoes with the shared priority/selection pattern; show the SGD180 no-match or its screenshot from the actual build. |
| 9:00–10:00 | 7. Study comparison | A usable comparison GUI versus full CUI, identical records and tasks. This tests the whole package, not the trace independently. |
| 10:00–11:00 | 8. Study procedure | Proposed 16–24 adults, four counterbalanced category/interface sequences, matched correction and visible-concern opportunities. Professor feedback precedes recruitment. |
| 11:00–12:00 | 9. What will be measured | Paired time/effort, comparative-reason comprehension, concern understanding, correction and confidence. Explain why high trust alone is insufficient. |
| 12:00–13:00 | 10. Evidence burden and interpretation | Source openings/time with comprehension; fewer openings can be good. Fast but misunderstood decisions are an adverse result. Surveys provide consistency; interviews explain why. |
| 13:00–14:00 | 11. What is verified | Report actual automated checks from the delivery notes and show the running build. Automated tests demonstrate consistency, not human usability findings. |
| 14:00–15:00 | 12. Limits and next study gate | Fixed fictional records and variants, bounded interpretation, no real payments, no participant results. Baseline/assignment/metrics/exports are required before recruitment. |

The outline allocates five minutes to the working demo and four to study design. It contains no invented results or pilot/red-team presentation section. Replace historical claims only after checking the original deck. The team still needs to rehearse the narration, obtain any required course feedback and make its final narrated recording.

## Verification and recording artifacts

Run from `backend`: `.venv/bin/python -m pytest -q -p no:cacheprovider`. Run from `frontend`: `npm run typecheck`, `npm run build`, `npm run test:e2e`.

Playwright uses isolated catalogue/mock servers at 3100/8100, blank credentials and a dedicated test database. The new CUI browser tests record screenshots in `frontend/test-results/`; the scripted recording test emits an actual silent WebM of both scenarios. These are verification artifacts, not participant recordings or a narrated 15-minute final submission. Test output is ignored by Git and regenerated on each run; copy chosen artifacts before running the suite again.

The source-to-acceptance map and final verification evidence live in `docs/cui-v2-delivery.md`.
