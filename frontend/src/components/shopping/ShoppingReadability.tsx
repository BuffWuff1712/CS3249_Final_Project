"use client";
import type { Action, Fact, MerchantRisk, Product, Site } from "@/lib/beany";
import { StarIcon } from "@phosphor-icons/react/dist/csr/Star";
import { WarningCircleIcon } from "@phosphor-icons/react/dist/csr/WarningCircle";
import { GlobeIcon } from "@phosphor-icons/react/dist/csr/Globe";
import { CheckCircleIcon, InfoIcon, ProhibitIcon } from "./ShoppingIcons";

export function PriceValue({ product }: { product: Product }) {
  const parts = new Intl.NumberFormat("en-SG", { style: "currency", currencyDisplay: "code", currency: product.currency }).formatToParts(product.price);
  return <span className="cui-money"><span>{parts.find(part => part.type === "currency")?.value}</span><span className="cui-money-amount">{parts.filter(part => part.type !== "currency").map(part => part.value).join("").trim()}</span></span>;
}

export function RatingStars({ rating, count }: { rating?: number | null; count?: number }) {
  if (rating == null || !Number.isFinite(rating) || rating < 0 || rating > 5) return <span>Rating not supplied</span>;
  return <span className="cui-rating"><span className="cui-rating-value"><span className="cui-stars" role="img" aria-label={`${rating} out of 5 stars`}>{[0, 1, 2, 3, 4].map(index => <span className="cui-star-slot" key={index} aria-hidden="true"><StarIcon weight="fill" /><span className="cui-star-fill" style={{ width: `${Math.max(0, Math.min(1, rating - index)) * 100}%` }}><StarIcon weight="fill" /></span></span>)}</span><strong aria-hidden="true">{rating}/5</strong></span><span className="cui-rating-count">{count == null ? "Rating count not supplied" : `${count.toLocaleString("en-SG")} aggregate ratings`}</span></span>;
}

function BadgeLabel({ full, short }: { full: string; short?: string }) {
  return short ? <><span className="sr-only">{full}</span><span aria-hidden="true">{short}</span></> : <span>{full}</span>;
}
export function RiskBadge({ risk, merchant = false, compact = false }: { risk: MerchantRisk | null; merchant?: boolean; compact?: boolean }) {
  const level = risk?.level.toLowerCase() || "Unknown";
  const full = `${merchant ? "Merchant" : "Seller"} risk: ${risk ? `${level} estimate` : "Unknown"}`;
  return <span className={`cui-badge cui-risk-badge cui-tone-${risk?.level.toLowerCase() || "unknown"}`}><WarningCircleIcon aria-hidden="true" /><BadgeLabel full={full} short={compact ? `Seller risk: ${level}` : undefined} /></span>;
}
export function SiteBadge({ site, compact = false }: { site?: Site | null; compact?: boolean }) {
  const tier = site ? site.tier[0].toUpperCase() + site.tier.slice(1) : "Unknown";
  return <span className={`cui-badge cui-site-badge cui-site-${site?.tier || "unknown"}`}><GlobeIcon aria-hidden="true" /><BadgeLabel full={`Website reputation: ${tier}`} short={compact ? `Website: ${tier}` : undefined} /></span>;
}
export function PolicyBadge({ decision, compact = false }: { decision: string; compact?: boolean }) {
  const Icon = decision === "BLOCK" ? ProhibitIcon : InfoIcon;
  const full = decision === "BLOCK" ? "Unavailable under your shopping rules" : decision === "REVIEW" ? "Needs your approval" : "Within checked policy limits";
  return <span className={`cui-badge cui-policy-badge ${decision === "BLOCK" ? "cui-tone-high" : decision === "REVIEW" ? "cui-tone-medium" : "cui-tone-unknown"}`}><Icon aria-hidden="true" /><BadgeLabel full={full} short={compact ? decision === "BLOCK" ? "Blocked" : decision === "REVIEW" ? "Approval needed" : "Within limits" : undefined} /></span>;
}

function normalized(text: string) {
  return text.toLowerCase().replace(/[-_]/g, " ").replace(/\banc\b|noise cancellation|noise canceling/g, "noise cancelling").replace(/\s+/g, " ").trim();
}
export function MatchedPriorities({ product, brief }: { product: Product; brief: Record<string, Fact> }) {
  const requested = brief.features?.source === "confirmed" ? brief.features.value.split(",").map(value => value.trim()).filter(Boolean) : [];
  const attributes = new Set(product.attributes.map(normalized));
  const matches = [...new Set(requested.filter(value => attributes.has(normalized(value))))];
  const unknown = requested.filter(value => !attributes.has(normalized(value)));
  if (!requested.length) return null;
  return <section className="cui-matched-priorities" aria-label="Priority matches"><h4>Matches your saved priorities</h4>{matches.length > 0 && <ul>{matches.map(match => <li key={match}><CheckCircleIcon weight="fill" aria-hidden="true" />{match}</li>)}</ul>}{unknown.length > 0 && <p className="cui-source">Not established from listed features: {unknown.join(", ")}. Missing evidence does not mean a feature is absent.</p>}</section>;
}

export function concernTitle(id: string) {
  const titles: Record<string, string> = { inconsistent: "Conflicting information", injection: "Instructions aimed at the assistant", low_price: "Unusually low price", missing_business: "Incomplete business details", excessive_data: "Unrelated personal data requested", unusual_payment: "Unsupported payment channel", external_payment: "Payment outside checkout", misleading_returns: "Conflicting return terms", lookalike: "Lookalike branding", pressure: "Pressure to act quickly", site_reputation_mid: "Website reputation concern", site_reputation_poor: "Poor website reputation" };
  return titles[id] || "Recorded concern";
}
export function uniqueConcerns(risk: MerchantRisk | null) {
  return (risk?.evidence || []).filter((item, index, items) => items.findIndex(other => other.evidence.trim() === item.evidence.trim()) === index);
}
export function blockingReasons(rules: Action["rules"], risk: MerchantRisk | null) {
  return rules.filter(rule => rule.decision === "BLOCK").flatMap(rule => rule.rule_id === "merchant_risk" && risk?.evidence.length ? uniqueConcerns(risk).map(item => item.evidence) : [rule.explanation]).filter((text, index, items) => items.indexOf(text) === index);
}
