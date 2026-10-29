import catalogue from "../../../shared/cui/catalogue.json";
import type { ShoppingScenario } from "./decision";
export const shoppingScenario: ShoppingScenario = catalogue;
export const SCENARIO_VERSION = shoppingScenario.version;
export const headphoneProducts = shoppingScenario.products.filter(product => product.category === "Headphones");
export const headphoneOffers = shoppingScenario.offers.filter(offer => headphoneProducts.some(product => product.id === offer.productId));
