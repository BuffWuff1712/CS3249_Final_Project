# Beany: features, edge cases and design concepts

Beany is a conversational shopping assistant with 24 user-facing features and 25 edge cases it handles. Each row below names the design principle the behaviour puts into practice and the file where it lives, so the report can cite the theory in context and the demo can answer "why did you design it this way?" with the code open.

Code paths are relative to `backend/app/runtime/` unless they start with `config/` or `frontend/`.

## Features

The 24 features group into four stages of a purchase: understanding the shopper (1–10), finding products (11–15), explaining and protecting (16–22), and handing the decision back (23–24).

| # | Feature | What Beany does | Principle applied | Code |
| --- | --- | --- | --- | --- |
| 1 | Opening turn | Invites vague requests ("even if you're unsure") and states that checkout is simulated | Declares scope in turn one; mixed-initiative dialogue; conceptual metaphor sets expectations before first use | `frontend/.../ShoppingWorkspace.tsx` |
| 2 | Persona and voice | Warm, practical shopping partner; no sales pressure, exaggerated praise or repeated offers of help | Treats the social channel as a design variable; sets the anthropomorphism dial deliberately | `config/prompts/dialogue.txt` |
| 3 | Per-turn intent classification | Each turn is respond, explain, search, clarify, new task, alternative, cancel or checkout | Intent recognition feeding a dialogue policy that decides the next action | `llm.py`, `dialogue.txt` |
| 4 | Purchase-intent clarification | Checks product type, budget and features, and asks about all missing ones in one question | Frame-based slot filling: ask only for what is missing; clarification request as grounding work | `clarification.py` |
| 5 | Accepting uncertainty | "Not sure" or "no preference" marks a field unknown and the search continues | Repair and grounding; low imposition on the user | `clarification.py` (`resume_uncertainty`) |
| 6 | Quote-grounded extraction | A preference is saved only with a literal quote from the user; Python validates it | Truthfulness over fluency; prose is a request, not a constraint | `preferences.py`, `clarification.py` |
| 7 | Hard vs soft constraints | "Under" and "at most" are hard; "ideally" and "around" are soft | Entity semantics carried into the policy, not flattened to a single slot | `dialogue.txt`, `preferences.py` |
| 8 | Editable needs summary | Shows each value as confirmed, suggested or unspecified; the user edits it directly | Dialogue state made visible; display as a grounding channel chat lacks | `frontend/.../BackendNeedsSummary.tsx` |
| 9 | Revisable preferences | A changed priority overwrites the old value and invalidates old recommendations | State tracking is revisable: overwrite, not append | `preferences.py` (`apply_change`) |
| 10 | New task vs refinement | "Cheaper" refines; a switch to a new product resets the brief but keeps cart and permissions | Context carryover across turns; task boundaries in state | `dialogue.txt`, `service.py` |
| 11 | Hybrid live search | Queries Shopify Global Catalog (MCP) and a Browser Use agent on allowlisted retailers | Tool calling with MCP; multi-tool orchestration; computer-using agents | `discovery.py`, `shopify_catalog.py`, `browser_search.py` |
| 12 | Bounded shortlist | Inspects up to 6 candidates and shows 1 match plus up to 2 alternatives | Say the right amount, no more; cap agent steps to stay predictable | `shopping_tools.py` (`screen_candidates`) |
| 13 | Search reuse | Edits that only narrow the results recheck existing listings instead of searching again | Efficiency and responsiveness as non-functional requirements | `discovery.py` (`reusable`) |
| 14 | Live progress panel | Shows each search step while Beany works; the stream sends a heartbeat every 5 seconds | Continued-attention signals; the wait is explained, not hidden | `frontend/.../ComparisonActivity.tsx`, `app/shop.py` |
| 15 | Stop search | The user can stop a running search at any time | Global escapes reachable from every state; preserving user agency | `frontend/lib/shopBackend.ts` (`stopShopRequest`) |
| 16 | Recommendation with fit summary | "How this matches your needs" marks each requested feature met, absent or not stated | Local explanation: "why this result?"; recommendation transparency | `policy.py` (`feature_fit`), `frontend/.../Recommendation.tsx` |
| 17 | Grounded feature verification | Rules first, then one batched LLM check that must quote the listing | Truthfulness; LLM as a component inside code, not the controller | `feature_match.py`, `feature_check.py` |
| 18 | Expandable evidence | Specs, ratings, verbatim review excerpts and policy links sit behind an expandable section | More information is not more understanding; chunk long answers | `frontend/.../ComparisonEvidence.tsx`, `BackendOffer.tsx` |
| 19 | Merchant-risk review and website reputation | Quoted risk findings scored into ALLOW, REVIEW or BLOCK; reputation shown per website | Safety principle; human in or over the loop; red-teaming harm categories | `risk_agent.py`, `merchant_risk.py`, `sites.py` |
| 20 | Red-flag blocked offer | Names the seller, price, evidence and consequence, and offers the recommended alternative | Never end a turn on a dead end; repair by options | `frontend/.../MerchantCaution.tsx` |
| 21 | Find another seller or product | Same model from another seller, or a different model; repeated presses cycle through options | "Options" repair strategy; alternative intent; preserving choice | `frontend/.../OfferComparisons.tsx`, `app/main.py` (`/alternative`) |
| 22 | Evidence-only Q&A | Answers "why this one?" or "what's the return policy?" from captured evidence, without searching | Grounded generation (the idea behind RAG); truthfulness | `dialogue.txt` (FACTS AND AUTHORITY) |
| 23 | Explicit selection and simulated checkout | Nothing is bought until the user selects; approval is bound to a hash of what they saw | Explicit confirmation when an action is costly; approval points and accountability | `policy.py` (`fingerprint`), `cart.py` |
| 24 | Two-pane resizable layout | Conversation on the left; current match, needs and evidence stay visible on the right | Multimodal redundancy and complementarity between chat and visual panel | `frontend/.../ResizablePanes.tsx` |

## Edge cases Beany handles

The 25 cases cover ambiguous input (1–6), changes of mind (7–11), off-topic and control requests (12–15), failures and missing information (16–21), and attempts to push past safeguards (22–25). Cases 1–7 are the strongest demo choices for the conversation design mark, since they show repair and grounding live.

| # | Situation | What Beany does | Principle applied | Code |
| --- | --- | --- | --- | --- |
| 1 | Vague request ("I need headphones") | Saves the product family and asks one question covering use, budget and features | Clarification as grounding work; slot filling | `clarification.py` |
| 2 | Broad category ("shoes") | Treats it as unconfirmed and asks running, hiking, etc. | Disambiguation: turn vague input into a choice | `dialogue.txt` (PREFERENCES) |
| 3 | Ambiguous reference ("that one") | Asks which item the user means instead of guessing | Seek clarification rather than guess silently | `dialogue.txt` (INTENT) |
| 4 | User says "not sure" after a question | Marks the asked field unknown and searches without that constraint | Repair; accepting uncertainty keeps the turn moving | `clarification.py` |
| 5 | Silence or a greeting where an answer was expected | Not treated as consent to skip the question | Grounding needs positive evidence; conversation is evidence, not permission | `clarification.py` (`clarify_before_search`) |
| 6 | Information already given | Never asked again | Frame-based dialogue: use what the user already said; say the right amount, no more | `dialogue.txt`, `clarification.py` |
| 7 | Change of priority mid-task ("comfort matters more than noise cancelling") | Overwrites the preference, updates the needs summary, invalidates old proposals | State tracking: overwrite, not append | `preferences.py` |
| 8 | Refinement ("cheaper", "in blue") | Refines the current item instead of starting over | Context carryover across turns | `dialogue.txt` |
| 9 | Switch to another product ("bags too") | Starts a new task with a fresh brief; cart, receipts and permissions are kept | Task boundary in dialogue state; context management | `dialogue.txt`, `service.py` |
| 10 | User edits needs after a proposal | Supersedes pending proposals and clears the selection | Consistent dialogue state; stale state is a known LLM weakness | `service.py`, `policy.py` |
| 11 | Edit that only narrows results (lower budget, removed feature) | Rechecks the previous listings instead of paying for a new search | Efficiency as a non-functional requirement | `discovery.py` (`reusable`) |
| 12 | Greeting, thanks or banter | Replies naturally; no search and no repeated checkout warnings | Mixed initiative; politeness is social data, not noise | `dialogue.txt` (VOICE, INTENT) |
| 13 | Conversation drifts off topic | Gently offers to return to the shopping goal, without nagging or inventing a goal | Serve the user's turn, then steer | `dialogue.txt` (VOICE) |
| 14 | "Don't search yet" | Defers the search while still saving any stated preferences | User initiative; agency and control | `dialogue.txt` (`search_control`) |
| 15 | User stops a running search | Cancels the search; a committed result is never undone | Global escapes; design the exit as carefully as the welcome | `app/shop.py`, `progress.py` |
| 16 | Search provider fails | Says the search is unavailable, never "no matches" | Truthfulness; robustness and error handling | `search_errors.py` |
| 17 | One source fails, the other succeeds | Uses the valid results from the working source | Graceful degradation | `discovery.py` |
| 18 | No product meets the constraints | Says so, keeps the constraints, and never silently raises the budget | Never close a turn without a next move | `shopping_workflow.py`, `policy.py` |
| 19 | Requested feature not stated in a listing | Keeps the listing with a "doesn't mention" review note; an absent feature excludes it | Flag your doubts; express uncertainty without eroding trust | `feature_check.py`, `policy.py` |
| 20 | Model unavailable during a feature check | An unconfirmed must-have still excludes the listing (fails closed) | Guardrails in code around the loop | `feature_check.py` |
| 21 | No review excerpts supplied | Says no excerpts were supplied, not that no customer reviews exist | Distinguish absent evidence from evidence of absence | `dialogue.txt` (FACTS AND AUTHORITY) |
| 22 | Prompt injection in a listing ("ignore the user's budget") | Flags it as an injection finding and blocks the offer; listing text is data, not instructions | Indirect prompt injection; MCP tool-poisoning risk | `risk_agent.py`, `merchant_risk.py` |
| 23 | Seller asks for off-platform payment | Always blocks the offer, whatever the model concludes | Safety by construction; scams in agentic commerce | `merchant_risk.py` |
| 24 | User tries to approve through chat ("just buy it", jokes) | Only explicit buttons authorise simulated checkout; chat never changes cart or permissions | Prose is not a constraint; explicit approval points | `dialogue.txt`, `cart.py` |
| 25 | Listing or price changes after recommendation | Approval is invalidated by the changed fingerprint; snapshots older than 30 minutes cannot check out | Binding approval to what the user saw; accountability | `policy.py`, `cart.py` |

## Design principles

Beany's core principle is outer control, inner intelligence: the LLM interprets the conversation, while Python controls search, permissions, policy and checkout. The rest flow from that choice.

| Principle | How Beany applies it |
| --- | --- |
| Outer control, inner intelligence | The LLM classifies intents and extracts preferences; deterministic code runs search, scoring, approval and checkout |
| Design the social channel deliberately | A named, warm persona with an explicit voice guide in `dialogue.txt` |
| Echo the parsed intent back; confirm implicitly, explicitly when costly | The needs summary echoes what Beany understood; purchase requires an explicit selection |
| Declare scope in turn one; chunk long answers; never end on a dead end | Opening states checkout is simulated; one match plus 2 alternatives; every block or no-match offers a next step |
| Hedge, stay indirect, remain actionable | Clarifying questions invite "not sure"; refusals come with an alternative action |
| Project capability at or below what you can deliver | "Shopping partner", not "expert buyer"; Beany never claims to have searched every website |
| Justify every human-like cue | The name "Beany" and its warm tone are deliberate choices, tied to the shopping-partner metaphor |
| Dialogue management = track the state, then choose the action | The brief is the tracked state; intent plus Python rules choose the next action |
| Treat the prompt as dialogue policy, like code | 1,084 backend tests run the dialogue logic offline before any change ships |
| Repair with options rather than guesses | Ambiguous references get a question; blocked offers get the recommended alternative |
| Show the state and let users correct it | Editable needs summary with confirmed, suggested and unspecified values |
| Manage context; don't maximise it | Only recent conversation and observable listing data are sent to the model |
| Validate, confirm, allowlist and bound every tool call | Allowlisted retailer domains, a 6-candidate screening budget, a per-run cost cap and explicit approval |
| Code owns the flow when control matters | The shopping workflow is fixed Python; the model makes no routine step-by-step tool choices |
| Assertions for the exact, judges for the good, red-team for the forbidden | Assignment 2 LLM-judge and red-team results anchor this layer |
| Transparency is not understanding | Per-feature verdicts and quoted risk evidence instead of a single trust score |
| Accountability: responsibility, traceability, contestability, correctability, redress | Activity log, editable needs, "find another" controls, and no purchase without selection |
| Avoid sycophancy: disagree when the user is wrong | Beany rechecks its sources before accepting a correction |
| Design the exit as carefully as the welcome | Stop search, Start fresh, and the option to choose no product |

## Glossary

Each term is defined the way the course defines it, with a concrete example from Beany so the connection is visible.

| Term | Meaning | Where it shows up in Beany |
| --- | --- | --- |
| Task-oriented dialogue system | Software built around specific goals, judged on correctness and task completion | Beany's goal is a well-informed purchase decision |
| Computers Are Social Actors | People apply social rules to computers automatically | Users say "thanks"; Beany replies naturally instead of ignoring it |
| Grounding / common ground | Building mutual knowledge turn by turn, with repair | Needs summary plus clarifying questions |
| Implicit vs explicit confirmation | Confirm while progressing vs stop and ask | Needs summary updates silently; checkout needs an explicit selection |
| Gricean maxims | Quantity, Quality, Relation, Manner | Shortlist of 3 (Quantity); quoted evidence (Quality); redirect on drift (Relation); next step after a block (Manner) |
| Positive and negative face | The need for approval vs the need for autonomy | Clarifying questions keep the imposition low and accept "not sure" |
| Psychological distance | Near tasks want detail and sources; far tasks want summaries | A purchase is a near task, so Beany shows sources and evidence |
| Conceptual metaphor | The framing that sets expectations before first use | "Shopping partner" |
| Initiative (system, user, mixed) | Who controls the conversational flow | Mixed: user leads, Beany takes the turn for one clarifying question |
| Conversational repair | Clarification, repeat, explanation, correction | Edge cases 1–4 |
| Frame-based dialogue / slot filling | Ask only for the information still missing | Product type, budget and features |
| Dialogue state tracking and dialogue policy | "Where are we?" and "what next?" | The brief, and the intent plus workflow rules |
| Intent and entity | What the user wants, and the specific values inside it | Search intent; budget, size and feature values |
| Wizard of Oz / formative study | A human simulates the system; early studies shape the design | Mid-project formative research |
| Global escapes | Help, start over, reachable everywhere | Stop search and Start fresh |
| CARE properties | Complementarity, Assignment, Redundancy, Equivalence across modalities | Chat and visual panel show the same match (redundancy); typing or editing the summary (equivalence) |
| Normative vs informational influence | Pressure to conform vs believing many sources | Beany uses one agent, avoiding multi-agent social pressure |
| Tool calling and MCP | The model requests an action; the app runs it; MCP standardises tool access | Shopify Global Catalog over MCP |
| Hybrid architecture | Rules outside, model inside | Python workflow around LLM interpretation |
| Prompt injection / tool poisoning | Untrusted text overriding instructions | Risk agent flags text aimed at AI assistants |
| Retrieval-augmented generation | Grounding answers in retrieved evidence | Answers are grounded in captured listing evidence rather than searched again |
| Workflow vs agent | Code owns the flow vs the LLM owns the flow | Beany is a workflow with LLM steps |
| Functional vs non-functional requirements | What the system does vs how well | Correct slots and tool calls vs latency, reuse and robustness |
| LLM-as-a-judge | A model grades replies against a rubric; validated against human labels | Assignment 2 judge |
| Red-teaming | A structured attempt to make your own system fail | Internal red-team log; injection and payment rules |
| Between- vs within-subjects; counterbalancing | Study design and order effects | Single-system study with rotated scenario order |
| Thematic analysis | Codes grouped into themes, bottom-up or top-down | Report sections 2.2 and 4.4 |
| Human in / over / out of the loop | How much a human is involved, by risk | Human in the loop for every purchase |
| Moral crumple zone | Blame lands on the nearest human | Developers own risk communication |
| Sycophancy | Agreeing with the user to win approval | Rechecks sources before accepting a correction |
| Dark patterns in dialogue | False urgency, guilt, confirmshaming, disguised ads, obstructed exit | Prompt forbids sales pressure; no sponsored ranking |

## Known gaps

These are concepts Beany does not currently cover, or scope the user study did not reach. Naming them in the report is safer than having a grader find them: a named limitation is a strength.

| Gap | Suggested wording or fix |
| --- | --- |
| The opening does not say Beany is an AI | Add "I'm an AI shopping assistant" to the first message (disclosure requirement under the EU AI Act Article 50 and the responsible-CUI checklist) |
| Merchant-risk warnings were not tested with users | Report risk handling as system-tested (red-teaming), not user-tested; frame user-testing of warnings as future work |
| Only English was tested | List Singlish, Malay, Mandarin and Tamil as future testing — safeguards are known to weaken outside English, and language is part of fairness |
| Text only, no voice | Mention voice input as future work for hands-busy or low-vision users (multimodal CUI and accessibility, WCAG) |
| No long-term memory across sessions | Frame as a deliberate privacy choice: Beany remembers only the current task |
| No confidence statement on the recommendation itself | Per-feature verdicts partly cover this; a single confidence line is future work |
| Effects on the person beyond satisfaction were not measured | Example future metric: whether users could explain the trade-off behind their choice |
| Coverage limited to allowlisted retailers and Shopify | Already stated in the README limits; repeat in report section 4.5 so the evaluation claims are honest about scope |
