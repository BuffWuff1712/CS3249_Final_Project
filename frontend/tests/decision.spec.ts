import { test, expect } from "@playwright/test";
import { compareNeeds, merchantConcern, referenceNeeds } from "../src/lib/shoppingScenario";
import { shoppingScenario } from "../src/lib/shoppingFixtures";
import { interpretPurchase } from "../src/lib/purchaseIntent";

test("budget eligibility excludes external payment and never relaxes a hard ceiling", () => {
  const needs = referenceNeeds();
  for (const budget of ["0", "-1", "180", "208.99", "250"]) {
    expect(compareNeeds({ ...needs, budget: { value: budget, hard: true, source: "confirmed" } }, 2).decision).toBeNull();
  }
  const result = compareNeeds({ ...needs, budget: { value: "269", hard: true, source: "confirmed" } }, 2);
  expect(result.decision?.offer.price).toBeLessThanOrEqual(269);
});

test("seller changes are restricted to the exact product and expose honest no-alternative state", () => {
  const needs = referenceNeeds();
  const next = compareNeeds(needs, 2, { productId: "echo-quiet", excludeOfferId: "echo-quiet-northline" });
  expect(next.decision?.product.id).toBe("echo-quiet");
  expect(next.decision?.offer.id).toBe("echo-quiet-everyday");
  const oneSeller = { ...shoppingScenario, offers: shoppingScenario.offers.filter(offer => !offer.id.endsWith("everyday")) };
  const none = compareNeeds(needs, 2, { productId: "echo-quiet", excludeOfferId: "echo-quiet-northline" }, oneSeller);
  expect(none.decision).toBeNull();
  expect(none.message).toContain("No other selectable seller");
});

test("missing evidence remains unknown and unavailable instead of becoming a completed claim", () => {
  const scenario = {
    ...shoppingScenario,
    products: shoppingScenario.products.map(product => ({ ...product, reviews: [] })),
    offers: shoppingScenario.offers.map(offer => ({ ...offer, returnsDays: null })),
  };
  const result = compareNeeds(referenceNeeds(), 1, undefined, scenario);
  expect(result.decision?.offer.returnsDays).toBeNull();
  expect(result.decision?.reasons.find(reason => reason.id === "seller")?.text).toContain("unknown");
  expect(result.activity.find(activity => activity.id === "evidence")?.state).toBe("unavailable");
  expect(result.decision?.concerns.some(concern => !concern.blocked)).toBe(true);
});

test("a small clean seller and benign discount are not a merchant warning", () => {
  expect(merchantConcern(shoppingScenario.offers.find(offer => offer.id === "echo-quiet-everyday")!)).toBeNull();
});

test("a currency clarification preserves the original stated needs", () => {
  const result = interpretPurchase("Headphones for commuting, under USD300, comfort first", {}, 0);
  expect(result.ready).toBe(false);
  expect(result.needs.category?.value).toBe("Headphones");
  expect(result.needs.budget?.value).toBe("300");
  expect(result.needs.currency?.value).toBe("USD");
  expect(result.needs.priority?.value).toBe("comfort");
});

test("negative amounts and negated priorities are not silently interpreted as positive preferences", () => {
  expect(interpretPurchase("My budget is SGD-10", referenceNeeds(), 0).ready).toBe(false);
  const result = interpretPurchase("I do not want noise cancellation; comfort first", referenceNeeds(), 0);
  expect(result.needs.priority?.value).toBe("comfort");
  expect(interpretPurchase("Comfort does not matter", referenceNeeds(), 0).ready).toBe(false);
  expect(interpretPurchase("Not SGD300, use SGD180", referenceNeeds(), 0).ready).toBe(false);
});

test("a failed comparison reports unavailable and does not fabricate successful checks", () => {
  const failing = { ...shoppingScenario, get products(): typeof shoppingScenario.products { throw new Error("Source unavailable"); } };
  const result = compareNeeds(referenceNeeds(), 1, undefined, failing);
  expect(result.status).toBe("error");
  expect(result.decision).toBeNull();
  expect(result.activity.every(activity => activity.state === "unavailable")).toBe(true);
  expect(result.message).toContain("Retry");
});

test("a single-model fixture admits the comparison limit without inventing an alternative", () => {
  const result = compareNeeds(referenceNeeds(), 1, undefined, { ...shoppingScenario, products: shoppingScenario.products.filter(product => product.id === "echo-quiet") });
  expect(result.decision?.alternative).toBeUndefined();
  expect(result.decision?.reasons.find(reason => reason.id === "comparison")?.text).toContain("limited");
  expect(result.decision?.reasons.find(reason => reason.id === "tradeoff")?.text).not.toContain("45g");
});

test("default decision text is concise and its source references resolve in both categories", () => {
  for (const category of ["Headphones", "Running shoes"]) {
    const needs = { ...referenceNeeds(), category: { value: category, source: "confirmed" as const, hard: true }, priority: { value: category === "Headphones" ? "noise cancellation" : "cushioning", source: "confirmed" as const, hard: false } };
    const decision = compareNeeds(needs, 1).decision!;
    const words = [decision.product.name, decision.offer.merchant, `SGD${decision.offer.price}`, ...decision.reasons.map(reason => reason.text)].join(" ").split(/\s+/);
    expect(words.length).toBeLessThanOrEqual(120);
    const ids = new Set([...shoppingScenario.products.map(product => product.id), ...shoppingScenario.offers.map(offer => offer.id)]);
    for (const reason of decision.reasons) for (const reference of reason.evidence) expect(reference.startsWith("needs:") || ids.has(reference)).toBe(true);
  }
});
