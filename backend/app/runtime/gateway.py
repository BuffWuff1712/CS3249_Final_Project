"""Single client/transport boundary. No provider or model fallback."""

import json
import os
import logging
import math
from time import perf_counter
from uuid import uuid4
from dataclasses import dataclass, field
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel


TIMEOUT = 200
logger = logging.getLogger("uvicorn.error")


class LLMError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    api: str
    structured: str
    reasoning: str
    timeout: float = TIMEOUT

    @classmethod
    def load(cls, require_model=True):
        values = [
            os.getenv(k, "").strip()
            for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")
        ]
        if not all(values[:2]) or (require_model and not values[2]):
            raise LLMError(
                "Configure OPENAI_API_KEY, OPENAI_BASE_URL and OPENAI_MODEL in backend/.env, or explicitly use BEANY_LLM_MODE=mock."
            )
        url = urlparse(values[1])
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise LLMError(
                "OPENAI_BASE_URL must be an HTTPS endpoint without embedded credentials, query or fragment."
            )
        api = os.getenv("OPENAI_API_MODE", "responses")
        structured = os.getenv("OPENAI_STRUCTURED_MODE", "schema")
        if api not in ("responses", "chat") or structured not in (
            "schema",
            "json",
            "text",
        ):
            raise LLMError(
                "Use OPENAI_API_MODE=responses|chat and OPENAI_STRUCTURED_MODE=schema|json|text."
            )
        if api == "responses" and structured != "schema":
            raise LLMError(
                "Responses requires schema mode; use the explicit chat adapter for JSON/text compatibility."
            )
        try:
            timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", str(TIMEOUT)))
            if not math.isfinite(timeout) or not 10 <= timeout <= 600:
                raise ValueError()
        except ValueError:
            raise LLMError("OPENAI_TIMEOUT_SECONDS must be a number between 10 and 600.") from None
        return cls(
            *values, api, structured, os.getenv("OPENAI_REASONING_EFFORT", "").strip(), timeout
        )


def make_client(settings=None):
    from openai import OpenAI

    config = settings or Settings.load()
    # Do not follow redirects carrying credentials to another host.
    return OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout,
        max_retries=0,
        http_client=httpx.Client(follow_redirects=False, timeout=config.timeout),
    )


def safe_error(exc):
    from openai import (
        AuthenticationError,
        PermissionDeniedError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        APIStatusError,
    )

    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return "Gateway rejected the credentials or model access. Check your NUS API key and permissions."
    if isinstance(exc, RateLimitError):
        return "Gateway rate limit reached. Wait briefly before retrying."
    if isinstance(exc, APITimeoutError):
        return "Gateway timed out. Retry your message."
    if isinstance(exc, APIConnectionError):
        return "Cannot connect to the configured gateway. Check network/VPN access and OPENAI_BASE_URL."
    if isinstance(exc, APIStatusError):
        return f"Gateway returned HTTP {exc.status_code}. Check the configured model, API mode and structured-output capabilities. No provider/model switch occurred."
    return "The gateway returned malformed or incomplete structured output. Rephrase or check model capabilities."


def structured_call(schema: type[BaseModel], instructions: str, payload, settings=None):
    from .progress import cancellable_call
    return cancellable_call(lambda: _structured_call(schema, instructions, payload, settings))


def _structured_call(schema, instructions, payload, settings=None):
    from openai import OpenAIError

    config = settings or Settings.load()
    client = make_client(config)
    request_id = uuid4().hex[:12]
    started = perf_counter()
    status = "error"
    error_type = "none"
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    instructions += (
        "\nOUTPUT CONTRACT: Return exactly one valid JSON object, no markdown or prose outside it. All fields must match this schema: "
        + json.dumps(schema.model_json_schema(), separators=(",", ":"))
    )
    # Metadata only: never log prompts, responses, credentials, URLs or exception bodies.
    logger.info("llm_call_start id=%s stage=%s api=%s mode=%s timeout_s=%s input_chars=%s",
                request_id, schema.__name__, config.api, config.structured, config.timeout,
                len(instructions) + len(payload_json))
    try:
        if config.api == "responses":
            options = (
                {"reasoning": {"effort": config.reasoning}} if config.reasoning else {}
            )
            result = client.responses.parse(
                model=config.model,
                instructions=instructions,
                input=payload_json,
                text_format=schema,
                store=False,
                **options,
            )
            output = result.output_parsed
        else:
            options = {"reasoning_effort": config.reasoning} if config.reasoning else {}
            messages = [
                {"role": "system", "content": instructions},
                {"role": "user", "content": payload_json},
            ]
            if config.structured == "schema":
                result = client.chat.completions.parse(
                    model=config.model,
                    messages=messages,
                    response_format=schema,
                    **options,
                )
                if not result.choices or result.choices[0].finish_reason != "stop":
                    raise ValueError("Incomplete response")
                output = result.choices[0].message.parsed
            else:
                if config.structured == "json":
                    options["response_format"] = {"type": "json_object"}
                result = client.chat.completions.create(
                    model=config.model, messages=messages, **options
                )
                if not result.choices or result.choices[0].finish_reason != "stop":
                    raise ValueError("Incomplete response")
                output = schema.model_validate_json(
                    result.choices[0].message.content or ""
                )
        if output is None:
            raise ValueError("Missing parsed output or refusal")
        validated = schema.model_validate(output)
        status = "ok"
        return validated
    except (OpenAIError, ValueError, TypeError, IndexError) as exc:
        error_type = type(exc).__name__
        raise LLMError(safe_error(exc)) from exc
    finally:
        logger.info("llm_call_end id=%s stage=%s status=%s elapsed_s=%.3f error_type=%s",
                    request_id, schema.__name__, status, perf_counter() - started, error_type)
        client.close()
