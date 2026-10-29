# Website Reputation Risk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Local merchants get a website-reputation tier from a fictional site registry. Code turns `mid` and `poor` tiers into risk signals, and the merchant details show the tier as a three-cell meter.

**Architecture:** A registry file maps exact hosts to `Site` records. `merchants()` attaches them to local merchants as `Merchant.site`. A single `site_evidence()` feeds both `assess()` and `assess_live()`, so rules and AI modes agree. The study dataset is reassigned onto good sites, `lookalike` becomes a knockoff product, and three new variants (`site-mid`, `site-bad`, `site-fake`) carry the new signal. The frontend reads `merchant_details.site`.

**Tech Stack:** FastAPI and Pydantic 2 backend (pytest via `backend/.venv/bin/python`), Next.js and TypeScript frontend (Playwright, `tsc`).

**Spec:** `docs/data/2026-10-29-website-reputation-design.md`

## Global Constraints

- Work on branch `ywt`. End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push.
- Unit tests stay offline. `tests/conftest.py` already pins `BEANY_RISK_DETECTION=rules` and mock LLM mode.
- All names are fictional and all domains end in `.test`. Repo artifacts are written in English.
- Original fixtures (`shoe-*`, `audio-*`, `bag-*`, `offer-*`, merchants `demo-store` to `concealed`) keep their data unchanged and get no registry entry.
- Dataset tests (`test_study_dataset.py`) assert signals, prices and ground truth only, never levels or decisions. Policy defaults are asserted in risk tests.
- The risk agent never sees registry data. `local_evidence()` does not map `site`, and the two new rules stay out of `risk_agent.AGENT_RULES`.
- The rule IDs are `site_reputation_mid` (default weight 1) and `site_reputation_poor` (default weight 4). The tiers are `good`, `mid` and `poor`.
- Evidence text is `"{name} ({domain}) has a mixed website reputation. {summary}"` for `mid` and `"{name} ({domain}) has a poor website reputation. {summary}"` for `poor`.

## Review Focus

1. **A session created before this change** stores a `risk_config` snapshot without the two new weights. Today `RiskConfig` validation would reject it and block checkout. The expected behaviour is that the old session keeps working exactly as before. `session_config()` fills the missing `site_reputation_*` weights with 0 for stored snapshots only. Researcher-submitted JSON must still list every rule. Tested in Task 2.
2. **Host spelling:** a website such as `https://Shopverse.test/store/x/` (capital letters, trailing slash) still resolves to `shopverse.test`. A port (`shopverse.test:8080`) or a subdomain (`www.shopverse.test`) does not match. Tested in Task 1.
3. **AI mode with a cached review:** the cached branch of `policy.evaluate()` must include site evidence too, because it is code-computed and not cached. Tested in Task 2.
4. **A website value the browser cannot parse** must not crash the merchant details. The display falls back to the raw string. Tested in Task 5.
5. **A malformed registry**, such as a duplicate domain or an unknown tier, must fail loudly when the registry loads, not silently drop the signal. Tested in Task 1.

---

### Task 1: Site registry, schema and lookup

**Files:**
- Create: `backend/data/sites/site_registry.json`, `backend/app/runtime/sites.py`, `backend/tests/test_sites.py`
- Modify: `backend/app/runtime/schemas.py` (add `Site`; add `Merchant.site`), `backend/app/runtime/merchants.py` (attach sites)

**Interfaces:**
- Produces:
  - `class Site(Model)` with fields `domain: str`, `name: str`, `kind: Literal["marketplace", "independent"]`, `tier: Literal["good", "mid", "poor"]`, `label: str = Field(max_length=40)` and `summary: str = Field(max_length=200)`.
  - `Merchant.site: Site | None = None`.
  - `sites.REGISTRY_PATH` and `sites.registry() -> dict[str, Site]`, keyed by domain. It raises `ValueError("Duplicate site domain")` on duplicates.
  - `sites.site_for(url: str) -> Site | None`, which matches `urlparse(url).hostname` exactly, so case is folded by urlparse. A URL with a port does not match.
  - `merchants()` returns merchants with `site` set from the registry.

- [ ] **Step 1: Write the registry.** Add the entries from spec §2.2 except `north1ine-outfitters.test`, which is 10 entries. Each of the six small-business domains gets its own store's name, and `best-gear-outlet.test` gets "Best Gear Outlet". `north1ine-outfitters.test` is added in Task 4, because until Task 3 it is still the lookalike merchant's website and would give that offer an extra poor-site signal.
- [ ] **Step 2: Write the failing tests** in `tests/test_sites.py`:

```python
def test_registry_entries_validate_and_are_unique():
    reg = sites.registry()
    assert len(reg) == 10 and all(d.endswith(".test") for d in reg)  # 11 after Task 4

def test_registry_rejects_duplicates_and_unknown_tier(tmp_path, monkeypatch): ...
    # duplicate domain -> ValueError("Duplicate site domain"); tier "great" -> ValidationError

@pytest.mark.parametrize("url,domain", [
    ("https://shopverse.test/store/daily-flash-picks", "shopverse.test"),
    ("https://Shopverse.test/store/x/", "shopverse.test"),
    ("https://northline-outfitters.test", "northline-outfitters.test"),
])
def test_site_for_matches_exact_host(url, domain):
    assert sites.site_for(url).domain == domain

@pytest.mark.parametrize("url", ["https://www.shopverse.test", "https://shopverse.test:8080", "https://trusted-sports.test", "not a url"])
def test_site_for_returns_none(url):
    assert sites.site_for(url) is None

def test_merchants_get_sites_but_records_do_not_store_them():
    raw = json.loads(MERCHANT_PATH.read_text(encoding="utf-8-sig"))
    assert all("site" not in m for m in raw)
    assert merchants()["study-m-trusted"].site.tier == "good"
    assert merchants()["demo-store"].site is None
```

- [ ] **Step 3: Run** `cd backend && .venv/bin/python -m pytest tests/test_sites.py -q`. Expected: FAIL on import (`sites` missing).
- [ ] **Step 4: Implement** `Site`, `Merchant.site`, `sites.py`, and attach in `merchants()` with `m.model_copy(update={"site": site_for(m.website)})`. Cache `registry()` the same way `merchants()` reads its file. Reading the file on each call is acceptable at this size.
- [ ] **Step 5: Run** `tests/test_sites.py` and the full suite `.venv/bin/python -m pytest -q`. Expected: all pass. `test_local_evidence.py::test_no_flags_or_labels_leak` and the replay fixture stay green because `local_evidence()` does not map `site`.
- [ ] **Step 6: Commit:** `feat: add site registry and attach sites to local merchants`.

### Task 2: Rules, policy defaults and the knockoff definition

**Files:**
- Modify:
  - `backend/app/runtime/merchant_risk.py`: `RULES`, `site_evidence`, `assess`, `assess_live`, `session_config`, and the lookalike text.
  - `backend/config/merchant_risk_rules.json`: two weights, and bump `version` to `risk-v2`.
  - `backend/app/runtime/risk_agent.py`: the lookalike definition only.
  - `backend/scripts/evaluate_risk_agent.py`: `compare` ignores `site_reputation_*`.
  - `docs/configuration-guide.md`: the two new weights, and a note that stored sessions without them score them 0.
- Test: `backend/tests/test_sites.py`, `backend/tests/test_risk_agent.py`, `backend/tests/test_evaluate_risk_agent.py`

**Interfaces:**
- Consumes: `Merchant.site` (Task 1).
- Produces:
  - `merchant_risk.SITE_RULES = {"mid": "site_reputation_mid", "poor": "site_reputation_poor"}`.
  - `merchant_risk.site_evidence(merchant, config) -> list[RiskEvidence]`.
  - The rule text `"The product name and brand imitate another brand."`.
  - The agent line `"- lookalike: product names or brands imitating a well-known brand (knockoff products)."`.

- [ ] **Step 1: Write the failing tests** in `tests/test_sites.py`. Build test merchants with `merchants()["study-m-neutral"].model_copy(update={"site": Site(...)})` so this task does not depend on Task 3 data:

```python
def test_site_evidence_by_tier():
    # good -> []; mid -> one item, rule site_reputation_mid, weight 1,
    # evidence == "DealBazaar (dealbazaar.test) has a mixed website reputation. Loosely regulated sellers; product quality varies; refunds are inconvenient."
    # poor -> rule site_reputation_poor, weight 4, "... has a poor website reputation. ..."; site=None -> []

def test_policy_defaults_for_site_tiers():
    # assess() on a clean product+merchant: mid -> recommended_decision "ALLOW"; poor -> "REVIEW"; no safeguard block

def test_ai_mode_adds_site_evidence(monkeypatch):
    # assess_live(view, poor_merchant, ..., review=Review(findings=[])) evidence ids == {"site_reputation_poor"}

def test_cached_ai_review_still_adds_site_evidence(monkeypatch):
    # BEANY_RISK_DETECTION=ai; propose once with a chooser; evaluate again (cache hit) -> evidence still has site_reputation_poor

def test_old_session_snapshot_without_site_weights_still_loads():
    # s.experiment["risk_config"] = current config dump minus both site weights -> session_config(s).weights["site_reputation_poor"] == 0

def test_researcher_config_must_list_site_rules():
    # RiskConfig.model_validate(dump minus site_reputation_mid) raises ValidationError
```

  In `test_risk_agent.py`, extend `test_prompt_covers_local_fields`: assert the knockoff line is in `INSTRUCTIONS`, that `"seller names or badges imitating"` is not, and that the `site_reputation_*` rules are not in `AGENT_RULES`. In `test_evaluate_risk_agent.py`, `compare({"site_reputation_poor"}, set())` has no false positives.
- [ ] **Step 2: Run** these tests. Expected: FAIL (`site_evidence` is missing, and the config has no new weights).
- [ ] **Step 3: Implement.**
  - `site_evidence` uses the two exact strings from Global Constraints.
  - `assess()` and `assess_live()` extend their evidence with it before calling `score()`.
  - `session_config()` adds `0.0` for any `SITE_RULES` value missing from a stored snapshot's weights before validating.
  - Change the lookalike text in `assess()` and the definition in `risk_agent.INSTRUCTIONS`.
- [ ] **Step 4: Run** the full suite. Expected: all pass. `test_merchant_extension.py::test_risk_scenarios` keeps its decisions, because only the text changed.
- [ ] **Step 5: Commit:** `feat: score website reputation and redefine lookalike as knockoff`.

### Task 3: Move existing study merchants onto registered sites, and make lookalike a knockoff

**Files:**
- Modify:
  - `backend/data/merchants/merchants.json`: study merchants only.
  - `backend/data/products/catalogue.json`: the three `study-*-target-lookalike` offers.
  - `backend/tests/test_study_dataset.py`
  - `docs/data/2026-10-21-study-dataset-design.md`: a one-line note linking the new spec.
- Regenerate: `backend/data/replay/study_listings.json`

**Interfaces:**
- Consumes: `sites.registry()` and `Merchant.site` (Task 1), and the knockoff rule (Task 2).
- Produces: every existing study merchant resolves to a `good` site. Slugs follow `https://shopverse.test/store/<kebab-case merchant name>`.

- [ ] **Step 1: Write the failing tests** in `test_study_dataset.py`:

```python
PLACEMENT = {  # spec §2.2
    "trusted": "northline-outfitters.test",
    **{v: "shopverse.test" for v in ["lowprice", "nobiz", "external", "pressure", "inconsistent", "injection", "concealed", "lookalike"]},
    **{v: "own" for v in ["neutral", "benign", "payment", "returns", "data-mid", "data-high"]},
}

@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_study_merchant_site_is_registered(v):
    m = merchants()[f"study-m-{v}"]
    assert m.site is not None
    assert ("/store/" in m.website) == (m.site.kind == "marketplace")

@pytest.mark.parametrize("v", [v for v in ALL_MERCHANT_KEYS if not any(s.startswith("site_reputation") for s in EXPECTED[v]["signals"])])
def test_single_signal_variants_sit_on_good_sites(v):
    assert merchants()[f"study-m-{v}"].site.tier == "good"

def test_placement_matches_spec(): ...  # "own" means kind == "independent", domain is not shopverse/dealbazaar, and it is not shared with another merchant

@pytest.mark.parametrize("v", ALL_MERCHANT_KEYS)
def test_merchant_text_names_only_its_own_host(v):
    # every *.test host found in contact/description/return_policy/checkout_note/reviews == m.site.domain

@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_lookalike_is_a_knockoff(cat):
    # name/brand differ from trusted (Lumin Hush ANC/Lumin, Vella Tempo Daily/Vella, Atlis Scholar 30/Atlis);
    # "Same design as the <trusted name> at a fraction of the price." in description;
    # specifications, attributes, rating, rating_count equal trusted
```

  Also make these changes:
  - `test_offers_share_product_fields`: skip `name` and `brand` for `lookalike`.
  - Add these names to `BRAND_DENYLIST`: "eBay", "Pinduoduo", "Temu", "Lazada", "Shopee", "Taobao", "AliExpress". "Amazon" is already listed.
  - Extend `test_no_real_brands_or_placeholder_text` to also scan registry `name`, `label` and `summary`.
- [ ] **Step 2: Run** `tests/test_study_dataset.py`. Expected: FAIL. Placement, knockoff and the old websites all fail.
- [ ] **Step 3: Edit the data.**
  - Rewrite `website`, and any `contact`, description or review text naming an old domain, for the merchants in `PLACEMENT`. Platform store email: `<slug>@shopverse.test`.
  - nobiz moves to `shopverse.test/store/topbuy-express` and stays without contact.
  - `study-m-lookalike` becomes "Brightway Goods" at `shopverse.test/store/brightway-goods`, with an ordinary description, and keeps `lookalike_identity: true`.
  - Each lookalike offer gets its knockoff name and brand, plus the imitation line appended to its description.
- [ ] **Step 4: Regenerate the replay fixture:** `cd backend && .venv/bin/python -m scripts.build_replay_fixture`.
- [ ] **Step 5: Run** the full suite. Expected: all pass, including `test_search_ranks_variant_first`, `test_signals_hold_in_wider_scopes`, `test_study_brands_absent_from_old_fixtures` and the replay tests.
- [ ] **Step 6: Commit:** `feat: place study merchants on registered sites and make lookalike a knockoff`.

### Task 4: Three website-reputation variants

**Files:**
- Modify:
  - `backend/data/merchants/merchants.json`
  - `backend/data/products/catalogue.json`
  - `backend/data/research/risk_offer_manifest.json`
  - `backend/data/research/merchant_ground_truth.json`
  - `backend/tests/test_study_dataset.py`
  - `backend/data/README.md`: registry row, the variant table with the three new rows and the changed `lookalike` row, and the editing rule "Every study merchant's domain must be in `data/sites/site_registry.json`; existing variants stay on good sites."
- Regenerate: `backend/data/replay/study_listings.json`

**Interfaces:**
- Consumes: the registry entries `dealbazaar.test` and `best-gear-outlet.test` (Task 1), the rules (Task 2), and `PLACEMENT` (Task 3).
- Adds: the registry entry `north1ine-outfitters.test` (spec §2.2), so `test_registry_entries_validate_and_are_unique` now expects 11.
- Produces: merchants `study-m-site-mid`, `study-m-site-bad` and `study-m-site-fake`, and offers `study-{hp,rs,bp}-target-{site-mid,site-bad,site-fake}`.

- [ ] **Step 1: Write the failing tests.** Add the three variants to `VARIANTS` and `PLACEMENT`, then make these changes:
  - `EXPECTED`:
    - `"site-mid": {"signals": ["site_reputation_mid"], "ground_truth": "UNCERTAIN"}`
    - `"site-bad": {"signals": ["site_reputation_poor"], "ground_truth": "SUSPICIOUS"}`
    - `"site-fake": {"signals": ["site_reputation_poor"], "ground_truth": "MALICIOUS"}`
  - `RATIOS`: `site-mid` 0.75, `site-bad` 0.80, `site-fake` 0.80.
  - `test_manifest_complete` expects 48 entries.
  - Add `site-mid`, `site-bad` and `site-fake` to `test_clean_merchants_have_clean_fields`.
  - New test: `study-m-site-fake.name == "Northline Outfitters"` and its website host is `north1ine-outfitters.test`.
- [ ] **Step 2: Run** `tests/test_study_dataset.py`. Expected: FAIL on missing merchants and offers.
- [ ] **Step 3: Add the data.**
  - **Merchants:** clean fields like neutral: verified, contact on their own host, Demo Visa and Demo Wallet, standard returns, and 3 to 5 merchant reviews about ordinary store conduct.
    - site-mid is at `dealbazaar.test/store/<slug>`.
    - site-fake copies trusted's name and its type of description, in its own words.
  - **Offers:** the target's shared fields; prices at the ratios, rounded to x.9 like the existing offers; 3 product reviews of their own, consistent with the specs, sharing at most one with any other offer.
  - **Manifest:** `visible_in: ["website_reputation"]`, and `reference_set` set to trusted and neutral.
  - **Ground truth:** labels for the three new merchants.
- [ ] **Step 4: Regenerate the replay fixture**, then run the full suite. Expected: all pass.
- [ ] **Step 5: Commit:** `feat: add website reputation study variants`.

### Task 5: Merchant details meter

**Files:**
- Modify: `frontend/src/lib/beany.ts`, `frontend/src/components/MerchantDetails.tsx` (catalogue branch only), `frontend/src/app/globals.css`
- Create: `frontend/tests/site-reputation.spec.ts`

**Interfaces:**
- Consumes: `merchant_details.site` in the session JSON (Task 1).
- Produces:
  - `export type Site = { domain: string; name: string; kind: "marketplace" | "independent"; tier: "good" | "mid" | "poor"; label: string; summary: string }` and `site?: Site | null` on `Merchant`.
  - `websiteHost(url: string): string`, which returns `new URL(url).host`, or the raw string if parsing throws.

- [ ] **Step 1: Write the failing Playwright test.** Create a session with `request.post`, then send "Find headphones under $150" to `/sessions/{id}/messages` (mock mode proposes an offer). Set `localStorage` like `shopping.spec.ts`. Use `page.route("**/sessions/*", ...)` with `route.fetch()`, rewriting GET responses only and passing other methods through with `route.continue()`, to rewrite `proposals[0].merchant_details`, in three cases:
  - (a) `website: "https://dealbazaar.test/store/harbour-deals"` with a `mid` site.
    - Expect the texts "Simulated website: dealbazaar.test", "Website reputation: Mid" and "Loosely regulated marketplace".
    - Expect `.site-meter[aria-hidden="true"]` with exactly 2 `.site-meter .filled` cells.
  - (b) `site: null`. Expect no "Website reputation" text and no `.site-meter`.
  - (c) `website: "not a url"`. Expect "Simulated website: not a url" and no crash.
- [ ] **Step 2: Run** `cd frontend && npx playwright test tests/site-reputation.spec.ts`. Expected: FAIL (text not found).
- [ ] **Step 3: Implement** per spec §5.
  - Replace the website line with `Simulated website: {websiteHost(m.website)}`.
  - When `m.site` is present, add `<p>Website reputation: {Good|Mid|Poor}</p>` followed by `<span className="site-meter" aria-hidden="true">` with three `<span>` cells (class `filled` and a tier colour class on filled cells), then `<p>{m.site.label}</p>`.
  - CSS:
    - `.site-meter`: `display:inline-flex; gap:2px; padding:2px; width:72px; height:14px; box-sizing:border-box; border:1px solid currentColor; border-radius:7px`, with the text colour as the outline.
    - Cells: `flex:1` with a light grey background, and outer cells `border-radius:4px 0 0 4px` and `0 4px 4px 0`.
    - Filled colours: green `#639922`, amber `#EF9F27`, red `#E24B4A`.
- [ ] **Step 4: Run** `npm run typecheck` and the new spec. Expected: both pass. Then run the whole Playwright suite (`npx playwright test`). Expected: no new failures.
- [ ] **Step 5: Verify in the browser preview.** Propose `study-*-target-site-mid` and a `shopverse.test` offer, then screenshot in light and dark mode.
- [ ] **Step 6: Commit:** `feat: show website reputation meter in merchant details`.
