"""Sanitized provider diagnostics; no raw response data reaches logs or chat."""
import json
import logging
from uuid import uuid4
from .gateway import LLMError

USER_MESSAGE = "My product-search agent isn’t available right now, so I couldn’t finish your search. Your shopping preferences are saved. You can try again later."
ACTIONS = {
    "credits": "Browser Use reports insufficient credits. Check billing and top up before retrying.",
    "access": "Check Browser Use credentials and access permissions.",
    "rate_limit": "Wait for the Browser Use rate limit before retrying.",
    "timeout": "Search timed out. Inspect the provider run before retrying.",
    "unavailable": "Browser Use could not be reached or is unavailable. Retry later.",
    "invalid_output": "Inspect the Browser Use run output and output schema.",
    "failed_run": "Inspect the failed Browser Use run in the provider dashboard.",
    "unknown": "Check Browser Use configuration and the provider dashboard.",
}

class SearchProviderError(LLMError):
    def __init__(self, reason, status=None, run_id=None, *, provider="browser_use", retry_after=None):
        self.provider = provider
        self.retry_after = retry_after
        self.reason = reason
        self.status = status
        self.run_id = run_id
        self.reference = str(uuid4())
        super().__init__(ACTIONS[reason] if provider == "browser_use" else "Shopify catalog is unavailable. Check access, rate limits or configuration.")


def provider_reason(data, status=None):
    # Recognize explicit machine codes only, never infer credits from a generic failure.
    code = data.get("code", "") if isinstance(data, dict) else ""
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        code = error.get("code", code)
    if code in ("insufficient_credits", "INSUFFICIENT_CREDITS", "insufficient_balance", "billing_error", "payment_required"):
        return "credits"
    if status in (401, 403): return "access"
    if status == 429: return "rate_limit"
    if status in (408, 504): return "timeout"
    if status and status >= 500: return "unavailable"
    return "unknown"


def report_failure(session, exc):
    from .schemas import Event
    detail = {"provider": exc.provider, "retry_after": exc.retry_after, "reason": exc.reason, "http_status": exc.status,
              "run_id": exc.run_id, "reference": exc.reference}
    logging.getLogger("uvicorn.error").warning("Search failure %s: %s", json.dumps(detail), str(exc))
    session.events.append(Event(kind="search_failure", detail=json.dumps(detail)))
