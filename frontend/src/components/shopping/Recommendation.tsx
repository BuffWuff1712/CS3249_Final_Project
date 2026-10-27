import type { ShoppingDecision } from "@/lib/decision";

export function Recommendation({ decision }: { decision: ShoppingDecision }) {
  return <article className="cui-result" aria-label="Current recommendation">
    <p className="eyebrow">RECOMMENDED FOR YOUR COMMUTE</p>
    <h2>{decision.product.name}</h2>
    <p className="cui-offer">SGD{decision.offer.price} · {decision.offer.merchant}</p>
    <section aria-label="Why I recommend this for you">
      <h3>Why I recommend this for you</h3>
      {decision.reasons.map(reason => <p key={reason.id}>{reason.text}</p>)}
    </section>
  </article>;
}
