# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: end shoppers trying a conversational shopping tool, typically in a short usability-study session. They are meeting Beany for the first time, do not want to read documentation, and are judging whether to trust an AI with a purchase decision.

Secondary: CS3249 graders evaluating the submission after end-user sessions. They care that the safety thesis is visible in the interface, not just described in the README.

## Product Purpose

Beany lets a shopper describe what they want in plain language — even vaguely — and does the searching, comparing and seller-safety work on their behalf, while keeping the final purchase decision with the shopper. Success is: the shopper finishes a search, can point at the on-screen reason the recommended match was chosen, and understands why the risky seller was flagged.

## Positioning

Beany is a conversational shopping copilot where the agent's understanding of the shopper's needs is **editable on-screen**, so the shopper can correct the agent's interpretation instead of arguing with it in chat. Other agentic shopping UIs bury the interpretation inside a scrolling transcript; Beany surfaces it as a structured, correctable brief next to the current match, the seller evidence, and the risk verdict.

## Operating Context

- Deployed and reachable at `https://35.240.146.219/shop` (self-signed HTTPS, Google Cloud Run; cold starts take 10–20s).
- Also runs locally in a mock mode (no API keys) and a real-LLM mode (with keys).
- A session is one short task: shopper arrives, describes a need, reviews one recommended offer plus up to two alternatives, inspects seller evidence, and explicitly selects an offer to finish.
- Checkout is **simulated**: no real payment, no real order, no personal data captured.
- Recorded test catalogue covers three categories: headphones, backpacks, running shoes — with a deliberate mix of trustworthy and risky sellers.

## Capabilities and Constraints

- Two-pane layout is a committed IA decision (conversation left, current match + needs + evidence right). Preserve across redesign.
- The editable needs summary (brief chips) is the product's primary differentiator; it must remain prominent and correctable in-place.
- Every offer carries a risk verdict (ALLOW / REVIEW / BLOCK) with quoted evidence; the three states must be visually distinct, not three shades of the same hue.
- Shopper-set guardrails exist: maximum budget, allowed merchants, restricted merchants, payment permissions, substitution permission. These must be surface-able before and during a purchase.
- "Find another seller" and "Find another product" are first-class actions, not refinements.
- Accessibility baseline already in code (skip link, aria-live status region, labeled nav, 44px targets, 3px focus outlines, prefers-reduced-motion) must be preserved.
- Terminology for end shoppers must not leak backend vocabulary ("brief", "proposal", "fingerprint", "replay", "scenario"). Backend and frontend vocabularies are allowed to diverge.

## Brand Commitments

- Name: **Beany**. Keep it.
- Voice (from current copy, confirmed binding): calm, plain, honest about limits. Example lines to preserve the register of: *"AI does the shopping. You stay in control."*, *"A little less searching. A lot more peace of mind."*, *"No receipt, order or payment has been created."*
- Sandbox framing: every surface must make clear this is a demo with simulated checkout. No copy that implies real purchases.
- No existing visual identity is binding. The current blue + Arial skin is **not** committed and is open to replacement.

## Evidence on Hand

- Working deployed instance at `https://35.240.146.219/shop`.
- Recorded listings at `backend/data/replay/study_listings.json` covering headphones, backpacks, running shoes — with trustworthy and risky sellers mixed deliberately.
- Scripted scenarios in the UI composer ("Try headphones", "Try backpacks", "Try running shoes").
- Risk-flag examples triggerable by specific seeded sellers (for REVIEW and BLOCK states).
- Team: four CS3249 Group 2 members (Bhavina Sathish Kumar, Goel Arnav, Low Bing Heng, Yuan Weitu).
- No real customer testimonials, benchmarks, pricing, licensing, or production users. Do not fabricate.

## Product Principles

1. **Correctable grounding over clever conversation.** When the agent is wrong about what the shopper wants, fixing it should take one click on the brief, not a paragraph of chat.
2. **Safety signals outrank brand signals.** A risky seller's warning must be the loudest thing on the surface at that moment; brand chrome recedes.
3. **The shopper decides, always.** No action with real-world consequence happens without an explicit selection. The interface never simulates agency it does not have.
4. **Honest about being a demo.** The sandbox nature is declared, not hidden behind polish.
5. **One decision per screen.** The right pane should make "pick this offer or not" easy, even when supporting evidence is rich.

## Accessibility & Inclusion

- Keyboard reachable end-to-end (currently incomplete — no Enter-to-send, no decision shortcuts; to be addressed in later rounds, not part of the redesign scope itself).
- WCAG AA contrast on all risk, status, and action states.
- `prefers-reduced-motion` honored.
- Skip link + aria-live status region + sr-only landmarks already present; preserve.
- Touch targets ≥ 44px.
- Mobile reachable: end shoppers may open the live link on phones.
