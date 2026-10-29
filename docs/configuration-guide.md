# Configuration guide: NUS gateway and merchant-risk studies

## NUS SoCLaaS

Only `backend/app/runtime/gateway.py` constructs the official OpenAI SDK client. Every extraction and outcome explanation uses that module. Configure `backend/.env` (ignored by Git):

```dotenv
OPENAI_API_KEY=your-NUS-key
OPENAI_BASE_URL=https://soclaas-api.comp.nus.edu.sg/v1
OPENAI_MODEL=qwen3.6:35b
OPENAI_API_MODE=responses
OPENAI_STRUCTURED_MODE=schema
OPENAI_REASONING_EFFORT=
BEANY_LLM_MODE=openai
```

The model above was explicitly selected by the project owner. Application code has no default model or provider URL. Model availability is account-specific and can change. `OPENAI_API_MODE=chat` explicitly selects the Chat Completions adapter. In chat mode, `OPENAI_STRUCTURED_MODE=schema|json|text` controls schema, JSON-object, or prompt-only JSON generation. All modes validate the result against the same Pydantic model. Malformed/refused/truncated output cannot update authoritative state. No request silently switches endpoints, providers, models or structured-output modes. Reasoning options are omitted when blank. SDK retries are disabled so operator-visible failures are not disguised as a different transport. HTTPS is required and redirects are not followed with credentials.

From **backend**, without starting the app:

```powershell
# List available models (model may be blank for this command).
.\.venv\Scripts\python.exe -m app.check_gateway
# Verify the configured model and transport (consumes model credits).
.\.venv\Scripts\python.exe -m app.check_gateway --generate
# Test all adapters and function-call request/argument compatibility.
.\.venv\Scripts\python.exe -m app.check_gateway --probe-all
```

On macOS/Linux substitute `.venv/bin/python`. The probe executes no tools or purchases. It emits no credentials. HTTP 401/403, rate limits, timeouts, unsupported endpoint/model errors and malformed responses are handled separately, with no upstream response bodies exposed. Restart the backend after editing `.env`.

### Observed compatibility, 20 October 2026

The authenticated NUS `/models` request succeeded. The originally configured `gpt-5.6-luna` was absent from that list and generation requests returned HTTP 503. The selected `qwen3.6:35b` passed minimal Responses-schema, Chat-schema/JSON/text, and Responses/Chat function-call probes at the configured NUS URL.

Important qualification: a larger intent extraction initially returned prose despite accepting a Responses schema parameter. The adapter now explicitly includes the JSON schema in the instructions, in addition to sending the SDK structured-output parameter. Pydantic remains the enforcement boundary. After that correction, live synthetic shopping and budget-revision turns produced catalogue-backed proposals with unchanged privacy permission and no checkout. One attempt returned HTTP 502; retrying the same model succeeded. A successful small probe does not prove server-side constrained decoding, universal schema adherence, or model quality. Re-run the real conversation evaluations after changing models/prompts. Public NUS endpoint documentation could not be retrieved during implementation, so the compatibility record is empirical and limited to this account/model and date.

Official SDK references: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat), [Chat Completions](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create). These describe SDK contracts, not guarantees about NUS gateway implementation.

## Editing data

- `backend/data/products/catalogue.json`: offers with unique IDs, category, brand, price/currency, specifications, attributes, sizes, stock and `merchant_id`. The existing display-name fields are retained for compatibility but canonical merchant names/verification are resolved from the merchant database.
- `backend/data/merchants/merchants.json`: observable merchant records. Include a unique ID, name, reserved `.test` URL, description, payment methods, return policy, contact, reviews, verification indicator, requested information and observable risk flags. The application never visits these addresses.
- Multiple offer IDs can describe the same product/brand/specification at different merchants. Use a different offer ID for each merchant's price. Low-price comparison uses same-brand/category/currency offers in the active scenario, excluding the evaluated offer. With no comparator, no low-price signal is inferred.
- `backend/data/research/merchant_ground_truth.json`: researcher-only labels keyed by merchant ID. Never add labels to product/merchant records or prompts. This file is loaded only when an authenticated researcher requests a report/export. Do not distribute backend fixture files to study participants.

## Risk policy

`backend/config/merchant_risk_rules.json` defines finite nonnegative weights, increasing medium/high/critical score thresholds, a low-price ratio, per-level ALLOW/REVIEW/BLOCK decisions, explanation detail and a version string. Validation rejects missing rules, unknown fields, negative/NaN weights and invalid thresholds. Invalid current configuration blocks consequential actions, including already-pending proposals.

`backend/app/runtime/merchant_risk.py` implements observable rules: price comparison, incomplete business info, excessive data, unsupported/external payment, conflicting refund terms, knockoff products (`lookalike`), identity inconsistency, pressure and instruction-injection patterns. Website reputation comes from the fictional site registry (`backend/data/sites/site_registry.json`) and applies only to local merchants: a `mid` site adds `site_reputation_mid` (default weight 1) and a `poor` site adds `site_reputation_poor` (default weight 4). Code computes it in both `rules` and `ai` modes; the risk agent never sees the registry. A session whose stored risk-config snapshot predates these two rules scores them 0, so it behaves as before. Configuration submitted from the research page must still list every rule. Research reports still attribute such a session's rows to its original profile. Proposals left pending across this upgrade cannot be checked out: merchant records gained the `site` field and study merchant websites changed, so their fingerprints no longer match and checkout fails safe. Start new participant sessions after upgrading. A discount alone is capped at LOW predicted risk. HIGH does not mean proven fraud. Pattern matching cannot detect all prompt injection or deception; absence of evidence is not evidence of safety.

Non-negotiable safeguards remain in Python: external checkout requests, sensitive credential/ID collection, and detected instruction injection block checkout regardless of experiment weights/decisions. User hard budgets, excluded brands, restricted merchants, payment and privacy permissions still apply through the original policy engine. A risk ALLOW never overrides those rules. Existing `backend/config/policy.json` baseline review settings also remain active; a lower risk score need not remove an independently required user approval.

`BEANY_RISK_DETECTION` in `backend/.env` chooses who finds risk signals in local products: `rules` (default) reads the structured merchant fields with `assess()`; `ai` sends each proposed offer's shopper-visible evidence (`app/runtime/local_evidence.py`) to the risk agent and scores its grounded findings with `assess_live()`, falling back to `assess()` and logging `risk_agent_fallback` when the agent is unavailable. The value is saved per session at creation, applies to scenario sessions too, and leaves web listings unchanged. The non-negotiable safeguards below still apply in `ai` mode: `merchant_risk.safeguard_block()` reads them from the record, whatever the agent reports. Each assessment records its `basis` (`rules`, `ai` or `rules_fallback`), which researcher reports and CSV exports include as `risk_basis`, next to the session's `risk_detection`. Differences in `ai` mode, for the policy owner: the same offer can be judged differently across sessions, which flows into researcher reports; and in mock mode the stand-in agent reads only evidence lists, so most variants come out LOW. Measure detection with `python -m scripts.evaluate_risk_agent` (paid model calls).

Profiles are in `backend/config/cui_profiles.json`. The standard and concise profiles change warning detail. Additional profiles can use the same schema. Configurations are snapshotted per session, hashed, versioned and retained in internal history for reproducibility. Applying a profile/config invalidates pending proposals. Editing the global valid risk configuration affects new sessions; active sessions retain their snapshot. An invalid global configuration still fails closed.

## Dialogue and clarification

- `backend/config/prompts/dialogue.txt`: conversational tone, explicit versus suggested preferences, corrections and treatment of merchant content as untrusted data.
- `backend/config/elicitation.json`: local default currency and fields sufficient to proceed without optional clarification. A bare `$` is not treated as an explicit USD confirmation; ambiguous currency is a suggestion, while explicit SGD/USD instructions remain authoritative.
- `backend/app/runtime/llm.py`: outcome explanation instructions. Only observable product/merchant/risk facts are supplied, never hidden labels or experiment metadata.

## Scenarios A–I

Append scenarios to `backend/data/scenarios/scenarios.json`. IDs `risk-a` through `risk-i` cover trusted, low-price-plus-other-signals, excessive data, external payment, substitution, injected instructions, benign discount, concealed malicious merchant and rejection/alternative conditions. Each specifies goals, initial brief/permissions, product and merchant availability, trigger action, expected decision/intervention and success/failure criteria. Ground truth is joined by merchant ID in research reports, not copied into participant scenarios or session objects.

The trusted case has no merchant-risk warning, though the user's default approval requirement still yields REVIEW. The concealed malicious case deliberately has LOW predicted risk: the engine cannot see hidden truth. The benign discount has LOW risk because price alone is weak evidence. This makes false-positive and false-negative evaluation meaningful.

## Research UI and exports

Open `/research`, authenticate with `BEANY_RESEARCH_KEY`, start a scenario and use **Load risk configuration**. Select a profile and adjust the JSON weights/thresholds. Apply changes, then trigger the scenario condition. Inspect results separately from the participant page. **New participant, same scenario** creates an independent session and preserves the old session for export.

The risk report/export includes proposal/product/merchant, configuration hash/version and profile, predicted risk, observed evidence, hidden truth, policy decision, warning, subsequent action and researcher observations. Mark understanding/appropriate response as Yes/No only after observation; null means not assessed and is never inferred from a click. Internal experiment metadata and observations are excluded from every participant session response.

The original anonymous event CSV still excludes labels and free-text content. **Export researcher risk CSV** includes ground truth and warning text; treat it as researcher material. Formula-leading CSV cells are escaped. Local exports are ignored by Git.

Binary mapping: predicted positive = HIGH/CRITICAL; predicted negative = LOW/MEDIUM. Ground-truth positive = SUSPICIOUS/MALICIOUS; negative = TRUSTWORTHY/UNCERTAIN. Metrics report TP/FP/TN/FN, precision and recall, with null for undefined denominators, plus a four-by-four ground-truth versus risk-level confusion matrix. The unit is a presented proposal; repeated offers count as separate exposures. `UNCERTAIN` as negative is an explicit study convention, not a claim of trustworthiness. Policy BLOCK and binary suspicious prediction are distinct outcomes: mandatory safeguards may block even with experimentally suppressed scores.

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm run typecheck
npm run build
npm run test:e2e
```

Backend tests use fake gateway transports or labelled mock conversation mode and make no paid requests. Live connectivity probes are opt-in. Browser tests launch isolated local test servers; run them yourself when desired. This is a controlled shopping-oversight experiment, not real merchant verification, fraud detection or payment security.
