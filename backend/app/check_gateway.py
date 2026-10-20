"""Opt-in SoCLaaS connectivity/capability probe. Does not launch the app."""

import argparse, json
from dataclasses import replace
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from .runtime.gateway import (
    Settings,
    make_client,
    structured_call,
    LLMError,
    safe_error,
)


class Ping(BaseModel):
    status: Literal["ok"]


def main():
    parser = argparse.ArgumentParser(
        description="Verify the configured gateway; generation probes may consume credits."
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Test selected model and structured transport",
    )
    parser.add_argument(
        "--probe-all",
        action="store_true",
        help="Test Responses, Chat schema/JSON/text, and function calling against the SAME endpoint/model",
    )
    args = parser.parse_args()
    try:
        settings = Settings.load(require_model=args.generate or args.probe_all)
    except LLMError as exc:
        parser.error(str(exc))
    report = {
        "base_url": settings.base_url,
        "model": settings.model,
        "capabilities": {},
    }
    client = make_client(settings)
    try:
        try:
            report["models"] = [m.id for m in client.models.list()]
        except Exception as exc:
            report["models_status"] = safe_error(exc)
    finally:
        client.close()
    modes = [(settings.api, settings.structured)] if args.generate else []
    if args.probe_all:
        modes = [
            ("responses", "schema"),
            ("chat", "schema"),
            ("chat", "json"),
            ("chat", "text"),
        ]
    for api, structured in modes:
        name = f"{api}:{structured}"
        try:
            structured_call(
                Ping,
                'Return the JSON object {"status":"ok"}.',
                {"task": "connectivity probe"},
                replace(settings, api=api, structured=structured),
            )
            report["capabilities"][name] = {"verified": True}
        except LLMError as exc:
            report["capabilities"][name] = {"verified": False, "error": str(exc)}
    if args.probe_all:
        schema = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["ok"]}},
            "required": ["status"],
            "additionalProperties": False,
        }
        for api in ("responses", "chat"):
            client = make_client(settings)
            try:
                if api == "responses":
                    result = client.responses.create(
                        model=settings.model,
                        input="Call report_status with status ok.",
                        tools=[
                            {
                                "type": "function",
                                "name": "report_status",
                                "description": "Connectivity probe only; no action is executed.",
                                "parameters": schema,
                            }
                        ],
                        tool_choice={"type": "function", "name": "report_status"},
                        store=False,
                    )
                    calls = [x for x in result.output if x.type == "function_call"]
                    valid = (
                        bool(calls)
                        and calls[0].name == "report_status"
                        and Ping.model_validate_json(calls[0].arguments).status == "ok"
                    )
                else:
                    result = client.chat.completions.create(
                        model=settings.model,
                        messages=[
                            {
                                "role": "user",
                                "content": "Call report_status with status ok.",
                            }
                        ],
                        tools=[
                            {
                                "type": "function",
                                "function": {
                                    "name": "report_status",
                                    "description": "Connectivity probe only; no action is executed.",
                                    "parameters": schema,
                                },
                            }
                        ],
                        tool_choice={
                            "type": "function",
                            "function": {"name": "report_status"},
                        },
                    )
                    calls = result.choices[0].message.tool_calls or []
                    valid = (
                        bool(calls)
                        and calls[0].function.name == "report_status"
                        and Ping.model_validate_json(calls[0].function.arguments).status
                        == "ok"
                    )
                report["capabilities"][api + ":function_calling"] = {"verified": valid}
            except Exception as exc:
                report["capabilities"][api + ":function_calling"] = {
                    "verified": False,
                    "error": safe_error(exc),
                }
            finally:
                client.close()
    print(json.dumps(report, indent=2))
    if any(not c["verified"] for c in report["capabilities"].values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
