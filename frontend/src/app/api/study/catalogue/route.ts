import { shoppingScenario } from "@/lib/shoppingFixtures";
import type { PublicCatalogue } from "@/lib/publicCatalogue";
export const dynamic = "force-dynamic";
export function GET() {
  const catalogue: PublicCatalogue = {
    version: shoppingScenario.version, currency: "SGD",
    products: shoppingScenario.products.map(product => ({
      id: product.id, name: product.name, category: product.category, variant: product.variant,
      attributes: product.attributes, specifications: product.specifications, weight: product.weight,
      rating: product.rating, rating_count: product.rating_count, reviews: product.reviews,
    })),
    offers: shoppingScenario.offers.map(offer => ({
      id: offer.id, productId: offer.productId, merchant: offer.merchant, price: offer.price,
      returnsDays: offer.returnsDays, rating: offer.rating, reviewCount: offer.reviewCount, payment: offer.payment,
    })),
  };
  return Response.json(catalogue, { headers: { "Cache-Control": "no-store" } });
}
