"use client";
import type { Action, Fact, FeatureFit, MerchantRisk, Product, Site } from "@/lib/beany";
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
  const level = risk ? risk.level[0] + risk.level.slice(1).toLowerCase() : "Unknown";
  const full = `Estimated ${merchant ? "merchant" : "seller"} risk: ${level}`;
  const tone = !risk || risk.level === "LOW" ? "unknown" : risk.level.toLowerCase();
  return <span className={`cui-badge cui-risk-badge cui-tone-${tone}`}><WarningCircleIcon aria-hidden="true" /><BadgeLabel full={full} short={compact ? `Estimated risk: ${level}` : undefined} /></span>;
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
export function MatchedPriorities({ product, brief, fit }: { product: Product; brief: Record<string, Fact>; fit?: FeatureFit[] }) {
  const requested = brief.features?.source === "confirmed" ? brief.features.value.split(",").map(value => value.trim()).filter(Boolean) : [];
  const attributes = new Set(product.attributes.map(normalized));
  // Prefer the backend's per-feature verdicts (tolerant matching and listing checks) over a literal attribute match.
  // Backend verdicts per need (tolerant rules and listing checks); kind-less entries are features.
  const verdict = (kind: NonNullable<FeatureFit["kind"]>) => fit?.find(item => (item.kind || "feature") === kind);
  const backendFeatures = (fit || []).filter(item => (item.kind || "feature") === "feature");
  const features: FeatureFit[] = backendFeatures.length ? backendFeatures : requested.map(value => ({ feature: value, status: attributes.has(normalized(value)) ? "met" : "unknown", quote: "" }));
  const unknown = features.filter(item => item.status === "unknown" || item.status === "unstated").map(item => item.feature);
  const budget = brief.budget;
  const amount = Number(budget?.value);
  // Match the needs strip's SGD default, while making the assumption explicit.
  const currency = brief.currency?.value?.trim().toUpperCase() || "SGD";
  const currencyAssumed = brief.currency?.source !== "confirmed";
  const validBudget = budget?.source === "confirmed" && Number.isFinite(amount) && amount > 0;
  const sameCurrency = currency === product.currency.toUpperCase();
  const budgetLabel = `${currency}${new Intl.NumberFormat("en-SG", { maximumFractionDigits: 2 }).format(amount)}`;
  const budgetKind = budget?.hard ? "budget" : "target budget";
  const budgetMatch = validBudget && sameCurrency && product.price <= amount
    ? `Within your ${budgetLabel} ${budgetKind}${currencyAssumed ? " (currency assumed)" : ""}` : "";
  const budgetNote = validBudget && !sameCurrency
    ? `Budget match unconfirmed: offer is priced in ${product.currency}; your ${budgetKind} is ${budgetLabel}. No currency conversion is performed.`
    : validBudget && product.price > amount ? `Above your ${budgetLabel} ${budgetKind}${currencyAssumed ? " (currency assumed)" : ""}.` : "";
  type Match = { label: string; state: "match" | "unknown" | "mismatch"; required: boolean; evidence?: string };
  const chips: Match[] = [];
  const add = (label: string, state: Match["state"], required: boolean, evidence = "") => chips.push({ label, state, required, evidence });
  if (budgetMatch) add(budgetMatch, "match", budget.hard);
  else if (budgetNote) add(sameCurrency ? "Above your budget" : "Budget match unconfirmed", sameCurrency ? "mismatch" : "unknown", budget.hard);
  const size = brief.size;
  if (size?.source === "confirmed" && size.value.trim()) {
    const checked = verdict("size");
    const supplied = product.sizes.length > 0;
    const state = checked ? (checked.status === "met" ? "match" : checked.status === "absent" ? "mismatch" : "unknown")
      : product.sizes.includes(size.value.trim()) ? "match" : supplied ? "mismatch" : "unknown";
    add(`Size ${size.value}: ${state === "match" ? "available" : state === "mismatch" ? "unavailable" : supplied ? "not confirmed" : "availability unknown"}`, state, size.hard, checked?.quote);
  }
  for (const [field, fact] of Object.entries(brief)) {
    if (fact.source !== "confirmed" || !fact.value.trim() || ["budget", "size", "features"].includes(field)) continue;
    if (!fact.hard && field !== "usage" && field !== "preferred_brands") continue;
    const values = fact.value.split(",").map(normalized).filter(Boolean);
    if (field === "category") {
      // A live listing's category is the type read from its page, so the backend's family check decides.
      const live = product.source === "browser_use" || product.source === "shopify_catalog";
      const state = !live ? (normalized(fact.value) === normalized(product.category) ? "match" : "mismatch") : product.relevance === "match" ? "match" : product.relevance === "mismatch" ? "mismatch" : "unknown";
      add(state === "unknown" ? `Category: ${fact.value} — not confirmed` : `Category: ${fact.value}`, state, fact.hard);
    }
    else if (field === "currency") {
      if (!validBudget) add(`Currency: ${fact.value}`, normalized(fact.value) === normalized(product.currency) ? "match" : "mismatch", fact.hard);
    } else if (field === "preferred_brands" || field === "excluded_brands") {
      const supplied = !!product.brand?.trim();
      const checked = field === "preferred_brands" ? verdict("brand") : undefined;
      const included = supplied && values.includes(normalized(product.brand));
      const match = field === "excluded_brands" ? !included : included;
      const state = checked ? (checked.status === "met" ? "match" : checked.status === "absent" ? "mismatch" : "unknown") : !supplied ? "unknown" : match ? "match" : "mismatch";
      add(field === "excluded_brands" ? `Excluded brands: ${!supplied ? "brand unknown" : included ? `${product.brand} is excluded` : "avoided"}` : `Brand: ${supplied ? product.brand : state === "match" ? fact.value : "unknown"}`, state, fact.hard);
    } else if (field === "merchants") {
      const supplied = !!product.merchant?.trim();
      const checked = verdict("merchant");
      const state = !supplied ? "unknown" : checked ? (checked.status === "met" ? "match" : "mismatch") : values.includes(normalized(product.merchant)) ? "match" : "mismatch";
      add(`Seller: ${supplied ? product.merchant : "unknown"}`, state, fact.hard);
    } else if (field === "usage") {
      const checked = verdict("usage");
      const state = checked ? (checked.status === "met" ? "match" : checked.status === "absent" ? "mismatch" : "unknown") : attributes.has(normalized(fact.value)) ? "match" : "unknown";
      add(`For ${fact.value}: ${state === "match" ? "listed" : state === "mismatch" ? "listing says otherwise" : "suitability unknown"}`, state, fact.hard, checked?.quote);
    } else add(`${field.replaceAll("_", " ")}: ${fact.value} — not verified`, "unknown", fact.hard);
  }
  const featureLabel = { met: "", absent: ": listing says otherwise", unstated: ": not mentioned in listing", unknown: ": not established" } as const;
  for (const item of features.filter((item, index) => features.findIndex(other => other.feature === item.feature) === index))
    add(`${item.feature}${featureLabel[item.status]}`, item.status === "met" ? "match" : item.status === "absent" ? "mismatch" : "unknown", brief.features.hard, item.quote);
  chips.sort((a, b) => Number(b.required) - Number(a.required));
  if (!chips.length && !budgetNote) return null;
  return <section className="cui-matched-priorities" aria-label="Priority matches"><h4>How this matches your needs</h4><ul>{chips.map((chip, index) => {
    const Icon = chip.state === "match" ? CheckCircleIcon : chip.state === "mismatch" ? ProhibitIcon : InfoIcon;
    return <li key={index} className={`cui-constraint-${chip.state}`} title={`${chip.required ? "Required constraint" : "Preference"}${chip.evidence ? ` — listing: “${chip.evidence}”` : ""}`} aria-label={`${chip.required ? "Required" : "Preferred"}: ${chip.label}`}><Icon weight={chip.state === "match" ? "fill" : "regular"} aria-hidden="true" />{chip.label}</li>;
  })}</ul>{budgetNote && <p className="cui-source">{budgetNote}</p>}{unknown.length > 0 && <p className="cui-source">Not established from listed features: {unknown.join(", ")}. Missing evidence does not mean a feature is absent.</p>}</section>;

}

export function concernTitle(id: string) {
  const titles: Record<string, string> = { inconsistent: "Conflicting information", injection: "Instructions aimed at the assistant", low_price: "Unusually low price", missing_business: "Incomplete business details", excessive_data: "Unrelated personal data requested", unusual_payment: "Unsupported payment channel", external_payment: "Payment outside checkout", misleading_returns: "Conflicting return terms", lookalike: "Lookalike branding", pressure: "Pressure to act quickly", site_reputation_mid: "Website reputation concern", site_reputation_poor: "Poor website reputation" };
  return titles[id] || "Recorded concern";
}
// Tone describes the recorded signal, not certainty that a seller is fraudulent.
export function concernTone(id: string): "danger" | "review" {
  return ["inconsistent", "injection", "excessive_data", "unusual_payment", "external_payment", "misleading_returns"].includes(id) ? "danger" : "review";
}
export function uniqueConcerns(risk: MerchantRisk | null) {
  return (risk?.evidence || []).filter((item, index, items) => items.findIndex(other => other.evidence.trim() === item.evidence.trim()) === index);
}
export function blockingReasons(rules: Action["rules"], risk: MerchantRisk | null) {
  return rules.filter(rule => rule.decision === "BLOCK").flatMap(rule => rule.rule_id === "merchant_risk" && risk?.evidence.length ? uniqueConcerns(risk).map(item => item.evidence) : [rule.explanation]).filter((text, index, items) => items.indexOf(text) === index);
}
