# Clarification and stopping a request

Before a conversational product search, Beany checks product type, budget and features.
Missing information is requested together. Broad words such as "shoes" must not silently
confirm running shoes. The interpreter reports grounded clarification answers separately
from shopping preferences; Python tracks which questions were asked for this item.
Partial replies keep only the remaining questions open. After a question, explicit
uncertainty lets that field remain unconstrained. An explicit "no feature preference"
or "no budget" also counts when supplied upfront. Silence and greetings do not count.
New tasks reset this tracking while retaining cart contents and permissions. No unknown
answer removes an existing hard constraint: changing a confirmed value still requires
the usual grounded preference edit. Catalogue coverage remains limited; broad suggestions
must be labelled as assumptions, not user-confirmed product types.

An answer flag does not substitute for an extracted preference. The interpreter gets
at most one corrective model call if a provided field was omitted or confirmed evidence
is not a literal quote. Python still validates the retry. Short uncertainty replies to
pending questions resume the shopping flow even if labelled small talk by the model.
Uncertainty never deletes a previously supplied feature. Legacy sessions with a missing
category are asked to supply it again rather than displaying a promise without a search.

The workspace shows one current public activity, elapsed seconds/minutes, and an arrow
to expand prior activities. These are operation updates, not private model reasoning.

Stop targets the current stream request ID, independently of the database lock. It
signals cancellation, aborts the browser stream and reloads authoritative saved state.
Uncommitted work is discarded; cancellation is checked before saving. A completed commit
cannot be undone, so the reload also handles a request finishing just before Stop.
The cancelled shopping workflow cannot continue selecting tools or save a late result.
An already-issued model HTTP request can continue remotely until completion/timeout;
its result is discarded. Known Browser Use runs receive best-effort cancellation when
the polling worker observes cancellation. External provider costs cannot be guaranteed
to stop immediately. Disconnects also signal cancellation. The single-worker convention
still applies because running request controls are held in process memory.

Validation uses offline backend tests plus desktop/mobile Playwright tests with isolated
mock servers. Live model interpretation of ambiguous language remains model-dependent.
