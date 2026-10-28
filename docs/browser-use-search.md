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
BROWSER_USE_TIMEOUT_SECONDS=240
BROWSER_USE_MAX_COST_USD=1
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

## Replay study listings (no web search)

To test the whole flow (conversation, clarification, search, risk review, cart and checkout) with
listings that are known to contain risk cues, replay the study dataset instead of calling Browser Use:

```dotenv
BEANY_SEARCH_PROVIDER=browser_use
BROWSER_USE_REPLAY=data/replay/study_listings.json
BEANY_LLM_MODE=openai
```

Restart the backend and click **Fresh session**. The replay path is saved per session, like the
provider. No Browser Use key, retailer list or credits are needed, and no network call is made for
search. Everything after search is unchanged: the configured model still runs clarification, the
search planner, the risk review agent and explanations. The UI labels these sessions as replays.
Use `BEANY_LLM_MODE=openai`. In mock mode the risk agent only reads the verbatim evidence lists,
which replayed study listings leave empty, so every offer comes out LOW.

A replay search returns every fixture listing in the brief's category whose name, brand, category,
description or attributes contain all search words. Only the top four appear as recommendations;
**Find another merchant** moves through the remaining offers. The supported categories come from the
fixture (Headphones, Running shoes and Backpacks for the study data). Fixture hosts use reserved
`.test` domains, which are accepted only in replay sessions.

`backend/scripts/build_replay_fixture.py` generates the fixture from `data/products/catalogue.json`
and `data/merchants/merchants.json`. It never reads `data/research/`. Evidence comes from
`app/runtime/local_evidence.py`, the same mapping the AI risk review uses for local products
(`BEANY_RISK_DETECTION=ai`), so replayed and local listings carry identical evidence. Fixture rows
are parsed as `ReplayListing`, whose evidence is `LocalEvidence`: `WebEvidence` plus four local-only
fields that live Browser Use search is never asked to capture. Only shopper-visible text is mapped:

| Study field | Replayed evidence field |
|---|---|
| merchant name, website | seller name, seller page URL; product URL is `<website>/products/<product id>` |
| merchant description | seller about |
| contact | seller email (or phone); when empty, the notice "No seller contact details listed" |
| verified business | seller badge "Verified business", or "Unverified seller" when false |
| merchant review count and rating | seller rating as displayed |
| return policy, payment methods | return policy, payment methods listed |
| checkout note | page notices |
| requested information | personal data requests: "Checkout asks for: …" with readable labels |
| product reviews, merchant reviews | product reviews, seller reviews (`LocalEvidence`), one "★rating title — text" line each |
| specifications | specifications (`LocalEvidence`), one "key: value" line each |
| product rating and count | product rating (`LocalEvidence`) |
| product name, brand, price, attributes, sizes, description, stock | same listing fields |

The boolean risk flags are never converted: they are not page text. A local record knows when a
detail is absent, so a missing contact or verification becomes explicit text; live listings keep
"blank means not visible", and blank fields are never evidence. The agent may quote a review only
when it reports concrete seller conduct, and its reason then starts with "Buyer report:".
Rebuild after editing study data (from `backend/`):

```sh
.venv/bin/python -m scripts.build_replay_fixture
.venv/bin/python -m scripts.build_replay_fixture --only study-hp-target-trusted,study-hp-target-external --output data/replay/hp_pair.json
```

`tests/test_replay.py` fails if the committed fixture is out of date.

## Behaviour and boundaries

The adapter posts a task with outputSchema and maxCostUsd, polls the run, and validates each returned
listing separately with Pydantic plus a check that its HTTPS product URL is on the retailer list. Currency
symbols are normalised (S$ or S to SGD, US$ to USD; a bare $ is rejected). Invalid listings are skipped;
the search fails only when every returned listing is invalid. It never follows
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
not another paid browse. Existing brief filters still apply. Fictional fraud classifications are not
reused; live risk comes from the captured evidence and review agent described below. Live proposals
always require review; detected instruction injection and existing hard-constraint checks still block.
Snapshots older than 30 minutes cannot check out.
Cart and checkout use snapshot data and **never call Browser Use** or a merchant purchase endpoint.
They do not verify the current live price, delivery, taxes, actual accepted payments or real stock.
To refresh, search again and replace the old cart item. Checkout and receipts remain simulated.

The app remains a local single-worker prototype; synchronous browser searches hold its mutation lock
and can take several minutes across multiple calls. UI cancellation cannot interrupt that locked request;
use the Browser Use dashboard to stop an active run. Background jobs/streaming are a future upgrade.

## Captured evidence and risk review

Each listing may also carry `web_evidence` (`schemas.WebEvidence`): seller name, page link, store description, badges,
displayed rating, business name, registration number, address, email, phone and ships-from location;
return policy summary and link, refund promises, warranty, listed payment methods, off-site payment
instructions, personal-information requests, urgency claims, text aimed at AI assistants, shipping and
other page notices.
Browser Use reads only the product page plus the seller and return-policy pages linked from it on the
same retailer. Images, review lists, other websites and price research are out of scope. Every field is
optional: a blank field means "not visible", and is neither a risk signal nor evidence of safety. Null
or overlong values are blanked or clipped instead of failing the run; links outside the retailer list are
dropped. A named seller becomes its own merchant ID, so "Find another merchant" excludes that seller
rather than the whole retailer. This extra browsing raises the cost and duration of each run.

When a live product is proposed, `runtime/risk_agent.py` makes one call to the configured model. It
reports signals from the existing merchant-risk categories (except `low_price`). Every finding must quote
the captured text. Findings whose quote does not appear in the snapshot are discarded, and each rule
counts once. Python scores the remaining findings with `merchant_risk_rules.json`, using the same
weights, levels and decisions as the catalogue. External payment and injection always block. `low_price`
is computed deterministically against other captured listings from the same session, with no extra
browsing. The review is cached per product snapshot, so cart review and checkout reuse it instead of
calling the model again. If the agent fails, the proposal shows "Automated risk review of this listing is
unavailable" and stays at REVIEW. Mock mode flags only the verbatim evidence lists, so it can run offline.
The agent can make a proposal stricter but never less strict than REVIEW.

## Validation

Offline tests in tests/test_browser_search.py and tests/test_risk_agent.py use httpx.MockTransport and fixtures; no paid calls.
Live compatibility and result quality have not been tested with your account. Start with a small
manual search when you choose to enable it, and inspect both the source listing and Cloud run.

Official references checked for this implementation:
- https://docs.browser-use.com/cloud/quickstart
- https://docs.browser-use.com/cloud/api-v4/runs/create-run
- https://docs.browser-use.com/cloud/agent/structured-output
- https://docs.browser-use.com/cloud/api-v4/runs/cancel-run
