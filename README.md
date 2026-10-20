# Beany — conversational shopping oversight

Beany is a blue-themed Next.js + FastAPI research prototype: **AI does the shopping. You stay in control.** OpenAI interprets conversations; Python controls permissions, product search, policy decisions and simulated checkout. Every product and merchant is fictional. No payment or real shopping service is connected.

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

## OpenAI configuration

Create an API key in your OpenAI platform project at https://platform.openai.com/api-keys and configure billing/model access as needed. Put the key only in `backend/.env`:

```dotenv
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-5.6-luna
OPENAI_REASONING_EFFORT=low
BEANY_LLM_MODE=openai
BEANY_RESEARCH_KEY=choose-a-local-researcher-secret
```

`OPENAI_MODEL` may be changed to `gpt-5.6-terra` or another model supporting Responses Structured Outputs and the configured reasoning effort. Account access varies; API errors are shown as recoverable errors. There is no automatic model substitution. Missing keys never silently activate mock responses.

For explicit offline testing set `BEANY_LLM_MODE=mock`. The interface labels this mode; its intentionally limited parser is **not suitable for evaluating conversational intelligence**. Automated tests use this mode or injected structured responses and never need paid API calls.

The SDK uses `client.responses.parse(..., text_format=PydanticModel)` and `output_parsed`, verified against [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and the [requested model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna). Conversation state is held in SQLite; requests use `store=False`. Recent conversation and structured preferences are sent to OpenAI; avoid entering personal data.

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

Live model quality and account access require the human-review evaluation run with a valid key. Automated tests validate the integration contract, not real model behaviour. LangGraph, MCP, RAG, website automation and real checkout are absent from the runtime.
