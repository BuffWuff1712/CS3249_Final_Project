import { useEffect, useRef } from "react";
import type { ShoppingDecision } from "@/lib/decision";
import { merchantConcern } from "@/lib/shoppingScenario";
import { MerchantCaution } from "./MerchantCaution";

export function ComparisonEvidence({ decision, focus }: { decision: ShoppingDecision; focus?: { id: string } }) {
  const details = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (!focus || !details.current) return;
    details.current.open = true;
    document.getElementById(`source-${focus.id}`)?.focus();
  }, [focus]);
  return <details className="cui-evidence" ref={details}>
    <summary>View comparison and sources</summary>
    <section aria-label="Comparison and sources">
      <p className="cui-source">Fictional catalogue records, not visited websites. Ratings and reviews are authored examples; authenticity was not verified.</p>
      <h3>Products compared</h3>
      {decision.comparedProducts.map(product => <section key={product.id} id={`source-${product.id}`} tabIndex={-1} className="cui-source-record" aria-label={`Product evidence for ${product.name}`}>
        <h4>{product.name}</h4>
        <p>{product.rating ?? "Unknown rating"} / 5 · {product.rating_count?.toLocaleString("en-SG") ?? "Unknown count"} product reviews</p>
        <dl>{Object.entries(product.specifications).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || "Unknown; not supplied"}</dd></div>)}</dl>
        {product.reviews?.map(review => <blockquote key={review.title}><strong>{review.title}</strong> · {review.rating}/5<p>{review.text}</p></blockquote>)}
        {!product.reviews?.length && <p>Product review excerpts: Unknown; not supplied.</p>}
        <small>Catalogue record: {product.id} · Variant: {product.variant}</small>
      </section>)}
      <h3>Offers for {decision.product.name}</h3>
      {decision.comparedOffers.map(offer => <section key={offer.id} id={`source-${offer.id}`} tabIndex={-1} className="cui-source-record" aria-label={`Seller evidence for ${offer.merchant}`}>
        <h4>{offer.merchant} · SGD{offer.price}</h4>
        {decision.needs.budget && offer.price > Number(decision.needs.budget.value) && <p><strong>Above your spending limit.</strong> This offer cannot be selected unless you explicitly change the limit.</p>}
        <p>{offer.rating ?? "Unknown rating"} / 5 · {offer.reviewCount.toLocaleString("en-SG")} seller reviews</p>
        <dl><div><dt>Return period</dt><dd>{offer.returnsDays === null ? "Unknown; not supplied" : `${offer.returnsDays} days`}</dd></div><div><dt>Payment terms</dt><dd>{offer.payment || "Unknown; not supplied"}</dd></div></dl>
        {merchantConcern(offer) && <MerchantCaution concern={merchantConcern(offer)!} flaggedOffer={offer} label={`Source caution for ${offer.merchant}`} />}
        <small>Catalogue record: {offer.id}</small>
      </section>)}
    </section>
  </details>;
}
