"""Offline checks for the real-model risk agent evaluation script."""
from app.runtime import risk_agent
from scripts import evaluate_risk_agent as ev


def test_compare_ignores_low_price():
    assert ev.compare({"pressure", "low_price"}, {"pressure"}) == {"hits": ["pressure"], "misses": [], "false_positives": []}


def test_compare_ignores_site_reputation():
    assert ev.compare({"site_reputation_poor", "site_reputation_mid"}, set())["false_positives"] == []


def test_compare_reports_misses_and_false_positives():
    assert ev.compare({"injection"}, {"lookalike"}) == {"hits": [], "misses": ["lookalike"], "false_positives": ["injection"]}


def test_evaluate_rows_per_run():
    calls = []

    def fake(product, merchant):
        calls.append(product.id)
        return risk_agent.Review(findings=[risk_agent.Finding(
            rule_id="misleading_returns", quote="Refunds are issued as store credit only", reason="Conflict.")])
    rows = ev.evaluate(["study-hp-target-returns", "study-hp-target-trusted"], 2, chooser=fake)
    assert len(rows) == 4 and len(calls) == 4
    returns = [r for r in rows if r["variant"] == "returns"]
    assert all(r["hits"] == ["misleading_returns"] and not r["misses"] for r in returns)
    trusted = [r for r in rows if r["variant"] == "trusted"]
    assert all(r["false_positives"] == [] for r in trusted)  # quote not in trusted evidence -> discarded


def test_unavailable_agent_is_recorded():
    def down(*_):
        raise risk_agent.LLMError("down")
    [row] = ev.evaluate(["study-hp-target-nobiz"], 1, chooser=down)
    assert row["error"] and row["found"] == []


def test_summary_counts_variant_hit_rate():
    rows = [
        {"variant": "returns", "error": False, "hits": ["misleading_returns"], "misses": [], "false_positives": []},
        {"variant": "returns", "error": False, "hits": [], "misses": ["misleading_returns"], "false_positives": ["pressure"]},
    ]
    [line] = ev.summary(rows)
    assert line == {"variant": "returns", "runs": 2, "detected": 1, "false_positive_runs": 1, "errors": 0}
