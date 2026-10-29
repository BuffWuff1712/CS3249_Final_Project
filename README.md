# Beany — Conversational Shopping User Interface

Beany is a Conversational User Interface designed for agentic shopping and commerce built with Next.js and FastAPI.

An LLM model interprets conversations; Python controls permissions, product search, policy decisions and simulated checkout. Every product and merchant is fictional. No payment or real shopping service is connected.

## Current CUI demo

Open **http://localhost:3000/shop** for the PRD v2 experience: headphones and running shoes, a compact editable needs summary, personalised comparative reasoning, optional source evidence, priority correction, exact-product seller changes, visible payment cautions and explicit offer selection. You can finish without opening evidence or entering checkout. All records are fictional.

This route runs entirely in the frontend with a bounded deterministic interpreter and the versioned `beany-cui-v3.0` fixtures in `frontend/src/lib/shoppingFixtures.ts`. No backend or API credentials are required. Run `npm install`, `npm run build` and `npm run start` from `frontend`, then open `/shop`; for development use `npm run dev`. It is a working interaction prototype, not open-ended LLM conversation or live web research.

Needs, the last request and any selected offer are stored in this browser. Refresh rechecks the offer against the current fixture and needs. Editing needs clears selection; `Start fresh` clears only this CUI decision. Storage failures are visible. Unsupported categories and USD requests ask for clarification, and budgets never silently increase.

The `/` route remains the classic backend-connected simulation described below. Its SQLite sessions, research exports, cart and receipts are independent of `/shop`. See the [demo/presentation script](docs/final-demo.md), [study protocol](docs/evaluation-guide.md), and [CUI delivery and verification notes](docs/cui-v2-delivery.md).

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

Open http://localhost:3000/research and enter the backend researcher key. Start a fresh scenario participant, open the participant interface, and trigger a predefined condition if applicable. Triggering a condition proposes a fixture product; it does not script the conversation. Refresh study results and export anonymous CSV. See `docs/evaluation-guide.md`.

## Editing and architecture

- Conversation instructions: `backend/config/prompts/dialogue.txt`
- Policy thresholds: `backend/config/policy.json`; rule logic: `backend/app/runtime/policy.py`
- Products: `backend/data/products/catalogue.json`
- Scenarios: `backend/data/scenarios/scenarios.json`
- UI: `frontend/src/app/page.tsx`, `frontend/src/components/Brief.tsx`, `frontend/src/app/globals.css`
- Backend state/orchestration: `backend/app/runtime/`
- Browser Use task and captured evidence fields: `backend/app/runtime/browser_search.py`, `backend/app/runtime/schemas.py` (`WebEvidence`)
- Live-listing risk review prompt and grounding: `backend/app/runtime/risk_agent.py`; weights and levels: `backend/config/merchant_risk_rules.json`
- Replay fixture: `backend/data/replay/study_listings.json`, rebuilt by `python -m scripts.build_replay_fixture`

See `docs/architecture.md` and `docs/editing-guide.md` for details.

## Limits

This is a local, single-worker study application, not an internet deployment. Session UUIDs act as local access tokens; there is no participant account authentication. The researcher key protects study controls, not a production research-data security perimeter. SQLite stores raw conversation and model interpretations locally; anonymous CSV deliberately omits that free text. Researchers must manage consent, retention and local database access. Do not use real personal/payment data.

LLM extraction remains probabilistic. Confirmed changes need a supporting quote and pass deterministic field validation; quote matching cannot prove semantic correctness. The editable brief and receipts make interpretation inspectable. Unknown free-text requirements require review. Search uses deterministic keyword/brand matching, not semantic retrieval. USD requests may have no matches because the seeded catalogue uses SGD. Prices use fixed catalogue decimals; no real financial processing occurs.

Live endpoint probes and synthetic shopping turns were exercised against the selected NUS model. Broader conversational quality still requires human-reviewed evaluations. Automated tests validate deterministic behaviour and gateway contracts. LangGraph, MCP, RAG and real checkout are absent from the runtime. Website automation is limited to optional, read-only Browser Use product search.

## Merchant-risk extension

Optional live product discovery is now available through Browser Use Cloud V4, disabled by default.
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
policy evaluation. See [the shopping workflow guide](docs/shopping-workflow.md) for tool contracts,
limits, audit events and offline testing. The new planner has offline regression coverage. Its
multi-step behaviour was exercised manually with DeepSeek (replay and live search), not yet with the NUS model.

Separate product and merchant databases support fictional multi-merchant offers. Risk is predicted from observable signals; hidden labels are joined only in authenticated researcher reports. Configure thresholds, warning profiles, scenarios and evaluation using [docs/configuration-guide.md](docs/configuration-guide.md). The participant UI offers merchant details and a deterministic “Find another merchant” control. Every checkout still passes policy rechecks and action-specific approval checks.

After this upgrade, start a fresh shopping request/session before approving: older proposals do not contain merchant snapshots and must not inherit approval across the schema change.
