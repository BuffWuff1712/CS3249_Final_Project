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
  return <article className="cui-result" aria-label={stale ? "Previous recommendation" : "Current recommendation"}>
    {stale && <p>Previous recommendation · Compare again using your updated needs.</p>}
    <p className="eyebrow">RECOMMENDED FOR YOUR NEEDS</p>
    <h2>{decision.product.name}</h2>
    <p className="cui-offer">SGD{decision.offer.price} · {decision.offer.merchant}</p>
    <section aria-label="Why I recommend this for you">
      <h3>Why I recommend this for you</h3>
      {decision.reasons.map(reason => <p key={reason.id}>{reason.text}</p>)}
    </section>
    {decision.concerns.map(concern => <MerchantCaution key={concern.offerId} concern={concern} />)}
    <div className="cui-actions">
      {!selected && <button className="primary" disabled={stale} onClick={select}>Select this offer</button>}
      <button disabled={stale} onClick={() => edit("priority")}>Change priorities</button>
      <button disabled={stale} onClick={() => reviseSeller("Keep the product but find another seller")}>Find another seller</button>
    </div>
    <DecisionTrace decision={decision} inspect={id => setFocus({ id })} edit={stale ? undefined : edit} updatedSteps={updatedSteps} />
    <ComparisonEvidence decision={decision} focus={focus} />
  </article>;
}
