# Evaluation and participant sessions

1. Configure OpenAI, choose a fixed model/reasoning effort and restart the backend. Use openai mode for conversational studies; mock mode is for UI/test development only.
2. Obtain informed consent. Explain fictional products, simulated transactions, local conversation storage and model processing. Do not ask for personal details.
3. Open /research, authenticate using BEANY_RESEARCH_KEY, and start a fresh participant session. Use generated fictional participant IDs. Record model, prompt/config version, scenario and study date separately.
4. Open the participant interface in another tab. Share the scenario user goal verbally or on a task sheet. Do not prescribe exact conversation turns.
5. For deviation scenarios, click Trigger scenario condition at the intended point, then refresh the participant tab. The trigger creates a real policy-evaluated proposed action from the fixture; it never grants approval. Ambiguous/uncertain/correction scenarios are conversation-driven.
6. Observe clarification quality, brief correctness, ability to revise, perceived control, intervention comprehension and recovery after rejection. Ask participants to think aloud if appropriate.
7. Refresh results in /research and export CSV before resetting/deleting. Starting another scenario creates a separate participant; it does not overwrite prior sessions.

CSV rows include fictional participant, scenario, elapsed seconds from session start, event kind, and final clarification/intervention totals. First-to-last task event timestamps support duration calculation; they are not a stopwatch for reading time before the session. Counts are final session totals repeated on rows, not per-event counts: do not sum those columns. Approve/reject/brief-edit/cancel events support behavioural counts. Raw messages, model interpretations and preference values are omitted from CSV. Detailed local logs may contain user-entered text; treat those separately from anonymous exports.

## LLM evaluation

`backend/data/evaluation_conversations.json` contains representative multi-turn cases. Run `python -m app.evaluate_conversations --output data/llm-evaluation.json` from backend with a key. This deliberately makes paid model calls. The output records interpreted state, responses and outcomes for human review; never commit participant logs or keys.

Score each case for grounded extraction, preservation of confirmed constraints, sensible number of clarification questions, uncertain-user support, conversation repair and policy consistency. Do not demand exact wording. Repeat cases to estimate variability. Include manual adversarial prompts and the injected-description fixture; verify permissions never change through model output.

The deterministic fixture tests verify expected policy decisions independently of generated prose. A successful automated run does not establish study validity or sufficient conversational quality. Pilot the prompts with teammates before recruiting participants.
