# Independent check: real SoCLaaS conversation with local products

Reviewed the completed session `7488e062-a227-4d06-9150-85296e9eb505` in `/tmp/beany-shop-soclass.sqlite3`, the before/after-question JSON snapshots, and the evidence-answer screenshot. This review made no API calls and did not read credentials.

| Check | Observed result |
| --- | --- |
| Runtime | `mode=openai`, product provider `catalogue`, risk detection `rules` |
| Needs | Headphones, daily train commute, confirmed SGD, hard budget 200, noise-cancellation preference |
| Actual shopping steps | Two searches, two product inspections, one propose step |
| Search repair | Initial “Headphones noise cancellation” query returned zero; broader “Headphones” query returned four local offers |
| Selected offer | Echo Study, Campus Clearance, SGD35; within hard budget |
| Follow-up evidence | Product has no supplied review excerpts or product rating; merchant record offers 30-day simulated refunds |
| Read-only question | Session ID, brief, selected proposal ID, cart and receipts are identical before/after the question |
| Approval gate | Both question snapshots have one selected cart item and zero receipts; final database has one receipt, with approve/checkout events after the question |
| Browser Use | Zero `browser_search` events; no live shopping source was used |

The real model asked for currency/budget, interpreted the confirmed needs, recovered from an empty query, selected a local offer, and answered a review/returns question without altering the saved selection. The evidence-answer capture shows the correct seller and SGD35 price.

## Quality limits

This is one successful end-to-end path, not broad language-understanding or recommendation-quality validation. Only two offers were inspected; the result does not establish the best noise cancellation across the catalogue. Risk assessment used rules, so AI risk-review behaviour was not tested.

The initial answer exposed a wording precision issue: it says “there are no customer reviews.” The precise supported statement is that no **product review excerpts are supplied in this catalogue record**. The merchant separately has an aggregate 120-review count and 4.5 rating; those are not product-review text. The answer correctly gave the 30-day simulated refund term and invented no review sentiment.

The `soclass-restored-receipt.png` capture was inspected independently: one Echo Study receipt at SGD35 is displayed after refresh, with the no-real-order/payment notice.

## Precision correction and follow-up

Reviewed the small change in `backend/config/prompts/dialogue.txt`: it explicitly distinguishes supplied product review excerpts, product aggregate ratings and seller aggregate ratings, and prohibits treating absent excerpts as proof that no reviews exist. It changes explanation guidance only.

The subsequent actual-model answer to an explicit excerpt question was: “No product review excerpts were supplied for the Echo Study. I will keep your current needs and offer unchanged while you decide.” The stored interpretation has `changes=[]` and `intent=explain`; there are no additional shopping-tool events after that question. The original brief remains unchanged and the current offer remains Campus Clearance/Echo Study/SGD35. The previously created receipt count remains one. The affected backend suites passed 39 tests in 5.55 seconds.

This follow-up used an explicit “review excerpts” question, rather than repeating the original broader reviews/returns wording. It supports the corrected response path without establishing that every review question will be answered correctly.

## Final independent conclusion

Cross-checked `soclass-final-audit.json` against the SQLite session: two proposals exist (the original plus the explicit UI reproposal used for the precision follow-up), the latest product is `offer-benign`, the original hard SGD200 brief is retained, the cart is empty after the completed checkout, and exactly one receipt exists. Browser Use event count remains zero.

Exact before/after state invariance is proven for the **first** review/returns question by the two saved snapshots. The final wording follow-up has an event/state audit, not a separate before/after snapshot pair; no stronger invariance claim is made for it.

The bounded real-SoCLaaS/local-catalogue journey passes independent review. No actionable flow or approval defect remains in this observed journey. Broad language understanding, exhaustive recommendation quality, AI risk detection and live product browsing remain outside this validation.
