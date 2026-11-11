# Beany demo video: operator notes

Prepared 1 November 2026 against commit `f9e49d9` on `ywt`. Live model (DeepSeek, `BEANY_LLM_MODE=openai`), `demo` scenario, headphones.

**Rehearsed end to end on 1 November 2026** in a fresh `demo` session with the live model; every step below passed. "Observed" lines record that run. The assistant's wording, and which seller it proposes first, can change between runs.

## Before recording (off camera)

1. Backend `curl localhost:8000/health` shows `"mode":"openai","configured":true`; frontend running on port 3000.
2. `http://localhost:3000/research` → researcher key from `backend/.env` → **Unlock scenarios** → **Demonstration (study data)** → **Start fresh participant**.
3. Open `http://localhost:3000/shop` in the same browser. Observed: an extra greeting *"Tell me what you would like to buy: headphones, running shoes or a backpack…"* and an empty needs bar.
4. A fresh `demo` session starts with **share personal data** unticked (permissions belong to the session), so no Settings reset is needed between takes.
5. For a retake, repeat step 2. **Start fresh** inside `/shop` leaves the `demo` scenario.
6. Model turns took 15–35 s in the rehearsal; cut the waits in editing.

## Step-by-step

### 1. Vague request → clarification

Type: `I want something to listen to music on my way to school.`

Observed: no search. The assistant filled in *Headphones* and *commuting* in the needs bar and asked for budget and features ("It's fine to say you're unsure…"). It also offered a button **I'm unsure about those; show me some options**. Don't click it, or step 2 is skipped.

### 2. Answer → search

Type: `Headphones, under SGD200. Wireless and noise cancelling would be nice.`

Keep the budget **at least SGD180**: the clean seller in step 6 costs SGD179.

Observed (about 35 s): needs bar = Headphones · commuting · Up to SGD200 · wireless, noise-cancelling. Match = **Lumen Hush ANC, SGD70.90, Campus Corner Clearance**, low risk, with an *Unusually low price* concern ("A discount alone does not establish wrongdoing"). Another run may propose Bargain Depot SG (SGD62.90), Bayfront Trading or similar instead; the following steps work the same.

### 3. "Show me some options"

No suggestion button for this appeared after step 2, so **type** `Show me some options`.

Observed (about 30 s): a table of matching models with the cheapest seller of each:

| Model / seller | Price |
|---|---|
| Lumen Hush ANC · Bargain Depot SG | SGD62.90 |
| **Lumin** Hush ANC · Brightway Goods | SGD142.90 |
| Brio Air 60 · EasyReturn Store | SGD28.90 |

"Your current selection and needs are unchanged", so the right panel still shows Lumen Hush ANC. Optional talking point: *Lumin* Hush ANC is a look-alike product name.

### 4. Stay on Lumen Hush ANC and open the sellers

The current match is already Lumen Hush ANC, so nothing needs switching. Scroll the right panel to **Compare sellers of this model** (17 sellers). Each row has **Details** and **Compare** buttons. Open **Details** on:

| Seller | Price | Shown as | Reason in Details |
|---|---|---|---|
| **TopBuy Express** ← recommended | SGD142.90 | Medium · Approval needed | *Incomplete business details* |
| **Best Gear Outlet** ← recommended | SGD142.90 | Medium · Approval needed | Website reputation: Poor |
| EasyReturn Store | SGD142.90 | Medium · Approval needed | Store-credit-only refunds and many exclusions |
| Lion City Sports Hub | SGD142.90 | Medium · Approval needed | Contradictory shipping information |

Other rows you will see: Bargain Depot SG and Campus Corner Clearance (low price, low risk); Bayfront Trading (website *Mid*, low risk); blocked: Quickpay Deals (critical, external payment), PrimeGift Mart (unsupported payment method), Everyday Value Co (hidden instructions), GlobalShip Direct and Urban Kit Club (data requests, see step 5).

### 5. Birthday request blocked → unlock in Settings

In the seller table, **Urban Kit Club, SGD142.90** shows *Blocked: "This merchant requests information you have not permitted sharing: date of birth, social media account."*

Click **Settings** (header) → tick **share personal data** → **Save Permissions**. Observed message: *"Permissions saved. Pending proposals have been cleared; request a new proposal when you return."* Click **Back to shopping**. It goes to `/` rather than `/shop`, but that is the same page.

Observed after returning: the chat adds *"Permissions saved. I rechecked the offer you were viewing…"*, and Urban Kit Club changes to **Medium · Needs your approval**. **GlobalShip Direct stays Blocked** (*"Checkout requests unrelated information: government ID."*): a good shot showing that some limits cannot be unlocked.

### 6. Choose a clean seller and check out

Optional: switch the seller table's **Sort by** dropdown (right of the table title) from *Price: low to high* to *Risk: lowest first*. The zero-score sellers (Riverside Supply Co, Harbour Lane Goods, Northline Outfitters SGD179.00) move to the top, and the blocked high and critical sellers to the bottom. In price order, Northline SGD179.00 is the last row.

In the seller table, click **Compare** on **Northline Outfitters, SGD179.00**. Do not click the SGD142.90 row: that one is the look-alike site (`north1ine-outfitters.test`, website *Poor*, medium risk). Clicking Compare posts *"Compare Lumen Hush ANC from Northline Outfitters."* and takes about 15 s.

Observed current match: **Lumen Hush ANC, SGD179.00, Northline Outfitters**. Website reputation: Good, Merchant risk: low estimate, *"No configured risk signals detected for Northline Outfitters"*, no low-price flag, 30-day free returns, seller reviews 4.7/5 (2,140).

Then **Select this offer** → green *Your selected offer* card (*"No receipt, order or payment has been created…"*) → **Finish decision** → *Decision complete* with a receipt ID and *"No real order or payment was created."* **Purchase history** (header) lists the simulated receipt.

Fallback clean seller: **Harbour Lane Goods, SGD169.90** (low risk, no flags).

Avoid using Riverside Supply Co or Daily Flash Picks as "safe" examples. Both show low risk, but in the study data Riverside is a concealed bad seller and Daily Flash Picks uses pressure tactics.
