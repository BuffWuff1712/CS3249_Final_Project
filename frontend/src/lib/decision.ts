import type { Fact, Product } from "./beany";

export type NeedKey = "category" | "usage" | "budget" | "currency" | "priority";
export type Needs = Partial<Record<NeedKey, Fact>>;
export type ShoppingProduct = Pick<Product, "id" | "name" | "category" | "attributes" | "specifications"> & {
  variant: string;
  weight: number;
  noise: number;
  comfort: number;
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
export type ShoppingDecision = {
  revision: number;
  needs: Needs;
  product: ShoppingProduct;
  offer: ShoppingOffer;
  alternative: ShoppingProduct;
  comparedProducts: ShoppingProduct[];
  comparedOffers: ShoppingOffer[];
  reasons: DecisionReason[];
};
