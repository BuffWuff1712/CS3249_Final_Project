# PR #25: changes and review checklist

This is the functional change inventory for the CUI feature branch, including the UI clarity follow-up. The new interface is at `/shop`. Test it on `feat/cui-v2-issues` before merging into `main`; merging is not necessary to run or review the changes.

## What changed

| Area | Delivered behaviour |
| --- | --- |
| Purchase entry | A prominent “What are you buying?” input explains product, use case, budget and priority. Editable headphone, running-shoe and risk examples are available before sending. |
| Purchase intent | Clearly labelled Buying, For, Spending limit and Most important values replace an undifferentiated row of tags. Confirmed facts and editable assumptions remain distinguishable. |
| Clarification | Specific requests compare immediately; vague requests receive bounded, useful questions. Browsing without a budget works. Unsupported inputs and USD requests clarify rather than inventing facts or exchange rates. |
| Needs editor | Users can edit/remove supported needs. Switching fields restores each field’s constraint state. Invalid values have a red, labelled error beside the input. |
| Recommendation | One primary product/offer, a meaningful alternative, price and seller. Product ranking follows the current represented priority, within the spending limit. |
| Default explanation | Four explicitly labelled reasons: Your intent, Model choice, Seller choice and Trade-off. The compromise is visually separate from actual errors. |
| Expanded reasoning | Five needs/eligibility/product/seller/final-choice steps with evidence links and criterion editors. Only affected steps receive Updated markers after correction. |
| Comparison activity | A local plan/completed-record account with actual model and offer counts and unavailable evidence. It does not pretend to browse websites or display private model reasoning. |
| Corrections | Changing comfort/noise cancellation or cushioning/light weight changes the choice or explains an unchanged winner. Budget and explicit-model changes receive their own causal explanation. |
| Hard limits | Budgets never silently increase. No-match states show a red constraints-conflict flag and useful actions to edit the limit, retry or change the search. |
| Seller changes | “Find another seller” preserves exact product/variant. Price, terms and seller rationale refresh together. Retry preserves that product; comparing other products is explicit. |
| Merchant risk | Every blocked seller offer actually encountered in the current comparison is surfaced by default. A red flag names the seller and price, quotes the payment demand, explains its consequence and recommends a specific eligible offer. |
| Risk action | The flag’s “Use [recommended seller] · SGD[price]” button explicitly selects the current eligible alternative, with the same revision/offer checks as normal selection. The blocked offer itself is never selectable. |
| Evidence | Separate product and seller ratings/counts, specifications, reviews and return/payment terms. Sources remain optional for completion. Missing values are unknown; above-limit offers are clearly labelled. |
| Final decision | Select this offer → recap → Finish decision. This creates no real order/payment and requests no credentials. Existing classic cart/checkout guards remain independent. |
| Refresh and stale state | Selection invalidates on edits. Refresh validates needs and recomputes the exact current offer from versioned fixtures. Corrupt/old state cannot silently restore selection. Browser storage failures are visible. |
| Second category | Running shoes reuse the same intent, explanation, correction, seller, risk and selection flows. Fixed demonstration variant: EU42/blue/new. |
| Accessibility | Keyboard operation, source focus, one status announcement, touch controls and narrow-screen layouts. Meaning is expressed through text and labels as well as colour. |
| Verification | Offline decision/state tests, desktop/mobile journeys, actual screenshots/recordings, input and storage recovery, and a budget-guard mutation regression. The classic settings assertion now targets the application alert rather than Next’s route announcer. |
| Study and presentation | A fair GUI-versus-CUI study protocol, counterbalancing, predefined comprehension/quality rubric, surveys/interviews, run instructions, a reproducible demo and a 15-minute presentation outline. No participant results are claimed. |

## How to read a flag

| Appearance | Meaning | User action |
| --- | --- | --- |
| Red “Blocked seller offer” | A concrete supplied payment term triggers the application’s block rule; the flag names the affected offer | Use the named ordinary-checkout alternative, or inspect the flagged source. The blocked offer cannot be selected. |
| Red comparison/input error | Comparison failed, a need is invalid, or the current constraints have no eligible offer | Retry or correct the highlighted need. The spending ceiling stays in force. |
| Amber information/trade-off | Evidence is incomplete, a prior recommendation is stale, or a product has a stated compromise | Review the uncertainty, compare again after edits, or revise a priority. Incomplete evidence alone is not proof of a scam. |
| Blue intent/update | The current need, editable assumption or changed decision | Correct it if it does not reflect your goal. |
| Green spending/selection status | A displayed price fits the stated ceiling, or an eligible offer has been selected | Review the fit/compromise and finish when ready. This is not a safety or authenticity certificate. |

“Possible scam risk” identifies a concerning seller payment request, not proven criminal intent. This prototype checks authored fictional records. It is not a general spam/scam detector. Small sellers and low prices alone do not trigger a block.

## Test before merging

From `frontend`, run `npm run dev` and open `http://localhost:3000/shop`. The new CUI does not need the backend or live credentials. The `/` route is the older backend-connected simulation.

1. Click Try headphones, inspect/edit the sample request, then Send. Read the labelled intent and the four recommendation reasons.
2. Verify the red SoundRush Deals/SGD209 flag. It must show the actual gift-card request, the consequence, and a selectable alternative. Use Northline Audio/SGD289 and verify that the recap names Northline, not SoundRush.
3. Try the risk example or request the cheapest Echo Quiet offer. Everyday Sound/SGD269 should be recommended as the ordinary-checkout alternative; smaller review history alone is not a block.
4. Change comfort to the highest priority. The needs, product, explanation and current selection must update together. Inspect a source only if useful.
5. Set SGD180. Confirm a red no-match state with the same ceiling and a working Change spending limit action.
6. Repeat with running shoes. Check cushioning versus light weight, exact-variant seller switching and explicit final selection.
7. Repeat at mobile width and with the keyboard. Refresh after selecting, then edit a need and confirm selection clears.

Merge PR #25 only after the updated interaction is acceptable in this manual review. Automated consistency checks do not establish that the interface communicates clearly to its intended users.

See `cui-v2-delivery.md` for verification evidence, `evaluation-guide.md` for the proposed study and `final-demo.md` for the presentation script. The team’s narrated course recording/rehearsal and pre-recruitment work #21–24 remain separate deliverables.
