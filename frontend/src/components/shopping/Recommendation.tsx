"use client";
import { useState } from "react";
import type { ShoppingDecision, NeedKey } from "@/lib/decision";
import { ComparisonEvidence } from "./ComparisonEvidence";
import { DecisionTrace } from "./DecisionTrace";

export function Recommendation({ decision, stale = false, edit }: { decision: ShoppingDecision; stale?: boolean; edit?: (key: NeedKey) => void }) {
  const [focus, setFocus] = useState<{ id: string }>();
  return <article className="cui-result" aria-label={stale ? "Previous recommendation" : "Current recommendation"}>
    {stale && <p role="status">Previous recommendation · Compare again using your updated needs.</p>}
    <p className="eyebrow">RECOMMENDED FOR YOUR NEEDS</p>
    <h2>{decision.product.name}</h2>
    <p className="cui-offer">SGD{decision.offer.price} · {decision.offer.merchant}</p>
    <section aria-label="Why I recommend this for you">
      <h3>Why I recommend this for you</h3>
      {decision.reasons.map(reason => <p key={reason.id}>{reason.text}</p>)}
    </section>
    <DecisionTrace decision={decision} inspect={id => setFocus({ id })} edit={edit} />
    <ComparisonEvidence decision={decision} focus={focus} />
  </article>;
}
