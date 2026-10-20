# Beany — Conversational Shopping User Interface

Beany is a Conversational User Interface designed for agentic shopping and commerce built with Next.js and FastAPI.

An LLM model interprets conversations; Python controls permissions, product search, policy decisions and simulated checkout. Every product and merchant is fictional. No payment or real shopping service is connected.

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

For offline testing set `BEANY_LLM_MODE=mock`. This mode is visibly labelled and is not a substitute for real conversational evaluation. Missing credentials never silently activate it. The API key must never appear in frontend variables or Git. Only recent conversation and observable catalogue/merchant/risk data are sent to the configured model; hidden ground truth is never included.

## Using Beany

Start with a prompt or free text. Vague requests can trigger a clarification; specific requests search immediately. The brief records confirmed, suggested and unspecified values. Edit/remove preferences directly. Currency accepts SGD/USD; category accepts Running shoes, Headphones, Backpacks; list fields use commas. A hard budget is never bypassed by approval.

Permissions are changed explicitly through their own form. Guided mode always asks for approval. Balanced mode can perform simulated checkout automatically only when approval is disabled and every policy rule returns ALLOW. Missing budgets and unverified fictional merchants require review by default.

Any brief/permission edit supersedes pending proposals. Ask for options again to search with the new state. Approvals bind to a proposal ID and a hash of its complete product/payment/data-sharing details. Reject, request an alternative, refine through chat, or cancel. Receipts and state survive refresh/restart. Fresh session deletes the current session; export study logs first.

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

See `docs/architecture.md` and `docs/editing-guide.md` for details.

## Limits

This is a local, single-worker study application, not an internet deployment. Session UUIDs act as local access tokens; there is no participant account authentication. The researcher key protects study controls, not a production research-data security perimeter. SQLite stores raw conversation and model interpretations locally; anonymous CSV deliberately omits that free text. Researchers must manage consent, retention and local database access. Do not use real personal/payment data.

LLM extraction remains probabilistic. Confirmed changes need a supporting quote and pass deterministic field validation; quote matching cannot prove semantic correctness. The editable brief and receipts make interpretation inspectable. Unknown free-text requirements require review. Search uses deterministic keyword/brand matching, not semantic retrieval. USD requests may have no matches because the seeded catalogue uses SGD. Prices use fixed catalogue decimals; no real financial processing occurs.

Live endpoint probes and synthetic shopping turns were exercised against the selected NUS model. Broader conversational quality still requires human-reviewed evaluations. Automated tests validate deterministic behaviour and gateway contracts. LangGraph, MCP, RAG, website automation and real checkout are absent from the runtime.

## Merchant-risk extension

Separate product and merchant databases support fictional multi-merchant offers. Risk is predicted from observable signals; hidden labels are joined only in authenticated researcher reports. Configure thresholds, warning profiles, scenarios and evaluation using [docs/configuration-guide.md](docs/configuration-guide.md). The participant UI offers merchant details and a deterministic “Find another merchant” control. Every checkout still passes policy rechecks and action-specific approval checks.

After this upgrade, start a fresh shopping request/session before approving: older proposals do not contain merchant snapshots and must not inherit approval across the schema change.
