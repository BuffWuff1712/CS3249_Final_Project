# Beany CUI evaluation protocol

Protocol v2.0 · 29 October 2026 · Scenario `beany-cui-v3.0`

This is a proposed study, not a report of participant results. The runnable `/shop` prototype uses a deterministic fictional catalogue and a bounded interpreter. It does not use the live model or the classic backend's research sessions. A mock implementation is permitted by the PRD; findings must be limited to the interaction demonstrated.

## Research questions and measures

The hypothesis is lower research effort with preserved or improved comprehension and decision quality. Higher confidence or more purchases alone is not success.

| Question | Measure and procedure | Supported interpretation |
| --- | --- | --- |
| Does delegation reduce effort? | Time from task reveal to final choice; 1–7 mental-effort and ease ratings; required actions and clarification turns | Convenience of the whole experience, subject to choice quality |
| Does the recommendation communicate personal fit? | Ask the participant to explain the decisive need and relevant alternative without prompting the answer; apply the rubric below | Comprehension of the personalised comparative explanation |
| Does the interface support justified confidence? | Confidence 0–100 after choice, scored comprehension and response to the visible payment concern | Whether confidence is accompanied by understanding; confidence alone cannot show calibration |
| Can the user redirect it? | Issue a matched priority correction; observe need, choice, explanation and final-selection changes | Correction success and recovery, including a justifiably unchanged winner |
| Does optional detail reduce verification burden? | Evidence openings, time in expanded detail, and whether the task was completed and understood without it | Reduced source-reading burden when understanding is preserved |

## Conditions and fairness

**A — comparison GUI:** a usable product/offer comparison view with filters, the exact same fictional specifications, prices, product reviews, seller rating counts, payment and return terms. No conversational assistant, agent ranking, personalised trace or generated concern explanation. Raw payment concerns remain visible; never hide information to make the baseline worse.

**B — Beany CUI:** the complete `/shop` experience: selective clarification, editable needs, personalised recommendation, decision explanation, correction, seller changes and optional sources. Use the same scenario records, available offers, spending limits and task instructions as A.

This compares the complete interface packages. It cannot identify conversation, personalisation or the decision trace as independent causes. A later trace-on/trace-off CUI experiment would be needed for a narrower causal claim.

**Implementation status:** B is implemented. A, paired condition assignments, task timing instrumentation and condition-aware exports are future recruitment requirements (#21–24). The existing classic `/research` standard/concise profiles are not condition A/B and cannot substitute for them.

## Participants and counterbalancing

Propose 16–24 adults with online-shopping experience, subject to recruitment feasibility and professor feedback. This is a feasible course sample proposal, not a power calculation. Obtain professor feedback and approve task/scoring materials before recruitment.

Use a within-participant design with one headphones and one running-shoes task. Assign participants evenly across these four sequences:

| Sequence | First task | Second task |
| --- | --- | --- |
| 1 | A: headphones | B: running shoes |
| 2 | B: headphones | A: running shoes |
| 3 | A: running shoes | B: headphones |
| 4 | B: running shoes | A: headphones |

Each participant sees each category once. Counterbalance task and interface order. Use fresh linked sessions with a shared pseudonymous study ID. Keep correction and concern opportunities comparable across categories. Do not reuse a practice-category task as a measured task.

## Task cards and procedure

1. Explain fictional records, no real purchases, voluntary participation and local data handling. Obtain consent; collect no real payment or address information.
2. Give a neutral practice task. Explain available controls without recommending a product or teaching the scoring answers.
3. Reveal the task card and start the task clock. Participants may phrase their own requests; do not prescribe the demo's exact dialogue.
4. Headphones: daily train commute, SGD300 ceiling, noise cancellation first. Running shoes: daily road runs, SGD200 ceiling, cushioning first; the fixed illustrative size/variant is EU42/blue/new. Record a participant's rejection of that fixed variant as a limitation, not an error.
5. At the same task stage in either interface, ask the participant to consider the cheapest offer. The visible gift-card/outside-checkout term is the concern. Observe recognition and their response; never grade on hidden labels.
6. Give a correction card: comfort now matters more for headphones; light weight now matters more for shoes. Allow them to revise and make a final choice. If a no-match task is included, use a separately predefined subtask and identical constraints in both conditions.
7. Stop timing on explicit final choice or participant-declared abandonment. Record abandonment separately. Do not require checkout or source openings.
8. Ask comprehension questions and a brief post-task survey, then reset before the second condition. Ask participants to avoid thinking aloud during timed tasks; use retrospective discussion so verbalisation does not distort task time differently between conditions.
9. Conduct a short comparative interview. Separate recorded facts from facilitator interpretations. Do not claim that the scripted demonstration is a participant session.

## Predefined scoring rubric

Use only participant-accessible information. Predefine acceptable equivalent answers, have two raters independently score a subset, and report disagreements and their resolution.

| Outcome | Score | Anchors |
| --- | --- | --- |
| Hard-constraint fit | 0–1 | 1: chosen offer fits the stated budget, category and fixed variant; 0: violates one. Record no-choice separately. |
| Personalisation comprehension | 0–2 | 0: wrong/no decisive need; 1: names the priority; 2: connects that priority to the chosen model relative to the alternative. |
| Tradeoff comprehension | 0–2 | 0: wrong/no compromise; 1: names a relevant compromise; 2: explains its practical consequence without claiming subjective comfort/fit is proven. |
| Visible concern understanding | 0–2 | 0: misses/misreads outside-checkout demand; 1: notices it; 2: explains the consequence and a feasible ordinary-checkout alternative. |
| Correction success | 0–2 | 0: old needs/selection persist; 1: updates the stated priority; 2: updates or justifies the choice and explanation, then explicitly selects the current offer. |

Keep scores separate in reporting; do not invent an overall weighted quality score after observing results. Do not grade rejection of a clean small seller as success. A benign discount alone is not fraud. Concealed malicious intent without an observable cue cannot be scored as an avoidable participant error.

## Survey and interview

After each task collect effort (1 = very low, 7 = very high), ease (1 = very difficult, 7 = very easy), understanding of the recommendation (1–7), ability to change the decision (1–7) and confidence in the final choice (0–100). The survey supplies comparable ratings; it does not replace observed comprehension.

Interview prompts: What made the choice credible? What was the most important compromise? Was opening evidence necessary? Did the correction do what you expected? What information was missing? Which interface reduced work, and what did it make harder?

## Analysis, data and limits

Report paired differences and their distributions/uncertainty, with category and order effects. Report quality/comprehension alongside time and effort. Fast decisions with missed material concerns are an adverse outcome. Fewer source openings are beneficial only if understanding is adequate. The small convenience sample and synthetic fixed tasks limit generalisation to real purchases, fraud detection and open-ended model conversation.

Before collection freeze source records, explanation wording, prototype commit, scenario version, baseline implementation and any model/prompt/config versions. Predefine exclusions for technical failure; retain a transparent count and explanation rather than silently removing bad sessions.

Collect study ID, condition, category/order, versions, task start/end, final choice, revisions, concern responses and evidence events. Keep consent/identity mapping separate and local. Set the retention period and access permissions with the course team before recruitment. Do not commit participant conversations, recordings or personal details. This document contains no participant results.

## Existing classic research tools

The `/` interface and FastAPI `/research` controls remain available for the older merchant-risk simulation. They use backend SQLite sessions and researcher authentication, independently of `/shop` browser state. Standard/concise profiles vary explanation length; they are not a fair GUI baseline. Classic CSV events omit raw messages but can contain repeated session totals; do not sum those totals as per-event counts. Export before resetting a classic study session.

Optional live-model evaluation remains `python -m app.evaluate_conversations --output data/llm-evaluation.json` from `backend/`; it deliberately uses configured paid model calls and needs human scoring. Offline pytest and Playwright pin mock/catalogue mode and blank credentials. Live evaluation is not required for the deterministic `/shop` demo.

Pilot/red-team activities belong to Assignment 2 and are excluded from the final-presentation agenda. Future recruitment and actual participant findings remain separate from this final study-plan presentation.
