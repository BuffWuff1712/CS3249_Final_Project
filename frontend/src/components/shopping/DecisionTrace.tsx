import type { NeedKey, ShoppingDecision } from "@/lib/decision";

export function DecisionTrace({ decision: d, inspect, edit }: {
  decision: ShoppingDecision; inspect: (id: string) => void; edit?: (key: NeedKey) => void;
}) {
  const reason = (id: string) => d.reasons.find(r => r.id === id)?.text;
  return <details className="cui-evidence">
    <summary>How I reached this recommendation</summary>
    <ol aria-label="Decision steps" className="cui-trace">
      <li><h3>Interpreted needs</h3><p>{reason("needs")}</p>{edit && <button onClick={() => edit("priority")}>Change this priority</button>}</li>
      <li><h3>Eligibility decisions</h3><p>{d.needs.budget ? `The selected SGD${d.offer.price} offer is within your SGD${d.needs.budget.value} limit. I kept that limit while comparing.` : "You have not confirmed a spending limit. I compared prices without claiming affordability."}</p><button onClick={() => inspect(d.offer.id)}>Inspect offer eligibility</button></li>
      <li><h3>Product comparison</h3><p>{reason("comparison")} That difference matters for your stated priority.</p><button onClick={() => inspect(d.product.id)}>Inspect product comparison</button></li>
      <li><h3>Seller comparison</h3><p>{reason("seller")}</p><button onClick={() => inspect(d.offer.id)}>Inspect seller comparison</button></li>
      <li><h3>Final choice</h3><p>I recommend {d.product.name} from {d.offer.merchant} at SGD{d.offer.price} using these criteria. {reason("tradeoff")}</p></li>
    </ol>
  </details>;
}
