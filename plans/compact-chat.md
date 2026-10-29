# Compact chat and inline completed checks

## Verified checklist

- [x] Reduce desktop chat text from 16px to 14px, avatars from 50px to 36px, header from 88px to 68px, and chip/card spacing.
- [x] Keep mobile input text at 16px and interactive targets at least 44px; preserve visible focus, reduced motion and existing shopping safeguards.
- [x] Place completed checks between the request and its comparison answer, replacing the separate bottom Completed section.
- [x] Collapse checks by default to Compared 2 models · Checked 3 sellers · Excluded 1; native details opens with keyboard or pointer.
- [x] Present actual blocked-offer counts during the seller-check stage; unavailable checks retain unavailable wording.
- [x] Keep explanations and evidence links attached to the comparison answer; evidence-only questions do not create comparison snapshots.
- [x] Save bounded, validated comparison snapshots with their assistant messages so later corrections do not overwrite old checks. Existing sessions without this optional metadata remain valid; their earlier plain messages stay unchanged until a new comparison records checks.
- [x] Verify timing, stable layout, reset/refresh, narrow layout, keyboard expansion, history ordering, follow-ups and corrections through browser regressions.
- [x] Check TypeScript, production build and whitespace validity.

## Verification

- Before the inline change: 24 compact-layout, clarity and transition tests passed.
- Combined inline change: 78 journey, transition, presentation and session cases passed on desktop/mobile (`cui-journey`, `cui-transitions`, `shopping-session`, `shopping-presentation`). New cases cover collapsed placement, keyboard expansion, follow-up/refresh persistence, immutable earlier evidence and rejecting unrecognized stored evidence.
- After the final mobile spacing fix: 2 controlled browser timing/layout cases passed again at desktop 1487×1058 and narrow 320×1058.
- TypeScript passed. Production build passed with isolated `.next-e2e` output, including lint/type validation and generation of all 10 routes. `git diff --check` passed.
- Desktop screenshots are 1:1 CSS pixels. Pixel 7 screenshots use device density 2.625; narrow-normalized.png is reduced to 320px CSS width before inspection. Screenshot capture disables CSS animation so the final card is fully opaque.
- Screenshot review caught cramped narrow needs chips and an input placeholder clipping; chip padding/icons and mobile textarea minimum height were adjusted and recaptured.
- Interactive in-app inspection was unavailable (`browser.user is unavailable`). Actual Chromium browser interactions and screenshot evidence came from the Playwright regression suite instead. No paid APIs or real purchases were used.

## Visual evidence

[Before/after at equal scale](verification/compact-chat/before-after.png) · [Desktop final](verification/compact-chat/desktop-final.png) · [In-progress checks](verification/compact-chat/desktop-progress.png) · [320px normalized](verification/compact-chat/narrow-normalized.png)

Typography is intentionally smaller; the palette, icon library, warning colours and two-column hierarchy remain unchanged. The current match, alternative and excluded seller remain distinct. At 320px, long need labels use the existing two-line truncation and retain their full accessible edit labels. The composer stays separate from the scrolling transcript.

Changes are confined to the shopping frontend, frontend conversation metadata and relevant tests. Backend APIs, fixtures and model/seller eligibility rules are unchanged. Local preview: http://localhost:3000/shop.
