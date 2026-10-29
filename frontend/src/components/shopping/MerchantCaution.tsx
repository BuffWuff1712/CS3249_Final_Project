import type { MerchantConcern, ShoppingOffer } from "@/lib/decision";
import { ProhibitIcon, InfoIcon } from "./ShoppingIcons";

export function MerchantCaution({ concern, label = "Merchant caution", flaggedOffer, alternative, useAlternative }: {
  concern: MerchantConcern; label?: string; flaggedOffer?: ShoppingOffer;
  alternative?: ShoppingOffer; useAlternative?: () => void;
}) {
  return <section className={`cui-flag ${concern.blocked ? "cui-flag--danger" : "cui-flag--review"}`} aria-label={label} data-severity={concern.blocked ? "blocked" : "review"}>
    {concern.blocked ? <ProhibitIcon aria-hidden="true" className="cui-flag-icon" /> : <InfoIcon aria-hidden="true" className="cui-flag-icon" />}
    <div><p className="cui-flag-offer"><strong>{concern.merchant}</strong>{flaggedOffer && <> · SGD{flaggedOffer.price}</>}</p><p>{concern.blocked ? "Gift-card or outside-checkout payment. This offer is blocked." : concern.observation}</p>
      <details className="cui-flag-source"><summary>View flagged source</summary><h5>{concern.blocked ? "Possible scam risk: outside-checkout payment" : "Seller information is incomplete"}</h5><dl className="cui-flag-facts"><div><dt>Flagged evidence</dt><dd>{concern.observation}</dd></div><div><dt>Why it matters</dt><dd>{concern.consequence}</dd></div><div><dt>What to do</dt><dd>{concern.nextStep}</dd></div></dl><p>Source: fictional seller record {concern.offerId}. This assessment concerns the supplied terms; it is not proof of fraud.</p></details>
      {concern.blocked && alternative && useAlternative && <button className="cui-link cui-alternative-action" onClick={useAlternative}>Use {alternative.merchant} · SGD{alternative.price}</button>}
    </div>
  </section>;
}
