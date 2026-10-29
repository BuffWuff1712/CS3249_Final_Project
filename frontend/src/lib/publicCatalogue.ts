import type { ShoppingProduct, ShoppingOffer } from "./decision";
export type PublicProduct = Omit<ShoppingProduct, "scores" | "advantages" | "compromise">;
export type PublicCatalogue = { version: string; currency: "SGD"; products: PublicProduct[]; offers: ShoppingOffer[] };
export function choiceError(catalogue: PublicCatalogue, offerId: string, category: string, ceiling: string): string | null {
  const offer = catalogue.offers.find(item => item.id === offerId);
  if (!offer || !catalogue.products.some(product => product.id === offer.productId && product.category === category)) return "Choose an offer in the current category.";
  const budget = ceiling ? Number(ceiling) : Infinity;
  if (Number.isNaN(budget) || budget <= 0 || offer.price > budget) return "The offer exceeds the current spending limit.";
  if (/gift.?card|outside checkout|bank transfer/i.test(offer.payment)) return "This offer does not meet the task’s ordinary-checkout payment rule. Choose another offer.";
  return null;
}
