import type { ShoppingDecision } from "@/lib/decision";

export function ComparisonEvidence({ decision, open = false }: { decision: ShoppingDecision; open?: boolean }) {
  return <details className="cui-evidence" open={open || undefined}>
    <summary>View comparison and sources</summary>
    <section aria-label="Comparison and sources">
      <p className="cui-source">Fictional catalogue records, not visited websites. Ratings and reviews are authored examples; authenticity was not verified.</p>
      <h3>Products compared</h3>
      {decision.comparedProducts.map(product => <section key={product.id} id={`source-${product.id}`} className="cui-source-record" aria-label={`Product evidence for ${product.name}`}>
        <h4>{product.name}</h4>
        <p>{product.rating ?? "Unknown rating"} / 5 · {product.rating_count?.toLocaleString("en-SG") ?? "Unknown count"} product reviews</p>
        <dl>{Object.entries(product.specifications).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || "Unknown; not supplied"}</dd></div>)}</dl>
        {product.reviews?.map(review => <blockquote key={review.title}><strong>{review.title}</strong> · {review.rating}/5<p>{review.text}</p></blockquote>)}
        <small>Catalogue record: {product.id} · Variant: {product.variant}</small>
      </section>)}
      <h3>Offers for {decision.product.name}</h3>
      {decision.comparedOffers.map(offer => <section key={offer.id} id={`source-${offer.id}`} className="cui-source-record" aria-label={`Seller evidence for ${offer.merchant}`}>
        <h4>{offer.merchant} · SGD{offer.price}</h4>
        <p>{offer.rating ?? "Unknown rating"} / 5 · {offer.reviewCount.toLocaleString("en-SG")} seller reviews</p>
        <dl><div><dt>Return period</dt><dd>{offer.returnsDays === null ? "Unknown; not supplied" : `${offer.returnsDays} days`}</dd></div><div><dt>Payment terms</dt><dd>{offer.payment || "Unknown; not supplied"}</dd></div></dl>
        <small>Catalogue record: {offer.id}</small>
      </section>)}
    </section>
  </details>;
}
