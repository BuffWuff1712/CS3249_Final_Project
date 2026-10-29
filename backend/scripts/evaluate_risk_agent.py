"""Run the AI risk agent on study offers and compare its findings with the manifest.

Researcher tool, not a test: it calls the configured model (paid) unless a chooser
is supplied. Each run uses a fresh session, so no cached review is reused.
low_price and website reputation are ignored on both sides because code, not the agent, computes them.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from app.runtime import risk_agent
from app.runtime.local_evidence import review_view
from app.runtime.merchants import merchants
from app.runtime.policy import catalogue
from app.runtime.schemas import Session

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/research/risk_offer_manifest.json"
DEFAULT_ONLY = "study-hp-target-,study-rs-target-,study-bp-target-"
OUTPUT = ROOT / "data/raw/risk_agent_eval.json"


CODE_RULES = {"low_price", "site_reputation_mid", "site_reputation_poor"}


def compare(found, expected):
    found, expected = set(found) - CODE_RULES, set(expected) - CODE_RULES
    return {
        "hits": sorted(found & expected),
        "misses": sorted(expected - found),
        "false_positives": sorted(found - expected),
    }


def expected_signals():
    entries = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    return {e["product_id"]: set(e["signals"]) for e in entries}


def evaluate(product_ids, repeat, chooser=None):
    products = {p.id: p for p in catalogue(Session())}
    expected = expected_signals()
    by_merchant = merchants()
    rows = []
    for pid in product_ids:
        p = products[pid]
        merchant = by_merchant[p.merchant_id]
        view = review_view(p, merchant)
        want = expected.get(pid, set())  # trusted and neutral have no manifest entry
        for run in range(repeat):
            out = risk_agent.review(Session(), view, merchant, chooser=chooser)
            found = sorted({f.rule_id for f in out.findings}) if out else []
            rows.append({
                "product_id": pid,
                "variant": pid.rsplit("-target-", 1)[-1],
                "run": run,
                "error": out is None,
                "found": found,
                "expected": sorted(want - CODE_RULES),
                **compare(found, want),
            })
    return rows


def summary(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["variant"]].append(r)
    return [
        {
            "variant": v,
            "runs": len(rs),
            "detected": sum(1 for r in rs if not r["error"] and r["hits"] and not r["misses"]),
            "false_positive_runs": sum(1 for r in rs if r["false_positives"]),
            "errors": sum(1 for r in rs if r["error"]),
        }
        for v, rs in grouped.items()
    ]


def main(argv=None):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--only", default=DEFAULT_ONLY, help="Comma-separated product ID prefixes")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    prefixes = tuple(x.strip() for x in args.only.split(",") if x.strip())
    ids = [p.id for p in catalogue(Session()) if p.id.startswith(prefixes)]
    rows = evaluate(ids, args.repeat)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"rows": rows, "summary": summary(rows)}, indent=1), encoding="utf-8")
    print(f"{'variant':<14}{'runs':>6}{'detected':>10}{'false+':>8}{'errors':>8}")
    for line in sorted(summary(rows), key=lambda x: x["variant"]):
        print(f"{line['variant']:<14}{line['runs']:>6}{line['detected']:>10}{line['false_positive_runs']:>8}{line['errors']:>8}")
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
