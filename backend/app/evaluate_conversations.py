"""Opt-in paid LLM evaluation. Never invoked by pytest."""

import argparse, json, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from .runtime import service
from .runtime.policy import ROOT


def main():
    parser = argparse.ArgumentParser(
        description="Run human-review conversation evaluations (paid OpenAI calls)."
    )
    parser.add_argument("--output", default="data/llm-evaluation.json")
    args = parser.parse_args()
    if os.getenv("BEANY_LLM_MODE", "openai") != "openai" or not os.getenv(
        "OPENAI_API_KEY"
    ):
        parser.error(
            "Configure a real API key and BEANY_LLM_MODE=openai for this evaluation."
        )
    results = []
    for case in json.loads(
        (ROOT / "data/evaluation_conversations.json").read_text(encoding="utf-8-sig")
    ):
        s = service.create()
        error = None
        try:
            for turn in case["turns"]:
                service.chat(s, turn)
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)
        results.append(
            {
                "case": case,
                "model": os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
                "reasoning_effort": os.getenv("OPENAI_REASONING_EFFORT", "low"),
                "session": s.model_dump(),
                "error": error,
            }
        )
        print(case["id"] + ": " + ("error" if error else "ready for human review"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
