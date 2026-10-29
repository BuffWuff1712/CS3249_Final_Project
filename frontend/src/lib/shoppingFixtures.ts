import type { ShoppingOffer, ShoppingProduct, ShoppingScenario } from "./decision";

export const SCENARIO_VERSION = "beany-cui-v3.0";
export const headphoneProducts: ShoppingProduct[] = [
  {
    id: "echo-quiet", name: "Echo Quiet", category: "Headphones", variant: "standard-new", weight: 290,
    rating: 4.6, rating_count: 730,
    reviews: [{ rating: 4, title: "Train journeys", text: "Noise cancellation helped on my commute, but the weight is noticeable.", date: "2026-10-01" }],
    scores: { "noise cancellation": 3, comfort: 2 },
    advantages: { "noise cancellation": "has stronger listed noise cancellation", comfort: "has standard cushioned pads" },
    compromise: { "noise cancellation": "45g extra weight. Comfort has not been personally tested.", comfort: "more weight. Comfort is subjective and untested." },
    attributes: ["wireless", "noise-cancelling"],
    specifications: { "Noise cancellation": "Stronger listed noise cancellation", Weight: "290g", "Ear pads": "Standard cushions" },
  },
  {
    id: "luma-air", name: "Luma Air", category: "Headphones", variant: "standard-new", weight: 245,
    rating: 4.4, rating_count: 460,
    reviews: [{ rating: 4, title: "Long listening", text: "Light to wear for long sessions. Train noise is still audible.", date: "2026-10-02" }],
    scores: { "noise cancellation": 2, comfort: 3 },
    advantages: { "noise cancellation": "lists moderate noise cancellation", comfort: "is lighter with cushioned pads" },
    compromise: { "noise cancellation": "less noise cancellation than Echo Quiet.", comfort: "less noise cancellation. Comfort is subjective and untested." },
    attributes: ["wireless", "cushioned pads"],
    specifications: { "Noise cancellation": "Moderate listed noise cancellation", Weight: "245g", "Ear pads": "Soft cushioned pads" },
  },
];
const runningProducts: ShoppingProduct[] = [
  {
    id: "stride-cloud", name: "Stride Cloud", category: "Running shoes", variant: "EU42-blue-new", weight: 285,
    rating: 4.5, rating_count: 312,
    reviews: [{ rating: 4, title: "Daily road runs", text: "The extra cushioning suits my easy runs, though the shoes feel heavier.", date: "2026-10-03" }],
    scores: { cushioning: 3, "light weight": 2 },
    advantages: { cushioning: "has more listed cushioning", "light weight": "weighs 285g per shoe" },
    compromise: { cushioning: "65g more per shoe. Fit and injury prevention are not verified.", "light weight": "65g more per shoe than Pace Light. Fit must be tried." },
    attributes: ["road running", "extra cushioning"],
    specifications: { Cushioning: "Extra foam cushioning", Weight: "285g per shoe", Size: "EU42", Colour: "Blue", Condition: "New" },
  },
  {
    id: "pace-light", name: "Pace Light", category: "Running shoes", variant: "EU42-blue-new", weight: 220,
    rating: 4.4, rating_count: 206,
    reviews: [{ rating: 4, title: "Shorter runs", text: "Light on my feet, with less cushioning than my daily trainers.", date: "2026-10-04" }],
    scores: { cushioning: 2, "light weight": 3 },
    advantages: { cushioning: "lists moderate cushioning", "light weight": "is 65g lighter per shoe" },
    compromise: { cushioning: "less cushioning than Stride Cloud. Fit must be tried.", "light weight": "less cushioning. Fit and injury prevention are not verified." },
    attributes: ["road running", "lightweight"],
    specifications: { Cushioning: "Moderate foam cushioning", Weight: "220g per shoe", Size: "EU42", Colour: "Blue", Condition: "New" },
  },
];
function offersFor(products: ShoppingProduct[], prices: number[], merchants: string[]): ShoppingOffer[] {
  return products.flatMap((product, index) => [
    { id: `${product.id}-northline`, productId: product.id, merchant: merchants[0], price: prices[index], returnsDays: 30, rating: 4.7, reviewCount: 2140, payment: "Ordinary checkout" },
    { id: `${product.id}-everyday`, productId: product.id, merchant: merchants[1], price: prices[index] - 20, returnsDays: 14, rating: 4.5, reviewCount: 84, payment: "Ordinary checkout" },
    { id: `${product.id}-soundrush`, productId: product.id, merchant: merchants[2], price: prices[index] - 80, returnsDays: null, rating: 4.8, reviewCount: 12, payment: "Pay by gift card outside checkout" },
  ]);
}
export const headphoneOffers = offersFor(headphoneProducts, [289, 279], ["Northline Audio", "Everyday Sound", "SoundRush Deals"]);
export const shoppingScenario: ShoppingScenario = {
  version: SCENARIO_VERSION,
  products: [...headphoneProducts, ...runningProducts],
  offers: [...headphoneOffers, ...offersFor(runningProducts, [179, 169], ["Northline Running", "Everyday Run", "SprintRush Deals"])],
};
