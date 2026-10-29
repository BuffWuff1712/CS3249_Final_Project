import type { MerchantConcern, ShoppingOffer } from "@/lib/decision";

export function MerchantCaution({ concern, label = "Merchant caution", flaggedOffer, alternative, useAlternative }: {
  concern: MerchantConcern; label?: string; flaggedOffer?: ShoppingOffer;
  alternative?: ShoppingOffer; useAlternative?: () => void;
}) {
  return <section className={`cui-flag ${concern.blocked ? "cui-flag--danger" : "cui-flag--review"}`} aria-label={label} data-severity={concern.blocked ? "blocked" : "review"}>
    <div className="cui-flag-heading"><span className="cui-flag-icon" aria-hidden="true">!</span><div>
      <p className="cui-flag-label">{concern.blocked ? "Blocked seller offer" : "Information needs review"}</p>
      <h3>{concern.blocked ? "Possible scam risk: outside-checkout payment" : "Seller information is incomplete"}</h3>
    </div></div>
    <p className="cui-flag-offer"><strong>{concern.merchant}</strong>{flaggedOffer && <> · SGD{flaggedOffer.price}</>}</p>
    <dl className="cui-flag-facts">
      <div><dt>Flagged evidence</dt><dd>{concern.observation}</dd></div>
      <div><dt>Why it matters</dt><dd>{concern.consequence}</dd></div>
      <div><dt>What to do</dt><dd>{concern.nextStep}</dd></div>
    </dl>
    {concern.blocked && <p className="cui-flag-scope"><strong>This offer is blocked.</strong> The flag applies to {concern.merchant}’s payment terms.</p>}
    {concern.blocked && alternative && useAlternative && <button className="cui-alternative-action" onClick={useAlternative}>Use {alternative.merchant} · SGD{alternative.price}</button>}
    <details className="cui-flag-source"><summary>View flagged source</summary><p>Source: fictional seller record {concern.offerId}. This is a simulated assessment of the supplied terms, not proof of fraud.</p></details>
  </section>;
}
