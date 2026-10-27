import type { ShoppingProduct, ShoppingOffer, ShoppingDecision, Needs } from "./decision";

export const SCENARIO_VERSION = "headphones-v2.1";
export const headphoneProducts: ShoppingProduct[] = [
  { id: "echo-quiet", name: "Echo Quiet", category: "Headphones", variant: "standard-new",
    weight: 290, noise: 3, comfort: 2, attributes: ["wireless", "noise-cancelling"],
    specifications: { "Noise cancellation": "Stronger listed noise cancellation", "Weight": "290g", "Ear pads": "Standard cushions" } },
  { id: "luma-air", name: "Luma Air", category: "Headphones", variant: "standard-new",
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

export function referenceDecision(): ShoppingDecision {
  const needs: Needs = {
    category: { value: "Headphones", source: "confirmed", hard: true },
    usage: { value: "daily train commute", source: "confirmed", hard: false },
    budget: { value: "300", source: "confirmed", hard: true },
    currency: { value: "SGD", source: "confirmed", hard: true },
    priority: { value: "noise cancellation", source: "confirmed", hard: false },
  };
  const [product, alternative] = headphoneProducts;
  const offers = headphoneOffers.filter(o => o.productId === product.id);
  const offer = offers[0], cheaper = offers[1];
  return { revision: 1, needs, product, offer, alternative,
    comparedProducts: headphoneProducts, comparedOffers: offers,
    reasons: [
      { id: "needs", text: "You prioritised noise cancellation for your train commute, within SGD300.", evidence: ["needs:priority", "needs:budget"] },
      { id: "comparison", text: `Both models fit your budget. ${product.name} has stronger listed noise cancellation than ${alternative.name}.`, evidence: [product.id, alternative.id] },
      { id: "seller", text: `I favoured ${offer.merchant}'s ${offer.returnsDays}-day returns over ${cheaper.merchant}'s ${cheaper.returnsDays} days, for SGD${offer.price - cheaper.price} more. Longer returns are my tie-breaker; you can change that.`, evidence: [offer.id, cheaper.id] },
      { id: "tradeoff", text: `The compromise is ${product.weight - alternative.weight}g extra weight. Comfort has not been personally tested.`, evidence: [product.id, alternative.id] },
    ] };
}
