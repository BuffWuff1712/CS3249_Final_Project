"use client";
import { useEffect, useState } from "react";
import type { ShoppingDecision, NeedKey, Priority } from "@/lib/decision";
import { compareNeeds } from "@/lib/shoppingScenario";
import { priorities } from "@/lib/shoppingNeeds";
import { ComparisonEvidence } from "./ComparisonEvidence";
import { DecisionTrace } from "./DecisionTrace";
import { MerchantCaution } from "./MerchantCaution";
import { CheckCircleIcon, MinusCircleIcon, ScalesIcon } from "./ShoppingIcons";

export function Recommendation({ decision, stale = false, edit, select, selected = false, reviseSeller, updatedSteps = [], source }: {
  decision: ShoppingDecision; stale?: boolean; edit: (key: NeedKey) => void;
  select: () => void; selected?: boolean; reviseSeller: (text: string) => void;
  updatedSteps?: string[]; source?: { id: string };
}) {
  const [focus, setFocus] = useState<{ id: string }>();
  useEffect(() => { if (source) setFocus(source); }, [source]);
  const priority = decision.needs.priority?.value as Priority;
  const alternative = decision.alternative;
  const otherPriority = priorities[decision.product.category as keyof typeof priorities]?.find(value => value !== priority);
  const alternativeDecision = alternative ? compareNeeds(decision.needs, decision.revision, { productId: alternative.id }).decision : null;
  const blocked = decision.concerns.filter(concern => concern.blocked);
  const advantage = (value: string) => { const text = value.replace(/^(?:has|is) /, ""); return text.charAt(0).toUpperCase() + text.slice(1); };
  return <article className="cui-result cui-recommendation" aria-label={stale ? "Previous recommendation" : "Current recommendation"}>
    {stale && <p className="cui-stale">Previous recommendation · Compare again using your updated needs.</p>}
    <div className="cui-recommendation-heading"><h2 className="cui-panel-title">{stale ? "Previous match" : "Your current match"}</h2><button className="cui-link" onClick={() => setFocus({ id: decision.product.id })}>View evidence</button></div>
    <div className="cui-product-heading"><h3>{decision.product.name}</h3><div><strong>SGD{decision.offer.price}</strong><span>{decision.offer.merchant}</span></div></div>
    {decision.product.category === "Running shoes" && <p className="cui-source">Variant: {decision.product.variant.replaceAll("-", " · ")}</p>}
    <p className={decision.needs.budget ? "sr-only" : "cui-fit-label"}>{decision.needs.budget ? `Within your ${decision.needs.currency?.value || "SGD"}${decision.needs.budget.value} spending limit` : "Spending limit not confirmed"} · {decision.product.variant}</p>
    <section aria-label="Why I recommend this for you" className="cui-choice-reasons">
      <h4 className="sr-only">Why I recommend this for you</h4>
      <dl>
        <div className="sr-only"><dt>Your intent</dt><dd>{decision.reasons.find(reason => reason.id === "needs")?.text}</dd></div>
        <div className="cui-benefit"><dt><CheckCircleIcon weight="fill" aria-hidden="true" /><span className="sr-only">Model choice</span></dt><dd>{advantage(decision.product.advantages[priority] || "Matches the represented priority")}.</dd></div>
        <div className="cui-tradeoff"><dt><MinusCircleIcon weight="fill" aria-hidden="true" /><span className="sr-only">Trade-off</span></dt><dd>{decision.reasons.find(reason => reason.id === "tradeoff")?.text}</dd></div>
        <div className="cui-seller-reason"><dt className="sr-only">Seller choice</dt><dd><ScalesIcon aria-hidden="true" /><span>{decision.needs.sellerPreference?.source === "confirmed" ? "Your seller preference" : "Suggested tie-breaker"}: {decision.needs.sellerPreference?.value || "longer returns"} · <button className="cui-link" disabled={stale} onClick={() => edit("sellerPreference")}>Edit</button></span></dd></div>
      </dl>
    </section>
    {!selected && <button className="primary cui-select" disabled={stale} onClick={select}>Select this offer</button>}
    {selected && <p className="cui-selected-label"><CheckCircleIcon weight="fill" aria-hidden="true" />Offer selected</p>}
    {alternative && <section className="cui-alternative" aria-label="Other model considered"><div className="cui-recommendation-heading"><h4>Other option</h4><button className="cui-link" onClick={() => setFocus({ id: alternative.id })}>View comparison</button></div><div className="cui-product-heading"><h3>{alternative.name}</h3>{alternativeDecision && <strong>SGD{alternativeDecision.offer.price}</strong>}</div><p>{advantage(alternative.advantages[otherPriority || priority] || "Limited comparative evidence")}. {alternative.compromise[otherPriority || priority]} {alternativeDecision ? "" : "No selectable offer within your current needs."}</p>{otherPriority && <button className="cui-link" disabled={stale} aria-description="Changes your product priority and compares the models again." onClick={() => reviseSeller(`${otherPriority} first`)}>Prioritise {otherPriority}</button>}</section>}
    {!!blocked.length && <section className="cui-excluded" aria-label="Excluded sellers"><h4>Excluded seller{blocked.length > 1 ? "s" : ""}</h4>{blocked.map(concern => <MerchantCaution key={concern.offerId} concern={concern} flaggedOffer={decision.comparedOffers.find(offer => offer.id === concern.offerId)} alternative={decision.offer} useAlternative={!stale && !selected ? select : undefined} />)}</section>}
    {decision.concerns.filter(concern => !concern.blocked).map(concern => <MerchantCaution key={concern.offerId} concern={concern} flaggedOffer={decision.offer} />)}
    <div className="cui-secondary-actions"><button disabled={stale} onClick={() => edit("priority")}>Change priorities</button><button disabled={stale} onClick={() => reviseSeller("Keep the product but find another seller")}>Find another seller</button></div>
    <DecisionTrace decision={decision} inspect={id => setFocus({ id })} edit={stale ? undefined : edit} updatedSteps={updatedSteps} />
    <ComparisonEvidence decision={decision} focus={focus} />
  </article>;
}
