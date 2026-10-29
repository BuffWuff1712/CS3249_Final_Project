import type { Fact, Product } from "./beany";

export type Category = "Headphones" | "Running shoes";
export type Priority = "noise cancellation" | "comfort" | "cushioning" | "light weight";
export type NeedKey = "category" | "usage" | "budget" | "currency" | "priority" | "sellerPreference";
export type Needs = Partial<Record<NeedKey, Fact>>;
export type ShoppingProduct = Pick<Product, "id" | "name" | "category" | "attributes" | "specifications" | "rating" | "rating_count" | "reviews"> & {
  variant: string;
  weight: number;
  scores: Partial<Record<Priority, number>>;
  advantages: Partial<Record<Priority, string>>;
  compromise: Partial<Record<Priority, string>>;
};
export type ShoppingOffer = {
  id: string;
  productId: string;
  merchant: string;
  price: number;
  returnsDays: number | null;
  rating: number | null;
  reviewCount: number;
  payment: string;
};
export type DecisionReason = { id: string; text: string; evidence: string[] };
export type MerchantConcern = { offerId: string; merchant: string; observation: string; consequence: string; nextStep: string; blocked: boolean };
export type ComparisonActivity = { id: string; label: string; state: "completed" | "unavailable"; evidence: string[] };
export type SellerChoice = { productId: string; excludeOfferId?: string };
export type ShoppingDecision = {
  revision: number;
  needs: Needs;
  product: ShoppingProduct;
  offer: ShoppingOffer;
  alternative?: ShoppingProduct;
  comparedProducts: ShoppingProduct[];
  comparedOffers: ShoppingOffer[];
  reasons: DecisionReason[];
  concerns: MerchantConcern[];
  productFixed: boolean;
};
export type ComparisonResult = {
  status: "ready" | "no-match" | "error";
  decision: ShoppingDecision | null;
  activity: ComparisonActivity[];
  message: string;
};
export type ShoppingScenario = { version: string; products: ShoppingProduct[]; offers: ShoppingOffer[] };
