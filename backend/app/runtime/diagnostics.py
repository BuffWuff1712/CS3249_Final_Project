"""Safe JSON diagnostics visible with Uvicorn's default logging configuration."""

import asyncio
import json
import logging
import time
import traceback
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from starlette.responses import JSONResponse

context = ContextVar("diagnostic_context", default=None)
logger = logging.getLogger("uvicorn.error")


def log(event, *, level=logging.INFO, **fields):
    # Callers supply only diagnostic metadata, never bodies or exception messages.
    logger.log(level, json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                                 "event": event, **(context.get() or {}), **fields}))


def failure_fields(exc):
    # Exception strings/chains can contain keys, model output or shopper text.
    return {
        "error_type": type(exc).__name__,
        "frames": [{"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
                   for f in traceback.extract_tb(exc.__traceback__)],
    }


@contextmanager
def span(stage):
    started = time.monotonic()
    log("stage_started", stage=stage)
    try:
        yield
    except Exception as exc:
        log("stage_failed", level=logging.ERROR, stage=stage,
            duration_ms=round((time.monotonic() - started) * 1000), **failure_fields(exc))
        raise
    else:
        log("stage_finished", stage=stage,
            duration_ms=round((time.monotonic() - started) * 1000))


class RequestDiagnostics:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        token = context.set({"request_id": request_id, "entry_point": "http"})
        started = time.monotonic()
        status, response_started = None, False

        async def tracked_send(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status, response_started = message["status"], True
                message["headers"] = [*message.get("headers", []),
                                      (b"x-request-id", request_id.encode())]
            await send(message)

        # Do not record raw paths: they may contain session IDs or arbitrary input.
        log("request_started", method=scope["method"])
        try:
            try:
                await self.app(scope, receive, tracked_send)
            except asyncio.CancelledError:
                log("request_cancelled", level=logging.WARNING)
                raise
            except Exception as exc:
                log("request_failed", level=logging.ERROR, **failure_fields(exc))
                if response_started:
                    raise
                response = JSONResponse(status_code=500, content={
                    "detail": f"The server could not complete this request. Reference: {request_id}",
                    "request_id": request_id,
                })
                await response(scope, receive, tracked_send)
        finally:
            route = scope.get("route")
            log("request_finished", route=getattr(route, "path", "unmatched"),
                status_code=status, duration_ms=round((time.monotonic() - started) * 1000))
            context.reset(token)
