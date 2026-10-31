# Beany Conversational Shopping Product Requirements

Version 2 | 27 October 2026 | CS3249 final project

## 1 Product decision

Beany helps consumers delegate product research while understanding why the resulting recommendation fits them. The core experience is a short conversation followed by a personalised recommendation with an explicit decision trace. Users see which needs shaped the search, what was compared, which source signals influenced the choice and what compromise remains. They can change a priority and see the decision change without repeating the research.

The central design tradeoff is trust versus convenience. Delegation loses its value if users must inspect every product, seller and review themselves. A recommendation also loses credibility when it supplies an unexplained answer. Beany must make the decisive reasoning visible at low reading cost, while keeping supporting evidence available on demand.

The product promise is: I researched for you, using your priorities. Here is why I chose this, what I checked and what would change my recommendation.

This PRD sets the product direction for the next CUI iteration. Its default recommendation, explanation and mock-backend requirements take precedence over conflicting requirements in the earlier product scope specification. The earlier codebase review remains a record of the assessed implementation; this PRD does not claim the proposed experience is already built.

## 2 Audience and intended outcome

The primary user wants help with a considered consumer purchase and has limited time, product knowledge or familiarity with sellers. They can usually describe their situation more easily than translate it into technical filters. They want a suitable recommendation and enough understanding to decide whether to accept it.

The initial demonstration covers headphones and one existing second category, recommended as running shoes. Purchases above SGD200 can motivate a task, but are not an eligibility requirement. State currency explicitly. No unsourced market statistic or public figure endorsement is needed to justify the product.

A comparison GUI can already present filters, products and seller information. It can also provide explanations. Beany's proposed value comes from combining conversational clarification, explicit personalised reasoning and conversational revision while the agent performs the comparison. The evaluation must test that value rather than assume that conversation is superior.

Success means users save research effort and can explain the main reason for the recommendation, recognise an important compromise or concern and redirect the agent when needed. Higher trust, more purchases or more evidence-panel openings alone do not establish success.

## 3 Product principles and scope

### Principles

- Delegate the research. The default path must not require reading raw reviews, opening sources, checking every seller or maintaining a long preference form.
- Explain the decision. Personalised rationale and the compact decision trace are essential product features, not optional detail below the recommendation.
- Make conversation consequential. A stated priority must affect the selection or its explanation. If the winner remains the same, explain why.
- Interrupt selectively. Ask when the answer could materially change the decision; use visible, editable assumptions for low-impact gaps.
- Preserve user authority. Never silently relax a spending ceiling or convert an assumption into a stated preference.
- Communicate uncertainty accurately. Seller history, ratings and return terms support a judgement; they do not prove safety or authenticity.

### Required experience

The minimum experience includes selective purchase intent clarification, a compact editable needs summary, one primary recommendation, explicit personalised decision reasoning, a meaningful alternative, a concise seller explanation, an actionable material warning, optional evidence detail, and conversational correction with an explanation of what changed.

The supporting catalogue, search, ranking, risk findings, source records and progress events may be mocked. They must be consistent with the visible scenario and user actions. The submitted interaction must work; recording an interaction that the submitted system cannot perform is insufficient.

### Deferred work

Real payments, real orders, autonomous purchasing, agent-to-agent commerce, live crawling, production infrastructure, general scam detection, raw model reasoning transcripts, elaborate streaming architecture and additional product categories are outside this iteration. Existing cart and receipt features may remain as secondary simulated paths. Expanding them is not a prerequisite for the CUI redesign.

The final presentation requires a study plan. Implementing the baseline, recruiting participants and reporting study results are later study-readiness work, unless the course subsequently requires otherwise.

## 4 Explicit decision trace

### Definition

The feature requested as a chain-of-thought display is implemented as a user-facing decision trace: an explicit, concise account grounded in purchase needs, comparison outcomes and source evidence. It explains the observable decision process. It is not a verbatim transcript of the model's private internal reasoning, and generated prose is not evidence that a check occurred.

Use the participant-facing title Why I recommend this for you. This makes the purpose clearer than a technical label. The trace must answer four questions in a connected sequence.


| Question | Required explanation | Example in a fictional task |
| --- | --- | --- |
| What did you optimise for me | Restate the decisive user priority and hard limit | You prioritised noise cancellation for commuting, within SGD300 |
| What did you compare | State the actual comparison scope and relevant difference | Both models fit your budget; Echo Quiet has stronger listed noise cancellation |
| Why this product and seller | Connect the choice to that priority and the merchant evidence | I chose Echo Quiet for noise cancellation; Northline provides more return time than the cheaper seller |
| What am I giving up | State the main compromise or material uncertainty | Echo Quiet is 45g heavier; comfort has not been personally tested |

The trace must include a comparative reason: I chose X over Y because you prioritised Z. A generic list such as great sound, good value and trusted merchant fails this requirement. If no comparable alternative exists, say that the comparison is limited rather than inventing a losing candidate.

### Default disclosure

Show one recommendation and a compact trace in the normal conversation flow. The trace should contain three or four short statements, with the recommendation and explanation together targeting no more than 120 words, excluding controls and optional detail. This is a proposed writing constraint, not a measured usability result.

Keep the main compromise and any material warning visible. Put full specifications, review excerpts, rejected candidates, source records and detailed price comparisons behind View comparison and sources. The user must be able to select an offer without opening those details. A trace should summarise the work the user delegated, not recreate that work as a reading assignment.

### Expanded explanation

An optional How I reached this recommendation view makes the reasoning sequence explicit through five steps: interpreted needs; eligibility decisions; product comparison; seller comparison; final choice. Each step states the criterion, the relevant observation and how that observation affected the decision, with a direct evidence link. A list of activity labels such as checking reviews is insufficient.

For the reference task, the sequence reads: You prioritised noise cancellation within SGD300; both models passed the budget limit; Echo Quiet's listed noise cancellation was stronger, so I preferred it despite extra weight; I favoured Northline's longer return period over saving SGD20, using a disclosed tie-breaker; therefore I recommend that product and offer, with weight as the compromise.

Users can select a criterion in this explanation to correct it. After a correction, highlight the affected comparison and conclusion rather than replaying all steps. This expanded view is optional; the decisive reason remains visible in the default result.

### Progress before the recommendation

Show the relevant plan briefly, such as comparing models against the commute and budget, then reviewing seller terms. Mark planned, running, completed and unavailable states accurately. As steps complete, concise observations can appear: Two eligible models compared; Three offers reviewed for the selected model. Keep the completed trace available with the result.

A catalogue simulation must say it compared records, not that it visited websites. Mock events should come from fixture operations or explicit scenario transitions. Do not use timed messages that claim checks succeeded regardless of what the scenario did. The synchronous fallback can show a labelled plan followed by the completed trace; genuine streaming is optional. Do not add artificial waiting to dramatise research.

### Evidence and limits

Each factual statement needs an inspectable source reference or structured comparison fact. Separate the observed value from the implication: 30-day returns is a term in the seller record; favouring more return time is a decision rule. If the user did not request flexible returns, present that tie-breaker as Beany's assumption and make it easy to change.

Show rating counts alongside ratings and distinguish product reviews from seller reviews. Missing evidence remains unknown. Neither an unfamiliar small merchant nor a low price alone establishes wrongdoing. If a check fails, say what is unavailable and adjust or qualify the recommendation; never display a completed check for a missing result.

## 5 Conversation and interaction requirements

### CUI01 Clarify purchase intent with low friction

Extract category, use case, budget, currency and explicitly stated priorities from the user's message. A detailed request can proceed immediately. For a bare category, ask the next question most likely to distinguish suitable products. Ask one question at a time and provide answer choices plus free text. Accept uncertainty and requests to browse.

For the ordinary demo path, target no more than two clarifying turns before offering a useful result or an explicit browse path. This is not permission to guess a hard limit. Explain an unresolved high-impact ambiguity or let the user browse without claiming all criteria are settled. Do not ask for a brand, specification or merchant preference solely to populate a field.

Acceptance: a detailed commute request does not trigger repeated questions; a bare headphones request receives a useful clarification; Show options works without a completed questionnaire; inferred currency or preferences remain labelled as assumptions.

### CUI02 Keep the needs summary compact and correctable

Display a short summary such as Commuting, up to SGD300, noise cancellation first. Make its values editable and allow natural-language corrections. Keep less important fields in an optional editor. No mandatory confirmation screen is required when the summary accurately reflects the request.

Acceptance: users can change a value from the summary or conversation; confirmed needs are distinguished from assumptions; an edit does not inherit another field's hard-constraint state; the next recommendation reflects the current needs.

### CUI03 Personalise the recommendation explicitly

The default result must name the user priority responsible for the choice, compare it with at least one relevant alternative when available, explain the seller choice separately and expose the main compromise. The interpretation must follow the data: stronger listed noise cancellation can support a commute recommendation, but cannot establish that everyone will find a model comfortable.

Acceptance: the result answers Why this for me and Why this over the alternative without opening details. Replacing the user's priority changes the choice or produces a concrete explanation of why the choice remains appropriate. Every cited alternative exists in the compared set.

### CUI04 Resolve routine tradeoffs and negotiate material conflicts

The agent should resolve routine comparisons using stated priorities and disclosed tie-breakers. It should ask the user to prioritise only when the answer is likely to change the recommendation or when no eligible option satisfies important needs. Avoid asking users to approve every ordinary comparison decision.

Acceptance: comparable products do not automatically produce another question; a genuine comfort-versus-noise conflict can produce a focused question; no product above a hard budget is presented as eligible until the user changes the limit. Exploratory options above that limit are labelled clearly.

### CUI05 Make corrections visibly consequential

Support replies such as Actually, comfort matters more or Keep the product but find another seller. On correction, acknowledge the changed criterion, update the compact summary, recompute the scenario outcome and show a short explanation of what changed. Preserve unaffected needs and comparison work where relevant.

Target a change explanation of no more than 40 words before the updated result. Do not require the user to reread a complete transcript. Superseded recommendations must be labelled as previous or replaced. If a selected offer no longer fits, explicitly require a fresh selection.

Acceptance: changing noise cancellation to comfort changes the seeded winner; a deliberately unchanged-winner scenario explains why; switching seller preserves the product variant; old reasons and concerns are not silently carried into the new result.

### CUI06 Explain merchant concerns through their consequence

A material concern must identify the observation, explain its practical consequence and offer a recommended next step. For example: This seller requests gift cards outside checkout. I recommend another offer for SGD20 more. Keep the underlying source available without making it compulsory to open.

Do not treat all uncertainty as a warning requiring interruption. Smaller review history can be disclosed neutrally; unusual payment demands merit prominent caution. Clean small merchants remain viable alternatives. A seller warning must not make the product itself appear unsuitable unless the evidence concerns the product.

Acceptance: material concerns are visible before selection; unfamiliarity alone does not block selection; a benign discount is not labelled fraudulent; hidden fixture labels never enter participant-facing explanations.

### CUI07 Support a concise final decision

The primary action is Select this offer. After selection, show a brief recap of the product, seller, price, fit and any remaining material concern. The user can revise or finish. Selection does not place a real order. Any existing checkout is secondary and visibly simulated.

Acceptance: users can finish the normal task without opening evidence details or changing settings; payment credentials are never requested; unresolved material concerns remain visible; invalidated offers cannot be silently selected from an earlier recommendation.

## 6 Screen structure and information hierarchy

Keep the conversation and its current recommendation together. On desktop, an adjacent comparison area may expand when requested. On mobile, place details immediately after the relevant recommendation. A permanent multi-product grid or separate oversight dashboard is not required.

| Surface | Always visible when relevant | Available on request |
| --- | --- | --- |
| Needs summary | Decisive need, spending limit and priority | Complete editor and assumption provenance |
| Conversation | Useful question, answer or concise update | Earlier turns |
| Recommendation | Product, seller, price and explicit personalised trace | Full product and seller comparison |
| Merchant concern | Material observation, consequence and next step | Original record and supporting excerpts |
| Comparison activity | Short, accurate status while work runs | Detailed record of completed checks |
| Selection | Selected offer and unresolved material issue | Secondary simulated checkout |

Provide one primary action per result, with Change priorities and View comparison and sources as secondary routes. Controls must work with keyboard and touch, disclosures must be labelled, and updates must be announced without repeatedly reading the full conversation. Evidence must remain available without hover.

## 7 Reference scenario

All names, prices, ratings and product differences in this scenario are fictional design fixtures. Stronger noise cancellation is an authored specification for demonstrating a decision rule, not a measured performance claim.

### Initial purchase needs

User: I need headphones for my daily train commute, under SGD300. Noise cancellation matters more than weight.

Beany proceeds without another question. The compact summary shows the commute, confirmed SGD300 ceiling and stated priority. It compares two models: Echo Quiet at a main offer of SGD289, weight 290g and stronger listed noise cancellation; Luma Air at SGD279, weight 245g and moderate listed noise cancellation.

For Echo Quiet, Northline Audio offers SGD289, 30-day returns and 2,140 seller reviews averaging 4.7. Everyday Sound offers SGD269, 14-day returns and 84 seller reviews averaging 4.5. It is a clean small merchant. SoundRush Deals offers SGD209, 12 seller reviews averaging 4.8, no supplied return policy and a request for gift-card payment outside checkout.

### Default recommendation

Recommended for your train commute: Echo Quiet, SGD289 from Northline Audio.

You prioritised noise cancellation within SGD300. Both models fit your budget; Echo Quiet has stronger listed noise cancellation than Luma Air. I favoured Northline's 30-day returns over the cheaper seller's 14 days, costing SGD20 more. That return preference is my tie-breaker. The compromise is 45g extra weight; comfort is not personally verified.

Controls: Select this offer; Change priorities; View comparison and sources.

The final explanation is intentionally short. The clean small merchant remains available if the user prefers saving SGD20. The suspicious offer does not have to dominate the initial recommendation; its material concern becomes visible whenever that offer is presented or inspected.

### Personalisation through correction

User: Actually, comfort matters more.

Beany: Updated: comfort now comes first. Luma Air's lighter weight and cushioned-pad specification make it the closer fit, while Echo Quiet still offers stronger noise cancellation. Comfort remains subjective.

The new recommendation uses the appropriate Luma Air offer and its own source records. It does not reuse Echo Quiet's seller prices or product review counts. The needs summary, comparison reason and current selection state all update together.

### Boundary paths

With a new hard budget of SGD180, the selected scenario has no eligible offer. Beany explains the conflict and offers to change the budget or explore a different product; it does not quietly raise the limit. If the user asks for the cheapest Echo Quiet offer, Beany surfaces the gift-card concern and proposes the clean SGD269 alternative. The known smaller merchant is not rejected merely because it has fewer reviews.

## 8 Mocking and explanation contract

The team may implement the complete experience through a small scenario-driven state manager. A real LLM is optional for wording or intent interpretation. Neither a new database nor live merchant detection is required to evaluate this design.

Use one shared structured scenario state for the needs summary, recommendation, trace and evidence. Each decision record should contain user priorities and assumptions, considered product and offer IDs, the chosen product and seller, the decisive comparison, seller tie-breakers, the main compromise, material concerns, evidence references and a needs revision. Explanations are rendered from that record; a model must not invent missing comparisons or checks.

The minimum scenario branches are complete request, ambiguous request, explicit browse, priority correction that changes the winner, correction that preserves the winner, same-product seller change, no eligible match, risky cheapest offer and unavailable evidence. Both demonstration categories should reuse the same interaction pattern.

The visible counts and activity states must agree with the scenario data. A preference correction must select the appropriate branch; replaying an identical script regardless of input fails the requirement. An unsupported input must prompt a useful clarification rather than silently mapping to an unrelated result.

Clearly label fictional data and simulated transactions. Study participants should understand that the prototype represents an interaction concept. Results can speak to comprehension, perceived credibility, effort and choice within the simulation; they cannot establish real merchant legitimacy or the factual reliability of a production agent.


## 9 Evaluation plan

### Research questions

RQ1: Does Beany reduce the time and perceived effort needed to reach a suitable choice compared with a comparison GUI?

RQ2: Can users explain how their own priorities influenced the recommendation and recognise the main product tradeoff and merchant concern?

RQ3: Does the explicit decision trace support justified confidence and effective correction without requiring users to inspect all supporting evidence?

### Conditions

Condition A is a usable comparison GUI with filters and the same raw product, offer, review and return information. Condition B is the full Beany CUI with selective clarification, personalised reasoning, decision trace, correction and optional evidence. Give both conditions the same task goals, source records and offer availability. Do not make the baseline artificially difficult or hide its raw information.

This comparison evaluates the complete experience. It does not isolate conversation, personalisation or the decision trace as independent causes. A later explanation-on versus explanation-off comparison within the same CUI could isolate the trace more directly, but is outside the required final study plan.

Use two matched category tasks and counterbalance condition and category order. A proposed course-feasible target is 16 to 24 adults with online-shopping experience; this is not a statistical power claim. Use fresh linked sessions and pseudonymous participant IDs. Obtain professor feedback before recruitment. No participant results are required for the final presentation.

### Measures and interpretation

| Measure | Collection method | Interpretation |
| --- | --- | --- |
| Convenience | Time to final choice, perceived effort, clarification turns and required actions | Reduced work must not come at the expense of suitable choices |
| Personalisation comprehension | Short post-task explanation of the decisive user need and alternative | Checks that the rationale was understood, not merely displayed |
| Decision quality | Fit with hard constraints and priorities; recognition of visible concerns | Uses participant-accessible evidence rather than hidden labels |
| Trust calibration | Confidence ratings alongside comprehension and response to uncertainty | High confidence with missed material concerns is an adverse outcome |
| Correction and recovery | Whether a correction updates the brief, choice and explanation coherently | Tests the value of conversational negotiation |
| Verification burden | Evidence openings, time in detail and whether detail was necessary | Fewer openings can be positive when understanding remains adequate |

Pair a brief survey after each task with a comparative interview. Surveys support consistent ratings of effort, understanding and control; interviews explain what made the reasoning credible, confusing or burdensome. Log only what is needed to interpret the task and manage free-text data appropriately.

Report paired differences, distributions and uncertainty, with order and category limitations. Predefine the scoring rules before data collection. Concealed malicious fixtures with no observable distinguishing evidence cannot count as avoidable participant errors. Do not equate accepting the agent's choice, rejecting a small seller or opening more details with success.

The main hypothesis is improved convenience with preserved or improved decision comprehension and quality. If participants save time but misunderstand important concerns, or understand everything only by rereading every source, the design has not resolved the central tradeoff. Pilot and red-team work belong to Assignment 2, not the final-presentation agenda.

## 10 Delivery priorities and acceptance

### Required before final recording

First implement the complete headphones journey with a consistent mock state and concise decision trace. Add correction, negotiation and the boundary paths before expanding to the second category. Reuse the same interaction components for running shoes. Prepare the controlled dataset and the study design, then record the working experience.

The following are mandatory in this new direction: explicit personalised rationale, comparison with an alternative, seller-choice explanation, visible compromise, user correction and a trace grounded in the represented checks. A generic recommendation banner without this content is insufficient. Full live streaming, extensive source panels and sophisticated ranking infrastructure are optional.

### Acceptance checklist

- A specific request reaches a recommendation without a compulsory questionnaire or brief confirmation.
- The default result identifies the user's decisive priority, the relevant alternative, the seller rationale and the main compromise within the proposed writing budget.
- Evidence opens are optional for the normal completion path; material concerns remain visible without opening details.
- Every completed check and factual reason maps to current scenario data or an actual operation.
- Priority changes update the brief, recommendation and explanation together; an unchanged recommendation receives a meaningful reason.
- Hard limits remain in force, and same-product merchant changes preserve the product variant.
- A clean small merchant and a benign discount remain viable; concrete risky behaviour receives an actionable explanation.
- Missing evidence and provider failures produce clear uncertainty rather than fictional completed checks.
- Both categories support the same core interactions on desktop and mobile with keyboard access.
- Selection is explicit and creates no real payment or order. The submitted system can reproduce the recorded interactions.
- The presentation contains the study plan and rationale, with no fabricated results.

### Work required before recruitment

Implement and validate the fair GUI baseline, condition assignment, linked participant IDs, task start and end markers, choice recording and minimal exports. Freeze scenario, explanation, model and configuration versions. These are study-readiness requirements, not additional conditions for presenting the plan.

## 11 Existing code and implementation boundaries

Reuse the current Next.js conversation page, Brief component, MerchantDetails component and active `frontend/src/lib/beany.ts` contracts where useful. Simplify the primary experience around conversation and its current recommendation. Existing backend events and fixtures can supply the decision record, or a local fixture adapter can supply it for the prototype. Avoid changing the underlying control architecture merely to stage the interaction.

Keep mock fixtures outside presentational components so the visible rationale, comparisons and source details share the same values. Use typed state and small, explicit transition functions. A real rendering pattern is `Fact(value=change.value, source=change.source, hard=change.hard)` in the existing Python runtime; preserve that clarity when adding scenario and explanation fields. Do not mix the older frontend contracts with the active runtime types.

Verification should cover user-visible state transitions and source consistency. Existing backend tests do not prove that the new CUI communicates clearly. Where applicable, run `.venv/bin/python -m pytest -q -p no:cacheprovider` from `backend`, then `npm run typecheck`, `npm run build` and `npm run test:e2e` from `frontend`. Browser checks should exercise correction, optional disclosures, stale recommendations, no-match and mobile behaviour. Pin test source mode and credentials so offline checks cannot call paid services.

Development commands remain `.venv/bin/python -m uvicorn app.main:app --reload --port 8000` from `backend`, and `npm run dev` from `frontend`. Tests live in the existing `backend/tests` and `frontend/tests` directories; product documentation and curated scenario records belong under `docs` and the existing fixture directories.

Always keep explanations grounded, assumptions visible, fictional data labelled and final selection under user control. Never fabricate completed checks, request payment credentials, expose participant data, or weaken hard constraints for a demonstration. Obtain a separate scope decision before adding real transactions, live-source dependencies or new categories.

## 12 Presentation and assumptions to validate

Allocate the 15 minutes to the problem and trust-convenience tension, 2 minutes; the revised CUI and why it changed, 2 minutes; a working demo showing explicit reasoning and a consequential correction, 5 minutes; the A/B study plan and rationale, 4 minutes; and limits and conclusion, 2 minutes. Validate claims about the mid-project version against the actual presentation materials.

The demo should make the contribution visible: start with a user goal, show the personalised decision trace, change a priority, show the changed recommendation and reason, then inspect one merchant concern only when it matters. The second category demonstrates reuse of the interaction pattern. End at an informed user selection; simulated checkout is optional.

Assumptions to validate are that a short decision trace is read and understood, comparative reasons feel more useful than generic benefits, users can correct priorities without extra research, and optional detail offers sufficient reassurance without becoming compulsory. Whether those assumptions hold is an evaluation question, not a claim established by a polished prototype.

