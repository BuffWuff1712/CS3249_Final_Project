# Decision panel: current presentation and proposed arrangement

Reviewed 30 October 2026. Scope: current recommendation, expanded evidence, alternative models and same-model sellers. No application code changed, model calls made, or shopping decisions taken.

Grounding: the user's Lumen Hush ANC screenshot; current frontend components; read-only backend data for that screenshot's session; and a fresh browser inspection of the same interface using the previously saved Echo Study session. The browser and supplied screenshot contain different selected products, so the captures establish arrangement, not a pixel comparison of the Lumen state.

## Inspected steps

| Step | Surface | Current health and finding |
| --- | --- | --- |
| 1 | Current match | Clear product/price hierarchy, but descriptions and risk paragraphs push selection down. Product attributes repeat the description. The size notice appears even for headphones. |
| 2 | Expanded evidence | Specifications, product excerpts and seller terms are available, but key returns/review facts sit behind expansion. Product descriptions and some merchant terms repeat. |
| 3 | Other models | Distinct model section exists, but name/price and a generic disclaimer provide little direct comparison of noise control, battery or weight. |
| 4 | Same-model sellers | Correctly separated from models; blocked offers cannot be selected. Repeated risk explanations make the list tall and comparisons require scrolling. |

## Proposed arrangement

1. Keep a compact selected-offer summary at the top: product, price, seller, three factual feature/concern points, a few labelled facts and the primary selection control.
2. Follow with a comparison area: separate Compare products and Compare sellers sections. Keep the items being compared together in one table, rather than putting each item behind a different tab. Compare two or three models by useful shared fields; compare sellers of the exact same model in rows. More offers remain expandable. Product and seller ratings must remain separate.
3. Expand full description, specifications, source records and detailed risk evidence on demand. Show material concerns and blocked status before selection. Never turn a good website rating or low merchant-risk estimate into a safety guarantee.

### Individual offer example: existing mock data

**Lumen Hush ANC — SGD62.90**
Bargain Depot SG

- Listed features: wireless, over-ear, active noise cancellation.
- Listed battery: up to 40 hours with ANC; weight: 272g.
- Review concern: one of the three supplied product excerpts reports a charging failure. This does not establish a failure rate.

| Fact | Supplied information |
| --- | --- |
| Product reviews | 4.6/5 from 2,310 aggregate ratings; 3 supplied excerpts |
| Seller reviews | 4.0/5 from 318 aggregate seller ratings |
| Returns | 30-day free returns; refund to original payment method |
| Website reputation | Good, in the fictional registry |
| Seller risk | Low predicted risk; rules-based estimate |
| Approval | Required by the user's settings |

Primary action: Select this offer. Secondary actions: Add to cart and More actions. Keep rejection/refinement/alternative controls available in More actions. BLOCK must still disable selection and cart addition, with a visible reason. Payment and data-sharing requests remain visible before final approval; a material data request must not be hidden in a disclosure.

### Different products: example comparison

Prices are shown for the specified catalogue sellers, not claimed market-wide minima. Specifications are listed claims, not independently tested performance.

| Field | Lumen Hush ANC (Bargain Depot SG) | Brio Air 60 (Northline Outfitters) | Brio Desk Headset (Northline Outfitters) |
| --- | --- | --- | --- |
| Price | SGD62.90 | SGD36.90 | SGD34.90 |
| Connection | Wireless Bluetooth; cable supplied | Wireless Bluetooth; cable supplied | Wired 3.5mm |
| Noise cancellation | Active ANC listed | Not listed | Not listed |
| Listed battery | Up to 40h with ANC | Up to 60h | Not supplied |
| Weight | 272g | Not supplied | Not supplied |

On the narrow right panel, show two models together and allow choosing the second comparison column. On mobile, use stacked labelled comparisons rather than squeezing multiple columns into 320px. No fabricated fit scores, subjective comfort guarantees or performance rankings.

### Same product: example seller comparison

| Seller | Price | Listed returns | Website / seller risk |
| --- | --- | --- | --- |
| Bargain Depot SG | SGD62.90 | 30 days; original-payment refund | Good / Low predicted risk |
| Campus Corner Clearance | SGD70.90 | 30 days; original-payment refund | Good / Low predicted risk |
| Northline Outfitters (northline-outfitters.test) | SGD179.00 | 30 days; original-payment refund | Good / Low predicted risk |

Each row has a Details/Compare control; show current offer clearly. Keep blocked offers separately identifiable with reasons and disabled selection. For example, Quickpay Deals is blocked despite a Good website rating. Other sellers can have important return exceptions even where the headline says 30 days: EasyReturn Store specifies store credit, opened-item exclusions and customer-paid shipping. Preserve these distinctions in the details and surface relevant exceptions in the row.

## Limits

This review checks content arrangement and the available structured fields. It does not establish recommendation quality, live seller reliability, measured accessibility compliance or improved usability from user testing. The proposal reuses existing backend data and preserves separate product identity, seller risk, website reputation and approval policy.

## Current screenshots

1. Current match: clear hierarchy, dense summary.

![Current match](/Users/arnav/Documents/Codex/2026-10-24/i-w/CS3249_Final_Project_fresh/plans/verification/decision-panel-review/01-current.png)

2. Product evidence: available facts, repeated description.

![Expanded evidence](/Users/arnav/Documents/Codex/2026-10-24/i-w/CS3249_Final_Project_fresh/plans/verification/decision-panel-review/02-evidence.png)

3. Seller terms and beginning of alternatives: important terms below the fold.

![Terms and alternatives](/Users/arnav/Documents/Codex/2026-10-24/i-w/CS3249_Final_Project_fresh/plans/verification/decision-panel-review/03-options.png)

4. Model alternatives and beginning of same-model sellers: little side-by-side information.

![Alternative models](/Users/arnav/Documents/Codex/2026-10-24/i-w/CS3249_Final_Project_fresh/plans/verification/decision-panel-review/04-sellers.png)

5. Seller detail: repeated paragraphs and blocked-offer evidence.

![Seller detail](/Users/arnav/Documents/Codex/2026-10-24/i-w/CS3249_Final_Project_fresh/plans/verification/decision-panel-review/05-seller-detail.png)

## Design references

[GOV.UK table guidance](https://design-system.service.gov.uk/components/table/) recommends tables for scanning and comparing structured rows/columns, with meaningful captions and header scopes. [Nielsen Norman Group comparison guidance](https://www.nngroup.com/articles/comparison-tables/) supports comparable attributes and understandable labels. [GOV.UK tabs guidance](https://design-system.service.gov.uk/components/tabs/) warns against making users remember information across tabs to compare it; therefore each comparison table keeps its alternatives together, and product/seller sections remain separately identifiable.
