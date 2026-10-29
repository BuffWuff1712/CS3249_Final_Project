# Beany /shop design QA

Date: 29 October 2026. Target: the user's selected first mockup, implemented in the fresh Next.js repository rather than a separate prototype.

## Source and comparison setup

- Source visual truth: `verification/shop-ui/mockup-1.png`, 1487 x 1058 pixels.
- Current implementation: `http://localhost:3000/shop`.
- Desktop state: headphones, daily train commute, hard SGD300 ceiling, noise cancellation first, Echo Quiet / Northline Audio / SGD289; sources collapsed and no selection.
- Desktop viewport: 1487 x 1058 CSS pixels, device scale 1. Screenshot is 1487 x 1058 pixels, with no browser frame or density rescaling.
- Equal-size full-view comparison: `verification/shop-ui/desktop-comparison.jpg` (source left, implementation right, 2974 x 1058). Images were placed side by side without altering the source or implementation pixels.
- Current desktop capture: `verification/shop-ui/desktop-current.jpg`.
- Supporting mobile views: `verification/shop-ui/mobile-decision-390.jpg` and `verification/shop-ui/mobile-decision-320.jpg`. The 320px view includes the explicit EU42 / blue / new variant.
- Earlier UI: `verification/shop-ui/before-desktop.png` (audit capture before redesign, full page; comparison evidence of old hierarchy, not pixel-matched source truth).

## Visual iterations

| Pass | Finding | Fix and evidence |
| --- | --- | --- |
| Initial screenshot | Capture occurred before the viewport had settled; clipped right-hand content. Rejected as comparison evidence. | Re-read viewport and layout, then took a fresh settled screenshot. |
| Settled first pass | P2: needs and currency/editor competed for horizontal space, wrapping the priority. Repeated intent reduced decision visibility. | Grid-aligned brief; compact editor; removed duplicate visible intent while retaining accessible needs and full trace. `desktop-pass-2.jpg` to `desktop-pass-3.jpg`. |
| Second pass | P2: expanded input and activity detail height clipped the composer in the reference viewport. | Single-row expanding composer, smaller section gaps and lightweight activity disclosure. `desktop-pass-4.jpg` to `desktop-current.jpg`. |
| Matched comparison | Main regions, product/price hierarchy, comparison summaries, blue selection action and excluded-seller area align with the source. Composer and primary selection fit in the viewport. | `desktop-comparison.jpg`; measured composer bottom 1021.3px and selection bottom 573.4px in a 1058px viewport. No horizontal overflow. |
| Mobile | Layout must reflow without clipping; fixed shoe variant must remain visible before selection. | Stacked workspace, working jump links, readable 320px decision panel and visible EU42 variant; no overflow. |

## Required fidelity surfaces

- **Typography:** existing Arial/Helvetica sans family retained; 16px conversation text, clear product/price hierarchy and smaller source metadata. No remote fonts. Exact raster letterforms are not reproducible font specifications; readable existing typography is retained intentionally.
- **Spacing and layout:** compact brief, conversation left and decision right, light dividers and restrained rounded surfaces. Desktop uses the matched reference dimensions. Mobile is an adaptation because the reference contains no mobile design.
- **Colours:** navy text, pale blue background, white surfaces and blue primary controls; red belongs only to the excluded seller. No invented green verification badges.
- **Assets:** existing text wordmark retained. Standard Phosphor icons replace screenshot glyphs; no invented product art, rasterised interface or handcrafted icon approximations. No product photography exists in the reference or fixtures.
- **Copy:** factual local comparison counts, explicit unknowns, short advantages and trade-offs. Unsupported mockup delivery, total-cost and suitability claims were corrected. Classic navigation, advanced trace, source controls and explicit selection/finish remain functional additions from the existing app.

## Functionality and accessibility evidence

- Direct in-app browser: headphone request, selection, read-only reviews, combined reasons/reviews/returns, source focus and decision completion.
- Direct mobile browser: shoe priority conflict, cushioning clarification, change to light weight, exact-product seller switch, 390px and 320px reflow.
- Browser logs: no warnings/errors in the inspected mobile session. Keyboard/evidence focus and both categories covered by automated browser regressions.
- Independent adversarial review found and drove fixes to seller-lock preservation, imperative read-only alternatives, capped-history scrolling and multi-topic answers. The repeated-preference edge was also fixed and independently verified by a third adversarial probe.

## Acceptance gate

- Final stable-source full frontend suite: **166 passed (1.4m)**, desktop and Pixel 7 projects, including explicit 320px checks. Log: `verification/shop-ui/frontend-tests.log`.
- Final TypeScript check: passed.
- Final production build: passed all ten static pages using `BEANY_E2E=1 npm run build`, keeping build output separate from the running developer preview. Log: `verification/shop-ui/production-build.log`.
- Independent adversarial source/visual review: no remaining actionable UI or functional issues within the agreed scope; three independently authored probes passed after fixes. Summary: `shop-ui-independent-review.md`.
- No backend, classic-route implementation or fictional fixture changes. No paid API calls, real website searches or purchases were required.
- The in-app browser preview is retained and visible, with its temporary viewport override reset. Source/state remains inspectable at localhost:3000/shop.
- Evidence establishes tested behaviour and visual quality; it is not a claim of exhaustive accessibility compliance or absence of every possible bug.

final result: passed
