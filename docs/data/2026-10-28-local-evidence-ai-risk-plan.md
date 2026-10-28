# Local Evidence and AI Risk Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map local records into a richer `LocalEvidence` (replay fixture and runtime), and let local products be risk-reviewed by the AI agent behind a `BEANY_RISK_DETECTION` switch. Rules remain the fallback.

**Architecture:** A new pure module, `app/runtime/local_evidence.py`, owns the local-record → evidence mapping. The replay builder and the runtime AI path both use it. `LocalEvidence` subclasses `WebEvidence`, so the Browser Use schema, built from `WebEvidence`, stays identical. In AI mode, `service.propose` reviews a "review view" of a catalogue product (a copy carrying `LocalEvidence`), and `policy.evaluate` scores the cached review with `assess_live`, falling back to `assess`.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest. Run every command from `backend/` with `.venv/bin/python`.

**Spec:** `docs/data/2026-10-28-local-evidence-ai-risk-design.md`

## Global Constraints

- **Unchanged:**
  - `data/scenarios/scenarios.json`, the scenario logic and frontend files are not modified.
  - `SearchOutput.model_json_schema()` (the Browser Use `outputSchema`) stays byte-identical to the snapshot taken in Task 1.
  - `mock_review()` and the injection regex in `policy.py` are unchanged.
- **Switch:**
  - `BEANY_RISK_DETECTION` accepts exactly `rules` or `ai`, and defaults to `rules`.
  - Any other value raises `ValueError("BEANY_RISK_DETECTION must be rules or ai")` at session creation.
- **Mapping:**
  - Boolean risk flags (`external_payment`, `misleading_returns`, `lookalike_identity`, `pressure_tactics`, `inconsistent_information`) never appear in any evidence.
  - `app/runtime/local_evidence.py` never reads `data/research/`.
- **Exact copy:**

| Item | Text |
|---|---|
| Badge for `verified_business` true / false | `"Verified business"` / `"Unverified seller"` |
| Notice when `contact` is empty | `"No seller contact details listed"` |
| `personal_data_requests` entry | `"Checkout asks for: " + ", ".join(labels)` |
| Review line | `"★{rating} {title} — {text}"` |
| Specification line | `"{key}: {value}"` |
| `product_rating` | `"{rating}/5 ({rating_count:,} ratings)"`, or `""` when `rating is None` |
| Fallback event | kind `"risk_agent_fallback"`, detail = product id |

- **Labels for `requested_information`:** strip `fictional_`, then replace `_` with a space. Overrides: `government_id` → `"government ID"`, `date_of_birth` → `"date of birth"`, `bank_password` → `"bank password"`, `card_number` → `"card number"`.

## Review Focus

1. **Stored local evidence must not lose its fields.** A session saved to SQLite and reloaded must still carry `LocalEvidence` with its review lines. Pinned in Task 1, `test_session_round_trips_local_evidence`.
2. **The proposal must use the same review the agent produced.** If `service.propose` and `policy.evaluate` build different views (e.g. different field order or merchant state), the snapshot never matches, and AI mode silently becomes rules mode. Pinned in Task 5, `test_ai_mode_scores_catalogue_offer_with_agent_findings`, which asserts that `a.risk.evidence` comes from the fake agent.
3. **`requested_information` holding only delivery fields** (e.g. `["fictional_name", "fictional_delivery_address"]`). Expected: still listed; the agent decides. Pinned in Task 2, `test_requested_information_becomes_readable_request`.
4. **Old fixture merchants without reviews or a checkout note** (e.g. `privacy`, `demo-store`). Expected: the mapping works with empty lists, and `privacy` still exposes its requests. Pinned in Task 2, `test_old_fixture_merchant_maps`.
5. **Rules mode is exactly as before.** Expected: with no environment variable set, catalogue proposals never call the agent. Pinned in Task 5, `test_rules_mode_never_calls_agent`.

---

### Task 1: `LocalEvidence` model, schema guard and storage

**Files:**
- Modify: `app/runtime/schemas.py` (add `LocalEvidence` after `WebEvidence`, line ~133; change `Product.web_evidence`, line 152)
- Modify: `app/runtime/browser_search.py` (add `ReplayListing` after `Listing`, line ~72; use it in `replay_rows`, line 210)
- Create: `tests/fixtures/browser_use_output_schema.json`
- Test: `tests/test_local_evidence.py` (new)

**Interfaces:**
- Produces:
  - `LocalEvidence(WebEvidence)` with fields `product_reviews: list[str]` (max 10), `seller_reviews: list[str]` (max 10), `specifications: list[str]` (max 20) and `product_rating: str` (max 200), each with an empty default.
  - `Product.web_evidence: WebEvidence | LocalEvidence | None`.
  - `browser_search.ReplayListing(Listing)` with `evidence: LocalEvidence`.

- [ ] **Step 1: Snapshot the current Browser Use schema (before any code change)**

Run: `.venv/bin/python -c "import json; from app.runtime.browser_search import SearchOutput; open('tests/fixtures/browser_use_output_schema.json','w').write(json.dumps(SearchOutput.model_json_schema(), indent=1, sort_keys=True))"`
Expected: the file exists.

- [ ] **Step 2: Write the failing tests**

```python
def test_browser_use_schema_is_unchanged():
    snap = json.loads(Path("tests/fixtures/browser_use_output_schema.json").read_text())
    assert SearchOutput.model_json_schema() == snap

def test_local_evidence_fields_default_empty():
    e = LocalEvidence()
    assert e.product_reviews == [] and e.seller_reviews == [] and e.specifications == [] and e.product_rating == ""
    assert isinstance(e, WebEvidence)

def test_session_round_trips_local_evidence(tmp_path, monkeypatch):
    # BEANY_DB -> tmp file; Session with live_products = {"x": Product(..., web_evidence=LocalEvidence(seller_reviews=["★1 Bad — asked for bank transfer"]))}
    # storage.save(s); loaded = storage.load(s.id)
    assert isinstance(loaded.live_products["x"].web_evidence, LocalEvidence)
    assert loaded.live_products["x"].web_evidence.seller_reviews == ["★1 Bad — asked for bank transfer"]
    # and a plain WebEvidence product round-trips as WebEvidence (not LocalEvidence-only fields)

def test_replay_listing_accepts_local_fields():
    row = ReplayListing.model_validate({...minimal listing..., "evidence": {"seller_reviews": ["★5 Ok — fine"]}})
    assert row.evidence.seller_reviews == ["★5 Ok — fine"]
    with pytest.raises(ValidationError):
        Listing.model_validate({...same...})
```

- [ ] **Step 3: Run the tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_local_evidence.py -q`
Expected: `test_browser_use_schema_is_unchanged` passes (it is a guard), and the others fail with `ImportError: cannot import name 'LocalEvidence'`.

- [ ] **Step 4: Implement the model changes**

- Add `LocalEvidence` and switch `Product.web_evidence` to the union, `WebEvidence` listed first.
- Add `ReplayListing`, and have `replay_rows` validate with it.
- `Observed.clip` already clips the new list and string fields.

- [ ] **Step 5: Run the suite and confirm it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass, including the schema guard.

- [ ] **Step 6: Commit** (`feat: add LocalEvidence model and replay listing type`)

### Task 2: Local evidence mapping

**Files:**
- Create: `app/runtime/local_evidence.py`
- Test: `tests/test_local_evidence.py`

**Interfaces:**
- Consumes: `LocalEvidence`, `SellerEvidence`, `Product` and `Merchant` from Task 1.
- Produces:
  - `local_evidence(product: Product, merchant: Merchant) -> LocalEvidence`
  - `review_view(product: Product, merchant: Merchant) -> Product`, which returns `product.model_copy(update={"web_evidence": local_evidence(product, merchant)})`
  - `request_label(item: str) -> str`

- [ ] **Step 1: Write the failing tests** (use real study records via `merchants()` and `catalogue(Session())`)

```python
def test_seller_fields_copied():                  # study-m-trusted: name, page_url=website, about=description, email=contact, badges==["Verified business"], rating=="4.7/5 (2,140 reviews)"
def test_unverified_and_no_contact_are_explicit(): # study-m-nobiz: badges==["Unverified seller"], email=="" and phone=="", "No seller contact details listed" in notices
def test_checkout_note_is_a_notice():             # study-m-data-mid: checkout_note in notices
def test_requested_information_becomes_readable_request():
    assert local_evidence(p, m_data_mid).personal_data_requests == ["Checkout asks for: date of birth, social media account"]
    # a merchant copy with ["fictional_name", "fictional_delivery_address"] -> ["Checkout asks for: name, delivery address"]
    # empty list -> []
def test_reviews_specs_and_rating():               # study-hp-target-trusted: 3 product_reviews lines "★{r} {title} — {text}", seller_reviews from merchant_reviews,
                                                   # specifications contains "Type: Over-ear, closed back", product_rating == "4.6/5 (2,310 ratings)"
def test_no_flags_or_labels_leak():                # for every study-m-* merchant: json of local_evidence contains none of the five flag names, "TRUSTWORTHY", "MALICIOUS", "SUSPICIOUS"
def test_old_fixture_merchant_maps():              # privacy merchant with audio-1-like product: personal_data_requests == ["Checkout asks for: email, government ID, bank password"]; seller_reviews == []
def test_review_view_is_a_copy():                  # review_view(p, m).web_evidence is LocalEvidence; p.web_evidence is None; same id/price
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_local_evidence.py -q`
Expected: FAIL with `ModuleNotFoundError: app.runtime.local_evidence`.

- [ ] **Step 3: Implement the mapping per spec §2.2 and the Global Constraints copy**

- The contact goes to `email` if it contains `@`, otherwise to `phone`.
- The seller rating string is unchanged from the current builder: `f"{rating}/5 ({count:,} reviews)"` when a rating exists, else `f"{count:,} reviews"`. It is omitted when `review_count` is 0.

- [ ] **Step 4: Run the tests and confirm they pass**, then run the full suite.

- [ ] **Step 5: Commit** (`feat: map local records to LocalEvidence`)

### Task 3: Replay fixture built from the shared mapping

**Files:**
- Modify: `scripts/build_replay_fixture.py` (replace `seller()` and `evidence()`, lines 25–48, with a call to `local_evidence`, which takes model objects)
- Regenerate: `data/replay/study_listings.json`
- Modify: `tests/test_replay.py:42-60` (`test_converter_keeps_only_shopper_visible_text`)

**Interfaces:**
- Consumes: `local_evidence(product, merchant)` from Task 2.

- [ ] **Step 1: Update the converter test to the new contract (failing)**

In `test_converter_keeps_only_shopper_visible_text`:
- Validate rows with `browser.ReplayListing` instead of `browser.Listing`.
- Replace `assert "email" not in nobiz and "badges" not in nobiz` with `nobiz["badges"] == ["Unverified seller"]`, and check that `"No seller contact details listed"` is in that row's `evidence["notices"]`.
- Add:
  - `rows["study-hp-target-data-mid"]...["personal_data_requests"] == ["Checkout asks for: date of birth, social media account"]`
  - `rows["study-hp-target-returns"]...["seller_reviews"]` is non-empty
  - `"specifications"` is in the trusted row's evidence
- Keep the flag-name loop. It still holds: `merchant_reviews` is a source key and never an output key.

Add `test_replayed_products_keep_local_evidence(replay)`: after `shopping_tools.search_products(headphones())`, every product in `s.live_products` has a `LocalEvidence` `web_evidence` with non-empty `product_reviews`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_replay.py -q`
Expected: the converter test and the new test fail.

- [ ] **Step 3: Implement** the builder as `listing(p, m)`, which builds `Product`/`Merchant` from the JSON records and sets `"evidence": local_evidence(...).model_dump(exclude_defaults=True)`.

- [ ] **Step 4: Regenerate the fixture**

Run: `.venv/bin/python -m scripts.build_replay_fixture`
Expected: "Wrote 62 listings".

- [ ] **Step 5: Run the full suite and confirm it passes** (`test_committed_fixture_is_current` included).

- [ ] **Step 6: Commit** (`feat: build replay fixture from shared local evidence mapping`)

### Task 4: Agent prompt for the new evidence fields

**Files:**
- Modify: `app/runtime/risk_agent.py` (`INSTRUCTIONS`, lines 22–45)
- Test: `tests/test_risk_agent.py`

**Interfaces:**
- Consumes: `LocalEvidence` from Task 1.

- [ ] **Step 1: Write the failing tests**

```python
def test_prompt_covers_local_fields():
    for text in ("product_reviews", "seller_reviews", "specifications", "Buyer report:",
                 "Unverified seller", "No seller contact details listed"):
        assert text in risk_agent.INSTRUCTIONS
    assert "website reputation" in risk_agent.INSTRUCTIONS   # unchanged clause

def test_quote_from_seller_review_is_grounded():
    # Product with web_evidence=LocalEvidence(seller_reviews=["★1 Never confirmed — Transferred the money as instructed, no reply."])
    # chooser returns Finding("external_payment", "Transferred the money as instructed", "Buyer report: ...")
    # plus Finding("pressure", "only 1 left today", ...) not present in the evidence
    assert [f.rule_id for f in out.findings] == ["external_payment"] and out.discarded == 1
```

- [ ] **Step 2: Run them and confirm the prompt test fails** (the grounding test may already pass, since `observed_text` covers all of `web_evidence`; keep it as a regression guard).

- [ ] **Step 3: Add to `INSTRUCTIONS`** the "when present" paragraph from spec §4.1. Put it after the empty-fields sentence and before the signal list. Extend the `missing_business` bullet with the two explicit texts.

- [ ] **Step 4: Run `tests/test_risk_agent.py`, then the full suite**, and confirm they pass.

- [ ] **Step 5: Commit** (`feat: let the risk agent use local review and specification evidence`)

### Task 5: `BEANY_RISK_DETECTION` switch and AI routing for catalogue products

**Files:**
- Modify: `app/runtime/schemas.py` (`Session`, add `risk_detection: Literal["rules", "ai"] = "rules"`)
- Modify: `app/runtime/local_evidence.py` (add `configured_detection() -> str`)
- Modify: `app/runtime/service.py` (`create()`, line 71; `propose()`, lines 147–149)
- Modify: `app/runtime/policy.py` (`evaluate()`, the `else:` branch at line ~186)
- Modify: `.env.example` (add the commented variable next to `BEANY_SEARCH_PROVIDER`)
- Test: `tests/test_local_evidence.py`

**Interfaces:**
- Consumes: `review_view` (Task 2), `risk_agent.review(session, product, merchant, chooser=None)`, `risk_agent.snapshot(product)`, and `merchant_risk.assess_live(product, merchant, comparables, config, review)`.
- Produces: `local_evidence.configured_detection()`, which reads the environment variable and validates it per the Global Constraints.

- [ ] **Step 1: Write the failing tests**

All tests use `BEANY_LLM_MODE=mock` and `BEANY_DB=tmp`, and pass the fake agent by monkeypatching `risk_agent.ask_model` and setting `BEANY_LLM_MODE=openai` around `propose`.

```python
def test_switch_defaults_to_rules(monkeypatch):            # unset -> service.create().risk_detection == "rules"
def test_switch_rejects_unknown_value(monkeypatch):        # "maybe" -> pytest.raises(ValueError, match="rules or ai")
def test_rules_mode_never_calls_agent(monkeypatch):        # ask_model patched to raise; propose(s, study-hp-target-external) -> decision BLOCK via rules, no "risk_agent" event
def test_ai_mode_scores_catalogue_offer_with_agent_findings(monkeypatch):
    # risk_detection="ai"; fake returns Finding("misleading_returns", "Refunds are issued as store credit only", "...") for study-hp-target-returns
    # assert a.risk.evidence[0].rule_id == "misleading_returns" and "Observed:" in a.risk.evidence[0].evidence
    # assert a.product.web_evidence is None   (proposal keeps original product)
def test_ai_mode_calls_agent_once_per_offer(monkeypatch):  # propose twice -> fake called once
def test_ai_mode_falls_back_to_rules(monkeypatch):         # fake raises LLMError -> a.risk from assess() (rule_ids == {"misleading_returns"}), event kind "risk_agent_fallback" with detail product id
def test_ai_mode_applies_to_scenario_sessions(monkeypatch):# s.scenario_id="risk-c", risk_detection="ai"; propose offer-privacy with fake findings -> a.risk built by assess_live (evidence text contains "Observed:")
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_local_evidence.py -q -k "switch or mode"`
Expected: FAIL. `Session` has no `risk_detection`.

- [ ] **Step 3: Implement**

- `create()` sets `risk_detection=configured_detection()`.
- `propose()`: when `s.risk_detection == "ai"` and `product.source == "catalogue"`, call `review_listing(s, review_view(product, merchant), merchant)`.
- `evaluate()`: in the catalogue branch with AI mode, set `view = review_view(p, merchant)` and `cached = s.live_risk.get(p.id)`.
  - If `cached and cached.snapshot == snapshot(view)`, use `assess_live(view, merchant, catalogue(s), session_config(s), cached)`.
  - Otherwise use `assess(...)` and append `Event(kind="risk_agent_fallback", detail=p.id)` once per proposal.

- [ ] **Step 4: Run the full suite and confirm it passes** (rules-mode tests unchanged).

- [ ] **Step 5: Commit** (`feat: AI risk review for local products behind BEANY_RISK_DETECTION`)

### Task 6: Real-model evaluation script

**Files:**
- Create: `scripts/evaluate_risk_agent.py`
- Test: `tests/test_evaluate_risk_agent.py`

**Interfaces:**
- Consumes: `review_view` (Task 2) and `risk_agent.review`.
- Produces:
  - `compare(found: set[str], expected: set[str]) -> dict` returning `{"hits": sorted, "misses": sorted, "false_positives": sorted}`, with `low_price` removed from both sides.
  - `evaluate(product_ids: list[str], repeat: int, chooser=None) -> list[dict]`, one row per product per run: `product_id`, `variant`, `found`, plus the `compare` keys.
  - CLI: `python -m scripts.evaluate_risk_agent --repeat N [--only PREFIXES] [--out data/raw/risk_agent_eval.json]`, which prints a per-variant table of hit rate, miss rate and false positives.

`trusted` and `neutral` have expected `set()`. Variants take their expected signals from the manifest.

- [ ] **Step 1: Write the failing tests**
  - `compare({"pressure","low_price"}, {"pressure"})` gives hits `["pressure"]` and no misses.
  - `compare(set(), {"lookalike"})` gives misses `["lookalike"]`.
  - `evaluate(["study-hp-target-returns", "study-hp-target-trusted"], 2, chooser=fake)` returns 4 rows with the right variants.

- [ ] **Step 2: Run them and confirm they fail; implement; run them and confirm they pass**

- [ ] **Step 3: Commit** (`feat: add real-model risk agent evaluation script`)

- [ ] **Step 4: Run the real evaluation once** (this spends model credits, which is allowed)

Run: `BEANY_LLM_MODE=openai .venv/bin/python -m scripts.evaluate_risk_agent --repeat 2`
Expected: a table covering 45 offers. Copy the per-variant summary into the final report to the user. Nothing is committed from `data/raw/`.

### Task 7: Documentation

**Files:**
- Modify: `docs/browser-use-search.md` (the "Replay study listings" mapping table and the "not converted" paragraph)
- Modify: `backend/data/README.md` (the replay section, plus the `BEANY_RISK_DETECTION` note)
- Modify: `docs/configuration-guide.md` (add `BEANY_RISK_DETECTION`, with the three spec §3.3 differences)

- [ ] **Step 1: Update the three docs** to match spec §2.2 and §3.3, then run `grep -n "LocalEvidence\|BEANY_RISK_DETECTION" ../docs/*.md data/README.md` and confirm each file mentions them.
- [ ] **Step 2: Run the full suite and confirm it passes**, then commit (`docs: document local evidence and AI risk detection switch`).
