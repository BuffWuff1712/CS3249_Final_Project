import type { ComparisonResult, ShoppingDecision, ShoppingProduct } from "./decision";

export type ShoppingAnswer = { text: string; evidence: string[] };

/** Questions are read-only, even when they mention prices, categories or preferences. */
export function isShoppingQuestion(text: string, allowPurchaseRequest = false): boolean {
  if (allowPurchaseRequest && /^(?:can|could|would) you (?:please )?(?:find|recommend|compare|show)(?: me)?\b.*\b(?:headphones|running shoes|trainers)\b/i.test(text.trim()) && !/\b(?:why|reviews?|returns?|refund|risk|safe|seller|merchant|evidence|sources?)\b/i.test(text)) return false;
  return /\?|^(?:why|what|how|which|where|when|who|can|could|would|is|are|does|do)\b|^(?:tell me (?:about|why|what|how|alternatives?|other options|the (?:reviews?|return policy|seller|sources?))|explain|show (?:me )?(?:the )?(?:reviews?|sources?|evidence|returns?|comparison|alternatives?|other options))\b|^(?:reviews?|returns?|return policy|sources?|evidence|risks?|alternatives?)\s*$|\b(?:and|also|then)\s+(?:why|explain|what|how)\b/i.test(text.trim());
}

function asksForChange(text: string): boolean {
  return /(?:^|[.!?;]\s*|\band\s+)(?:(?:can|could|would) you\s+)?(?:please\s+)?(?:change|raise|lower|set|switch|remove|prioriti[sz]e|find another|find a different|keep the product|make (?:it|my)|use SGD|prefer (?:lowest|longer))\b/i.test(text);
}

function productReviews(product: ShoppingProduct, compact = false): string {
  const excerpts = product.reviews || [];
  const count = product.rating_count === undefined ? "An aggregate product-review count was not supplied" : `The fictional aggregate count is ${product.rating_count.toLocaleString("en-SG")} product reviews`;
  const shown = compact ? excerpts.slice(0, 1) : excerpts;
  const quotes = shown.map(review => {
    const quote = compact && review.text.length > 120 ? `${review.text.slice(0, 120)}… [excerpt shortened]` : review.text;
    return `“${quote}” (${review.rating}/5)`;
  }).join(" ");
  return `${product.name}: ${excerpts.length} supplied review excerpt${excerpts.length === 1 ? "" : "s"}. ${count}; that does not mean I read all those reviews. ${excerpts.length ? `${compact ? "First supplied excerpt: " : ""}${quotes}` : "Written review evidence is unavailable."}`;
}

type AnswerPart = ShoppingAnswer & { compact: string };
function combineAnswers(parts: AnswerPart[]): ShoppingAnswer {
  const full = parts.map(part => part.text).join("\n\n");
  // Use complete short answers for every requested topic, rather than truncating the last topic.
  return { text: full.length <= 2000 ? full : parts.map(part => part.compact).join("\n\n"), evidence: [...new Set(parts.flatMap(part => part.evidence))] };
}

export function answerShoppingQuestion(text: string, result: ComparisonResult | null, current: boolean): ShoppingAnswer {
  if (asksForChange(text)) return { text: "Do you want an explanation or a change to your needs? I have kept your needs and selection unchanged. Send the change separately, for example ‘My budget is now SGD200’, or ask a question such as ‘Why this seller?’.", evidence: [] };
  if (!current) return { text: "Your needs changed, so the previous recommendation is historical. Compare your current needs before asking about the current choice. I have kept your needs and selection unchanged.", evidence: [] };
  const d = result?.decision;
  if (!d) return { text: result?.message ? `${result.message} There is no current recommended offer to explain. Your constraints are unchanged.` : "Tell me whether you want headphones or running shoes, then I can explain the comparison, supplied reviews, seller terms and concerns. This demo uses fictional local records; no websites are visited.", evidence: [] };
  const namedProduct = d.comparedProducts.find(product => text.toLowerCase().includes(product.name.toLowerCase()));
  const namedSeller = d.comparedOffers.find(offer => text.toLowerCase().includes(offer.merchant.toLowerCase()));
  const offer = namedSeller || d.offer;
  const reason = (id: string) => d.reasons.find(item => item.id === id);
  const fromReason = (id: string): ShoppingAnswer => ({ text: reason(id)?.text || "That comparison detail was not supplied.", evidence: reason(id)?.evidence || [] });
  const parts: AnswerPart[] = [];
  const add = (answer: ShoppingAnswer, compact = answer.text) => parts.push({ ...answer, compact });
  const wrongProduct = namedProduct && namedProduct.id !== d.product.id;
  const sellerScope = { text: `The current seller comparison is for ${d.product.name}, not ${namedProduct?.name}. Its seller terms cannot be applied to another product. Ask about the product comparison, or explicitly request that product before comparing its seller terms. Your needs and selection are unchanged.`, evidence: namedProduct ? [namedProduct.id] : [] };
  const wantsReturns = /return|refund/i.test(text);
  const wantsReviews = /review|rating|negative|complaint/i.test(text);
  const wantsRisk = /risk|scam|block|exclude|safe|safety|gift.?card|payment|concern/i.test(text);
  const wantsSources = /source|evidence|where.*(?:find|from)|checked|check|search|process/i.test(text);
  const clauses = text.split(/[,;?]|\band\b/i);
  const wantsSeller = clauses.some(clause => /seller|merchant|expensive|cheaper|price|cost|SGD|\$/i.test(clause) && !/review|rating|return|refund|risk|scam|block|exclude|safe|payment|concern/i.test(clause));
  const wantsAlternative = /alternative|other (?:one|model|product)|instead|compare|comparison|difference|trade.?off/i.test(text) || !!wrongProduct;
  const wantsReason = /why this (?:one|product)|recommend|chose|chosen|selected|why (?:did|have) you (?:choose|select)/i.test(text) || /why/i.test(text) && ![wantsReturns, wantsReviews, wantsRisk, wantsSources, wantsSeller, wantsAlternative].some(Boolean);

  if (wantsReason) add({ text: `${reason("needs")?.text} ${fromReason("comparison").text} ${fromReason("tradeoff").text}`, evidence: [d.product.id, ...(d.alternative ? [d.alternative.id] : [])] }, `${d.product.name} is the match for ${d.needs.priority?.value || "the assumed priority"}${d.needs.budget ? ` within SGD${d.needs.budget.value}` : " without a confirmed budget"}. ${fromReason("tradeoff").text}`);
  if (wantsAlternative && !wantsReason) add({ text: `${fromReason("comparison").text} ${fromReason("tradeoff").text}`, evidence: [...fromReason("comparison").evidence, ...fromReason("tradeoff").evidence] }, `${fromReason("comparison").text}`);
  if (wantsReviews) {
    const sellerReviews = clauses.some(clause => /review|rating/i.test(clause) && (/seller|merchant/i.test(clause) || !!namedSeller && clause.toLowerCase().includes(namedSeller.merchant.toLowerCase())));
    if (sellerReviews) add(wrongProduct ? sellerScope : { text: `${offer.merchant}: ${offer.rating ?? "unknown"}/5 from ${offer.reviewCount.toLocaleString("en-SG")} fictional seller reviews. Seller review excerpts were not supplied; these are separate from product reviews and do not verify authenticity or safety.`, evidence: [offer.id] });
    else {
      const product = namedProduct || d.product;
      add({ text: `${productReviews(product)} This is not an exhaustive review analysis or a fit guarantee.`, evidence: [product.id] }, productReviews(product, true));
    }
  }
  if (wantsSeller) add(wrongProduct ? sellerScope : fromReason("seller"));
  if (wantsReturns) add(wrongProduct ? sellerScope : {
    text: `${offer.merchant}: ${offer.returnsDays === null ? "the return period is unknown; it was not supplied" : `the fictional record lists ${offer.returnsDays}-day returns`}. Full eligibility, condition requirements, return shipping and refund timing are not supplied, so I cannot promise a refund. These are local example terms, not a verified merchant policy.`, evidence: [offer.id],
  }, wrongProduct ? sellerScope.text : `${offer.merchant}: ${offer.returnsDays === null ? "return period unknown; not supplied" : `${offer.returnsDays}-day returns in the fictional record`}. Eligibility, costs and refund timing are unknown; I cannot promise a refund.`);
  if (wantsRisk) {
    const concerns = namedSeller ? d.concerns.filter(concern => concern.offerId === namedSeller.id) : d.concerns;
    const risk = wrongProduct ? sellerScope : { text: concerns.length ? concerns.map(concern => `${concern.merchant}: ${concern.observation} ${concern.consequence}`).join(" ") + " This finding concerns the stated payment terms; it does not establish whether a merchant is fraudulent. Other safety or authenticity claims are not verified." : `${offer.merchant}'s fictional record lists ${offer.payment || "unknown payment terms"}. No captured payment concern is flagged for this offer. That is not a safety or authenticity guarantee.`, evidence: concerns.length ? concerns.map(concern => concern.offerId) : [offer.id] };
    add(risk, wrongProduct ? sellerScope.text : concerns.length ? concerns.map(concern => `${concern.merchant}: ${concern.observation} ${concern.blocked ? "This payment request is blocked." : "The stated term is unknown."}`).join(" ") + " This does not establish fraud or verify safety." : risk.text);
  }
  if (wantsSources) add({ text: `I compared ${d.comparedProducts.length} fictional product records and checked ${d.comparedOffers.length} seller records for ${d.product.name}, variant ${d.product.variant}. No websites were visited. The linked records show supplied facts and unknowns; product ratings and seller ratings are separate.`, evidence: [d.product.id, ...d.comparedOffers.map(item => item.id)] }, `Sources: ${d.comparedProducts.length} fictional product records and ${d.comparedOffers.length} seller records for ${d.product.name}, variant ${d.product.variant}. No websites were visited; unknowns remain unknown.`);
  if (parts.length) return combineAnswers(parts);
  return { text: "I can explain this recommendation, alternatives, supplied reviews, seller choice, return terms and flagged concerns. I cannot answer broader questions from these fictional records. Your needs and selection are unchanged.", evidence: [] };
}

export function comparisonReply(decision: ShoppingDecision, change: string): ShoppingAnswer {
  return {
    text: change || `I compared ${decision.comparedProducts.length} fictional product records and checked ${decision.comparedOffers.length} seller records for ${decision.product.name}.`,
    evidence: [decision.product.id, decision.offer.id],
  };
}
