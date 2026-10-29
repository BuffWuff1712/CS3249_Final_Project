"""Site registry and website reputation (docs/data/2026-10-29-website-reputation-design.md)."""

import json
import pytest
from pydantic import ValidationError
from app.runtime import sites
from app.runtime.merchants import MERCHANT_PATH, merchants


def test_registry_entries_validate_and_are_unique():
    reg = sites.registry()
    assert len(reg) == 10 and all(d.endswith(".test") for d in reg)


def test_registry_rejects_duplicates_and_unknown_tier(tmp_path, monkeypatch):
    entry = json.loads(sites.REGISTRY_PATH.read_text(encoding="utf-8-sig"))[0]
    path = tmp_path / "sites.json"
    monkeypatch.setattr(sites, "REGISTRY_PATH", path)
    path.write_text(json.dumps([entry, entry]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate site domain"):
        sites.registry()
    path.write_text(json.dumps([{**entry, "tier": "great"}]), encoding="utf-8")
    with pytest.raises(ValidationError):
        sites.registry()


@pytest.mark.parametrize("url,domain", [
    ("https://shopverse.test/store/daily-flash-picks", "shopverse.test"),
    ("https://Shopverse.test/store/x/", "shopverse.test"),
    ("https://northline-outfitters.test", "northline-outfitters.test"),
])
def test_site_for_matches_exact_host(url, domain):
    assert sites.site_for(url).domain == domain


@pytest.mark.parametrize("url", [
    "https://www.shopverse.test",
    "https://shopverse.test:8080",
    "https://trusted-sports.test",
    "not a url",
])
def test_site_for_returns_none(url):
    assert sites.site_for(url) is None


def test_merchants_get_sites_but_records_do_not_store_them():
    raw = json.loads(MERCHANT_PATH.read_text(encoding="utf-8-sig"))
    assert all("site" not in m for m in raw)
    assert merchants()["study-m-trusted"].site.tier == "good"
    assert merchants()["demo-store"].site is None


# --- Rules and policy defaults (spec §4) -------------------------------------

from app.runtime import merchant_risk, merchants as merchants_module, risk_agent, service  # noqa: E402
from app.runtime.merchant_risk import RiskConfig, assess, assess_live, load_config, session_config, site_evidence  # noqa: E402
from app.runtime.policy import catalogue  # noqa: E402
from app.runtime.schemas import Session, Site  # noqa: E402

MID = Site(domain="dealbazaar.test", name="DealBazaar", kind="marketplace", tier="mid",
           label="Loosely regulated marketplace",
           summary="Loosely regulated sellers; product quality varies; refunds are inconvenient.")
POOR = Site(domain="best-gear-outlet.test", name="Best Gear Outlet", kind="independent", tier="poor",
            label="Little-known website",
            summary="This website is rarely mentioned anywhere and has almost no independent buyer reports.")


def neutral_on(site):
    return merchants()["study-m-neutral"].model_copy(update={"site": site})


def neutral_offer():
    return next(p for p in catalogue(Session()) if p.id == "study-hp-target-neutral")


def test_site_evidence_by_tier():
    config = load_config()
    good = merchants()["study-m-neutral"]
    assert good.site.tier == "good" and site_evidence(good, config) == []
    assert site_evidence(neutral_on(None), config) == []
    [mid] = site_evidence(neutral_on(MID), config)
    assert (mid.rule_id, mid.weight) == ("site_reputation_mid", 1)
    assert mid.evidence == ("DealBazaar (dealbazaar.test) has a mixed website reputation. "
                            "Loosely regulated sellers; product quality varies; refunds are inconvenient.")
    [poor] = site_evidence(neutral_on(POOR), config)
    assert (poor.rule_id, poor.weight) == ("site_reputation_poor", 4)
    assert poor.evidence == ("Best Gear Outlet (best-gear-outlet.test) has a poor website reputation. "
                             "This website is rarely mentioned anywhere and has almost no independent buyer reports.")


def test_policy_defaults_for_site_tiers():
    p, config = neutral_offer(), load_config()
    assert assess(p, neutral_on(MID), [p], config).recommended_decision == "ALLOW"
    poor = assess(p, neutral_on(POOR), [p], config)
    assert poor.recommended_decision == "REVIEW" and poor.level == "MEDIUM"


def test_ai_mode_adds_site_evidence():
    p = neutral_offer()
    r = assess_live(p, neutral_on(POOR), [p], load_config(), risk_agent.Review(findings=[]))
    assert {e.rule_id for e in r.evidence} == {"site_reputation_poor"}


def test_cached_ai_review_still_adds_site_evidence(monkeypatch):
    real = merchants_module.registry()
    monkeypatch.setattr(merchants_module, "registry",
                        lambda: {**real, "harbour-lane-goods.test": POOR.model_copy(update={"domain": "harbour-lane-goods.test"})})
    monkeypatch.setenv("BEANY_RISK_DETECTION", "ai")
    monkeypatch.setenv("BEANY_LLM_MODE", "openai")
    calls = []
    monkeypatch.setattr(risk_agent, "ask_model", lambda product, merchant: calls.append(1) or risk_agent.Review(findings=[]))
    s = service.create()
    for _ in range(2):
        service.propose(s, next(x for x in catalogue(s) if x.id == "study-hp-target-neutral"))
        assert {e.rule_id for e in s.proposals[-1].risk.evidence} == {"site_reputation_poor"}
    assert calls == [1]


def test_old_session_snapshot_without_site_weights_still_loads():
    old = load_config().model_dump()
    for rule in ("site_reputation_mid", "site_reputation_poor"):
        del old["weights"][rule]
    s = Session(experiment={"risk_config": old})
    assert session_config(s).weights["site_reputation_poor"] == 0


def test_researcher_config_must_list_site_rules():
    cfg = load_config().model_dump()
    del cfg["weights"]["site_reputation_mid"]
    with pytest.raises(ValidationError):
        RiskConfig.model_validate(cfg)
