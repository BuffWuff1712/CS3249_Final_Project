"use client";
import type { Action, Fact, Merchant, MerchantRisk, Product } from "@/lib/beany";
import { MerchantDetails } from "@/components/MerchantDetails";
import { money } from "@/lib/shopBackend";
import { CheckCircleIcon } from "./ShoppingIcons";
import { BatteryHighIcon } from "@phosphor-icons/react/dist/csr/BatteryHigh";
import { RatingStars, RiskBadge, SiteBadge, PolicyBadge, MatchedPriorities, uniqueConcerns, concernTitle, blockingReasons } from "./ShoppingReadability";

export function readableRule(explanation: string) {
  const labels: Record<string, string> = { government_id: "government ID", date_of_birth: "date of birth", social_media_account: "social media account" };
  return explanation.replace(/government_id|date_of_birth|social_media_account/g, key => labels[key]);
}

export function BackendRisk({ merchant, risk, decision, rules }: { merchant: Merchant | null; risk: MerchantRisk | null; decision: string; rules: Action["rules"] }) {
  const site = merchant?.site;
  const concerns = uniqueConcerns(risk);
  const checks = rules.filter(rule => rule.rule_id !== "approval" && !(rule.rule_id === "merchant_risk" && risk));
  const restrictions = blockingReasons(checks, risk);
  const detailChecks = decision === "BLOCK" ? checks.filter(rule => rule.decision !== "BLOCK") : checks;
  return <section aria-label="Merchant and website assessment" className="cui-backend-risk">
    <div className="cui-site"><SiteBadge site={site} /><p>{site ? `${site.domain} · ${site.label}` : "No registered website assessment supplied."}</p></div>
    <div className="cui-risk-summary"><RiskBadge risk={risk} merchant /><small>{risk?.basis === "ai" ? "AI evidence review" : risk?.basis === "rules_fallback" ? "Rules fallback; AI review unavailable" : risk ? "Rules-based assessment" : "Assessment unavailable"}. An estimate, not proof of fraud or a safety guarantee.</small></div>
    <p className="cui-policy-status"><PolicyBadge decision={decision} /><small>{decision === "BLOCK" ? "This offer cannot be selected." : "Your explicit selection is required before simulated checkout."}</small></p>
    {decision === "BLOCK" && restrictions.length > 0 && <ul className="cui-visible-concerns">{restrictions.map(text => <li key={text}>{readableRule(text)}</li>)}</ul>}
    {risk && ["HIGH", "CRITICAL"].includes(risk.level) && concerns.length > 0 && <p className="cui-visible-concerns"><strong>Key concern: {concernTitle(concerns[0].rule_id)}</strong></p>}
    <details><summary>View risk evidence</summary>
      {concerns.length > 0 ? <ul className="cui-concern-list">{concerns.map(item => <li key={item.rule_id + item.evidence}><strong>{concernTitle(item.rule_id)}</strong><p>{readableRule(item.evidence)}</p></li>)}</ul> : <p>{risk?.explanation || "No assessment supplied; risk remains unknown."}</p>}
      {detailChecks.length > 0 && <section className="cui-shopping-checks"><h4>Shopping restrictions and checks</h4><ul>{detailChecks.map(rule => <li key={rule.rule_id}>{readableRule(rule.explanation)}</li>)}</ul></section>}
    </details>
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

export function BackendCurrentOffer({ action, brief = {}, selected, disabled, selectionInvalid = false, select, seller, edit, addCart, reject, alternative, replay = false, evidenceId }: { action: Action; brief?: Record<string, Fact>; selected: boolean; disabled: boolean; selectionInvalid?: boolean; select: () => void; addCart: () => void; reject: () => void; alternative: () => void; seller: () => void; edit: () => void; replay?: boolean; evidenceId?: number }) {
  return <article className="cui-recommendation" aria-label="Current recommendation">
    <h2 className="cui-panel-title">Your current match</h2><div className="cui-product-heading"><h3>{action.product.name}</h3><div><strong>{money(action.product)}</strong><span>{action.product.merchant}</span></div></div>
    <MatchedPriorities product={action.product} brief={brief} />
    <ul className="cui-product-points">
      <li><strong>Listed features:</strong> {action.product.attributes.join(", ") || "Not supplied"}</li>
      {Object.entries(action.product.specifications).filter(([key]) => /battery|weight|capacity|cushion|drop|laptop/i.test(key)).slice(0, 2).map(([key, value]) => <li key={key} className={/battery/i.test(key) ? "cui-battery-fact" : undefined}>{/battery/i.test(key) && <BatteryHighIcon aria-hidden="true" />}<span><strong>{key}:</strong> {/battery/i.test(key) && /^(up to )?\d+(?:\.\d+)?\s*(?:hours?|h)\b/i.test(value) ? <><strong className="cui-key-spec">{value.match(/^(up to )?\d+(?:\.\d+)?\s*(?:hours?|h)\b/i)![0]}</strong>{value.replace(/^(up to )?\d+(?:\.\d+)?\s*(?:hours?|h)\b/i, "")}</> : value}</span></li>)}
      {!!action.product.sizes.length && <li><strong>Available sizes:</strong> {action.product.sizes.join(", ")}</li>}
    </ul>
    <dl className="cui-match-facts">
      <div><dt>Returns</dt><dd>{action.merchant_details?.return_policy || "Not supplied"}</dd></div>
      <div><dt>Product reviews</dt><dd><RatingStars rating={action.product.rating} count={action.product.rating_count} /><small>{action.product.reviews?.length || 0} supplied excerpts</small></dd></div>
      <div><dt>Seller reviews</dt><dd><RatingStars rating={action.merchant_details?.review_rating} count={action.merchant_details?.review_count} /></dd></div>
    </dl>
    {action.product.reviews?.find(review => review.rating <= 2) && <p className="cui-review-concern"><strong>Review concern:</strong> One supplied product excerpt says “{action.product.reviews.find(review => review.rating <= 2)!.text}” This does not establish a failure rate.</p>}
    <p className="cui-source">Payment: {action.payment_method} · Data sharing: {action.shares_personal_data ? "requested" : "none"}</p>
    <BackendRisk merchant={action.merchant_details} risk={action.risk} decision={action.decision} rules={action.rules} />
    {selected ? <p className="cui-selected-label"><CheckCircleIcon weight="fill" aria-hidden="true" />Offer selected; no receipt created yet</p> : <button className="primary cui-select" disabled={disabled || selectionInvalid || action.decision === "BLOCK"} onClick={select}>Select this offer</button>}
    <div className="cui-secondary-actions"><button disabled={disabled || selectionInvalid || action.decision === "BLOCK"} onClick={addCart}>Add to cart</button><button disabled={disabled} onClick={reject}>Reject offer</button><button disabled={disabled} onClick={alternative}>Find another merchant</button><button disabled={disabled} onClick={edit}>Change needs</button><button disabled={disabled} onClick={seller}>Find another seller</button></div>
    <details key={evidenceId || 0} open={!!evidenceId}><summary>View comparison and sources</summary><BackendProductEvidence product={action.product} merchant={action.merchant_details} replay={replay} /></details>
  </article>;
}
