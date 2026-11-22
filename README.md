# Beany — Conversational Shopping User Interface

Beany is a Conversational User Interface designed for agentic shopping and commerce built with Next.js and FastAPI.

An LLM model interprets conversations; Python controls permissions, product search, policy decisions and simulated checkout. Every product and merchant is fictional. No payment or real shopping service is connected.

## Current CUI demo

Open **http://localhost:3000/shop** for the PRD v2 experience: headphones and running shoes, a compact editable needs summary, personalised comparative reasoning, optional source evidence, priority correction, exact-product seller changes, visible payment cautions and explicit offer selection. You can finish without opening evidence or entering checkout. All records are fictional.

This route runs entirely in the frontend with a bounded deterministic interpreter and the versioned `beany-cui-v3.0` fixtures in `frontend/src/lib/shoppingFixtures.ts`. No backend or API credentials are required. Run `npm install`, `npm run build` and `npm run start` from `frontend`, then open `/shop`; for development use `npm run dev`. It is a working interaction prototype, not open-ended LLM conversation or live web research.

Needs, the last request and any selected offer are stored in this browser. Refresh rechecks the offer against the current fixture and needs. Editing needs clears selection; `Start fresh` clears only this CUI decision. Storage failures are visible. Unsupported categories and USD requests ask for clarification, and budgets never silently increase.

The `/` route remains the classic backend-connected simulation described below. Its SQLite sessions, research exports, cart and receipts are independent of `/shop`.

Blocked seller offers use a prominent red flag with the affected seller/price, evidence, consequence and an action to select the recommended alternative. Missing information remains a separate caution; colour never substitutes for the reason or next action.

## Requirements

Python 3.11+, Node.js 20.9+ (Node 22 recommended), npm. Run one backend worker for local studies.

## Windows (PowerShell)

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env locally; do not paste your key into chat or frontend files.
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

If your existing virtual environment was created with uv and has no pip, use `uv pip install --python .venv/Scripts/python.exe -r requirements.txt` instead.

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

## macOS / Linux

```sh
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env before launching.
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
# Separate terminal:
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Backend API docs: http://localhost:8000/docs.

## NUS SoCLaaS configuration

Configure `backend/.env` using `backend/.env.example`. Obtain your NUS SoCLaaS API credentials through your course/project access; keep them on the backend. Set `OPENAI_API_KEY`, `OPENAI_BASE_URL=https://soclaas-api.comp.nus.edu.sg/v1`, and an available `OPENAI_MODEL`. The project owner's selected model is `qwen3.6:35b`. No model or provider is hardcoded in application logic.

Responses is the default API mode; Chat Completions is an explicit compatible adapter. The selected NUS model passed endpoint probes, but full-schema responses require explicit JSON instructions plus Pydantic validation; accepting a schema parameter does not prove constrained decoding. See [configuration guide](docs/configuration-guide.md) for exact settings, empirical compatibility results, model listing and connectivity commands.

Any OpenAI-compatible HTTPS endpoint works through the same settings. For DeepSeek, use `OPENAI_BASE_URL=https://api.deepseek.com/v1`, `OPENAI_API_MODE=chat`, `OPENAI_STRUCTURED_MODE=json`, a blank `OPENAI_REASONING_EFFORT`, and a model listed by `python -m app.check_gateway` (`deepseek-flash` was used for testing). `backend/.env.example` shows both setups. Run `python -m app.check_gateway --generate` from `backend/` before starting the app; it consumes a small amount of credit.

For offline testing set `BEANY_LLM_MODE=mock`. This mode is visibly labelled and is not a substitute for real conversational evaluation. Missing credentials never silently activate it. The API key must never appear in frontend variables or Git. Only recent conversation and observable catalogue/merchant/risk data are sent to the configured model; hidden ground truth is never included.

## Using Beany

Start with a prompt or free text. Vague requests can trigger a clarification; specific requests search immediately. The brief records confirmed, suggested and unspecified values. Edit/remove preferences directly. Currency accepts SGD/USD; category accepts Running shoes, Headphones, Backpacks; list fields use commas. A hard budget is never bypassed by approval.

Permissions in the classic interface are changed explicitly through their own form. Missing budgets and unverified fictional merchants require review by default. Even ALLOW proposals wait for explicit checkout; adding an item to the cart is not approval.

Any classic brief/permission edit supersedes pending proposals. Ask for options again to search with the new state. Approvals bind to a proposal ID and a hash of its complete product/payment/data-sharing details. Reject, request an alternative, refine through chat, or cancel. Receipts and state survive refresh/restart. A fresh classic session retains prior server sessions; export study logs before any explicit deletion.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

On macOS/Linux use `.venv/bin/python`. Playwright starts isolated servers at 3100/8100 with an explicit mock LLM and test SQLite file. It exercises desktop and mobile layouts, approval/receipt persistence, cancellation, hard blocking and exports.

Pytest never uses your `backend/.env`: `backend/tests/conftest.py` pins mock mode, catalogue search, blank API keys and a temporary database before the app is imported, so a live configuration cannot trigger paid model or Browser Use calls from the test suite.

Your original learning modules (`workflow.py`, `review.py`, `checkout.py`, `shopping_service.py`, etc.) remain intact as optional exercises. The integrated `app.main` does **not** import LangGraph. `legacy_main.py` preserves the earlier scripted API for regression tests only. To run LangGraph exercises/tests, install `requirements-legacy.txt`; those tests skip when LangGraph is absent. Do not expose the legacy app as the participant backend.

## Study sessions

Open http://localhost:3000/research and enter the backend researcher key. Start a fresh scenario participant, open the participant interface, and trigger a predefined condition if applicable. Triggering a condition proposes a fixture product; it does not script the conversation. Refresh study results and export anonymous CSV.

## Editing and architecture

- Conversation instructions: `backend/config/prompts/dialogue.txt`
- Policy thresholds: `backend/config/policy.json`; rule logic: `backend/app/runtime/policy.py`
- Products: `backend/data/products/catalogue.json`
- Merchants: `backend/data/merchants/merchants.json`; website reputation registries in `backend/app/runtime/sites.py`: `backend/data/sites/site_registry.json` (fictional local sites, exact host) and `backend/data/sites/live_site_registry.json` (live retailers, host or subdomain)
- Scenarios: `backend/data/scenarios/scenarios.json`
- UI: `frontend/src/app/page.tsx`, `frontend/src/components/Brief.tsx`, `frontend/src/app/globals.css`
- Backend state/orchestration: `backend/app/runtime/`
- Browser Use task and captured evidence fields: `backend/app/runtime/browser_search.py`, `backend/app/runtime/schemas.py` (`WebEvidence`)
- Live-listing risk review prompt and grounding: `backend/app/runtime/risk_agent.py`; weights and levels: `backend/config/merchant_risk_rules.json`
- Replay fixture: `backend/data/replay/study_listings.json`, rebuilt by `python -m scripts.build_replay_fixture`

## Limits

This is a local, single-worker study application, not an internet deployment. Session UUIDs act as local access tokens; there is no participant account authentication. The researcher key protects study controls, not a production research-data security perimeter. SQLite stores raw conversation and model interpretations locally; anonymous CSV deliberately omits that free text. Researchers must manage consent, retention and local database access. Do not use real personal/payment data.

LLM extraction remains probabilistic. Confirmed changes need a supporting quote and pass deterministic field validation; quote matching cannot prove semantic correctness. The editable brief and receipts make interpretation inspectable. Unknown free-text requirements require review. Catalogue search uses deterministic keyword/brand matching, not semantic retrieval; live listings use tolerant feature matching with an LLM check (see "Open-ended live product search"). USD requests may have no matches because the seeded catalogue uses SGD. Prices use fixed catalogue decimals; no real financial processing occurs.

Live endpoint probes and synthetic shopping turns were exercised against the selected NUS model. Broader conversational quality still requires human-reviewed evaluations. Automated tests validate deterministic behaviour and gateway contracts. LangGraph, RAG and real checkout are absent from the integrated runtime. MCP is used only for read-only Shopify Global Catalog discovery; website automation uses read-only Browser Use.

## Merchant-risk extension

Live product discovery queries both Shopify Global Catalog and Browser Use Cloud V4 in default hybrid mode and compares their eligible results. Browser-only and fictional catalogue modes remain selectable.
See [Browser Use setup and switching guide](docs/browser-use-search.md). Catalogue/research records
remain fictional; Browser Use listings are clearly labelled unverified web snapshots. All checkout
and receipts remain simulated. Live search was checked manually against amazon.sg.

Browser Use also captures seller, return-policy, payment and page-notice details when visible
(blank when not). A risk review agent checks each proposed live listing once: every finding must
quote the captured text, and Python scores the findings with the existing merchant-risk weights.
External payment and injection always block. Live listings never drop below REVIEW. To test the full
flow with known risk cues and no web search, set `BROWSER_USE_REPLAY` to replay the study listings.
Details and the field mapping are in the [Browser Use guide](docs/browser-use-search.md).

The participant UI supports a persistent session cart, `/checkout` review, and `/receipts` history.
Adding an item is not approval. Final checkout submits specific proposal IDs and fingerprints,
rechecks catalogue/merchant data and current permissions, and commits all selected receipts together.
Cart lines retain their original briefs so later searches can target different categories. Budgets
are per item; there is no aggregate basket budget or quantity editing (one unit per proposal).
Even ALLOW proposals now wait for explicit checkout. Fresh session retains prior server sessions;
receipt history uses session IDs stored in this browser, not a user account. Clearing browser storage
loses access to that history. No real payment, tax, shipping or order processing is performed.

Chat requests now use a bounded search-and-inspect workflow over the fictional catalogue before
policy evaluation. The new planner has offline regression coverage. Its
multi-step behaviour was exercised manually with DeepSeek (replay and live search), not yet with the NUS model.

Separate product and merchant databases support fictional multi-merchant offers. Risk is predicted from observable signals; hidden labels are joined only in authenticated researcher reports. Configure thresholds, warning profiles, scenarios and evaluation using [docs/configuration-guide.md](docs/configuration-guide.md). The participant UI offers merchant details and deterministic “Find another seller” (same model) and “Find another product” (different model) controls; repeated presses walk through every option before starting again. Every checkout still passes policy rechecks and action-specific approval checks.

After this upgrade, start a fresh shopping request/session before approving: older proposals do not contain merchant snapshots and must not inherit approval across the schema change.


### Open-ended live product search

`BEANY_SEARCH_PROVIDER=browser_use` enables arbitrary product families on the retailers
listed in `BROWSER_USE_ALLOWED_DOMAINS`. Restart the backend and start a fresh session
when changing provider configuration: existing sessions retain their provider. Leave
`BROWSER_USE_REPLAY` empty for live calls. A replay path uses recorded listings without
paid browsing; `catalogue` uses the fictional demo inventory. SGD/USD and simulated
checkout remain the supported scope. Category examples do not limit live searches.

The live category editor accepts free text. Beany saves a product family while clarifying
budget, subtype and features; explicit uncertainty after a question can continue the
search. Additional features use additive updates. New product tasks reset the active
brief but preserve cart, receipts and permissions. Historical sessions lacking a reliable
task boundary require clarification rather than recovery from unrelated older messages.

Live listings include observed product type and source evidence. Semantic relevance is
an LLM assessment, not independent verification or checkout authority. It is bound to
the request and listing snapshot; mismatches are blocked and unknown relevance requires
review. Existing cart receipts are not rewritten. Changed snapshots invalidate approvals.

Features are matched differently for live listings (`app/runtime/feature_match.py`,
`app/runtime/feature_check.py`). Rules first: a feature counts when the listing's name,
description, attributes or specifications show the same concept (noise control, comfort,
portability, durability, water resistance, battery, sound, storage) or most of its words.
Must-have features the rules cannot confirm go to one batched LLM call per search. Each
verdict is met, absent or unstated and must quote the listing; an ungrounded or skipped
verdict counts as unstated. Absent excludes the listing; unstated keeps it with a REVIEW
note ("The listing doesn't mention …"); if the model is unavailable, an unconfirmed
must-have still excludes. Provider-inferred features and selling points never confirm a
feature. Catalogue products keep exact matching against their attributes. The offer card's
"How this matches your needs" chips show these per-feature verdicts (`feature_fit`).

Live merchants on a retailer in `backend/data/sites/live_site_registry.json` show its
website reputation (amazon.sg good, qoo10.sg mid); other hosts, such as independent
Shopify stores, show Unknown.

If Browser Use fails, chat displays a saved search-unavailable response instead of no
matches. Read the backend terminal (`uvicorn.error`) for `Search failure`: reason code,
HTTP status, run ID where available, and diagnostic reference. Only explicit recognized
billing codes produce an insufficient-credit/top-up diagnostic. Generic HTTP 402 or
failed runs do not establish the cause; check the Browser Use dashboard. Access errors,
rate limits, timeouts and invalid results have separate diagnostics. No automatic paid
retry or fictional fallback occurs. User cancellation is separate. No keys, raw provider
responses or prompts are included in these failure diagnostics.

Regression validation uses mocked/recorded providers. Live compatibility and actual
retailer coverage require a separately authorized, cost-bounded smoke check; offline
passing tests do not establish live reliability.


### Shopify Global Catalog and hybrid discovery

New sessions default to `BEANY_SEARCH_PROVIDER=hybrid`: each new search queries Shopify
and Browser Use once, sequentially, with cancellation checked between sources.
Both sources are searched even if the first succeeds. No automatic paid retry occurs.

A search after an edit that only filters reuses the last search's listings instead
(`reusable()` in `app/runtime/discovery.py`): must-have/preferred toggles, a lower budget,
removed features, brands, usage or size, newly excluded brands, or a rejected offer with
unchanged needs. Reuse needs both sources to have succeeded and lasts 25 minutes from the
search's start, since snapshots older than 30 minutes cannot check out. A new or changed
category, currency, feature, usage, size or preferred brand, a higher or removed budget, a
hard budget made preferred, an un-excluded brand, or unchanged needs search again. A reuse
with no eligible listing falls back to a new search. Reuse is logged as a `search_reuse`
event and shown as "Rechecked N web listing offers from your last search".

A deterministic workflow cheaply ranks and deduplicates results before inspecting
up to six candidates total (configurable `screening_budget` in `backend/config/policy.json`).
It stops once three eligible, distinct products are found: one primary and up to two
alternatives. `recommendation_limit` defaults to 3 and is capped at 3 in the workflow. Ranking prioritizes
relevance, grounded preference matches and information completeness, with price
breaking ties within a currency. This is the best of the bounded results, not a
claim to compare every available listing. Fewer than three are returned when needed. Blocked and known irrelevant products are excluded.
Partial source failures are logged; valid results from the other source can still
be used. A failed search with no usable results remains a service failure.

`shopify_catalog`, `browser_use` and `catalogue` remain single-source modes.
Existing sessions retain their stored provider. Hybrid invokes Browser Use
on each new search and may consume its configured credits, subject to the existing
per-run cost cap. No real carts, orders or payments are created. Provider diagnostics
stay in backend logs; participant UI avoids internal provider/routing labels.

Install backend requirements (including the official `mcp` Python SDK). Anonymous
Shopify discovery needs no key: leave BOTH `SHOPIFY_CLIENT_ID` and
`SHOPIFY_CLIENT_SECRET` empty. The default `SHOPIFY_UCP_PROFILE_URL` uses Shopify's
hosted 2026-08-25 example profile. Only search_catalog, lookup_catalog and get_product
are permitted by Beany regardless of the capabilities advertised by that example.
For production, host a discovery-only profile and optionally configure Catalog client
credentials; bearer tokens are cached in memory and renewed before their 60-minute
expiry. No buyer account or IP address is sent to Global Catalog.

`SHOPIFY_MARKET_COUNTRY=SG` and the brief currency (SGD by default) localize discovery.
`SHOPIFY_TIMEOUT_SECONDS=30` bounds each MCP operation. Anonymous capacity is shared:
rate limits are reported with a sanitized Retry-After value when supplied. No automatic
retry is issued. A failed Shopify search followed by no Browser Use results is reported
as unavailable, not as an exhaustive no-match finding.

Only concrete seller/variant prices are imported (SGD/USD minor units converted to
major units). Product-level price ranges and checkout permalinks are not offers.
Variant details are fetched before proposals; unknown or inferred properties do not
become verified hard-feature evidence. Distinct variants and sellers retain separate
IDs. Product snapshots, relevance, fingerprints and simulated approval checks cover
both live sources. Each offer identifies its actual provider. Saved cart snapshots are
not silently refreshed or reapproved.

Search failure logs include the actual provider. Shopify access/rate-limit failures
are not Browser Use credit errors. An explicit Browser Use insufficient-credit error
still produces the existing top-up diagnostic in the backend terminal.

References: [Global Catalog MCP](https://shopify.dev/docs/agents/catalog/global-catalog),
[authentication](https://shopify.dev/docs/agents/get-started/authentication), and
[rate limits](https://shopify.dev/docs/agents/profiles/auth-and-rate-limiting).
Offline fixtures validate the integration; no live compatibility or market-coverage
claim is made until a separately authorized live smoke check succeeds.


### Product images and Shopify live verification (2026-11-19)

The current-match card displays the selected product image between its title/price
and the needs summary. Shopify variant media is preferred, with parent media as a
fallback. Browser Use is instructed to return the main product image URL in its next
search; no Browser Use live test was performed. Existing snapshots without images
show a placeholder until a fresh search. Missing, unsafe or failed image URLs show
"Product image unavailable"; Beany does not invent photos. Images load directly in
the browser over HTTPS with no referrer; no backend image proxy is used.

Anonymous Shopify-only search and get_product calls succeeded for desk lamps, coffee
machines and wireless headphones. The first probe exposed two adapter issues: Shopify
returned structuredContent without the MCP SDK's required content array, and product
URLs were on variants rather than the parent. Both are now supported, with regression
fixtures. SGD market context can still return USD listings; normal currency policy
checks remain authoritative. This verifies those calls, not every category or retailer.

### Diagnosing slow shopping requests

Backend terminal logs include `timing_start`, `timing_end` and `timing_summary` at
INFO level through the Uvicorn logger. Each workspace mutation has a generated
`trace` ID; `span` and `parent` connect nested work, including cancellable threads.
Logs cover database lock waiting/load/save, response construction, conversation,
LLM schema calls, both discovery providers, each product inspection, relevance,
risk review and policy evaluation. `elapsed_s` uses a monotonic clock.

At completion, `timing_summary` lists stages sorted by total duration, with call
count and maximum duration. Durations are inclusive: parent and child spans overlap,
so do not add them together. A repeated `product.risk_review` or `llm.Review` can
explain why screening several products is slower than discovery alone. A start
without an end identifies an in-flight operation. Errors and cancellations are
labelled without logging exception bodies, prompts, product text or credentials.
Cancelled remote calls may continue in the background; the request summary measures
how long Beany waited, not when a remote provider actually stopped. No live search
is required to test this instrumentation, and it does not change timeout settings.

Additional `diagnostic` lines share the same `trace` and active `span`:
- `workflow.choose/chosen/override`: iteration, action and why Python overrode it.
- `workflow.search_results`, `shortlist.*`: candidate references, exclusions and shortlist.
- `inspection.*`, `relevance.cache/result`, `risk.cache/result`: cache hits/misses,
  snapshot/binding changes, model failures and whether another assessment was needed.
- `llm.start/usage/end`: correlated call ID, schema, input character counts, token
  counts and provider-reported reasoning/cached tokens (null if unavailable).

Product references are stable hashes, not listing titles or URLs. To diagnose a run,
keep all lines from its first `timing_start` through `timing_summary`, including
`diagnostic` lines. Join using `trace`, `span`, `call_id` and `product_ref`. These
metrics identify repeated calls, cache invalidation and large requests; they cannot
measure provider-internal queue time or time to first token in non-streaming calls.


### Phase 1 conversation and deterministic search

`runtime/llm.py` retains the conversational interpreter. `Interpretation.search_control`
records request/defer/unchanged; `Session.search_requested` remembers a requested search
while clarifying. Grounded preference changes are saved even during discussion, and
invalidate old recommendations and approval opportunities. A complete brief is not
permission to search: `clarify` stays clarification. Explicit deferral prevents search.
`new_task` additionally requires a grounded product-family change and a literal switch
quote before resetting the brief. Cart, receipts and permissions survive that reset.
Existing SQLite snapshots load the new fields with defaults; no migration is required.

Once requested and ready, `shopping_workflow.run_shopping` builds a confirmed-brief
query, calls existing discovery, then `shopping_tools.screen_candidates` filters,
ranks, deduplicates, inspects and policy-checks a bounded set. Exact duplicates are
removed first; other sellers/variants remain available if the preferred one fails.
After one model is accepted, near-duplicate variants do not fill the alternatives.
Each candidate still uses its own relevance assessment and risk review, with existing
snapshot-bound caches. A final snapshot check prevents returning changed offers.
There are no routine ShoppingStep LLM calls. The explanation model and explicit
approval/simulated-checkout paths remain intact. Workspace comparisons are limited
to the saved shortlist; they cannot introduce unscreened alternatives.

Offline verification and measurement are described in `docs/phase1-validation.md`.
To collect live evidence yourself, run the same request in a fresh session and retain
the backend timing summary plus `shortlist.start`, `shortlist.result`, relevance/risk
cache events and LLM token diagnostics. Timings are nested: do not sum parent and child
stage durations. No live search is needed for the automated tests.


### Shopify product-card evidence

The adapter maps product/variant aggregate ratings (variant first, supported five-star
scales), rating counts, catalogue feature summaries, selling points, variant options,
condition, same-currency reference price and seller policy links. Product and variant
HTML descriptions are converted to text and retained without the previous 2,000-character
cutoff. The card shows catalogue highlights and ratings directly, with full descriptions
and specifications in an expandable section. Policy links are buttons to read the supplied
policies; their presence is not a claim that the return terms have been reviewed.

Provider summaries remain separate from confirmed feature evidence and cannot satisfy
hard constraints by themselves. Aggregate counts do not create written review excerpts or
seller ratings. Sparse detail responses preserve omitted search evidence for the same
variant, while explicit empty fields replace it; price and availability never fall back.
Old saved cards are not backfilled automatically: run a new search to populate the new fields.
Mapping tests are offline, using the saved response's field shapes; no live provider call
is necessary (`tests/test_shopify_evidence.py`).


### Browser Use product-card evidence

The runtime accepts both its nested listing schema and the flat standalone diagnostic
shape (`features`, `seller`, `availability`, ratings, review excerpts and return fields).
Nested safety evidence is retained. The runtime now requests specifications, complete
stock/delivery notices, visible aggregate ratings and review excerpts already on the page.
These map to card features, expandable specifications/descriptions, ratings/counts,
verbatim excerpts, return terms and an allowlisted policy link. Seller percentages remain
verbatim rather than becoming fabricated star ratings. Only explicit five-star aggregates
are parsed numerically; unknown ratings remain text. Review excerpts never receive invented
authors, dates or scores. Availability notices remain visible, including a location that
cannot receive delivery; in-stock does not establish shipping eligibility.

`tests/fixtures/browser_use_listing_output.json` contains only the four public product
records from the successful standalone run, excluding workspace/session identifiers and
polling metadata. Offline tests replay it through the actual parser and discovery mapper.
No live Browser Use run is required. Older saved product cards need a new search to collect
fields that were never requested or stored previously.
