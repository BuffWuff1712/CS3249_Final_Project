# Browser review of readability annotations

Reviewed 1 November 2026 on main at a53ac86. No implementation changes.

The local servers were stopped, so the existing frontend was started at localhost:3200 and backend at localhost:8200 using the mock LLM, local catalogue, rules assessment and an isolated audit database. No paid APIs, Browser Use or purchases. A desktop viewport override (1280 x 900) reproduced the table layout; the override was reset afterward. The default narrow layout was also observed, but this was not a full mobile or accessibility audit.

## Browser steps and findings

1. Search headphones and compare Lion City Sports Hub. Summary works; readability needs improvement. The browser shows Lumen Hush ANC at SGD142.90, product rating 4.6/5 with 2,310 aggregate ratings and three supplied excerpts, seller rating 4/5 with 133 ratings, 40-hour listed battery, Good website reputation and Medium merchant risk. Features have no match highlighting; ratings and risk are plain text. Capture: verification/readability-browser-audit/01-current-offer.png.
2. Open View risk evidence. Disclosure works; information hierarchy is poor. The inconsistency concern is visible three times: in the risk explanation, individual evidence and merchant-risk policy explanation. The approval requirement is mixed into the same block. Capture: verification/readability-browser-audit/02-risk-evidence.png.
3. Scroll to the seller table. Actions and current-offer indicator work; price wrapping and information density impair reading. SGD142.90 and SGD62.90 split inside their numeric amount at desktop panel width. Buttons repeat seller names over multiple lines. Website and merchant risk are both small muted text. Capture: verification/readability-browser-audit/03-seller-table.png.
4. Open Everyday Value Co Details. Evidence access works; the row is already very tall before expansion because a whole risk paragraph is inline. Its Compare action remains disabled, while the current Lion City row is disabled because it is already current. These are different reasons and should be labelled differently. Capture: verification/readability-browser-audit/04-blocked-seller.png.

## Recommended presentation changes

| Area | Solution |
| --- | --- |
| Priority matching | Show supported saved needs as labelled match chips with icons; use all relevant attributes/specifications, not the first four. Keep unknowns distinct. Do not infer a battery-duration requirement from commuting alone. |
| Battery | Emphasise “Up to 40 hours” with a battery icon; preserve “with noise cancelling on” next to it. |
| Ratings | Reuse a fractional-star component with exact numeric rating and count. Product and seller ratings stay separately labelled; supplied excerpts are not the aggregate count. Unknown ratings show text rather than zero stars. |
| Risk | Amber Medium / red High or Critical badges with icon and text. Low remains an estimate, not a safety guarantee. Prefer categorical indicators to an uncalibrated percentage bar. |
| Evidence | Show each unique concern once, with a bold short title and supplied evidence. Separate concerns, permission restrictions and assessment method. Keep one uncertainty note and preserve all distinct material reasons. |
| Reputation versus risk | Reuse compact, separately labelled website-tier and seller-risk badges in summary and table; never imply that Good website reputation means a safe merchant. |
| Price | Keep numeric amounts unbroken, use tabular digits and sufficient column width; currency may be on a separate line. Do not make the entire table overflow narrow layouts. |
| Actions | Use concise visible Compare / Current offer / Blocked labels, retaining seller names in accessible names. Keep all actual policy gates intact. |
| Blocked rows | Show a concise specific reason inline; put the longer methodology and raw evidence in Details. Do not conceal the blocking reason. |

## Limits and implementation boundaries

- The browser reproduces the supplied states and confirms the visible issues; suggested redesigns have not been implemented or usability-tested.
- Current evidence only says merchant/product information is inconsistent. Neither the displayed source nor its generic fixture signal identifies the exact fields that conflict; a more specific explanation requires richer evidence data.
- The mock parser persisted noise cancellation but did not fully extract every phrase of the test request. This review does not establish live-LLM intent extraction quality. Highlighting must use reliable saved needs and supported product evidence.
- Existing controls, current-offer highlighting, product/seller rating separation, source access and blocking rules are useful and should be preserved.
- Icons must accompany readable text; colour alone is insufficient. Contrast, screen-reader output and keyboard behaviour of proposed components need checking during implementation.
