"use client";
import { Fragment, useState } from "react";
import type { Action, Product } from "@/lib/beany";
import { money, type OfferPreview } from "@/lib/shopBackend";
import { PriceValue, RatingStars, RiskBadge, SiteBadge, PolicyBadge, blockingReasons } from "./ShoppingReadability";
import { BackendProductEvidence, BackendRisk, readableRule } from "./BackendOffer";

export function listedSpec(product: Product, name: string) {
  return Object.entries(product.specifications).find(([key]) => key.toLowerCase().includes(name.toLowerCase()))?.[1] || "Not supplied";
}
export function OfferDetails({ offer, replay = false }: { offer: OfferPreview; replay?: boolean }) {
  const [open, setOpen] = useState(false);
  return <details className="cui-row-details" onToggle={event => setOpen(event.currentTarget.open)}><summary>Details</summary>{open && <><BackendRisk merchant={offer.merchant} risk={offer.risk} decision={offer.decision} rules={offer.rules} /><BackendProductEvidence product={offer.product} merchant={offer.merchant} replay={replay} /></>}</details>;
}
export function ProductComparison({ current, alternatives, disabled, choose, replay = false }: { current: Action; alternatives: OfferPreview[]; disabled: boolean; choose: (id: string) => void; replay?: boolean }) {
  const [alternativeId, setAlternativeId] = useState("");
  const alternate = alternatives.find(offer => offer.product.id === alternativeId) || alternatives[0];
  if (!alternate) return null;
  const products = [current.product, alternate.product];
  const rows: [string, (product: Product) => string][] = [
    ["Price", money], ["Type", product => listedSpec(product, "type")],
    ["Listed features", product => product.attributes.join(", ") || "Not supplied"],
    ["Noise control", product => listedSpec(product, "noise") !== "Not supplied" ? listedSpec(product, "noise") : product.attributes.filter(attribute => /noise.?cancel/i.test(attribute)).join(", ") || "Not supplied"],
    ["Battery", product => listedSpec(product, "battery")], ["Weight", product => listedSpec(product, "weight")],
    ["Product rating", product => product.rating == null ? "Not supplied" : `${product.rating}/5`],
  ];
  return <section className="cui-alternative" aria-label="Other models"><h2>Compare products</h2>
    <label className="cui-comparison-picker">Compare your match with<select disabled={disabled} value={alternate.product.id} onChange={event => setAlternativeId(event.target.value)}>{alternatives.map(offer => <option key={offer.product.id} value={offer.product.id}>{offer.product.name}</option>)}</select></label>
    <div className="cui-table-wrap"><table className="cui-compare-table"><caption className="sr-only">Listed product features; missing information is not assumed</caption><thead><tr><th scope="col">Feature</th>{products.map((product, index) => <th scope="col" key={product.id}>{product.name}<small>{index === 0 ? "Current match" : product.merchant}</small></th>)}</tr></thead><tbody>{rows.filter(([label, get]) => !["Battery", "Weight", "Type", "Noise control"].includes(label) || products.some(product => get(product) !== "Not supplied")).map(([label, get]) => <tr key={label}><th scope="row">{label}</th>{products.map(product => <td key={product.id} data-label={product.name} className={label === "Price" ? "cui-price-cell" : undefined}>{label === "Price" ? <PriceValue product={product} /> : label === "Product rating" ? <RatingStars rating={product.rating} count={product.rating_count} /> : get(product)}</td>)}</tr>)}</tbody></table></div>
    <p className="cui-source">Listed claims, not independently tested. Missing features are not assumed absent.</p>
    {alternate.decision === "BLOCK" && <p className="cui-blocked-status">This offer is blocked. Open Details to see why.</p>}<OfferDetails offer={alternate} replay={replay} />
    <button disabled={disabled || alternate.decision === "BLOCK"} onClick={() => choose(alternate.product.id)}>Compare {alternate.product.name}</button>
  </section>;
}
// Unassessed offers sort after every scored one; equal scores fall back to price.
const riskScore = (offer: OfferPreview) => offer.risk ? offer.risk.score : Number.MAX_SAFE_INTEGER;
export function SellerComparison({ offers, disabled, choose, replay = false, all = false, currentId }: { offers: OfferPreview[]; disabled: boolean; choose: (id: string) => void; replay?: boolean; all?: boolean; currentId?: string }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sort, setSort] = useState<"price" | "risk">("price");
  const rows = all || sort === "price" ? offers : [...offers].sort((a, b) => riskScore(a) - riskScore(b) || a.product.price - b.product.price);
  return <div className="cui-table-wrap cui-seller-table">{!all && <label className="cui-seller-sort">Sort by<select aria-label="Sort sellers by" value={sort} onChange={event => setSort(event.target.value as "price" | "risk")}><option value="price">Price: low to high</option><option value="risk">Risk: lowest first</option></select></label>}<table className="cui-offer-table"><caption>{all ? "All matching offers" : "Compare sellers of this model"}</caption><thead><tr><th scope="col">{all ? "Product / seller" : "Seller"}</th><th scope="col">Price</th><th scope="col">Returns & checks</th><th scope="col">Action</th></tr></thead><tbody>{rows.map(offer => <Fragment key={offer.product.id}><tr aria-label={all ? `Catalogue offer ${offer.product.id}` : `Seller offer ${offer.product.merchant}`} aria-current={offer.product.id === currentId ? "true" : undefined}>
    <th scope="row">{all && <strong>{offer.product.name}</strong>}<span>{offer.product.merchant}</span>{offer.product.id === currentId && <small className="cui-current-offer">Current offer</small>}<button className="cui-table-details" aria-expanded={expanded === offer.product.id} aria-label={`Details for ${offer.product.merchant}`} onClick={() => setExpanded(expanded === offer.product.id ? null : offer.product.id)}>Details</button></th>
    <td data-label="Price" className="cui-price-cell"><PriceValue product={offer.product} /></td>
    <td data-label="Returns & checks"><span>{offer.merchant?.return_policy || "Returns not supplied"}</span><div className="cui-table-badges"><SiteBadge compact site={offer.merchant?.site} /><RiskBadge compact risk={offer.risk} /><PolicyBadge compact decision={offer.decision} /></div>{offer.decision === "BLOCK" && <ul className="cui-table-reasons">{blockingReasons(offer.rules, offer.risk).map(reason => <li key={reason}>{readableRule(reason)}</li>)}</ul>}</td>
    <td><button aria-label={all ? "Compare this offer" : `Compare offer from ${offer.product.merchant}`} disabled={disabled || offer.decision === "BLOCK" || offer.product.id === currentId} onClick={() => choose(offer.product.id)}>{offer.product.id === currentId ? "Current offer" : offer.decision === "BLOCK" ? "Blocked" : "Compare"}</button></td>
  </tr>{expanded === offer.product.id && <tr className="cui-expanded-offer"><td colSpan={4}><BackendRisk merchant={offer.merchant} risk={offer.risk} decision={offer.decision} rules={offer.rules} /><BackendProductEvidence product={offer.product} merchant={offer.merchant} replay={replay} /></td></tr>}</Fragment>)}</tbody></table><p className="cui-source">Risk estimates are not safety guarantees. Open Details for evidence and the assessment method.</p></div>;
}
