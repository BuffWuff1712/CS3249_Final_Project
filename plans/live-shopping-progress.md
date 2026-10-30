# Actual shopping progress

Implemented request-scoped NDJSON activity streaming for chat, compare, choosing an offer, same-model seller changes and general alternatives. Existing atomic revision and fingerprint checks still own all state changes; progress does not grant approval. No model reasoning or raw provider responses are streamed.

The chat shows actual request reading, search, product/seller inspection, policy checking and answer preparation as they run. Checks finish only after the corresponding operation returns. Saved summaries collapse above the answer, use product/seller names, and translate technical approval codes into ordinary labels. Previously saved technical activity is rendered with the same readable labels without rewriting sessions.

Reset/unmount abort the reader and ignore old events. A server operation already running may finish committing its original session, as with the previous non-streaming requests; reset creates a different session. Interrupted connections require state reload before another mutation, preventing unsafe blind retry. Reduced motion disables the activity spinner animation.

Verification: 635 backend tests passed, 4 pre-existing skips. Three new backend tests prove an activity packet is available before the model returns/transaction commits, error rollback, and stale-revision rejection. Twelve focused desktop/mobile browser cases passed, including progress before result, readable completed evidence, reset/late stream protection, failed requests, restoration and explicit simulated checkout. Browser tests gate the first real backend activity line to inspect the intermediate state; no fake application progress steps are added. An initial duplicate-text test selector was corrected before the successful rerun. TypeScript and production build passed. Screenshots are under plans/verification/live-shopping-progress/.

All automated verification used local catalogue, mock LLM and blank provider keys. No Browser Use or paid model calls were made for this change. The user-facing preview was restarted with its previously configured SoCLaaS model and local catalogue, preserving its database. No push is authorized.
