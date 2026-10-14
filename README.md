# Beany — AI does the shopping. You stay in control.

A CS3249 conversational interface prototype using Next.js/React/TypeScript/Tailwind and FastAPI/Pydantic. All products, merchants, and payments are fictional. No LLM, internet product search, order creation, or financial transactions are connected.

## Run locally (Windows PowerShell)

Prerequisites: Node.js 20.9+ and Python 3.11+. Run each server in its own terminal. Commands below start from this project directory.

Backend:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file .env --host 127.0.0.1 --port 8000
```

If Python is available as `python` instead of `py -3`, use `python -m venv .venv`. Alternatively, with uv installed: `uv venv .venv --python 3.12`, then `uv pip install --python .venv\Scripts\python.exe -r requirements.txt`.

Frontend (second terminal):

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open [localhost:3000](http://localhost:3000). Backend health: [localhost:8000/health](http://localhost:8000/health). Interactive API contracts: [localhost:8000/docs](http://localhost:8000/docs). Use `localhost` consistently for CORS. To change ports/origins, update the example environment values in your local files and restart both servers. Public frontend environment variables contain URLs only, never credentials.

macOS/Linux equivalent: `python3 -m venv .venv`, then `.venv/bin/python -m pip install -r requirements.txt` and `.venv/bin/python -m uvicorn app.main:app --reload --env-file .env`; use `cp` for copying environment files.

## Try the demonstration

1. Review and save boundaries. Defaults: SGD 150, Northstar/Everyday/Market Lane allowed, Market Lane restricted, Demo Visa allowed, substitutions and data sharing disabled.
2. Choose **Within budget**, enter a message and send. Approve records a simulated decision.
3. Try **Over budget** (SGD 189), **Substitution** (earbuds), or **Restricted merchant** (Market Lane). Each shows the specific affected boundary and disables approval. The backend also rejects direct attempts to bypass the disabled button.
4. Reject, or refine with a note. Refinement records your instruction and closes the old proposal; select a new scenario and send to create another selection. Alternatively, explicitly change and save a boundary to re-evaluate a pending proposal, then approve if all checks pass.
5. Expand Decision history to inspect proposals, policy checks, permission changes, and responses. Reset deletes the current session and creates a fresh one.

The selected scenario controls results. Arbitrary text is retained as conversation context but is not semantically interpreted. A new request supersedes the previous pending proposal. Guided mode displays individual activity steps; balanced groups comparison steps. Both require final review. Activity is a completed scripted trace, not streamed background execution. Currency mismatch blocks approval; currency selection does not convert prices.

## Structure and contracts

```text
frontend/src/app/             Page composition, lifecycle and styling
frontend/src/components/      PreferencesPanel and ProposalCard
frontend/src/lib/api.ts       Typed HTTP adapter
frontend/src/lib/contracts.ts Frontend DTO types
backend/app/main.py          API routes/session workflow
backend/app/models.py        Pydantic request/response contracts
backend/app/agent.py         ShoppingAgent protocol + fictional mock catalogue
backend/app/policy.py        Deterministic boundary evaluation
backend/app/explanations.py  Human-readable decision explanations
backend/app/store.py         In-memory sessions and timestamped audit events
backend/tests/test_api.py    Policy and API workflow tests
```

The canonical machine-readable contract is `GET /openapi.json`. Session responses contain `id`, `preferences`, `messages`, `proposals`, `activity`, and `audit`. Proposals include product details, payment/data intentions, status, violations, and explanation. All successful mutation routes return the full updated Session, except deletion (204).

| Route | Request | Purpose |
| --- | --- | --- |
| POST /sessions | none | Create independent session |
| GET /sessions/{id} | none | Read state |
| PUT /sessions/{id}/preferences | Preferences | Replace and recheck boundaries |
| POST /sessions/{id}/messages | `{ "text": "Find headphones", "scenario": "normal" }` | Add turn and proposal |
| POST /sessions/{id}/proposals/{pid}/decision | `{ "action": "approve", "note": "" }` | Record decision |
| DELETE /sessions/{id} | none | Delete session and audit |

For the decision body choose one action string: `approve`, `reject`, or `refine`. Invalid input returns 422; unknown session/proposal 404; blocked approval or already-resolved proposal 409. Frontend errors are shown with retry available on initial connection failure.

Implemented: multi-turn UI, editable saved permissions, product cards, deterministic checks, approval/rejection/refinement lifecycle, audit history, reset, loading/error states, responsive layout. Mocked: agent reasoning/search/comparison, catalogue, payments, and checkout. Data-sharing permission is policy-checked, but current catalogue proposals never request sharing. Payment selection in mock proposals is always Demo Visa; removing it blocks approval. No external data is shared.

Sessions are process-local and are lost on backend restart, browser refresh starts a new session, and there is no authentication. Run a single local worker; this is a local testing prototype, not a hosted service. Audit is prototype history, not tamper-proof compliance storage. Approvals refer to the boundary snapshot at the time of decision; later preference changes recheck pending proposals only.

## Checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run typecheck
npm run build
```

Manual UI checks: run all four scenarios; save a lower budget while a proposal is pending; reject and refine; use reset; stop the backend and confirm a visible error; test narrow/mobile viewport and keyboard focus. Production frontend can be run with `npm run start` after build.

Verified during initial implementation: 8 backend tests passed; frontend TypeScript checking and production build passed. Browser checks confirmed the budget warning with disabled approval, a normal proposal with successful simulated approval, and a stacked layout at 390px width. The test stack emits a Starlette warning about a future HTTP test-client migration; tests still pass. Other manual checks above remain a recommended user-testing checklist.

## Owner-led LangGraph integration sequence

1. Study the DTOs, workflow, and policy tests; keep the deterministic policy authoritative.
2. Implement a LangGraph adapter behind `ShoppingAgent`, starting with the same fictional catalogue. Extend its input to include intent, conversation, and saved boundaries explicitly; keep the mock adapter for repeatable tests.
3. Map graph progress/events into the activity and audit contracts, add cancellation and an approval interrupt, and recheck policy immediately before any consequential action. Preserve HTTP DTOs or version them deliberately.
4. Introduce SQLite behind the store boundary, session ownership/authentication, and concurrency safeguards before multi-user hosting.
5. Add permitted real product retrieval only after defining source, privacy, and tool permissions. Keep checkout simulated until separately scoped and authorized.
