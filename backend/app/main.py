"""Integrated app. Earlier classroom prototype remains in legacy_main.py."""

import csv, io, json, os, secrets, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from .runtime import service, storage
from .runtime.diagnostics import RequestDiagnostics, context, log, span
from .runtime import cart
from .runtime.schemas import CartSelection, CartCheckout
from .runtime.schemas import (
    Chat,
    Decision,
    Edit,
    Permissions,
    Fact,
    Session,
    SessionView,
)
from .runtime.llm import LLMError
from .runtime.policy import ROOT, catalogue

app = FastAPI(title="Beany Shopping Oversight", version="1.0.0")
# CORS wraps diagnostics so generated error responses remain browser-readable.
app.add_middleware(RequestDiagnostics)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Research-Key"],
    expose_headers=["X-Request-ID"],
)


def rejected_response(status, exc):
    from fastapi.responses import JSONResponse
    import logging

    request_id = (context.get() or {}).get("request_id")
    log("request_rejected", level=logging.WARNING, status_code=status,
        error_type=type(exc).__name__)
    return JSONResponse(status_code=status, content={"detail": str(exc), "request_id": request_id})


@app.exception_handler(LLMError)
async def llm_error(request, exc):
    return rejected_response(503, exc)


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return rejected_response(409, exc)


@app.exception_handler(LookupError)
async def missing(request, exc):
    return rejected_response(404, exc)


def mutate(sid, fn):
    # Run one Uvicorn worker. The lock prevents lost updates and duplicate checkouts.
    with span("mutation"):
        waiting = time.monotonic()
        log("mutation_lock_waiting")
        with storage.lock:
            log("mutation_lock_acquired", wait_ms=round((time.monotonic() - waiting) * 1000))
            s = storage.load(sid)
            fn(s)
            with span("session_save"):
                storage.save(s)
            return s


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": os.getenv("BEANY_LLM_MODE", "openai"),
        "configured": all(
            os.getenv(k) for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")
        )
        or os.getenv("BEANY_LLM_MODE") == "mock",
    }


@app.post("/sessions/{sid}/cart", response_model=SessionView)
def add_cart(sid: str, body: CartSelection):
    return mutate(sid, lambda s: cart.add(s, body))


@app.delete("/sessions/{sid}/cart/{pid}", response_model=SessionView)
def remove_cart(sid: str, pid: str):
    def remove(s):
        s.cart = [i for i in s.cart if i.action.id != pid]
        service.event(s, "cart_removed", pid)
    return mutate(sid, remove)


@app.get("/sessions/{sid}/cart/review")
def review_cart(sid: str):
    with storage.lock:
        return cart.review(storage.load(sid))


@app.post("/sessions/{sid}/cart/checkout", response_model=SessionView)
def checkout_cart(sid: str, body: CartCheckout):
    return mutate(sid, lambda s: cart.checkout(s, body))


@app.post("/sessions", response_model=SessionView)
def create():
    with storage.lock:
        s = service.create()
        storage.save(s)
        return s


@app.get("/sessions/{sid}", response_model=SessionView)
def read(sid: str):
    return storage.load(sid)


@app.delete("/sessions/{sid}", status_code=204)
def delete(sid: str):
    with storage.lock:
        storage.load(sid)
        storage.delete(sid)


@app.post("/sessions/{sid}/messages", response_model=SessionView)
def chat(sid: str, body: Chat):
    return mutate(sid, lambda s: service.chat(s, body.text))


@app.post("/sessions/{sid}/cancel", response_model=SessionView)
def cancel(sid: str):
    def stop(s):
        service.invalidate(s)
        s.stage = "cancelled"
        service.event(s, "cancel", "Cancelled through explicit control")
        service.message(s, "Cancelled. No pending proposal can be approved.")

    return mutate(sid, stop)


@app.put("/sessions/{sid}/brief", response_model=SessionView)
def brief(sid: str, body: Edit):
    return mutate(sid, lambda s: service.edit(s, body.field, body.fact))


@app.put("/sessions/{sid}/permissions", response_model=SessionView)
def permissions(sid: str, body: Permissions):
    def update(s):
        service.invalidate(s)
        s.permissions = body
        s.stage = "ready"
        service.event(
            s, "permissions", "Permissions explicitly updated through controls"
        )

    return mutate(sid, update)


@app.post("/sessions/{sid}/products/{product_id}/propose", response_model=SessionView)
def choose(sid: str, product_id: str):
    def select(s):
        if product_id not in {p.id for p in s.recommendations}:
            raise ValueError("Search again before selecting this product.")
        product = next((p for p in catalogue(s) if p.id == product_id), None)
        if product is None:
            raise ValueError("Product unavailable")
        service.propose(s, product)

    return mutate(sid, select)


@app.post("/sessions/{sid}/proposals/{pid}/decision", response_model=SessionView)
def decide(sid: str, pid: str, body: Decision):
    return mutate(sid, lambda s: service.decide(s, pid, body))


def researcher(x_research_key: str = Header(default="")):
    expected = os.getenv("BEANY_RESEARCH_KEY", "")
    if not expected or not secrets.compare_digest(x_research_key, expected):
        raise HTTPException(
            403, "Researcher key required. Configure BEANY_RESEARCH_KEY on the backend."
        )


def scenarios():
    return json.loads(
        (ROOT / "data/scenarios/scenarios.json").read_text(encoding="utf-8-sig")
    )


@app.get("/research/scenarios", dependencies=[Depends(researcher)])
def list_scenarios():
    return scenarios()


@app.post(
    "/research/scenarios/{scenario_id}/sessions",
    response_model=SessionView,
    dependencies=[Depends(researcher)],
)
def study(scenario_id: str):
    spec = next((x for x in scenarios() if x["id"] == scenario_id), None)
    if spec is None:
        raise LookupError("Scenario not found")
    with storage.lock:
        s = service.create(search_provider="catalogue")
        s.scenario_id = scenario_id
        s.brief = {k: Fact.model_validate(v) for k, v in spec["initial_brief"].items()}
        s.permissions = Permissions.model_validate(spec["permissions"])
        service.message(s, spec["context"])
        service.event(s, "scenario_loaded", scenario_id)
        storage.save(s)
        return s


@app.post(
    "/research/sessions/{sid}/trigger",
    response_model=SessionView,
    dependencies=[Depends(researcher)],
)
def trigger(sid: str):
    def run(s):
        spec = next((x for x in scenarios() if x["id"] == s.scenario_id), None)
        if not spec or not spec["trigger_product"]:
            raise ValueError(
                "This scenario is conversation-driven. Send its user goal in chat."
            )
        product = next(p for p in catalogue(s) if p.id == spec["trigger_product"])
        service.propose(s, product, **spec["action"])
        service.event(s, "scenario_trigger", spec["id"])

    return mutate(sid, run)


@app.get("/research/sessions/{sid}/export", dependencies=[Depends(researcher)])
def export(sid: str):
    from datetime import datetime

    s = storage.load(sid)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "participant",
            "scenario",
            "seconds",
            "kind",
            "clarifications",
            "interventions",
        ]
    )
    # No free-text messages, preference values or model outputs in anonymised export.
    for e in s.events:
        writer.writerow(
            [
                s.participant,
                s.scenario_id or "",
                round(
                    (
                        datetime.fromisoformat(e.timestamp)
                        - datetime.fromisoformat(s.created_at)
                    ).total_seconds(),
                    3,
                ),
                e.kind,
                s.clarification_count,
                s.intervention_count,
            ]
        )
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="beany-events.csv"'},
    )


# All ground-truth access lives behind this dependency. Participant routes never join it.
from .runtime import research


@app.get("/research/profiles", dependencies=[Depends(researcher)])
def research_profiles():
    return {
        "profiles": research.profiles(),
        "risk_config": research.load_config().model_dump(),
    }


@app.put(
    "/research/sessions/{sid}/configuration",
    response_model=SessionView,
    dependencies=[Depends(researcher)],
)
def configure_study(sid: str, body: research.ExperimentUpdate):
    return mutate(sid, lambda s: research.configure(s, body))


@app.put(
    "/research/sessions/{sid}/observation",
    response_model=SessionView,
    dependencies=[Depends(researcher)],
)
def observation(sid: str, body: research.Observation):
    def save(s):
        if body.proposal_id not in {a.id for a in s.proposals}:
            raise LookupError("Proposal not found")
        s.experiment.setdefault("observations", {})[body.proposal_id] = (
            body.model_dump()
        )

    return mutate(sid, save)


@app.get("/research/sessions/{sid}/risk-report", dependencies=[Depends(researcher)])
def risk_report(sid: str):
    return research.report(storage.load(sid))


@app.get("/research/sessions/{sid}/risk-export", dependencies=[Depends(researcher)])
def risk_export(sid: str):
    return Response(
        research.export_csv(storage.load(sid)),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="beany-risk-results.csv"'
        },
    )


@app.post("/sessions/{sid}/alternative", response_model=SessionView)
def another_merchant(sid: str):
    def alternative(s):
        if s.proposals:
            previous = s.proposals[-1]
            if previous.status == "pending":
                previous.status = "rejected"
            s.rejected_products.append(previous.product.id)
            s.rejected_merchants.append(previous.product.merchant_id)
            service.event(s, "alternative", previous.id)
        service.propose(s)

    return mutate(sid, alternative)
