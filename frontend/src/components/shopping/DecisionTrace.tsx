import type { NeedKey, ShoppingDecision } from "@/lib/decision";

export function DecisionTrace({ decision: d, inspect, edit, updatedSteps = [] }: {
  decision: ShoppingDecision; inspect: (id: string) => void; edit?: (key: NeedKey) => void; updatedSteps?: string[];
}) {
  const reason = (id: string) => d.reasons.find(r => r.id === id)?.text;
  const title = (id: string, label: string) => <h3>{label} {updatedSteps.includes(id) && <span className="cui-updated-label">Updated</span>}</h3>;
  return <details className="cui-evidence">
    <summary>How I reached this recommendation</summary>
    <ol aria-label="Decision steps" className="cui-trace">
      <li>{title("needs", "Interpreted needs")}<p>{reason("needs")}</p>{edit && <><button onClick={() => edit("priority")}>Change this priority</button> <button onClick={() => edit("usage")}>Change this use case</button></>}</li>
      <li>{title("eligibility", "Eligibility decisions")}<p>{d.needs.budget ? `The selected SGD${d.offer.price} offer is within your SGD${d.needs.budget.value} limit. I kept that limit while comparing.` : "You have not confirmed a spending limit. I compared prices without claiming affordability."}</p><button onClick={() => inspect(d.offer.id)}>Inspect offer eligibility</button> {edit && <button onClick={() => edit("budget")}>Change this budget</button>}</li>
      <li>{title("comparison", "Product comparison")}<p>{reason("comparison")} That difference matters for {d.needs.priority?.source === "confirmed" ? "your stated" : "the assumed"} priority.</p><button onClick={() => inspect(d.product.id)}>Inspect product comparison</button></li>
      <li>{title("seller", "Seller comparison")}<p>{reason("seller")}</p><button onClick={() => inspect(d.offer.id)}>Inspect seller comparison</button> {edit && <button onClick={() => edit("sellerPreference")}>Change this seller preference</button>}</li>
      <li>{title("choice", "Final choice")}<p>I recommend {d.product.name} from {d.offer.merchant} at SGD{d.offer.price} using these criteria. {reason("tradeoff")}</p><button onClick={() => inspect(d.offer.id)}>Inspect selected offer</button></li>
    </ol>
  </details>;
}
