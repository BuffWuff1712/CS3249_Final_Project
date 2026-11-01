# Candidate Sellers and Demo Scenario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nine existing study candidates gain 30 offers from existing study merchants, and a conversation-driven `demo` scenario lists only study data, so a corrected need leads to a product whose sellers include risky ones.

**Architecture:** Data-only change. New offers copy their candidate's product fields and differ in merchant, price and reviews. Their signals come from the unchanged merchant records. The researcher manifest, replay fixture, scenario file and dataset tests are extended to match. No runtime code changes.

**Tech Stack:** JSON data files, pytest via `backend/.venv/bin/python` (run from `backend/`).

**Spec:** `docs/data/2026-11-01-candidate-sellers-design.md`

## Global Constraints

- Work on branch `ywt`. Do not push. Commit messages carry no attribution lines.
- Stage files by explicit path only. The working tree holds someone else's uncommitted changes in `backend/app/runtime/{cart,llm,merchant_risk,policy,service,shop_workspace}.py`, `backend/tests/test_merchant_extension.py` and `frontend/src/components/shopping/BackendOffer.tsx`. Never edit, stage, stash or revert them.
- No runtime code changes, and no changes to merchant records, `research/merchant_ground_truth.json`, `sites/site_registry.json`, existing scenarios or anything under `frontend/`.
- Offer IDs are `study-{cat}-{n}-{variant}`. Variants used: `neutral`, `pressure`, `returns`, `site-mid`, `payment`, `external`, `nobiz`, `site-bad`, `inconsistent`, `injection`, `site-fake`, `data-mid`, `data-high`. Never `lowprice`, `benign`, `lookalike` or `concealed`.
- Price = candidate price × ratio, rounded down to the nearest `.9` (`floor(x + 0.1) - 0.1`). Ratios: neutral 0.95, pressure 0.85, site-mid 0.75, external 0.75, every other variant 0.80. Spec §2 lists every resulting price.
- Dataset tests assert signals, prices and ground truth, never risk levels or decisions.
- JSON data files are written with `json.dumps(data, indent=2, ensure_ascii=False)` and no trailing newline, which is how they are stored now. A data edit must show only insertions in `git diff --stat`.
- Repo artifacts are in English. All names stay fictional.

## Review Focus

1. **Existing tests that search free sessions** now also see 30 more study offers. A test that pins a free-session result list could change. Expected: no test outside the ones this plan edits changes outcome. The baseline run in Task 1 Step 0 makes this checkable.
2. **Duplicate IDs:** a copy-paste slip can give two offers one ID, and the later record silently wins in dictionaries. Expected: every catalogue ID is unique. Tested in Task 1.
3. **`/shop` grouping:** the seller table groups offers by `shop_workspace.model_key()`. A new offer whose shared fields drift from its candidate shows up as a separate model. Expected: each new offer has its candidate's `model_key`. Tested in Task 1.
4. **A hard feature in a correction** ("it must have a microphone"). Expected: the same candidate family ranks first as with a soft feature. Tested in Task 3.
5. **Rejecting the first risky seller after a correction.** Expected: the next offer of the same product moves up, not a different product. Tested in Task 3.

---

### Task 1: Candidate seller offers

**Files:**
- Modify: `backend/data/products/catalogue.json` (append 30 records), `backend/data/replay/study_listings.json` (regenerated)
- Test: `backend/tests/test_study_dataset.py`

**Interfaces:**
- Consumes: existing helpers in `test_study_dataset.py`: `products()`, `fired(product_id, scope)`, `EXPECTED`, `PINNED`, `STUDY_CATEGORIES`, `SHARED`.
- Produces, in `test_study_dataset.py`:
  - `SELLERS: dict[str, list[str]]`: candidate ID → new variants, in spec §2 order. Keys are `study-hp-2`, `study-hp-3`, `study-hp-1`, `study-rs-2`, `study-rs-4`, `study-rs-1`, `study-bp-4`, `study-bp-2`, `study-bp-1`.
  - `SELLER_RATIOS: dict[str, float]`: the four-value ratio rule from Global Constraints.
  - `seller_offer(candidate: str, v: str) -> str`: returns `f"{candidate}-{v}"`.
  - `seller_offers() -> list[tuple[str, str]]`: every `(candidate, variant)` pair, 30 in total.

- [ ] **Step 0: Record the baseline**

Run: `.venv/bin/python -m pytest -q -p no:cacheprovider > "$SCRATCH/baseline.txt" 2>&1; tail -5 "$SCRATCH/baseline.txt"` (`$SCRATCH` is the session scratchpad directory)
Expected: a summary line. Keep the list of any failures; they come from the uncommitted work above and are not this plan's to fix.

- [ ] **Step 1: Write the failing tests**

Add the constants and helpers above, then:

```python
def test_catalogue_ids_unique():
    ids = [p["id"] for p in json.loads((ROOT / "data/products/catalogue.json").read_text(encoding="utf-8-sig"))]
    assert len(ids) == len(set(ids))

def test_seller_offers_complete():
    ps = products()
    assert len(seller_offers()) == 30
    for c, v in seller_offers():
        o, base = ps[seller_offer(c, v)], ps[c]
        assert o.merchant_id == f"study-m-{v}" and base.merchant_id == "study-m-trusted"
        for f in [*SHARED, "description", "stock"]:
            assert getattr(o, f) == getattr(base, f), (o.id, f)

def test_seller_offers_share_model_key():
    from app.runtime.shop_workspace import model_key
    ps = products()
    assert all(model_key(ps[seller_offer(c, v)]) == model_key(ps[c]) for c, v in seller_offers())

@pytest.mark.parametrize("c,v", seller_offers())
def test_seller_offer_prices(c, v):
    ps = products()
    price, base = ps[seller_offer(c, v)].price, ps[c].price
    assert abs(price / base - SELLER_RATIOS[v]) <= 0.03 and price < base
    assert round(price * 10) % 10 == 9

@pytest.mark.parametrize("c", list(SELLERS))
def test_seller_offers_pair_reviews(c):
    ps = products()
    a, b, c3 = [r.text for r in ps[c].reviews]
    new = [seller_offer(c, v) for v in SELLERS[c]]
    texts = [[r.text for r in ps[i].reviews] for i in new]
    d, e = texts[0][1], texts[1][1]
    assert d != e and not {d, e} & {a, b, c3}
    assert texts == [[a, d], [b, e], [c3, d], [a, e]][: len(new)]
    family = [{a, b, c3}, *(set(t) for t in texts)]
    for i, x in enumerate(family):
        for y in family[i + 1:]:
            assert len(x & y) <= 1

@pytest.mark.parametrize("c,v", seller_offers())
@pytest.mark.parametrize("width", ["category", "catalogue"])
def test_seller_signals_hold_in_wider_scopes(c, v, width):
    ps = products()
    prefix = c.rsplit("-", 1)[0] + "-"   # e.g. "study-hp-"
    ids = [i for i in ps if i.startswith(prefix)] if width == "category" else list(ps)
    assert fired(seller_offer(c, v), [ps[i] for i in ids]) == set(EXPECTED[v]["signals"])
```

`test_seller_offer_prices` imports nothing new. `model_key` is imported inside its test, because `shop_workspace.py` is among the uncommitted files and is only read here, never edited.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_study_dataset.py -q -k "seller or ids_unique"`
Expected: `test_catalogue_ids_unique` passes. Every `seller` test fails with `KeyError: 'study-hp-2-neutral'` (or similar).

- [ ] **Step 3: Append the 30 records to `catalogue.json`**

Use a throwaway script in the scratchpad, not committed. For each `(candidate, variant)` in spec §2 order, deep-copy the candidate record and set `id`, `merchant_id` (`study-m-{variant}`), `price` (Global Constraints rule; the result must equal the spec §2 table) and `reviews`. Leave `merchant` and `trust` as copied; they are recomputed on load. Append the records after the last existing record and write the file back in the stored format.

Reviews follow spec §3: per candidate, write two new reviews D and E (`rating`, `title`, `text`, `date` in `2026-04-01`..`2026-10-20`, as in the existing ones); 18 in all. Copy the candidate's existing reviews A, B, C (stored order) and assign pairs in §2 order: (A, D), (B, E), (C, D), (A, E), first three for three-offer families. Rules for D and E:

- Only about the product, never the seller, delivery or price. Risk cues stay in merchant fields.
- Consistent with the candidate's `specifications` and `description`. Praise or criticise only what they list. For example, Brio Air 60 has no noise cancelling and has a 60-hour battery, so a review can complain about outside noise and praise the battery.
- Text differs from A, B and C and from each other.
- No real brands, URLs, "fictional" or "for simulation only" (`test_no_real_brands_or_placeholder_text` checks this).

- [ ] **Step 4: Regenerate the replay fixture**

Run: `.venv/bin/python -m scripts.build_replay_fixture`
Expected: `data/replay/study_listings.json` gains the 30 offers.

- [ ] **Step 5: Run the dataset, replay and site tests**

Run: `.venv/bin/python -m pytest tests/test_study_dataset.py tests/test_replay.py tests/test_sites.py -q`
Expected: all pass. That includes the existing `test_candidates_fire_no_signals`, `test_only_target_meets_goal_within_budget` and `test_committed_fixture_is_current`.

- [ ] **Step 6: Compare the full suite with the baseline**

Run: `.venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -5`
Expected: the same failures as Step 0 and no new ones. Run `git diff --stat backend/data` and check it shows only insertions.

- [ ] **Step 7: Commit**

```bash
git add backend/data/products/catalogue.json backend/data/replay/study_listings.json backend/tests/test_study_dataset.py
git commit -m "feat: add study sellers to nine candidate products"
```

### Task 2: Manifest entries

**Files:**
- Modify: `backend/data/research/risk_offer_manifest.json` (append 21 entries)
- Test: `backend/tests/test_study_dataset.py`

**Interfaces:**
- Consumes: `SELLERS`, `seller_offer`, `seller_offers` (Task 1); existing `manifest()`, `products()`, `EXPECTED`, `PINNED`.
- Produces: none.

- [ ] **Step 1: Write the failing tests**

Change `test_manifest_complete` to `assert len(entries) == 69`, and add:

```python
@pytest.mark.parametrize("c,v", [(c, v) for c, v in seller_offers() if v != "neutral"])
def test_seller_manifest_matches_engine(c, v):
    ps, entries = products(), manifest()
    entry = entries[seller_offer(c, v)]
    cat = c.split("-")[1]
    target = entries[offer(cat, v)]
    assert entry["merchant_id"] == f"study-m-{v}" and entry["variant"] == v
    assert entry["category"] == PINNED[cat]["category"]
    assert entry["price_ratio"] == SELLER_RATIOS[v]
    assert entry["visible_in"] == target["visible_in"]
    assert entry["reference_set"] == [c, seller_offer(c, "neutral")]
    scope = [ps[i] for i in entry["reference_set"]] + [ps[entry["product_id"]]]
    r = assess(ps[entry["product_id"]], merchants()[entry["merchant_id"]], scope, load_config())
    assert {e.rule_id for e in r.evidence} == set(EXPECTED[v]["signals"]) == set(entry["signals"])
    assert entry["ground_truth"] == EXPECTED[v]["ground_truth"]

def test_neutral_sellers_have_no_manifest_entry():
    assert not any(seller_offer(c, "neutral") in manifest() for c in SELLERS)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_study_dataset.py -q -k "manifest"`
Expected: `test_manifest_complete` fails (48 != 69); each `test_seller_manifest_matches_engine` case fails with `KeyError`.

- [ ] **Step 3: Append 21 entries**

Use a throwaway script, in spec §2 order with `neutral` skipped. Field values are in spec §4. `signals` and `ground_truth` are copied from the same variant's target entry, so they cannot drift from `EXPECTED`. Write the file back in the stored format.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_study_dataset.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/data/research/risk_offer_manifest.json backend/tests/test_study_dataset.py
git commit -m "feat: record candidate seller risk offers in the manifest"
```

### Task 3: Demo scenario

**Files:**
- Modify: `backend/data/scenarios/scenarios.json` (append one entry)
- Test: `backend/tests/test_study_dataset.py`

**Interfaces:**
- Consumes: `SELLERS`, `seller_offer` (Task 1); existing `products()`, `PINNED`, `STUDY_CATEGORIES`.
- Produces: `demo_session(category: str, features: str, budget: int, hard_features: bool = False) -> Session` in `test_study_dataset.py`. It returns a `Session` with `scenario_id="demo"`, a `category` fact, a hard `budget` fact and a `features` fact.

- [ ] **Step 1: Write the failing tests**

```python
DEMO_CORRECTIONS = [  # (cat, features, budget, candidate, expected top four variants), spec §6
    ("hp", "wireless, foldable, long-battery", 200, "study-hp-2", ["returns", "pressure", "neutral", None]),
    ("hp", "wireless, microphone", 200, "study-hp-3", ["external", "site-mid", "payment", "neutral"]),
    ("hp", "wireless, noise-cancelling, foldable", 300, "study-hp-1", ["nobiz", "site-bad", "neutral", None]),
    ("rs", "trail", 180, "study-rs-2", ["inconsistent", "injection", "pressure", "neutral"]),
    ("rs", "road, lightweight", 180, "study-rs-4", ["site-mid", "returns", "neutral", None]),
    ("rs", "cushioned, road, responsive", 250, "study-rs-1", ["nobiz", "site-fake", "neutral", None]),
    ("bp", "travel", 120, "study-bp-4", ["data-high", "data-mid", "pressure", "neutral"]),
    ("bp", "laptop, lightweight", 120, "study-bp-2", ["site-mid", "nobiz", "neutral", None]),
    ("bp", "laptop, water-resistant, rolling", 150, "study-bp-1", ["payment", "returns", "neutral", None]),
]
# None stands for the candidate's own trusted record.

def demo_spec():
    specs = json.loads((ROOT / "data/scenarios/scenarios.json").read_text(encoding="utf-8-sig"))
    return next(s for s in specs if s["id"] == "demo")

def test_demo_scenario_lists_every_study_product():
    spec = demo_spec()
    ids = spec["product_ids"]
    assert len(ids) == len(set(ids))
    assert set(ids) == {i for i in products() if i.startswith("study-")}
    assert spec["trigger_product"] is None and spec["initial_brief"] == {} and spec["permissions"] == {}

def test_no_other_scenario_lists_seller_offers():
    specs = json.loads((ROOT / "data/scenarios/scenarios.json").read_text(encoding="utf-8-sig"))
    new = {seller_offer(c, v) for c, v in seller_offers()}
    assert all(not new & set(s.get("product_ids") or []) for s in specs if s["id"] != "demo")

@pytest.mark.parametrize("cat", STUDY_CATEGORIES)
def test_demo_default_goal_shows_only_the_target(cat):
    s = demo_session(PINNED[cat]["category"], PINNED[cat]["features"], PINNED[cat]["budget"])
    top = [p.id for p in search(s)]
    assert len(top) == 4 and all(i.startswith(f"study-{cat}-target-") for i in top)

@pytest.mark.parametrize("cat,features,budget,c,expected", DEMO_CORRECTIONS)
def test_demo_correction_ranks_candidate_sellers(cat, features, budget, c, expected):
    s = demo_session(PINNED[cat]["category"], features, budget)
    assert [p.id for p in search(s)] == [seller_offer(c, v) if v else c for v in expected]

def test_demo_hard_feature_correction_matches_soft():
    soft = demo_session("Headphones", "wireless, microphone", 200)
    hard = demo_session("Headphones", "wireless, microphone", 200, hard_features=True)
    assert [p.id for p in search(hard)][0] == [p.id for p in search(soft)][0] == "study-hp-3-external"

def test_demo_rejecting_first_seller_keeps_the_product():
    s = demo_session("Headphones", "wireless, microphone", 200)
    s.rejected_merchants = ["study-m-external"]
    assert search(s)[0].id == "study-hp-3-site-mid"
```

`demo_session` builds facts the way `goal_session` does, with `Fact(value=..., hard=...)`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_study_dataset.py -q -k "demo or other_scenario"`
Expected: `demo` tests fail with `StopIteration` (no `demo` scenario) or `Scenario not found`. `test_no_other_scenario_lists_seller_offers` passes.

- [ ] **Step 3: Append the `demo` entry to `scenarios.json`**

Use the field values in spec §5. `product_ids` is every `study-*` ID in catalogue order. Give the remaining required fields short English text, using `site-reputation` as the shape. `ground_truth_reference` and `observable_indicators_reference` are `null`. Write the file back in the stored format.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_study_dataset.py tests/test_sites.py -q`
Expected: all pass. That includes `test_study_scenarios_match_manifest[demo]`, which now also runs for `demo`.

- [ ] **Step 5: Smoke-test the research route**

Run a short offline check: from `backend/`, with `BEANY_DB` pointing at a scratchpad file and `BEANY_LLM_MODE=mock`, use `TestClient(app)` to `POST /research/scenarios/demo/sessions` with header `X-Research-Key`. Before importing the app, set `BEANY_RESEARCH_KEY` in the script's environment to a throwaway value.
Expected: HTTP 200 and a session whose `scenario_id` is `demo`.

- [ ] **Step 6: Commit**

```bash
git add backend/data/scenarios/scenarios.json backend/tests/test_study_dataset.py
git commit -m "feat: add demo scenario over all study data"
```

### Task 4: Documentation

**Files:**
- Modify: `backend/data/README.md`, `docs/configuration-guide.md`, `docs/data/2026-11-01-candidate-sellers-design.md` (status line)

**Interfaces:** none.

- [ ] **Step 1: Update `backend/data/README.md`**

- In "Study dataset at a glance", add a bullet **Candidate sellers.** It says that nine candidates (listed by ID) also sell through `neutral` and two or three risk merchants as `study-{cat}-{n}-{variant}`, with the candidate's product fields and the variant price ratios. It names the excluded variants with their reason in one clause each, and links the design.
- Under "Building a study scenario", add one paragraph: `demo` lists every study product, has no trigger and no initial brief, and is opened from `/research` for demonstrations. Its sessions are not for analysis.
- Change the "Candidates" bullet so it still says that, among candidate records `study-{cat}-1` onward, only the target meets the goal within budget.

- [ ] **Step 2: Update `docs/configuration-guide.md`**

After the `site-reputation` paragraph, add one paragraph: what `demo` contains, that it is conversation-driven, and that a corrected need moves the recommendation to a candidate whose risky sellers rank first. Give one example correction from spec §6.

- [ ] **Step 3: Set the design status**

In the design doc, change `Status: Draft for review` to `Status: Implemented`.

- [ ] **Step 4: Verify**

Run: `.venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -5`
Expected: the same failures as the Task 1 baseline and no new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/data/README.md docs/configuration-guide.md docs/data/2026-11-01-candidate-sellers-design.md
git commit -m "docs: describe candidate sellers and the demo scenario"
```

### Task 5: Second batch of candidate sellers (spec §2.2)

**Files:**
- Modify: `backend/data/products/catalogue.json` (append 24 records), `backend/data/replay/study_listings.json` (regenerated), `backend/data/research/risk_offer_manifest.json` (append 16 entries), `backend/data/README.md`
- Test: `backend/tests/test_study_dataset.py`, `backend/tests/test_replay.py`

**Interfaces:**
- Consumes: `SELLERS`, `SELLER_RATIOS`, `seller_offer`, `seller_offers` (Task 1); every seller test is parametrized over `SELLERS`, so extending the constant extends the tests.

- [ ] **Step 1: Extend the tests.** Append the eight §2.2 candidates to `SELLERS` in table order. In `test_seller_offers_complete` change 30 to 54; in `test_manifest_complete` change 69 to 85; in `test_replay.py` change the headphone replay count from 34 to 43.
- [ ] **Step 2: Run them to verify they fail.** Run: `.venv/bin/python -m pytest tests/test_study_dataset.py tests/test_replay.py -q -p no:cacheprovider`. Expected: `KeyError` on `study-hp-4-neutral` and siblings, and the three count assertions fail.
- [ ] **Step 3: Append the 24 records** with the Task 1 Step 3 script rules, including two new reviews D and E per candidate (16 in all) paired (A, D), (B, E), (C, D). Then regenerate the replay fixture.
- [ ] **Step 4: Append the 16 manifest entries** with the Task 2 Step 3 rules.
- [ ] **Step 4b: Extend `demo` `product_ids`** to every `study-*` ID in catalogue order; `test_demo_scenario_lists_every_study_product` fails until it does.
- [ ] **Step 5: Run the tests to verify they pass**, including `test_demo_correction_ranks_candidate_sellers` unchanged. Then run the full suite and compare it with the baseline.
- [ ] **Step 6: Update the README** "Candidate sellers" bullet to say every candidate has extra sellers.
- [ ] **Step 7: Commit** the data, tests, README and both docs.
