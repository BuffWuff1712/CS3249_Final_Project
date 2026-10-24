# Optional Browser Use search

The default remains the local catalogue. No Browser Use account is contacted unless a session uses
`browser_use` and performs a search. Integration uses Cloud V4 REST through the existing httpx
dependency; no additional SDK or local browser installation is required.

## Enable later

Add these settings to your ignored **backend/.env**, not frontend environment variables:

```dotenv
BEANY_SEARCH_PROVIDER=browser_use
BROWSER_USE_API_KEY=your_browser_use_cloud_key
BROWSER_USE_ALLOWED_DOMAINS=retailer.example,another-retailer.example
BROWSER_USE_TIMEOUT_SECONDS=120
BROWSER_USE_MAX_COST_USD=0.5
# Optional: select a model supported by your Browser Use account.
# BROWSER_USE_MODEL=
```

Replace the example hostnames with real public retailers you intend to search (no https:// or paths).
Create a Browser Use Cloud account/key and check its credits. Browser Use bills separately from NUS.
Leaving BROWSER_USE_MODEL unset uses the provider's current default, not OPENAI_MODEL. The NUS model
still interprets requests, chooses tools and explains results. Do not put keys in chat or source control.

Restart the backend using your normal command, then click **Fresh session**. The provider is saved
per session: existing sessions stay on their original source. Ask for one specific product and currency
(SGD or USD), e.g. a desk lamp under SGD 50. The UI should show Browser Use live search, a source link
and a capture time. Research scenarios always use the catalogue regardless of this setting.

After this schema upgrade, replace any old pending proposals/cart entries before approval: their
fingerprints predate the new provenance fields. Existing receipts remain historical records.

To revert, set `BEANY_SEARCH_PROVIDER=catalogue`, restart the backend and start a fresh session.
Do not run the cloud quickstart simply to check configuration: it starts billable infrastructure.

## Behaviour and boundaries

The adapter posts a task with outputSchema and maxCostUsd, polls the run, validates output with
Pydantic and validates returned HTTPS product URLs against the retailer list. It never follows
provider redirects carrying credentials. There is no automatic provider fallback or task retry.
Up to two search tool calls can each start a run; the cost setting is per run, not per conversation.
Timeout cancels the known run on a best-effort basis. If creation times out before an ID is returned,
or cancellation fails, inspect Cloud dashboard runs before retrying. A finished browser may remain
idle for the provider's 120-second keepAlive interval and incur charges.

Only selected shopping-brief fields and search words are sent, not session history, participant IDs,
permissions, API keys, or hidden research labels. Avoid personal information in shopping preferences.
No profiles, cookies, account secrets, email capability or payment integrations are attached.
The task forbids login, merchant carts, purchases and submissions. This is a hosted general-purpose
agent: these behavioural instructions are not a hard read-only browser sandbox. The retailer list
constrains accepted results and instructs navigation; it is not a provider-enforced network allowlist.

Results are unverified snapshots saved with the session. Details inspection reads that snapshot,
not another paid browse. Existing brief filters still apply. Live merchant risk is unknown: fictional
fraud classifications are not reused. Live proposals require review; detected instruction injection
and existing hard-constraint checks still block. Snapshots older than 30 minutes cannot check out.
Cart and checkout use snapshot data and **never call Browser Use** or a merchant purchase endpoint.
They do not verify the current live price, delivery, taxes, actual accepted payments or real stock.
To refresh, search again and replace the old cart item. Checkout and receipts remain simulated.

The app remains a local single-worker prototype; synchronous browser searches hold its mutation lock
and can take several minutes across multiple calls. UI cancellation cannot interrupt that locked request;
use the Browser Use dashboard to stop an active run. Background jobs/streaming are a future upgrade.

## Validation

Offline tests in tests/test_browser_search.py use httpx.MockTransport and fixtures; no paid calls.
Live compatibility and result quality have not been tested with your account. Start with a small
manual search when you choose to enable it, and inspect both the source listing and Cloud run.

Official references checked for this implementation:
- https://docs.browser-use.com/cloud/quickstart
- https://docs.browser-use.com/cloud/api-v4/runs/create-run
- https://docs.browser-use.com/cloud/agent/structured-output
- https://docs.browser-use.com/cloud/api-v4/runs/cancel-run
