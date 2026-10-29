import type { ComparisonResult, MerchantConcern, Needs, Priority, SellerChoice, ShoppingDecision, ShoppingOffer, ShoppingScenario } from "./decision";
import { categoryOf, priorities, validateNeed } from "./shoppingNeeds";
import { shoppingScenario } from "./shoppingFixtures";
export { SCENARIO_VERSION, headphoneProducts, headphoneOffers } from "./shoppingFixtures";

export function merchantConcern(offer: ShoppingOffer): MerchantConcern | null {
  if (/gift.?card|outside checkout|bank transfer/i.test(offer.payment)) return {
    offerId: offer.id, merchant: offer.merchant, blocked: true,
    observation: `${offer.merchant} requests: “${offer.payment}”.`,
    consequence: "Payment outside checkout removes the ordinary checkout protections; this offer cannot be selected here.",
    nextStep: "Choose an offer using ordinary checkout instead.",
  };
  if (offer.returnsDays === null || !offer.payment) return {
    offerId: offer.id, merchant: offer.merchant, blocked: false,
    observation: `${offer.merchant} has ${offer.returnsDays === null ? "no supplied return period" : "no supplied payment terms"}.`,
    consequence: "That term is unknown; I cannot promise return flexibility or checkout protection.",
    nextStep: "Confirm the missing terms or choose another seller with supplied terms.",
  };
  return null;
}

export function compareNeeds(needs: Needs, revision: number, choice?: SellerChoice, scenario: ShoppingScenario = shoppingScenario): ComparisonResult {
  try { return runComparison(needs, revision, choice, scenario); }
  catch {
    return { status: "error", decision: null, activity: [{ id: "comparison", label: "The comparison could not complete. No result was verified.", state: "unavailable", evidence: [] }], message: "Comparison is unavailable. Your needs and message are preserved. Retry the comparison or edit your needs." };
  }
}

function runComparison(needs: Needs, revision: number, choice: SellerChoice | undefined, scenario: ShoppingScenario): ComparisonResult {
  const invalid = Object.entries(needs).map(([key, fact]) => validateNeed(key as keyof Needs, fact.value, needs)).find(Boolean);
  if (invalid) return { status: "no-match", decision: null, activity: [], message: invalid };
  const category = categoryOf(needs);
  if (!category) return { status: "no-match", decision: null, activity: [], message: "Choose headphones or running shoes before comparing." };
  const products = scenario.products.filter(product => product.category === category);
  const productIds = new Set(products.map(product => product.id));
  const offers = scenario.offers.filter(offer => productIds.has(offer.productId));
  const budget = needs.budget ? Number(needs.budget.value) : Infinity;
  const eligibleOffers = offers.filter(offer => offer.price <= budget && !merchantConcern(offer)?.blocked);
  const eligibleProducts = products.filter(product => eligibleOffers.some(offer => offer.productId === product.id));
  const activity: ComparisonResult["activity"] = [
    { id: "products", label: `Compared ${products.length} fictional product records against your needs.`, state: products.length ? "completed" : "unavailable", evidence: products.map(product => product.id) },
    { id: "eligibility", label: `${eligibleProducts.length} models have a selectable offer${needs.budget ? ` within SGD${budget}` : "; no spending limit is confirmed"}.`, state: "completed", evidence: eligibleOffers.map(offer => offer.id) },
  ];
  const priority = (needs.priority?.value || priorities[category][0]) as Priority;
  const ranked = [...eligibleProducts].sort((a, b) => (b.scores[priority] ?? 0) - (a.scores[priority] ?? 0));
  const product = choice ? ranked.find(candidate => candidate.id === choice.productId) : ranked[0];
  if (!product) return { status: "no-match", decision: null, activity, message: choice
    ? `No selectable seller for the same product variant fits ${needs.budget ? `your SGD${budget} limit` : "these needs"}. Keep the product and change the limit explicitly, or compare other products.`
    : `No selectable offer fits ${needs.budget ? `your SGD${budget} limit` : "these needs"}. I kept your constraints. Change the budget explicitly or explore the other category.` };
  const comparedOffers = offers.filter(offer => offer.productId === product.id);
  const sellerOptions = eligibleOffers.filter(offer => offer.productId === product.id && offer.id !== choice?.excludeOfferId);
  const lowestPrice = needs.sellerPreference?.value === "lowest price";
  sellerOptions.sort((a, b) => lowestPrice ? a.price - b.price : (b.returnsDays ?? -1) - (a.returnsDays ?? -1) || a.price - b.price);
  const offer = sellerOptions[0];
  if (!offer) return { status: "no-match", decision: null, activity, message: "No other selectable seller for this exact product variant fits your limit. Keep the current seller or explicitly change your needs." };
  const alternative = products.find(candidate => candidate.id !== product.id);
  const alternativeEligible = alternative && eligibleProducts.some(candidate => candidate.id === alternative.id);
  const cheaper = sellerOptions.find(candidate => candidate.price < offer.price);
  const longer = sellerOptions.find(candidate => (candidate.returnsDays ?? -1) > (offer.returnsDays ?? -1));
  const terms = offer.returnsDays === null ? "an unknown return period" : `${offer.returnsDays}-day returns`;
  const sellerReason = lowestPrice
    ? `You preferred price: ${offer.merchant} is the cheapest selectable seller, with ${terms}.${longer ? ` You give up ${longer.returnsDays}-day returns.` : ""}`
    : cheaper && offer.returnsDays !== null && cheaper.returnsDays !== null
      ? `I favoured ${offer.merchant}'s ${offer.returnsDays}-day returns over ${cheaper.merchant}'s ${cheaper.returnsDays} days, for SGD${offer.price - cheaper.price} more. Longer returns are ${needs.sellerPreference?.source === "confirmed" ? "your preference" : "my editable tie-breaker"}.`
      : `${offer.merchant} fits your limit with ${terms}. A smaller review history alone is not a warning.`;
  const concerns = comparedOffers.map(merchantConcern).filter((concern): concern is MerchantConcern => !!concern && (concern.offerId === offer.id || lowestPrice && concern.blocked)).map(concern => concern.blocked ? { ...concern, nextStep: `I recommend ${offer.merchant} at SGD${offer.price}, using ordinary checkout instead.` } : concern);
  const missingEvidence = comparedOffers.some(candidate => candidate.returnsDays === null || !candidate.payment) || products.some(candidate => !candidate.reviews?.length);
  activity.push(
    { id: "sellers", label: `Reviewed ${comparedOffers.length} seller records for ${product.name}, variant ${product.variant}.`, state: "completed", evidence: comparedOffers.map(candidate => candidate.id) },
    { id: "evidence", label: missingEvidence ? "Some return, payment or product-review evidence is unavailable; those values remain unknown." : "Product reviews and seller terms are available as fictional source records.", state: missingEvidence ? "unavailable" : "completed", evidence: missingEvidence ? [...products.filter(candidate => !candidate.reviews?.length).map(candidate => candidate.id), ...comparedOffers.filter(candidate => candidate.returnsDays === null || !candidate.payment).map(candidate => candidate.id)] : [product.id, offer.id] },
  );
  return { status: "ready", activity, message: "", decision: {
    revision, needs, product, offer, alternative, comparedProducts: products, comparedOffers, concerns, productFixed: !!choice,
    reasons: [
      { id: "needs", text: `${needs.priority?.source === "confirmed" ? "Your priority is" : "I assumed"} ${priority} for ${needs.usage?.value || "everyday use"}. ${needs.budget ? `Spending limit: SGD${budget}.` : "No spending limit is confirmed."}`, evidence: ["needs:priority", "needs:budget"] },
      { id: "comparison", text: choice ? `You fixed ${product.name} for this seller comparison.${ranked[0]?.id !== product.id ? ` ${ranked[0].name} ranks higher for ${priority}; I kept your requested model.` : ` It ${product.advantages[priority]}.`}` : alternative ? `${!needs.budget ? "I compared both models without a confirmed spending limit." : alternativeEligible ? "Both models fit your budget." : "The other model has no selectable offer within your limit."} ${product.name} ${product.advantages[priority] || "best meets the represented priority"} compared with ${alternative.name}.` : "Only one model is available; this comparison is limited.", evidence: [product.id, ...(alternative ? [alternative.id] : [])] },
      { id: "seller", text: sellerReason, evidence: [offer.id, ...(cheaper ? [cheaper.id] : []), ...(longer ? [longer.id] : [])] },
      { id: "tradeoff", text: `The compromise is ${alternative ? product.compromise[priority] || "limited comparative evidence; suitability is not verified." : "limited comparative evidence; suitability is not verified."}`, evidence: [product.id, ...(alternative ? [alternative.id] : [])] },
    ],
  } };
}

export function createDecision(needs: Needs, revision: number): ShoppingDecision | null {
  return compareNeeds(needs, revision).decision;
}
export function referenceNeeds(): Needs {
  return {
    category: { value: "Headphones", source: "confirmed", hard: true },
    usage: { value: "daily train commute", source: "confirmed", hard: false },
    budget: { value: "300", source: "confirmed", hard: true },
    currency: { value: "SGD", source: "confirmed", hard: true },
    priority: { value: "noise cancellation", source: "confirmed", hard: false },
  };
}
