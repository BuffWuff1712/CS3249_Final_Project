import type { ShoppingProduct, ShoppingOffer, ShoppingDecision, Needs } from "./decision";

export const SCENARIO_VERSION = "headphones-v2.1";
export const headphoneProducts: ShoppingProduct[] = [
  { id: "echo-quiet", name: "Echo Quiet", category: "Headphones", variant: "standard-new",
    rating: 4.6, rating_count: 730, reviews: [{ rating: 4, title: "Train journeys", text: "Noise cancellation helped on my commute, but the weight is noticeable.", date: "2026-10-01" }],
    weight: 290, noise: 3, comfort: 2, attributes: ["wireless", "noise-cancelling"],
    specifications: { "Noise cancellation": "Stronger listed noise cancellation", "Weight": "290g", "Ear pads": "Standard cushions" } },
  { id: "luma-air", name: "Luma Air", category: "Headphones", variant: "standard-new",
    rating: 4.4, rating_count: 460, reviews: [{ rating: 4, title: "Long listening", text: "Light to wear for long sessions. Train noise is still audible.", date: "2026-10-02" }],
    weight: 245, noise: 2, comfort: 3, attributes: ["wireless", "cushioned pads"],
    specifications: { "Noise cancellation": "Moderate listed noise cancellation", "Weight": "245g", "Ear pads": "Soft cushioned pads" } },
];

export const headphoneOffers: ShoppingOffer[] = headphoneProducts.flatMap((p, i) => {
  const price = i === 0 ? 289 : 279;
  return [
    { id: `${p.id}-northline`, productId: p.id, merchant: "Northline Audio", price, returnsDays: 30, rating: 4.7, reviewCount: 2140, payment: "Ordinary checkout" },
    { id: `${p.id}-everyday`, productId: p.id, merchant: "Everyday Sound", price: price - 20, returnsDays: 14, rating: 4.5, reviewCount: 84, payment: "Ordinary checkout" },
    { id: `${p.id}-soundrush`, productId: p.id, merchant: "SoundRush Deals", price: price - 80, returnsDays: null, rating: 4.8, reviewCount: 12, payment: "Pay by gift card outside checkout" },
  ];
});

export function referenceNeeds(): Needs {
  return {
    category: { value: "Headphones", source: "confirmed", hard: true },
    usage: { value: "daily train commute", source: "confirmed", hard: false },
    budget: { value: "300", source: "confirmed", hard: true },
    currency: { value: "SGD", source: "confirmed", hard: true },
    priority: { value: "noise cancellation", source: "confirmed", hard: false },
  };
}

export function createDecision(needs: Needs, revision: number): ShoppingDecision | null {
  const budget = needs.budget ? Number(needs.budget.value) : Infinity;
  if (!(budget > 0)) return null;
  const eligible = headphoneProducts.filter(p => headphoneOffers.some(o =>
    o.productId === p.id && o.price <= budget && o.payment === "Ordinary checkout"));
  const comfort = needs.priority?.value === "comfort";
  eligible.sort((a, b) => comfort ? b.comfort - a.comfort : b.noise - a.noise);
  const product = eligible[0];
  if (!product) return null;
  const alternative = headphoneProducts.find(p => p.id !== product.id)!;
  const offers = headphoneOffers.filter(o => o.productId === product.id);
  const offer = offers.find(o => o.price <= budget && o.payment === "Ordinary checkout")!;
  const cheaper = offers.find(o => o.price < offer.price && o.payment === "Ordinary checkout");
  return { revision, needs, product, offer, alternative,
    comparedProducts: headphoneProducts, comparedOffers: offers,
    reasons: [
      { id: "needs", text: `${needs.priority?.source === "confirmed" ? "Your priority is" : "I assumed"} ${needs.priority?.value || "noise cancellation"} for ${needs.usage?.value || "everyday listening"}. ${needs.budget ? `Spending limit: SGD${budget}.` : "No spending limit is confirmed."}`, evidence: ["needs:priority", "needs:budget"] },
      { id: "comparison", text: `${!Number.isFinite(budget) ? "I compared both models without a confirmed limit." : eligible.length > 1 ? "Both models fit your budget." : "The other model has no suitable offer within your limit."} ${product.name} ${comfort ? "is lighter with cushioned pads" : "has stronger listed noise cancellation"} than ${alternative.name}.`, evidence: [product.id, alternative.id] },
      { id: "seller", text: cheaper ? `I favoured ${offer.merchant}'s ${offer.returnsDays}-day returns over ${cheaper.merchant}'s ${cheaper.returnsDays} days, for SGD${offer.price - cheaper.price} more. Longer returns are my tie-breaker; you can change that.` : `${offer.merchant} fits your limit and lists ${offer.returnsDays}-day returns. A smaller review history alone is not a warning.`, evidence: [offer.id, ...(cheaper ? [cheaper.id] : [])] },
      { id: "tradeoff", text: comfort ? `The compromise is less noise cancellation. Comfort is subjective and untested.` : `The compromise is ${product.weight - alternative.weight}g extra weight. Comfort has not been personally tested.`, evidence: [product.id, alternative.id] },
    ] };
}

export function referenceDecision(): ShoppingDecision {
  return createDecision(referenceNeeds(), 1)!;
}
