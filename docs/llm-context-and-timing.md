# Conversation context and model timing

Each interpretation call receives the dialogue instructions, current brief, permissions,
proposal/selection evidence, cart context, and the last 20 complete messages. Message IDs
and timestamps are omitted from model history, but the persisted session is unchanged.
Older conversation is not summarized: references outside the window may require clarification.
Confirmed constraints remain in the brief even when the original message leaves the window.

The dialogue prompt is condensed; JSON/text mode sends the output schema once in the
instructions. Schema mode also supplies the schema through the provider's structured-output
parameter. Evidence is retained so explanation questions can still use supplied facts.
No model calls were added for summarization, and tool selection remains model-driven.

Set `OPENAI_TIMEOUT_SECONDS=200` in backend/.env and restart the backend to configure
network-operation timeouts (10–600 seconds). The default preserves the existing 200-second
setting. This is not a total shopping-turn deadline; a turn can use several sequential calls.
Automatic retries remain disabled, and model/provider settings are not changed.

The backend's Uvicorn INFO log emits paired `llm_call_start` and `llm_call_end` records.
Match their `id` values. `stage` is the output schema name, such as Interpretation,
ShoppingStep, or OutcomeExplanation. End records show elapsed seconds, success/error,
and exception class. Start records include API mode, timeout, and input character count
(not token count). Prompts, responses, user text, credentials and upstream error bodies
are not logged. Configuration failures happen before a model call and are not timed.

Offline tests cover context preservation, transport configuration, schema duplication,
and safe timing logs on success and timeout. They cannot establish live Qwen latency or
prompt quality. Compare representative live conversations before claiming a speedup.
