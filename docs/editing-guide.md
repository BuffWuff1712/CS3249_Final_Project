# Team editing guide

| Change | File | Notes |
|---|---|---|
| Tone, clarification, uncertain-user handling | backend/config/prompts/dialogue.txt | Change prompts, then run human-reviewed conversation evals. |
| Outcome explanation prompt | backend/app/runtime/llm.py | Keep wording subordinate to deterministic policy. |
| Supported preference fields | backend/app/runtime/schemas.py and frontend/src/components/Brief.tsx | Also update validate_fact/search/policy. |
| Search/ranking | backend/app/runtime/policy.py | Hard filters first, soft ranking second; stable price/ID tie breaks. |
| Intervention thresholds | backend/config/policy.json | Restart backend after edits. |
| New safety rules | backend/app/runtime/policy.py | Add a rule ID, outcome, reason and boundary tests. |
| Product facts | backend/data/products/catalogue.json | Unique IDs, fictional brands/merchants, positive prices. |
| Study conditions | backend/data/scenarios/scenarios.json | Set initial brief, permissions, product_ids, trigger_product and action. |
| Main wording and cards | frontend/src/app/page.tsx | Retain visible simulation labels and action-specific controls. |
| Brief/permission controls | frontend/src/components/Brief.tsx | Saving supersedes pending actions. |
| Colours/layout | frontend/src/app/globals.css | Verify mobile overflow, labels and keyboard focus. |
| Research controls | frontend/src/app/research/page.tsx | Backend key authorization must remain enforced. |

Product prices and permission changes never come from LLM-written executable code. Add payment options only as fictional literals. Do not relax hard-block checks to make a scenario pass: edit the scenario's underlying explicit constraints and propose again.

Current runtime is intentionally grouped under `app/runtime` to avoid confusing it with the student's earlier modules. If reorganizing into separate packages later, preserve the public schemas and policy boundary. The unfinished TODOs in the old shopping_service.py are retained historical exercises, not missing work in the integrated app.

For NUS transport settings, separate merchant records, observable risk rules, hidden ground truth, experimental profiles and reports, see [configuration-guide.md](configuration-guide.md). Core additions: `runtime/gateway.py`, `runtime/merchants.py`, `runtime/merchant_risk.py`, and researcher-only `runtime/research.py`. Product offers now reference `merchant_id`. Never put ground-truth fields into observable records or frontend schemas.

## Study dataset

Study products (`study-{hp,rs,bp}-*`), merchants (`study-m-*`) and the 13-variant risk offer library are described in [data/2026-10-21-study-dataset-design.md](data/2026-10-21-study-dataset-design.md). Each risk offer's declared signals and ground truth are listed in the researcher-only `backend/data/research/risk_offer_manifest.json`, which the runtime never loads. After editing any study record, re-run `backend/tests/test_study_dataset.py`. Those tests check signals, prices and ranking; they do not check risk levels or ALLOW/REVIEW/BLOCK decisions, which belong to the policy owner. Raw Amazon samples live in the git-ignored `backend/data/raw/` and can be regenerated with `python -m scripts.sample_amazon` from `backend/`.
