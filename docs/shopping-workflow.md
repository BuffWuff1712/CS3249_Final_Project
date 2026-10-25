# Catalogue shopping workflow

The integrated chat now uses a bounded shopping workflow in `backend/app/runtime/shopping_workflow.py`.
It is ordinary Python, separate from the earlier LangGraph learning exercises. It does not use MCP,
live shops, or real transactions.

1. `OpenAIConversation.interpret` extracts the brief and conversational intent.
2. `run_shopping` asks the configured model for a validated `ShoppingStep`.
3. `search_products(session, query)` applies the existing eligibility filters before optional
   keyword filtering. An empty query searches the eligible catalogue. Up to two searches are allowed.
4. `get_product_details` returns the product and observable merchant record. Only a returned search
   result may be inspected. Descriptions and reviews are untrusted data.
5. `propose` may select only an inspected ID. The server retrieves the product again; the model
   never supplies price, permission, merchant identity or an approval.
6. The service passes that product to its existing policy/proposal function. Checkout and exact
   fingerprint approval checks remain there. The CUI emits one outcome response, with deterministic
   wording if the optional outcome-explanation call fails.

The loop has at most six model decisions and two searches. A query refinement changes search words,
not the stored brief or hard constraints. No-match, invalid decisions, provider errors and exhaustion
produce no new proposal or receipt. Previous pending proposals are superseded when a new search starts.
The explicit mock mode uses search → inspect first result → propose, without network calls.

The workflow returns `ShoppingResult(status, product, candidates)` and records tool observations as
`shopping_tool` events plus a `shopping_result` event. Research ground truth and experiment settings
are not sent to the planner. Scenario catalogue restrictions still apply. Research-triggered proposals,
explicit product selection and the deterministic alternative button retain their direct service paths.

Test offline from backend with `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`.
In the app, try a normal headphone request, inspect activity, reject and ask for an alternative, and
try an impossible budget. Approval must still refer to the displayed proposal.

Limitations: keyword matching is literal; there is no synonym expansion, live inventory or basket
planning. The additional model decisions add latency and consume gateway usage (up to eight calls
including interpretation and final explanation, plus one risk-review call per newly proposed
Browser Use listing). Existing single-worker locking remains. Structured
steps use the existing gateway JSON adapter, not native provider tool-calling. Model explanations
remain generated wording; the proposal card and policy records are authoritative.
