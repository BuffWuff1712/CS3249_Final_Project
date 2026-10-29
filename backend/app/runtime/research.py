"""Research-only label joins and evaluation. Never imported by search or LLM modules."""

import csv, io, json
from .policy import ROOT
from .merchant_risk import RiskConfig, load_config, digest, stored_config
from .schemas import Model, Field

TRUTH_PATH = ROOT / "data/research/merchant_ground_truth.json"


class ExperimentUpdate(Model):
    profile_id: str = "standard"
    risk_config: RiskConfig | None = None


class Observation(Model):
    proposal_id: str
    understood: bool | None = None
    responded_appropriately: bool | None = None


def profiles():
    return json.loads(
        (ROOT / "config/cui_profiles.json").read_text(encoding="utf-8-sig")
    )


def configure(s, update):
    from .service import invalidate, event

    profile = next((p for p in profiles() if p["id"] == update.profile_id), None)
    if not profile:
        raise ValueError("Unknown experimental profile")
    config = update.risk_config or load_config()
    config = RiskConfig.model_validate(
        {**config.model_dump(), "explanation_detail": profile["explanation_detail"]}
    )
    s.experiment.setdefault("configuration_history", {})[digest(config)] = {
        "profile": profile["id"],
        "risk_config": config.model_dump(),
    }
    invalidate(s)
    s.stage = "ready"
    s.experiment = {
        **s.experiment,
        "profile": profile["id"],
        "risk_config": config.model_dump(),
        "config_hash": digest(config),
    }
    event(
        s,
        "experiment_updated",
        "Researcher updated the experimental configuration; prior pending actions invalidated.",
    )


def evaluate_rows(rows):
    # A binary operating point, not an assertion that all malicious merchants are detectable.
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    matrix = {
        label: {level: 0 for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
        for label in ("TRUSTWORTHY", "UNCERTAIN", "SUSPICIOUS", "MALICIOUS")
    }
    for row in rows:
        if (
            row["ground_truth"] not in matrix
            or row["predicted_risk"] not in matrix[row["ground_truth"]]
        ):
            continue
        actual = row["ground_truth"] in ("SUSPICIOUS", "MALICIOUS")
        predicted = row["predicted_risk"] in ("HIGH", "CRITICAL")
        counts[
            "tp"
            if actual and predicted
            else "fn"
            if actual
            else "fp"
            if predicted
            else "tn"
        ] += 1
        matrix[row["ground_truth"]][row["predicted_risk"]] += 1
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    return {
        **counts,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "confusion_matrix": matrix,
        "binary_mapping": {
            "predicted_positive": ["HIGH", "CRITICAL"],
            "ground_truth_positive": ["SUSPICIOUS", "MALICIOUS"],
            "ground_truth_negative": ["TRUSTWORTHY", "UNCERTAIN"],
        },
        "unit": "presented proposal; repeated merchant offers are separate exposures",
    }


def profile_for(s, config_hash):
    """Profile of the configuration that produced config_hash, including pre-upgrade snapshots."""
    history = s.experiment.get("configuration_history", {})
    if config_hash in history:
        return history[config_hash].get("profile")
    for entry in history.values():
        try:
            if digest(stored_config(entry["risk_config"])) == config_hash:
                return entry.get("profile")
        except (KeyError, ValueError):
            continue
    return None


def report(s):
    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8-sig"))
    rows = []
    for event in s.events:
        if event.kind != "merchant_assessment":
            continue
        data = json.loads(event.detail)
        risk = data["risk"]
        pid = data["proposal_id"]
        a = next((a for a in s.proposals if a.id == pid), None)
        decisions = [
            e.kind
            for e in s.events
            if e.detail == pid and e.kind in ("approve", "reject", "alternative")
        ]
        obs = s.experiment.get("observations", {}).get(pid, {})
        label = truth["labels"].get(data["merchant_id"], "UNKNOWN")
        predicted = risk["level"] if risk else "UNAVAILABLE"
        rows.append(
            {
                "scenario_id": s.scenario_id,
                "participant_id": s.participant,
                "proposal_id": pid,
                "product_id": data["product_id"],
                "merchant_id": data["merchant_id"],
                "profile": profile_for(s, risk["config_hash"]) if risk else None,
                "configuration_version": risk["config_version"] if risk else None,
                "configuration_hash": risk["config_hash"] if risk else None,
                "risk_detection": s.risk_detection,
                "risk_basis": risk.get("basis", "rules") if risk else None,
                "predicted_risk": predicted,
                "ground_truth": label,
                "triggered_rules": [e["rule_id"] for e in risk["evidence"]]
                if risk
                else [],
                "evidence": risk["evidence"] if risk else [],
                "policy_decision": data["decision"],
                "warning_shown": data["warning"],
                "subsequent_action": decisions[-1]
                if decisions
                else a.status
                if a
                else "unknown",
                "threat_identified": predicted in ("HIGH", "CRITICAL")
                if label in ("SUSPICIOUS", "MALICIOUS")
                else None,
                "understood": obs.get("understood"),
                "responded_appropriately": obs.get("responded_appropriately"),
            }
        )
    return {
        "truth_version": truth["version"],
        "active_configuration": s.experiment,
        "rows": rows,
        "metrics": evaluate_rows(rows),
    }


def export_csv(s):
    rows = report(s)["rows"]
    out = io.StringIO()
    if not rows:
        return "participant_id,scenario_id,proposal_id\r\n"
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        safe = {}
        for k, v in row.items():
            text = (
                json.dumps(v)
                if isinstance(v, (list, dict))
                else ""
                if v is None
                else str(v)
            )
            safe[k] = (
                "'" + text
                if text.startswith(("=", "+", "-", "@", "\t", "\r"))
                else text
            )
        writer.writerow(safe)
    return out.getvalue()
