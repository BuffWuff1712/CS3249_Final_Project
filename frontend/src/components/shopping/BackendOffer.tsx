"use client";
import { productTitle } from "@/lib/productTitle";
import { ProductImage } from "./ProductImage";
import type { ReactNode } from "react";
import type { Action, Fact, Merchant, MerchantRisk, Product } from "@/lib/beany";
import { MerchantDetails } from "@/components/MerchantDetails";
import { money } from "@/lib/shopBackend";
import { CheckCircleIcon, InfoIcon, ScalesIcon, ShoppingCartIcon, ArrowsLeftRightIcon } from "./ShoppingIcons";
import { ListBulletsIcon } from "@phosphor-icons/react/dist/csr/ListBullets";
import { BatteryHighIcon } from "@phosphor-icons/react/dist/csr/BatteryHigh";
import { PackageIcon } from "@phosphor-icons/react/dist/csr/Package";
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
    <div className="cui-assessment-badges"><SiteBadge site={site} /><RiskBadge risk={risk} merchant /><PolicyBadge decision={decision} /></div>
    <section className="cui-seller-concerns" aria-label="Seller and listing concerns"><h4>Seller / listing concerns</h4>
      {concerns.length > 0 ? <ul className="cui-concern-list">{concerns.map(item => <li key={item.rule_id + item.evidence}><strong>{concernTitle(item.rule_id)}</strong><p>{readableRule(item.evidence)}</p></li>)}</ul> : <p className="cui-source">{risk?.explanation || "No assessment supplied; risk remains unknown."}</p>}
    </section>
    {decision === "BLOCK" && restrictions.length > 0 && <ul className="cui-visible-concerns">{restrictions.map(text => <li key={text}>{readableRule(text)}</li>)}</ul>}
    <aside className="cui-assessment-info" aria-label="About these checks"><InfoIcon aria-hidden="true" /><div><strong>About these checks</strong>
      <p>{site ? `${site.domain} · ${site.label}` : "No registered website assessment supplied."}</p>
      <p>{risk ? <>{risk.basis === "ai" ? "AI evidence review" : risk.basis === "rules_fallback" ? "Rules fallback; AI review unavailable" : "Rules-based assessment"}. An estimate, not proof of fraud or a safety guarantee.</> : "Merchant assessment unavailable; risk remains unknown."}</p>
      <p>{decision === "BLOCK" ? "This offer cannot be selected." : "Your explicit selection is required before simulated checkout."}</p>
    </div></aside>
    {detailChecks.length > 0 && <details><summary>More assessment details</summary><section className="cui-shopping-checks"><h4>Shopping restrictions and checks</h4><ul>{detailChecks.map(rule => <li key={rule.rule_id}>{readableRule(rule.explanation)}</li>)}</ul></section></details>}
  </section>;
}

const policyLabels: Record<string, string> = {
  refund_policy: "Read return policy", shipping_policy: "Read shipping policy",
  privacy_policy: "Read privacy policy", terms_of_service: "Read terms of service",
};
function PolicyLinks({ product }: { product: Product }) {
  return <div className="cui-policy-links">{Object.entries(product.policy_links || {}).filter(([key, url]) => {
    try { const parsed = new URL(url); return key in policyLabels && parsed.protocol === "https:" && !parsed.username && !parsed.password; } catch { return false; }
  }).map(([key, url]) => <a className="cui-policy-link" key={key} href={url} target="_blank" rel="noopener noreferrer">{policyLabels[key]} ↗</a>)}</div>;
}
function ListingSummary({ product }: { product: Product }) {
  const features = product.inferred_attributes || [];
  const points = (product.selling_points || []).filter(point => !features.includes(point));
  if (!features.length && !points.length) return null;
  return <section className="cui-listing-summary" aria-label="Catalogue feature summary">
    <h4>Catalogue highlights</h4>
    {points.map(point => <p key={point}>{point}</p>)}
    {!!features.length && <ul>{features.map(feature => <li key={feature}>{feature}</li>)}</ul>}
    <p className="cui-source">Catalogue summaries, not independently verified. These do not confirm your required features.</p>
  </section>;
}

export function BackendProductEvidence({ product, merchant, replay = false }: { product: Product; merchant: Merchant | null; replay?: boolean }) {
  return <section className="cui-source-record" aria-label={`Product evidence for ${productTitle(product)}`} tabIndex={-1}>
    <h3>{productTitle(product)}</h3><p className="cui-source">{product.brand} · {product.category} · {money(product)} · {product.merchant}</p>
    <p className="cui-listing-description">{product.description || "Description not supplied."}</p>
    <ListingSummary product={product} /><PolicyLinks product={product} />
    <dl className="cui-spec-grid">{Object.entries(product.specifications).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || "Unknown; not supplied"}</dd></div>)}</dl>
    <p>{product.rating === null || product.rating === undefined ? "Unknown product rating" : `${product.rating}/5`} · {product.rating_count ?? 0} aggregate product ratings</p>
    <p className="cui-source">{(product.reviews?.length || 0) + (product.review_excerpts?.length || 0)} supplied product review excerpts. Aggregate counts do not mean all reviews were read; {["browser_use", "shopify_catalog"].includes(product.source || "") ? "captured excerpts are unverified." : "these catalogue reviews are fictional."}</p>
    {product.reviews?.map((review, index) => <blockquote key={index}><strong>{review.title}</strong> · {review.rating}/5<p>{review.text}</p></blockquote>)}
    {product.review_excerpts?.map((text, index) => <blockquote key={`captured-${index}`}><p>{text}</p></blockquote>)}
    {!product.reviews?.length && !product.review_excerpts?.length && <p className="cui-source">Product review excerpts: Unknown; not supplied.</p>}
    <h4>Seller terms</h4><dl className="cui-spec-grid"><div><dt>Returns</dt><dd>{product.web_evidence?.return_policy || merchant?.return_policy || "Unknown; not supplied"}</dd></div><div><dt>Payment</dt><dd>{merchant?.payment_methods.join(", ") || "Unknown; not supplied"}</dd></div><div><dt>Website</dt><dd>{merchant?.website || "Unknown; not supplied"}</dd></div><div><dt>Contact</dt><dd>{merchant?.contact || "Unknown; not supplied"}</dd></div></dl>
    {merchant?.merchant_reviews?.map((review, index) => <blockquote key={index}><strong>Seller review: {review.title}</strong> · {review.rating}/5<p>{review.text}</p></blockquote>)}
    <MerchantDetails replay={replay} action={{ product, merchant_details: merchant, risk: null, id: "evidence", fingerprint: "", status: "snapshot", decision: "REVIEW", rules: [], payment_method: "", shares_personal_data: false }} />
  </section>;
}

export function BackendCurrentOffer({ sellerPreferences, action, brief = {}, selected, disabled, selectionInvalid = false, select, seller, addCart, alternative, replay = false, evidenceId }: { sellerPreferences?: ReactNode; action: Action; brief?: Record<string, Fact>; selected: boolean; disabled: boolean; selectionInvalid?: boolean; select: () => void; addCart: () => void; alternative: () => void; seller: () => void; replay?: boolean; evidenceId?: number }) {
  const lowReview = action.product.reviews?.find(review => review.rating <= 2);
  return <article className="cui-recommendation" aria-label="Current recommendation">
    {/* ANCHOR: compact product head + primary actions, pinned at top */}
    <header className="cui-offer-anchor">
      <div className="cui-offer-head">
        <div className="cui-offer-thumb"><ProductImage key={action.product.id + (action.product.image_url || "")} product={action.product} /></div>
        <div className="cui-offer-head-text">
          <p className="cui-offer-eyebrow">Your current match</p>
          <h3>{productTitle(action.product)}</h3>
          <p className="cui-offer-sub"><strong>{money(action.product)}</strong><span>{action.product.merchant}</span></p>
        </div>
      </div>
      <section className="cui-offer-actions" aria-label="Offer actions">
        <div className="cui-offer-primary">
          {selected ? <p className="cui-selected-label"><CheckCircleIcon weight="fill" aria-hidden="true" />Offer selected; no receipt created yet</p> : <button className="primary cui-select" disabled={disabled || selectionInvalid || action.decision === "BLOCK"} onClick={select}><CheckCircleIcon aria-hidden="true" />Select this offer</button>}
          <button disabled={disabled || selectionInvalid || action.decision === "BLOCK"} onClick={addCart}><ShoppingCartIcon aria-hidden="true" />Add to cart</button>
        </div>
        <div className="cui-offer-explore"><div className="cui-actions"><button disabled={disabled} onClick={alternative}><PackageIcon aria-hidden="true" />Find another product</button><button disabled={disabled} onClick={seller}><ArrowsLeftRightIcon aria-hidden="true" />Find another seller</button></div></div>
        {sellerPreferences}
      </section>
    </header>

    {/* RISK: always open — safety signals outrank brand signals */}
    <BackendRisk merchant={action.merchant_details} risk={action.risk} decision={action.decision} rules={action.rules} />

    {/* FIT CHIPS: single wrapping row */}
    <MatchedPriorities product={action.product} brief={brief} fit={action.feature_fit} />

    {/* Evidence sections, collapsed by default */}
    <details className="cui-offer-section"><summary>Why this match</summary>
      {productTitle(action.product) !== action.product.name && <p className="cui-source">Full listing title: {action.product.name}</p>}
      <ListingSummary product={action.product} />
      <ul className="cui-product-points">
        {(action.product.attributes.length > 0 || !action.product.inferred_attributes?.length) && <li className="cui-icon-fact"><ListBulletsIcon aria-hidden="true" /><span><strong>Listed features:</strong> {action.product.attributes.join(", ") || "Not supplied"}</span></li>}
        {Object.entries(action.product.specifications).filter(([key]) => /battery|weight|capacity|cushion|drop|laptop/i.test(key)).slice(0, 2).map(([key, value]) => <li key={key} className={/battery|weight/i.test(key) ? "cui-icon-fact" : undefined}>{/battery/i.test(key) ? <BatteryHighIcon aria-hidden="true" /> : /weight/i.test(key) ? <ScalesIcon aria-hidden="true" /> : null}<span><strong>{key}:</strong> {/battery/i.test(key) && /^(up to )?\d+(?:\.\d+)?\s*(?:hours?|h)\b/i.test(value) ? <><strong className="cui-key-spec">{value.match(/^(up to )?\d+(?:\.\d+)?\s*(?:hours?|h)\b/i)![0]}</strong>{value.replace(/^(up to )?\d+(?:\.\d+)?\s*(?:hours?|h)\b/i, "")}</> : value}</span></li>)}
        {!!action.product.sizes.length && <li><strong>Available sizes:</strong> {action.product.sizes.join(", ")}</li>}
      </ul>
      {action.product.availability_note && <aside className="cui-listing-summary" aria-label="Availability and delivery notice"><strong>Availability and delivery</strong><p>{action.product.availability_note}</p><p className="cui-source">Check delivery for your location; stock availability does not confirm shipping eligibility.</p></aside>}
    </details>

    <details className="cui-offer-section"><summary>Reviews &amp; terms</summary>
      <dl className="cui-match-facts">
        <div><dt>Returns</dt><dd>{action.product.web_evidence?.return_policy || action.merchant_details?.return_policy || "Not supplied"}</dd></div>
        <div><dt>Product reviews</dt><dd>{action.product.rating == null && action.product.product_rating_text ? <span>{action.product.product_rating_text}</span> : <RatingStars rating={action.product.rating} count={action.product.rating_count} />}<small>{action.product.rating_scope === "variant" ? "Rating for this variant. " : action.product.rating_scope === "product" ? "Product-wide rating; not specific to this variant. " : ""}{(action.product.reviews?.length || 0) + (action.product.review_excerpts?.length || 0)} supplied excerpts</small></dd></div>
        <div><dt>Seller reviews</dt><dd>{action.product.seller_rating_text ? <span>{action.product.seller_rating_text}</span> : <RatingStars rating={action.merchant_details?.review_rating} count={action.merchant_details?.review_count} />}</dd></div>
      </dl>
      {!!action.product.review_excerpts?.length && <details><summary>Read captured review excerpts</summary>
        {action.product.review_excerpts.map((text, index) => <blockquote key={index}><p>{text}</p></blockquote>)}
        <p className="cui-source">Captured from the listing, not independently verified. These excerpts are not the full set of reviews.</p>
      </details>}
      <PolicyLinks product={action.product} />
      {lowReview && <p className="cui-review-concern"><strong>Review concern:</strong> One supplied product excerpt says “{lowReview.text}” This does not establish a failure rate.</p>}
    </details>

    {["shopify_catalog", "browser_use"].includes(action.product.source || "") && <details className="cui-offer-section"><summary>Full product details</summary>
      <p className="cui-listing-description">{action.product.description || "Description not supplied."}</p>
      <dl className="cui-spec-grid">{Object.entries(action.product.specifications).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
      <p>Availability: {action.product.stock == null ? "Not supplied" : action.product.stock ? "Listed as in stock" : "Listed as unavailable"}</p>
      {action.product.list_price != null && <p>Listed reference price: {money({ ...action.product, price: action.product.list_price })}. This is the listing's reference price, not a verified saving.</p>}
      {action.product.source_url?.startsWith("https://") && <a className="cui-policy-link" href={action.product.source_url} target="_blank" rel="noopener noreferrer">View product listing ↗</a>}
    </details>}

    <details className="cui-offer-section" key={evidenceId || 0} open={!!evidenceId}><summary>Comparison &amp; sources</summary><BackendProductEvidence product={action.product} merchant={action.merchant_details} replay={replay} /></details>
  </article>;
}
