# Beany Codebase Review

Review date: 27 October 2026. Baseline: commit `13e124f`. Scope: the integrated FastAPI and Next.js application, its fixtures, tests and project documentation. Findings below distinguish observed behaviour from proposed changes.

## Overall assessment

Beany has a credible foundation for the revised project. Its strongest contribution is the separation between probabilistic conversation and deterministic control: the model extracts preferences and selects candidates, while Python validates constraints, assesses configured merchant signals and controls simulated checkout. The editable brief, provenance states, exact-action approvals and researcher-only ground-truth joins are worth preserving.

The main weakness is product alignment. Much of the application is organised around permissions, approvals and simulated transactions, while the feedback prioritises understanding purchase intent and helping users inspect source evidence before deciding. More checkout work would contribute less than making the existing information understandable and evaluable.

The synthetic database is already implemented: 81 offer records, 23 merchants, 62 study offers and three categories. Calling the database an outstanding greenfield feature would misrepresent the repository. The remaining work is scenario curation, evidence presentation and repeatability.

## Findings requiring changes

### F01 High priority Purchase intent readiness is too weak

Evidence: `backend/config/elicitation.json`; `backend/config/prompts/dialogue.txt`; `backend/app/runtime/service.py:242`; `backend/app/runtime/llm.py:53`.

The configuration treats category and budget as sufficient and the prompt explicitly discourages use-case clarification once they are present. The service can replace a model clarification with search solely because those two fields are confirmed. Thus a request such as headphones under a budget may proceed without resolving commute versus exercise, comfort or the user's most important criterion. The mock interpreter also searches for the bare input `headphones`; a direct offline service probe produced one proposal and zero clarifications. That probe establishes mock behaviour, not the quality of the live model.

Change: define category-sensitive purchase intent readiness. Ask one relevant question when a decision-changing ambiguity remains, accept an explicit request to browse, and never silently invent preferences. Preserve a direct route to results for already specific requests.

### F02 High priority Hard constraints can inherit an unrelated field state

Evidence: `frontend/src/components/Brief.tsx:80`.

The preference selector updates `field` and `value` but does not update `hard`. After editing a hard budget and switching the selector to another preference, saving can attach the budget's hard setting to the new field. Switching in the opposite direction can make an existing hard preference soft. This is a concrete state-management defect in a control intended to establish trust.

Change: load `value` and `hard` from the selected fact together; default a new field deliberately. Verify both directions, including category changes and empty fields. Use user-facing labels such as Must have and Prefer where appropriate.

### F03 High priority The activity panel does not show the actual research process

Evidence: `backend/app/runtime/shopping_workflow.py:52`; `backend/app/runtime/service.py:163`; `backend/app/main.py:51`; `frontend/src/app/page.tsx:337` and its activity filter.

The backend records searches and inspections as `shopping_tool` events, plus risk assessments. The UI filters these out and displays generic historical labels after the complete request finishes. The only in-progress feedback is Beany is working. The current `search` event says Compared N matches even though returning candidates does not establish that each was inspected.

Change: distinguish found, inspected and assessed counts; expose a safe activity projection with evidence references. A live display requires a transport change: the current synchronous request and save-at-completion design cannot stream its stored events. Do not fake intermediate work with timers or reveal raw model interpretations.

### F04 High priority The proposed A/B comparison does not exist

Evidence: `backend/config/cui_profiles.json`; `backend/app/runtime/research.py:23`; `backend/app/main.py:197`; `docs/evaluation-guide.md`.

The standard and concise profiles change explanation length. They do not disable conversational clarification, extracted brief display, risk presentation or agent recommendations. Existing risk scenarios test interventions; they are not a traditional comparison-site baseline. Research session creation also generates a new participant identifier each time, so paired-condition analysis needs an explicit shared study participant identifier.

Change: add assigned study conditions, a baseline comparison view, task boundaries and condition-aware exports. Keep raw evidence available in both conditions and measure the whole interface package. Existing synthetic detector precision and recall do not measure user trust or decision quality.

### F05 Medium priority Review and specification data stop before the UI

Evidence: `backend/app/runtime/schemas.py:38`, `:45` and `:148`; `frontend/src/lib/beany.ts`; `frontend/src/components/MerchantDetails.tsx`; `frontend/src/app/page.tsx:304`.

Backend products contain ratings, rating counts and review excerpts; merchants contain merchant reviews and checkout notes. The active TypeScript contracts omit these additions, and the participant UI does not render them. Product specifications are declared but not shown in the main product and comparison cards. Merchant aggregate ratings exist, mostly inside collapsed details. Users therefore cannot inspect much of the evidence already authored for the study.

Change: extend the active contracts and render product and merchant evidence separately. Surface concise signals per offer with expandable specifications, review excerpts and source details. Missing evidence must remain visibly unknown.

### F06 Medium priority Same product comparison has no reliable identity

Evidence: `backend/app/runtime/merchant_risk.py:187`; `backend/app/runtime/policy.py:115`; `backend/app/main.py` alternative endpoint.

The low-price reference set matches category, brand and currency, rather than exact product and variant. Different products from one brand can therefore become misleading comparables. The alternative endpoint excludes the previous merchant and searches all eligible products; it does not preserve product identity. An offline probe changed Echo Study to Brio Desk Headset after the merchant-alternative operation.

Change: introduce a stable product group and variant key, separate merchant offers from product identity, and restrict Find another merchant to the same product variant. Offer a separately labelled alternative-product action when no other seller exists. Compare prices only within a documented comparable offer set.

### F07 Medium priority Ranking does not express negotiated priorities

Evidence: `backend/app/runtime/policy.py:115`; `backend/app/runtime/shopping_workflow.py:25`; `backend/app/runtime/schemas.py:21`.

Catalogue ranking uses feature substring matches, a fixed brand bonus, a usage substring match and then price. Facts have no priority order. The planner can choose any inspected result; returned candidate order and proposed product need not agree. No structured mismatch summary or explicit preference-negotiation state exists.

Change: record user-confirmed priority order, compute match and mismatch explanations deterministically, and request an explicit change before relaxing constraints. Treat a Most recommended banner as optional scope until the team chooses it; do not describe it as already agreed or implemented.

### F08 Medium priority Fixture annotations can be mistaken for detected evidence

Evidence: `backend/app/runtime/merchant_risk.py:75`; `backend/app/runtime/schemas.py:45`; `backend/app/runtime/shopping_workflow.py:86`.

Catalogue risk rules read authored flags such as misleading returns and lookalike identity. They are not discovering those facts from arbitrary websites. Full merchant records, including these flags, can enter planner observations and participant snapshots. Ground-truth labels are correctly separated, but that does not make the authored flags independent evidence extraction.

Change: describe this honestly as a simulated assessment. Link each participant-facing finding to the relevant visible fixture text. Keep annotations in the assessment layer and project only observable fields into planner and participant views. This is especially necessary for a credible baseline.

### F09 Medium priority Current tasks underrepresent the stated purchase stakes

Evidence: `backend/tests/test_study_dataset.py:65`; `backend/data/products/catalogue.json`.

Study target prices are SGD179, SGD159 and SGD99, with budgets of SGD200, SGD180 and SGD120. Only three of all 81 catalogue offers exceed SGD200. These fixtures demonstrate comparison and risk communication, but cannot substantiate a claim about higher-stakes purchases over $200 without clarifying currency and revising task prices or narrowing the claim.

Change: either add a frozen above-SGD200 task set and update dependent assertions, or frame the initial study as consumer product comparison without claiming the threshold was evaluated. A laptop example is not a reason to add a fourth category for this submission.

### F10 Lower priority Documentation and transaction emphasis obscure the final scope

Evidence: `README.md`; `docs/architecture.md`; `docs/shopping-workflow.md`; active cart and checkout routes.

The README contains historical statements about automatic checkout and fresh-session deletion that conflict with later descriptions and the current UI. The architecture diagram does not describe the newer planner, merchant-risk and cart paths. The active UI invites checkout and shows purchase history before establishing the two feedback pillars.

Change: rewrite current behaviour as one coherent account, centre find, compare and decide, and retain existing simulated checkout as a secondary demonstration boundary. No real payment integration is required. Keep legacy modules clearly identified rather than refactoring or deleting them during this scope change.

## Verification and limits

- Backend: `.venv/bin/python -m pytest -q -p no:cacheprovider` from `backend` completed with 412 passed and 5 skipped. One upstream TestClient deprecation warning was reported. Skips are not counted as coverage.
- Frontend: `npm run typecheck` and `npm run build` from `frontend` both passed. The resolved Next.js build version was 15.5.27.
- Direct offline probes reproduced bare-headphones search without clarification and product changes during merchant alternatives. They used the test suite's environment isolation and did not call external services.
- Browser E2E tests, paid model calls and live Browser Use searches were not run for this review. UI findings are grounded in source inspection; no runtime accessibility or visual-quality claim is made.
- Passing tests establish existing deterministic behaviour. They do not establish conformity with the new feedback, validity of the proposed experiment, scam-detection capability or live conversational quality.

## Recommended response

Preserve the validated control boundary and existing dataset. First repair the brief editor and align purchase intent handling. Then expose evidence and honest activity, establish exact-product offer comparison, and build the A/B conditions. Keep checkout expansion, live-search infrastructure and additional categories outside the critical path. The accompanying specification defines observable acceptance criteria for these changes.
