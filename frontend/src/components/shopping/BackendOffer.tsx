"use client";
import type { Action, Merchant, MerchantRisk, Product } from "@/lib/beany";
import { MerchantDetails } from "@/components/MerchantDetails";
import { money } from "@/lib/shopBackend";
import { CheckCircleIcon, InfoIcon, ProhibitIcon } from "./ShoppingIcons";

export function BackendRisk({ merchant, risk, decision, rules }: { merchant: Merchant | null; risk: MerchantRisk | null; decision: string; rules: Action["rules"] }) {
  const site = merchant?.site;
  return <section aria-label="Merchant and website assessment" className="cui-backend-risk">
    {site ? <div className="cui-site"><strong>Website reputation: {site.tier === "good" ? "Good" : site.tier === "mid" ? "Mid" : "Poor"}</strong><span className={`site-meter ${site.tier}`} aria-hidden="true">{[1, 2, 3].map(i => <span key={i} className={i <= (site.tier === "good" ? 3 : site.tier === "mid" ? 2 : 1) ? "filled" : undefined} />)}</span><p>{site.domain} · {site.label}</p></div> : <p className="cui-source">Website reputation: Unknown; no registered site assessment supplied.</p>}
    {risk && <><p><strong>Merchant risk: {risk.level.toLowerCase()} predicted risk</strong> · {risk.basis === "ai" ? "AI evidence review" : risk.basis === "rules_fallback" ? "Rules fallback; AI review unavailable" : "Rules-based assessment"}</p><p className="cui-source">{risk.explanation}</p></>}
    <p className={decision === "BLOCK" ? "cui-policy-block" : "cui-source"}>{decision === "BLOCK" ? <ProhibitIcon aria-hidden="true" /> : <InfoIcon aria-hidden="true" />} {decision === "BLOCK" ? "Blocked by backend policy" : decision === "REVIEW" ? "Review and explicit approval required" : "Within checked policy limits; your explicit selection is still required"}</p>
    {decision === "BLOCK" && <ul>{rules.filter(rule => rule.decision === "BLOCK").map(rule => <li key={rule.rule_id}>{rule.explanation}</li>)}</ul>}
    <details><summary>View risk evidence</summary>{risk?.evidence.length ? <ul>{risk.evidence.map(item => <li key={item.rule_id}>{item.evidence}</li>)}</ul> : <p>No configured risk signals were reported. This does not guarantee safety.</p>}{rules.length > 0 && <ul>{rules.map(rule => <li key={rule.rule_id}>{rule.explanation}</li>)}</ul>}</details>
  </section>;
}

export function BackendProductEvidence({ product, merchant, replay = false }: { product: Product; merchant: Merchant | null; replay?: boolean }) {
  return <section className="cui-source-record" aria-label={`Product evidence for ${product.name}`} tabIndex={-1}>
    <h3>{product.name}</h3><p className="cui-source">{product.brand} · {product.category} · {money(product)} · {product.merchant}</p>
    <p>{product.description || "Description not supplied."}</p>
    <dl className="cui-spec-grid">{Object.entries(product.specifications).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || "Unknown; not supplied"}</dd></div>)}</dl>
    <p>{product.rating === null || product.rating === undefined ? "Unknown product rating" : `${product.rating}/5`} · {product.rating_count ?? 0} aggregate product ratings</p>
    <p className="cui-source">{product.reviews?.length || 0} supplied product review excerpts. Aggregate counts do not mean all reviews were read; {product.source === "browser_use" ? "captured excerpts are unverified." : "these catalogue reviews are fictional."}</p>
    {product.reviews?.map((review, index) => <blockquote key={index}><strong>{review.title}</strong> · {review.rating}/5<p>{review.text}</p></blockquote>)}
    {!product.reviews?.length && <p className="cui-source">Product review excerpts: Unknown; not supplied.</p>}
    <h4>Seller terms</h4><dl className="cui-spec-grid"><div><dt>Returns</dt><dd>{merchant?.return_policy || "Unknown; not supplied"}</dd></div><div><dt>Payment</dt><dd>{merchant?.payment_methods.join(", ") || "Unknown; not supplied"}</dd></div><div><dt>Website</dt><dd>{merchant?.website || "Unknown; not supplied"}</dd></div><div><dt>Contact</dt><dd>{merchant?.contact || "Unknown; not supplied"}</dd></div></dl>
    {merchant?.merchant_reviews?.map((review, index) => <blockquote key={index}><strong>Seller review: {review.title}</strong> · {review.rating}/5<p>{review.text}</p></blockquote>)}
    <MerchantDetails replay={replay} action={{ product, merchant_details: merchant, risk: null, id: "evidence", fingerprint: "", status: "snapshot", decision: "REVIEW", rules: [], payment_method: "", shares_personal_data: false }} />
    <p className="cui-source">Offer: {product.id}. {product.source === "browser_use" ? "Listing evidence is unverified; prices and stock may change." : "No website was visited and authenticity has not been verified."}</p>
  </section>;
}

export function BackendCurrentOffer({ action, selected, disabled, selectionInvalid = false, select, seller, edit, addCart, reject, alternative, replay = false, evidenceId }: { action: Action; selected: boolean; disabled: boolean; selectionInvalid?: boolean; select: () => void; addCart: () => void; reject: () => void; alternative: () => void; seller: () => void; edit: () => void; replay?: boolean; evidenceId?: number }) {
  return <article className="cui-recommendation" aria-label="Current recommendation">
    <h2 className="cui-panel-title">Your current match</h2><div className="cui-product-heading"><h3>{action.product.name}</h3><div><strong>{money(action.product)}</strong><span>{action.product.merchant}</span></div></div>
    <p>{action.product.description}</p><p className="cui-source">{action.product.attributes.join(" · ")}</p><p className="cui-source">{action.product.sizes.length ? `Available sizes: ${action.product.sizes.join(", ")}. Select the required size in your needs.` : "No selectable size supplied."} Suitability and comfort are not personally verified.</p>
    <p className="cui-source">Payment: {action.payment_method} · Data sharing: {action.shares_personal_data ? "requested" : "none"}</p>
    <BackendRisk merchant={action.merchant_details} risk={action.risk} decision={action.decision} rules={action.rules} />
    {selected ? <p className="cui-selected-label"><CheckCircleIcon weight="fill" aria-hidden="true" />Offer selected; no receipt created yet</p> : <button className="primary cui-select" disabled={disabled || selectionInvalid || action.decision === "BLOCK"} onClick={select}>Select this offer</button>}
    <div className="cui-secondary-actions"><button disabled={disabled || selectionInvalid || action.decision === "BLOCK"} onClick={addCart}>Add to cart</button><button disabled={disabled} onClick={reject}>Reject offer</button><button disabled={disabled} onClick={alternative}>Find another merchant</button><button disabled={disabled} onClick={edit}>Change needs</button><button disabled={disabled} onClick={seller}>Find another seller</button></div>
    <details key={evidenceId || 0} open={!!evidenceId}><summary>View comparison and sources</summary><BackendProductEvidence product={action.product} merchant={action.merchant_details} replay={replay} /></details>
  </article>;
}
