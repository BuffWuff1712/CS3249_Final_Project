# Website Reputation Risk for Local Data

Date: 2026-10-29
Status: Draft for review
Related: [study dataset design](2026-10-21-study-dataset-design.md), [local evidence and AI risk review](2026-10-28-local-evidence-ai-risk-design.md)

## 1. Goal

Add a risk signal for the reputation of the website an offer is sold on. A local site registry records every study website with a reputation tier and a short description. Code looks the merchant's website up by domain, raises a signal for mid and poor sites, and the merchant details show the tier as a three-cell meter.

Three further changes come with it:

1. Study merchant websites are reassigned, so the dataset contains both large marketplaces and small independent stores.
2. `lookalike` is redefined as a knockoff product, which is a product that imitates another brand's name. Imitation websites become a poor-reputation case of the new signal.
3. Three new risk variants test the new signal.

### Out of scope

- Live Browser Use search and replay sessions. Their merchants have no registry entry, so the signal never fires for them.
- The original fixtures (`shoe-*`, `audio-*`, `bag-*`, `offer-*`, merchants `demo-store` to `concealed`). Their data stays unchanged and their domains are not registered.
- The `/shop` page, which does not read backend data.
- Real-world website names. Every registry entry is fictional, though modelled on real kinds of websites.

### Decisions taken in review

| Topic | Decision |
|---|---|
| Tiers | `good` means a large, reliable site such as a big marketplace or an established retailer. `mid` means the site is not necessarily fraudulent, but its sellers are loosely regulated, quality varies, and prices are lower. `poor` means low quality, counterfeits, imitation, or an obscure site that buyers are easily scammed on. |
| Names | Fictional, modelled on real sites. |
| Lookup | By exact host of `Merchant.website`. A registry entry describes what the domain is, and that description is the evidence for the tier. |
| Coverage | Every study domain is registered, including obscure and imitation sites, whose descriptions say so. An unregistered domain raises no signal. |
| Description | A one-sentence summary per site, not a chain of evidence. |
| Detection | Computed by code in both `rules` and `ai` modes, like `low_price`. The risk agent never sees the registry. |
| Single signal | Every existing variant is placed on a `good` site. Only the new variants use `mid` or `poor` sites. |
| Imitation | Two separate risks. A knockoff product (`lookalike`) changes only the product name and brand. An imitation domain is a `poor` site. |
| Display | A three-cell meter with the tier word and a short label. No full description. |
| Policy defaults | The policy owner asked this change to propose defaults. See section 4. |

## 2. Site Registry

### 2.1 File and schema

New runtime file: `backend/data/sites/site_registry.json`. It is shopper-visible data, not researcher data. It is a list of entries:

```json
{"domain": "shopverse.test", "name": "Shopverse", "kind": "marketplace", "tier": "good",
 "label": "Large marketplace",
 "summary": "Large established marketplace; buyer protection and platform-managed refunds on all orders."}
```

New model `Site` in `app/runtime/schemas.py`:

| Field | Type | Use |
|---|---|---|
| `domain` | str | Exact host to match. Unique in the registry. |
| `name` | str | Site name. The assistant uses it in explanations. The UI does not show it. |
| `kind` | `"marketplace"` or `"independent"` | Marketplace stores use `https://<domain>/store/<slug>`. Independent sites use `https://<domain>`. |
| `tier` | `"good"`, `"mid"` or `"poor"` | Reputation tier. |
| `label` | str, at most 40 characters | Short phrase shown under the meter. |
| `summary` | str, at most 200 characters | One-sentence description, used in risk evidence. |

### 2.2 Entries

| Domain | Name | Kind | Tier | Label | Summary | Used by |
|---|---|---|---|---|---|---|
| `shopverse.test` | Shopverse | marketplace | good | Large marketplace | Large established marketplace; buyer protection and platform-managed refunds on all orders. | lowprice, nobiz, external, pressure, inconsistent, injection, concealed, lookalike |
| `dealbazaar.test` | DealBazaar | marketplace | mid | Loosely regulated marketplace | Loosely regulated sellers; product quality varies; refunds are inconvenient. | site-mid |
| `northline-outfitters.test` | Northline Outfitters | independent | good | Established retailer | Established independent retailer; verified business since 2014. | trusted |
| `harbour-lane-goods.test`, `campus-corner-clearance.test`, `primegift-mart.test`, `easyreturn-store.test`, `urban-kit-club.test`, `globalship-direct.test` | the store's name | independent | good | Verified small business | Registered small business; Small Business Verified. | neutral, benign, payment, returns, data-mid, data-high |
| `north1ine-outfitters.test` | North1ine Outfitters | independent | poor | Imitation website | This website imitates Northline Outfitters and is not registered to that business. | site-fake |
| `best-gear-outlet.test` | Best Gear Outlet | independent | poor | Little-known website | This website is rarely mentioned anywhere and has almost no independent buyer reports. | site-bad |

The site-bad summary describes obscurity, not missing registration. A summary that said "not registered" would contradict the merchant's verification indicator, and the variant must keep `verified_business: true` to stay a single signal.

### 2.3 Lookup

`app/runtime/sites.py` loads the registry once and provides `site_for(url) -> Site | None`. It parses the host and matches it exactly. Subdomains and `www.` do not match.

`merchants()` in `app/runtime/merchants.py` attaches the entry to each local merchant through a new optional field `Merchant.site: Site | None = None`. `merchants.json` never contains `site`, so the registry stays the single source. Live and replay merchants keep `site = None`.

`local_evidence()` does not map `site`, so the risk agent sees only the store's URL, as it does today.

## 3. Dataset Changes

### 3.1 Merchant websites

- **Marketplace stores** get `https://shopverse.test/store/<slug>` (or `dealbazaar.test`). Contact emails, descriptions and reviews that named the old domain are rewritten. Store emails use the platform domain, for example `daily-flash-picks@shopverse.test`.
- **nobiz** moves to `shopverse.test`. Its throwaway domain `shop-8812.test` is removed. It keeps no contact and `verified_business: false`, so its only signal is still `missing_business`.
- **Independent sites** keep their current domains.

### 3.2 `lookalike` becomes a knockoff product

- **Products:** the three `study-*-target-lookalike` offers change name and brand to imitate the genuine product. Specifications, attributes, rating and rating count stay the same as the target. Each description adds one knockoff marketing line, for example "Same design as the Lumen Hush ANC at a fraction of the price." Without that line neither the agent, which sees one listing at a time, nor a participant could tell what the product imitates.

  | Category | Genuine | Knockoff name | Knockoff brand |
  |---|---|---|---|
  | Headphones | Lumen Hush ANC | Lumin Hush ANC | Lumin |
  | Running shoes | Vela Tempo Daily | Vella Tempo Daily | Vella |
  | Backpacks | Atlas Scholar 30 | Atlis Scholar 30 | Atlis |

- **Merchant:** `study-m-lookalike` gets an ordinary name, Brightway Goods, at `shopverse.test/store/brightway-goods`. Its description no longer claims to be the Northline store. It keeps `lookalike_identity: true`, which now means "sells knockoff products". Its signal and ground truth (SUSPICIOUS) are unchanged.
- **Rule text** in `assess()`: "The product name and brand imitate another brand."
- **Agent definition** in `risk_agent.INSTRUCTIONS`: "lookalike: product names or brands imitating a well-known brand (knockoff products)."
- **Original fixtures** that set `lookalike_identity` now show the new rule text. Their scenarios are no longer used.
- **Test exception:** `test_offers_share_product_fields` exempts the lookalike offers from sharing name, brand and description.

### 3.3 New variants

Each new variant has one merchant and three target offers, one per category. Apart from the website, every field is as clean as `neutral`: verified, contact listed, standard payment and returns.

| Variant | Merchant | Website | Price | Signal | Ground truth |
|---|---|---|---|---|---|
| `site-mid` | `study-m-site-mid` | `dealbazaar.test/store/<slug>` | 0.75P | site_reputation_mid | UNCERTAIN |
| `site-bad` | `study-m-site-bad` | `best-gear-outlet.test` | 0.80P | site_reputation_poor | SUSPICIOUS |
| `site-fake` | `study-m-site-fake` | `north1ine-outfitters.test` | 0.80P | site_reputation_poor | MALICIOUS |

- **site-fake:** the merchant copies the name "Northline Outfitters" exactly. The only cue is the domain, which matches how imitation sites work.
- **Price:** every new price stays above the `low_price` ratio of 0.5P.
- **Reviews:** follow the existing rules. Each offer has 3 reviews of its own, and any two listings share at most one review.

The dataset grows from 15 to 18 study merchants and from 15 to 18 target offers per category.

### 3.4 Research files

- `risk_offer_manifest.json`: add the 9 new offers. `visible_in` for the new variants is `["website_reputation"]`.
- `merchant_ground_truth.json`: add the 3 new merchants.
- `data/replay/study_listings.json`: regenerate it, because merchant URLs changed and offers were added.

## 4. Rules, Policy Defaults and Explanation

- **Rule IDs:** `RULES` in `merchant_risk.py` gains `site_reputation_mid` and `site_reputation_poor`. They stay out of `risk_agent.AGENT_RULES`.
- **Default weights** in `config/merchant_risk_rules.json`. The policy owner can change them:

  | Rule | Weight | Alone | Reference |
  |---|---|---|---|
  | site_reputation_mid | 1 | LOW → ALLOW | Same as `pressure` and `low_price` |
  | site_reputation_poor | 4 | MEDIUM → REVIEW | Same as `lookalike` |

  Neither rule is a non-negotiable block. Thresholds and decisions are unchanged.
- **Detection:** `site_evidence(merchant, config) -> list[RiskEvidence]` returns one item for a `mid` or `poor` site and nothing otherwise. Both `assess()` and `assess_live()` call it.
- **Evidence text:** `"{name} ({domain}) has a mixed website reputation. {summary}"` for `mid`, and `"... has a poor website reputation. {summary}"` for `poor`. The `score()` template and the brief profile are unchanged.
- **Evaluation script:** `scripts/evaluate_risk_agent.py` ignores both rules, as it ignores `low_price`.

## 5. Display

`frontend/src/lib/beany.ts` adds the `Site` type and `site?: Site | null` on `Merchant`. In `MerchantDetails.tsx`, only the catalogue branch changes:

- **Website line:** shows only the host, for example "Simulated website: shopverse.test". This applies to every catalogue merchant.
- **Reputation line**, when `site` is present: the text "Website reputation: Good", "Mid" or "Poor", followed by the meter. The text is what screen readers read.
- **Meter:**
  - 72 × 14 px, pill-shaped (fully rounded ends), with a 1px outline in the primary text colour. That is black in light mode and flips in dark mode.
  - Three cells sit inside the outline, separated by white gaps rather than lines. The outer cells round their outer corners.
  - Fills: Good is 3 green cells, Mid is 2 amber cells, Poor is 1 red cell. Empty cells are light grey.
  - The meter is `aria-hidden`.
- **Label line:** `site.label`, for example "Large marketplace".
- **Without a site** (original fixtures): only the website line is shown.

## 6. Testing

All backend tests stay offline.

- **Registry:**
  - Every entry validates and every domain is unique.
  - Every study merchant's host is registered.
  - Marketplace URLs have a `/store/` path and independent URLs do not.
  - `merchants.json` has no `site` key.
  - An unregistered host gives `site = None` and no signal.
  - Subdomains do not match.
- **Consistency:** a study merchant's text mentions no domain other than its own host.
- **Single signal:** every manifest variant without a `site_reputation_*` signal is on a `good` site. site-mid fires only `site_reputation_mid`. site-bad and site-fake fire only `site_reputation_poor`.
- **Policy defaults** (risk tests, not dataset tests): weights are 1 and 4. site-mid is ALLOW. site-bad and site-fake are REVIEW. The evidence text matches section 4.
- **AI mode:** `assess_live()` with a fake chooser includes site evidence. `local_evidence()` output contains no registry text.
- **Knockoff:**
  - Lookalike offers differ from the target in name and brand.
  - Their descriptions contain the imitation line, and their specifications match the target.
  - The agent prompt carries the new definition.
- **Denylist:** add real platform names (Amazon, eBay, Pinduoduo, Temu, Lazada, Shopee, Taobao, AliExpress) and check registry text against it.
- **Existing tests:** manifest, scenario, search-ranking and replay tests keep passing after regeneration. `evaluate_risk_agent` ignores the new rules.
- **Frontend:**
  - `npm run typecheck` passes.
  - A Playwright test mocks a session whose merchant has a `mid` site and checks "Simulated website: dealbazaar.test", "Website reputation: Mid", "Loosely regulated marketplace", two filled cells, and `aria-hidden` on the meter. A merchant without a site shows none of these.
  - A browser preview check in light and dark mode.

## 7. Documentation

- `backend/data/README.md`: registry row in the file table, updated variant table, and an editing rule that every study domain must be registered.
- `docs/configuration-guide.md`: the two new weights.
- `docs/data/2026-10-21-study-dataset-design.md`: a note that `lookalike` now means knockoff product, linking here.
