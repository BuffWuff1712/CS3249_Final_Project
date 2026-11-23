# Beany: a conversational shopping agent

**CS3249 Final Project · Group 2** · Bhavina Sathish Kumar, Goel Arnav, Low Bing Heng, Yuan Weitu

## Core task

Beany is a conversational user interface (CUI) for agentic shopping. A shopper describes what they want in plain English, even vaguely ("I need headphones for my commute"). Beany then:

1. **Clarifies purchase intent.** It asks one concise question about anything still missing (product type, budget, must-have features) and keeps an editable needs summary that the user can correct at any time.
2. **Finds and compares products.** It searches live product sources, checks each listing against the user's stated needs, and presents one recommended match plus up to two alternatives, explaining how each one fits.
3. **Surfaces merchant risk.** It checks each seller for scam signals (unusual or off-site payment, missing business details, lookalike branding, misleading returns, prompt injection on the page) and labels every offer ALLOW, REVIEW or BLOCK, with the quoted evidence.
4. **Leaves the decision to the user.** Nothing is bought until the user explicitly selects an offer. Checkout is **simulated**: no real payment, order or personal data is ever involved.

The interface has two panes: the conversation on the left, and the current match, needs summary and evidence on the right.

## For graders: how to try Beany

| Option | What you need | What you get |
|---|---|---|
| **A. Hosted version (small online session with us)** | A browser and a short online session with us | The full system as submitted, running on Google Cloud Run with the real LLM and live web search. **Link: [https://35.240.146.219/shop](https://35.240.146.219/shop)** (self-signed HTTPS — click through the browser warning). Hosting the live server incurs daily costs, so it is not kept running 24/7: see Option A below. |
| **B. Local, with the real LLM** | Option C's requirements plus an OpenAI-compatible API key | The full conversational behaviour. Uses the recorded listings, or live search if you also add a Browser Use key. |
| **C. Local, no keys (offline)** | Python 3.11+, Node 20.9+ | The full interface and backend, with recorded product listings and a keyword-based stand-in for the LLM. Good for checking setup, the UI, risk flags and the selection flow. Conversation quality is limited. |

No accounts or personal data are needed for any option. All test data ships in this repository (`backend/data/`).

**Paid API keys.** The full system uses API keys that are not included in this submission: a **paid Browser Use Cloud key** for live web search (charged per search) and an API key for the OpenAI-compatible LLM. Option A uses both. Option B needs the LLM key, plus the Browser Use key only for live search. Option C runs with no keys at all.

### Option A: using the hosted version

- **Please contact us to arrange a short online session.** The hosted version runs on paid services (cloud hosting, the LLM and Browser Use) that cost money for every day it stays online, so we do not keep it running for the whole grading period. If you would like to view or use the web version, please email weituyuan@u.nus.edu. We will start the service for the session, and you can then use it yourself at the link above.
- The hosted version uses **live web search** (Shopify Global Catalog and Browser Use). One search can take 1–5 minutes; the progress panel shows what Beany is doing while you wait.
- Sessions are kept only while the service is running and may be cleared when it restarts. This is expected: everything is a demo, and checkout is simulated.

### Option B: run locally with the real LLM

Follow the setup steps in Option C below, but in `backend/.env` set `BEANY_LLM_MODE=openai` and fill in:

```
OPENAI_BASE_URL=https://api.openai.com/v1   # or any OpenAI-compatible endpoint
OPENAI_API_KEY=<your key>
OPENAI_MODEL='gpt-6-luna'                               # the model we used
OPENAI_API_MODE=responses
OPENAI_STRUCTURED_MODE=schema
```

For **live web search** instead of recorded listings, leave `BROWSER_USE_REPLAY` empty, set `BEANY_SEARCH_PROVIDER=hybrid` and add a `BROWSER_USE_API_KEY` plus `BROWSER_USE_ALLOWED_DOMAINS` (for example `amazon.sg,qoo10.sg`). Shopify Global Catalog needs no key. Live search is paid per run (capped by `BROWSER_USE_MAX_COST_USD`) and takes 1–4 minutes per search.

After changing `.env`, restart the backend and click **Start fresh** in the interface, because each session keeps the search provider it started with.

### Option C: run locally with no API keys

macOS / Linux:

```sh
# Terminal 1: backend
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Then edit backend/.env and set these four lines:
#   BEANY_LLM_MODE=mock
#   BEANY_SEARCH_PROVIDER=browser_use
#   BROWSER_USE_REPLAY=data/replay/study_listings.json
#   BEANY_RISK_DETECTION=rules
.venv/bin/python -m uvicorn app.main:app --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev
```

Windows (PowerShell):

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend\.env as above, then:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# In a second terminal:
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. Backend API docs are at http://localhost:8000/docs.

The recorded listings (`backend/data/replay/study_listings.json`) cover **headphones, backpacks and running shoes**, with a deliberate mix of trustworthy and risky sellers. In mock mode, include the product, budget and feature in one message, for example:

- `I want wireless headphones under 300 SGD with noise cancelling`
- `I need a lightweight backpack under 80 SGD`
- `Running shoes under 150 SGD, size 42, with cushioning`

Leave out a detail (for example `I need a backpack under 80 SGD`) to see Beany ask a clarifying question first. Then inspect the current match, open the seller evidence, use **Find another seller** or **Find another product**, and select an offer to finish the simulated decision. Some replayed sellers trigger REVIEW or BLOCK so that you can see the risk flags.

## Deploying to Google Cloud Run (how the hosted version runs)

The hosted version runs as two Cloud Run services built from this repository: `beany-backend` (FastAPI) and `beany-frontend` (Next.js). The browser calls the backend directly, so the frontend needs the backend's URL at build time, and the backend needs the frontend's URL for CORS. API keys are stored in Google Secret Manager, never in the repository.

**Prerequisites:** a Google Cloud project with billing enabled (light use stays within Cloud Run's free tier; set a budget alert anyway), and the [gcloud CLI](https://cloud.google.com/sdk/docs/install).

**1. Set up the project (once).**

```sh
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# Store keys as secrets (paste the key, then press Ctrl-D)
gcloud secrets create openai-api-key --data-file=-
gcloud secrets create browser-use-api-key --data-file=-      # only for live web search

# Let Cloud Run read the secrets
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**2. Deploy the backend.** Run from the repository root:

```sh
gcloud run deploy beany-backend --source backend --region asia-southeast1 \
  --allow-unauthenticated --timeout 3600 --max-instances 1 --memory 1Gi \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-env-vars "BEANY_LLM_MODE=openai,OPENAI_BASE_URL=https://api.openai.com/v1,OPENAI_MODEL='gpt-6-luna',OPENAI_API_MODE=responses,OPENAI_STRUCTURED_MODE=schema,OPENAI_TIMEOUT_SECONDS=200,BEANY_DB=/tmp/beany.sqlite3,BEANY_SEARCH_PROVIDER=browser_use,BROWSER_USE_REPLAY=data/replay/study_listings.json"
```

This uses the recorded listings. For **live web search**, add `BROWSER_USE_API_KEY=browser-use-api-key:latest` to `--set-secrets` (comma-separated), and replace the `--set-env-vars` value with the version below. It starts with `^@^` because the domain list contains commas, so the variables are separated by `@` instead:

```sh
  --set-env-vars "^@^BEANY_LLM_MODE=openai@OPENAI_BASE_URL=https://api.openai.com/v1@OPENAI_MODEL='gpt-6-luna'@OPENAI_API_MODE=responses@OPENAI_STRUCTURED_MODE=schema@OPENAI_TIMEOUT_SECONDS=200@BEANY_DB=/tmp/beany.sqlite3@BEANY_SEARCH_PROVIDER=hybrid@BROWSER_USE_ALLOWED_DOMAINS=amazon.sg,qoo10.sg@BROWSER_USE_TIMEOUT_SECONDS=600@BROWSER_USE_MAX_COST_USD=1"
```

Why these settings:
- `--timeout 3600` lets a long live search (several minutes) finish. The progress stream also sends a heartbeat every 5 seconds, so the connection never looks idle.
- `--max-instances 1` keeps every session on one instance, because sessions are stored in a single SQLite file.
- `BEANY_DB=/tmp/...` puts the database on the container's temporary disk. It is cleared on restart, which is acceptable for a demo.
- Scaling to zero when idle keeps the cost at or near $0. Add `--min-instances 1` to avoid cold starts, which costs a small amount to keep one instance running.

Then check that the backend can reach the model:

```sh
BACKEND_URL=$(gcloud run services describe beany-backend --region asia-southeast1 --format='value(status.url)')
curl "$BACKEND_URL/health"
```

**3. Deploy the frontend with the backend's URL.** Next.js reads `.env.production` at build time:

```sh
echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" > frontend/.env.production
gcloud run deploy beany-frontend --source frontend --region asia-southeast1 \
  --allow-unauthenticated --memory 1Gi
```

**4. Allow the frontend to call the backend (CORS).**

```sh
FRONTEND_URL=$(gcloud run services describe beany-frontend --region asia-southeast1 --format='value(status.url)')
gcloud run services update beany-backend --region asia-southeast1 --update-env-vars FRONTEND_ORIGIN=$FRONTEND_URL
```

Open `$FRONTEND_URL`. This is the hosted link to put at the top of this README.

**Updating after a code change:** rerun step 2 (backend) or step 3 (frontend). A redeploy restarts the service and clears sessions, so avoid redeploying while graders are testing.

**Logs:** `gcloud run services logs read beany-backend --region asia-southeast1` shows the backend's timing and diagnostic lines (see "Diagnosing slow shopping requests" below).

## Models, APIs and services

| Service | Used for | Key needed |
|---|---|---|
| OpenAI-compatible LLM. We used **OpenAI GPT-6 Luna**; | Interpreting each turn (intent and preference extraction), grounded feature checks, merchant-risk review and explanations | Yes (not for mock mode) |
| **Shopify Global Catalog** via the Model Context Protocol (MCP), read-only | Structured live product discovery | No (anonymous) |
| **Browser Use Cloud** | A browser agent that reads listings, seller and return-policy pages on allowlisted retailers | Yes (not for replay mode) |
| SQLite (local file) | Sessions, conversations, cart and simulated receipts | No |

Stack: **Next.js 15 / React 19** frontend, **FastAPI / Pydantic** backend, Python 3.11+.

## How to use Beany

- Start with a request in your own words. Vague requests trigger one clarifying question; specific ones search straight away. Saying "not sure" or "no preference" lets Beany continue without that constraint.
- The **needs summary** shows each value as confirmed, suggested or unspecified. Edit or remove values directly, or say what changed in chat ("actually, comfort matters more than noise cancelling").
- Each offer card shows **How this matches your needs** (each feature is met, absent or not stated in the listing), price, product and seller evidence, website reputation, and any risk flag.
- Ask questions about the results ("why this one?", "what's the return policy?"). Beany answers from the captured evidence only.
- Off-topic chat gets a brief natural reply and a gentle offer to return to shopping. A failed search is reported as unavailable, never as "no matches".
- Nothing is bought without your explicit selection, and checkout is always simulated. Blocked offers cannot be selected.

## Features at a glance

Beany has 24 user-facing features and handles 25 edge cases. In summary:

- **Understanding the shopper** — one-question clarification covering product, budget and features; editable needs summary with confirmed / suggested / unspecified values; quote-grounded preference extraction; "not sure" accepted without stalling the turn.
- **Finding products** — hybrid live search over Shopify Global Catalog (MCP) and a Browser Use browser agent on allowlisted retailers; bounded shortlist (1 match + up to 2 alternatives); search reuse when edits only narrow results; live progress panel with stop control.
- **Explaining and protecting** — per-feature fit chips ("met / absent / not stated"); expandable specs, ratings, verbatim review excerpts and policy links; merchant-risk review with quoted evidence scored to ALLOW / REVIEW / BLOCK; per-website reputation; evidence-only Q&A.
- **Handing the decision back** — explicit selection with simulated checkout; approval bound to a hash of what the user saw; "Find another seller" and "Find another product" controls; two-pane resizable layout.

Full mapping of every feature and edge case to the design principle and source file: [docs/features-and-edge-cases.md](docs/features-and-edge-cases.md).

## Where the main code is

| Component | Location |
|---|---|
| Conversation prompt (Beany's voice, intents, extraction rules) | `backend/config/prompts/dialogue.txt` |
| LLM interpretation and structured-output gateway | `backend/app/runtime/llm.py`, `backend/app/runtime/gateway.py` |
| Turn handling and orchestration | `backend/app/runtime/service.py`, `backend/app/shop.py` (API for the two-pane UI), `backend/app/main.py` |
| Preference grounding and clarification | `backend/app/runtime/preferences.py`, `backend/app/runtime/clarification.py` |
| Search workflow, shortlist and ranking | `backend/app/runtime/shopping_workflow.py`, `backend/app/runtime/shopping_tools.py`, `backend/app/runtime/discovery.py` |
| Product sources | `backend/app/runtime/shopify_catalog.py` (MCP), `backend/app/runtime/browser_search.py` (Browser Use and replay) |
| Feature verification | `backend/app/runtime/feature_match.py`, `backend/app/runtime/feature_check.py` |
| Merchant-risk review and scoring | `backend/app/runtime/risk_agent.py`, `backend/app/runtime/merchant_risk.py`, `backend/config/merchant_risk_rules.json`, `backend/app/runtime/sites.py` |
| Policy, approvals and simulated checkout | `backend/app/runtime/policy.py`, `backend/config/policy.json`, `backend/app/runtime/cart.py` |
| Frontend (two-pane workspace) | `frontend/src/components/shopping/ShoppingWorkspace.tsx` and the rest of `frontend/src/components/shopping/`; API client `frontend/src/lib/shopBackend.ts` |
| Test data | `backend/data/` (replay listings, fictional catalogue, merchants, scenarios, site reputation registries) |
| Tests | `backend/tests/` (pytest), `frontend/tests/` (Playwright) |

## What is new: how Beany differs from other chat shopping agents

Current chat shopping interfaces — ChatGPT shopping, Perplexity, Amazon Rufus, Google's Gemini shopping, Shopify's Shop assistant, and generic "buy-for-me" LLM agents — trust the model end-to-end. The user's request is paraphrased, listings are summarised, features are claimed, and either the agent links out or acts autonomously. None of them show *where each claim came from*, and none of them defend against the fact that the merchant page itself can be hostile to an AI reader. Beany's design stance is the opposite: **every LLM claim is a hypothesis that must cite a verbatim source — the user's message or the listing text — before it affects the brief, the match, or checkout.** Deterministic Python code enforces this around the model.

Each item below is marked in the code with a comment starting with `INNOVATION:` beside the relevant implementation — search the repository for `INNOVATION:` to jump to them.

1. **Quote-grounded preference extraction.** *How other chat agents handle it:* the model paraphrases "I want something comfortable" into stored preferences without anyone checking that the user actually said it. Drift compounds across turns. *Beany:* a preference is saved as **confirmed** only when the model supplies a verbatim quote from the user and Python verifies the quote is in the message. Assumptions can only be saved as **suggested**. Ungrounded extractions are sent back to the model once as validation feedback. → `preferences.py` (`grounded_change`), `clarification.py` (`extraction_issues`)

   *Example:* A shopper writes "extra cushioning in the soles". If the model returns an evidence quote with invented ellipses, the extraction is sent back once for repair; a literal quote such as "extra cushioning" passes the grounding check.

   *Regression tests:* [extraction repair](backend/tests/test_extraction_repair.py) — `test_repairs_ellipsized_evidence_once`.

2. **Conversation is evidence, not permission.** *How other chat agents handle it:* the moment the brief "looks complete" the agent searches, and a stray "not sure" is often treated as answering whatever the agent most recently thought about. *Beany:* Python tracks which of product type, budget and features were **actually asked and actually answered** as separate state from the brief. A search runs only when the user requested one and the asked fields are resolved. "Not sure" only clears questions that were asked. → `clarification.py` (`clarify_before_search`)

   *Example:* After "I need shoes" and "running shoes under $100", Beany still asks about features. Replying "no preference" resolves that question and lets the pending search proceed without inventing a feature.

   *Regression tests:* [clarification flow](backend/tests/test_clarification_and_stop.py) — `test_partial_answer_does_not_skip_remaining_questions` and `test_ungrounded_skip_is_ignored`.

3. **Two-stage, quote-grounded feature verification.** *How other chat agents handle it:* an offer card says "noise cancelling ✓" because the model paraphrased the listing. There is no distinction between "the listing says this", "the listing doesn't mention this", and "the listing contradicts this". *Beany:* deterministic concept and word-stem rules confirm common features cheaply. Needs the rules cannot settle (features, size and use, must-have or preferred) go to one batched LLM call per search whose met/absent verdicts **must quote the listing**; an ungrounded verdict counts as unstated. Only must-haves affect eligibility: an absent must-have excludes the listing, and an unstated one keeps it with a REVIEW note ("the listing doesn't mention…"); a model outage leaves the strict filter in place and unconfirmed must-haves still exclude. → `feature_match.py` (`met`), `feature_check.py` (`ensure`)

   *Example:* For "connects to two devices", the model can ground a match in "multipoint Bluetooth 5.3". A fabricated quote such as "dual connection" becomes "unstated"; a model outage leaves the strict filter in place.

   *Regression tests:* [feature verification](backend/tests/test_feature_check.py) — `test_verdicts_decide_search_and_review`, `test_ungrounded_quote_counts_as_unstated` and `test_model_failure_keeps_strict_rules`.

4. **Grounded merchant-risk review of untrusted web content.** *How other chat agents handle it:* trust is a retailer allowlist at best; the page content itself is fed to the model as instructions. This is the specific attack surface created by AI shopping agents, and we have not seen a competing product that treats it as a threat model. *Beany:* a per-listing LLM reviewer proposes signals (unusual payment, missing business details, misleading returns, lookalike branding, pressure, prompt injection, …), every finding must **quote the captured page verbatim**, ungrounded findings are discarded, and **text addressed to AI assistants is itself a finding**. Fixed Python weights, not the model, turn findings into ALLOW, REVIEW or BLOCK. External payment and injection always block; live listings never fall below REVIEW. → `risk_agent.py` (`grounded`), `merchant_risk.py`, `config/merchant_risk_rules.json`

   *Example:* If the captured page only says "Sale ends tonight", a model finding quoting "Pay via WhatsApp only" is discarded. The supported urgency finding remains and is counted once even if the model repeats it.

   *Regression tests:* [risk grounding](backend/tests/test_risk_agent.py) — `test_ungrounded_and_duplicate_findings_are_discarded`; `test_external_payment_blocks` covers a captured off-platform payment request.

5. **Approval bound to exactly what the user saw.** *How other chat agents handle it:* "buy-for-me" agents either act autonomously (the page they bought from may no longer be the one you saw) or hand off to a retailer checkout with no cryptographic link back to what the user approved. *Beany:* each proposal is **hashed** over product, merchant, risk rules, payment method and data-sharing details; checkout compares that hash, so any change — a $1 price bump, a rewritten return policy, a new risk finding — invalidates earlier approval. Nothing is bought without the user explicitly selecting the exact artefact they are now looking at. → `policy.py` (`fingerprint`), `cart.py`

   *Example:* A shopper selects an offer, then its catalogue price increases by $1 before checkout. Checkout rejects the stale selection and creates no receipt.

   *Regression tests:* [checkout integrity](backend/tests/test_cart.py) — `test_changed_catalogue_rejected` and `test_atomic_and_fingerprint_bound`.

6. **Bounded hybrid shortlist with search reuse.** *How other chat agents handle it:* every turn fires a fresh web search, and either three cards appear instantly from a cache (no verification) or the user waits several minutes with no feedback. *Beany:* results from Shopify Global Catalog (MCP) and Browser Use are merged, deduplicated and inspected under a fixed budget (6 inspections), stopping at three distinct eligible products. **Narrowing edits reuse the previous search** within 25 minutes — a lower or newly added budget, a newly excluded brand, a need switched between must-have and preferred — so refinement is instant instead of another paid live browse. Any edit that asks for listings the last search never looked for (a higher or removed budget, added or removed features, a new usage, size, preferred brand, category or currency) searches again, as does asking again with unchanged needs ("search again", "find something else"), even after rejecting an offer, or fewer than three listings still qualifying. → `shopping_tools.py` (`screen_candidates`), `discovery.py` (`reusable`)

   *Example:* Lowering the budget to SGD50 rechecks the existing pool and keeps the SGD30 and SGD45 listings without calling either search provider again. If reuse yields no eligible listings, discovery performs a new search.

   *Regression tests:* [search reuse](backend/tests/test_search_reuse.py) — `test_lower_budget_refilters_without_searching`, `test_broadening_and_new_needs_search_again`, `test_rejected_offer_with_unchanged_needs_searches_again` and `test_empty_reuse_falls_back_to_a_real_search`; [hybrid shortlist](backend/tests/test_hybrid_shortlist.py) — `test_both_successes_are_combined_and_best_three_screened`.

7. **Two-pane, inspectable interface.** *How other chat agents handle it:* the agent's interpretation of the user's needs is buried inside a scrolling transcript, if it is shown at all; correcting it means arguing in prose. *Beany:* the conversation scrolls on the left while an **editable needs summary**, per-feature fit chips, seller evidence and risk flags stay visible on the right. Every value is labelled confirmed / suggested / unspecified and can be edited directly, which is the UI surface through which the grounding work above becomes correctable at any point. → `frontend/src/components/shopping/`

   *Example:* After selecting headphones under SGD200, the shopper edits the budget to SGD1 in the needs summary. The selection clears; comparing again shows "No eligible offer" while preserving the SGD1 limit.

   *Regression tests:* [workspace interaction](frontend/tests/shop-backend.spec.ts) — "needs editor uses server fields, clears selection, and impossible budget does not relax"; [pane controls](frontend/tests/shop-pane-resize.spec.ts) — "pane resizing, persistence and bounds".

## Tests

```sh
cd backend
.venv/bin/python -m pytest -q          # 1,124 tests, offline: no paid calls
cd ../frontend
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Pytest never reads your `backend/.env`. `backend/tests/conftest.py` forces mock mode, blank keys and a temporary database, so the test suite cannot trigger paid model or Browser Use calls.

## Study tools (optional)

Open http://localhost:3000/research and enter `BEANY_RESEARCH_KEY` from `backend/.env` to start scenario sessions and export anonymous CSV logs. This is not needed to try the core task.

## Limits

- This is a local, single-worker research prototype, not a production deployment. There are no user accounts; session IDs act as local access tokens.
- LLM extraction is probabilistic. Quote grounding prevents invented preferences but cannot prove semantic correctness, which is why the needs summary is editable.
- Mock mode uses keyword matching and does not represent the real conversation quality. Use the hosted version or Option B for that.
- Live search covers only the allowlisted retailers and Shopify's catalogue, and compares a bounded shortlist rather than every listing. Risk signals are indicators, not proof of fraud or safety.
- All checkout and receipts are simulated. Do not enter real personal or payment data.

---

# Technical reference

The sections below document configuration and behaviour in more detail. For every setting, see [docs/configuration-guide.md](docs/configuration-guide.md) and [docs/browser-use-search.md](docs/browser-use-search.md).

Editable configuration:

- Conversation instructions: `backend/config/prompts/dialogue.txt`
- Policy thresholds: `backend/config/policy.json`; rule logic: `backend/app/runtime/policy.py`
- Fictional products and merchants: `backend/data/products/catalogue.json`, `backend/data/merchants/merchants.json`
- Website reputation registries: `backend/data/sites/site_registry.json` (fictional sites) and `backend/data/sites/live_site_registry.json` (live retailers)
- Scenarios: `backend/data/scenarios/scenarios.json`
- Replay fixture: `backend/data/replay/study_listings.json`, rebuilt by `python -m scripts.build_replay_fixture`

The older learning modules (`workflow.py`, `review.py`, `checkout.py`, `shopping_service.py`, `legacy_main.py`) are kept only as exercises and regression references. The integrated app (`app.main`) does not import LangGraph, and `legacy_main.py` must not be used as the participant backend.

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

Needs are matched tolerantly for live listings (`app/runtime/feature_match.py`,
`app/runtime/feature_check.py`, `policy.status()`). Rules come first. A feature or use counts
when the listing's name, description, attributes, specifications or sizes show the same concept
(noise control, comfort, portability, durability, water resistance, battery, sound, storage) or
most of its words; hyphenated words compare by their parts. A size matches when written
differently ("7-8 years" = "7-8 Years", "7T-8T", "7-8 jaar"), when age ranges overlap (months
convert to years) or when letter sizes agree (M = Medium); a clearly different size does not.
A brand matches the brand field, or the title when that field is empty (Shopify listings). A seller
matches its name or the listing's host ("amazon" matches "Amazon US (www.amazon.sg)"); this also
applies to restricted sellers in settings. Features, size and use the rules cannot settle go to one
batched LLM call per search, must-have or preferred, so a clearly met preference is shown as met.
Each verdict is met, absent or unstated and must quote the listing; an ungrounded or skipped verdict
counts as unstated. Only must-have needs exclude: absent excludes the listing, unstated keeps it
with a REVIEW note, and if the model is unavailable an unconfirmed must-have feature still
excludes while an unconfirmed size is kept for review. A required brand the listing doesn't show
is reviewed, not excluded. Provider-inferred features and selling points never confirm a need.
Catalogue products keep exact attribute matching for features. The offer card's "How this matches
your needs" chips show these verdicts (`feature_fit`, one entry per need with its `kind`).

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

After an edit that only narrows the needs (a lower or newly added budget, a newly excluded brand, or a
need switched between must-have and preferred), the next search first rechecks the current batch,
the listings from the latest search, against the new needs (`reusable()` and `narrows()` in
`app/runtime/discovery.py`). Earlier batches are never brought back: they were fetched for other
needs. If at least three listings in the batch are eligible (`REUSE_MINIMUM`, a full shortlist) they
are used without a new search. A new search runs and its listings replace the batch otherwise:
after any edit that asks for listings the last search never looked for (a higher or removed budget,
added or removed features, a new usage, size, preferred brand or seller, category or currency), when
the needs are unchanged since the last search or recheck (the user asks again, including "search
again" or "find something else" after rejecting an offer), when fewer than three listings still
qualify, or when the batch is older than 25 minutes (snapshots older than 30 minutes cannot check
out). Needs are compared ignoring case, spacing and list order. A batch from a search where one source
failed is still rechecked. Reuse is logged as a `search_reuse` event and shown as "Rechecked N offers
from your last search".

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
to the models in the saved shortlist; they cannot introduce unscreened models. In catalogue mode,
every other eligible seller of a shortlisted model can also be compared (screening keeps one seller
per model); live listings stay limited to the screened shortlist.

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
