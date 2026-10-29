"use client";
import { useState } from "react";
import type { ShoppingDecision, NeedKey } from "@/lib/decision";
import { ComparisonEvidence } from "./ComparisonEvidence";
import { DecisionTrace } from "./DecisionTrace";
import { MerchantCaution } from "./MerchantCaution";

export function Recommendation({ decision, stale = false, edit, select, selected = false, reviseSeller, updatedSteps = [] }: {
  decision: ShoppingDecision; stale?: boolean; edit: (key: NeedKey) => void;
  select: () => void; selected?: boolean; reviseSeller: (text: string) => void;
  updatedSteps?: string[];
}) {
  const [focus, setFocus] = useState<{ id: string }>();
  const reasonLabels: Record<string, string> = { needs: "Your intent", comparison: "Model choice", seller: "Seller choice", tradeoff: "Trade-off" };
  return <article className="cui-result" aria-label={stale ? "Previous recommendation" : "Current recommendation"}>
    {stale && <p className="cui-stale">Previous recommendation · Compare again using your updated needs.</p>}
    <div className="cui-section-heading"><span className="cui-step-number">3</span><p className="eyebrow">{stale ? "PREVIOUS OPTION" : "RECOMMENDED FOR YOUR INTENT"}</p></div>
    <h2>{decision.product.name}</h2>
    <p className="cui-offer">SGD{decision.offer.price} · {decision.offer.merchant}</p>
    <p className={`cui-fit-label ${decision.needs.budget ? "" : "cui-fit-label--unknown"}`}>{decision.needs.budget ? `Within your ${decision.needs.currency?.value || "SGD"}${decision.needs.budget.value} spending limit` : "Spending limit not confirmed"} · {decision.product.variant}</p>
    <section aria-label="Why I recommend this for you">
      <h3>Why I recommend this for you</h3>
      <dl className="cui-reasoning">{decision.reasons.map(reason => <div key={reason.id} className={reason.id === "tradeoff" ? "cui-reason-tradeoff" : undefined}><dt>{reasonLabels[reason.id]}</dt><dd>{reason.text}</dd></div>)}</dl>
    </section>
    {decision.concerns.map(concern => <MerchantCaution key={concern.offerId} concern={concern} flaggedOffer={decision.comparedOffers.find(offer => offer.id === concern.offerId)} alternative={decision.offer} useAlternative={!stale && !selected ? select : undefined} />)}
    <div className="cui-actions">
      {!selected && <button className="primary" disabled={stale} onClick={select}>Select this offer</button>}
      <button disabled={stale} onClick={() => edit("priority")}>Change priorities</button>
      <button disabled={stale} onClick={() => reviseSeller("Keep the product but find another seller")}>Find another seller</button>
    </div>
    <DecisionTrace decision={decision} inspect={id => setFocus({ id })} edit={stale ? undefined : edit} updatedSteps={updatedSteps} />
    <ComparisonEvidence decision={decision} focus={focus} />
  </article>;
}
