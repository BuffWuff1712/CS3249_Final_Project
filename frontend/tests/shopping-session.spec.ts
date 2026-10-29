import { test, expect } from "@playwright/test";
import { initialShoppingState, shoppingReducer, restoreShoppingState, saveShoppingState } from "../src/lib/shoppingSession";
import { SCENARIO_VERSION } from "../src/lib/shoppingFixtures";

const request = "Headphones for my train commute under SGD300, noise cancellation first";

test("changing needs invalidates selection and explains changed and unchanged winners", () => {
  let state = shoppingReducer(initialShoppingState, { type: "send", text: request });
  state = shoppingReducer(state, { type: "select", revision: state.revision });
  expect(state.selected).toBe(true);
  state = shoppingReducer(state, { type: "send", text: "Actually, comfort matters more" });
  expect(state.selected).toBe(false);
  expect(state.result?.decision?.product.id).toBe("luma-air");
  expect(state.change).toContain("Echo Quiet");
  expect(state.change).toContain("Luma Air");
  state = shoppingReducer(state, { type: "send", text: "Comfort first" });
  expect(state.change).toContain("still");
});

test("stale revision cannot be selected and refresh revalidates the exact seller", () => {
  let state = shoppingReducer(initialShoppingState, { type: "send", text: request });
  state = shoppingReducer(state, { type: "send", text: "Keep the product but find another seller" });
  state = shoppingReducer(state, { type: "select", revision: state.revision - 1 });
  expect(state.selected).toBe(false);
  state = shoppingReducer(state, { type: "select", revision: state.revision });
  const restored = restoreShoppingState(saveShoppingState(state));
  expect(restored.selected).toBe(true);
  expect(restored.result?.decision?.offer.id).toBe("echo-quiet-everyday");
});

test("corrupt storage and outdated fixtures never restore a selected offer", () => {
  expect(restoreShoppingState("{broken").selected).toBe(false);
  expect(restoreShoppingState(JSON.stringify({ needs: { budget: { value: "-10", source: "confirmed", hard: true } }, revision: 1, selected: true, version: SCENARIO_VERSION })).selected).toBe(false);
  let state = shoppingReducer(initialShoppingState, { type: "send", text: request });
  state = shoppingReducer(state, { type: "select", revision: state.revision });
  const saved = JSON.parse(saveShoppingState(state));
  saved.version = "old-fixture";
  expect(restoreShoppingState(JSON.stringify(saved)).selected).toBe(false);
});

test("switching categories clears unrelated needs and never carries a selected offer", () => {
  let state = shoppingReducer(initialShoppingState, { type: "send", text: request });
  state = shoppingReducer(state, { type: "select", revision: state.revision });
  state = shoppingReducer(state, { type: "send", text: "Running shoes for daily road runs under SGD200, cushioning first" });
  expect(state.needs.priority?.value).toBe("cushioning");
  expect(state.needs.budget?.value).toBe("200");
  expect(state.result?.decision?.product.category).toBe("Running shoes");
  expect(state.selected).toBe(false);
});

test("retrying a seller failure retains the exact product until a different-product search is explicit", () => {
  let state = shoppingReducer(initialShoppingState, { type: "send", text: "Headphones for commuting under SGD260, comfort first" });
  expect(state.result?.decision?.offer.id).toBe("luma-air-everyday");
  state = shoppingReducer(state, { type: "send", text: "Find another seller" });
  expect(state.result?.decision).toBeNull();
  state = shoppingReducer(state, { type: "compare" });
  expect(state.result?.decision).toBeNull();
  expect(state.choice?.productId).toBe("luma-air");
  state = shoppingReducer(state, { type: "compare", currentSeller: true });
  expect(state.result?.decision?.offer.id).toBe("luma-air-everyday");
});

test("a model change caused by budget or an explicit product request never claims the priority changed", () => {
  let state = shoppingReducer(initialShoppingState, { type: "send", text: "Headphones for commuting under SGD260, noise cancellation first" });
  state = shoppingReducer(state, { type: "send", text: "Raise the budget to SGD300" });
  expect(state.result?.decision?.product.id).toBe("echo-quiet");
  expect(state.change).toContain("spending limit");
  expect(state.change).not.toContain("now comes first");
  state = shoppingReducer(state, { type: "send", text: "Actually, comfort matters more" });
  state = shoppingReducer(state, { type: "send", text: "Find the cheapest Echo Quiet offer" });
  expect(state.result?.decision?.product.id).toBe("echo-quiet");
  expect(state.result?.decision?.reasons.find(reason => reason.id === "comparison")?.text).toContain("Luma Air ranks higher");
  expect(state.change).toContain("requested this model");
});

test("seller-only preferences preserve the explicit product lock through chat, editor and refresh", () => {
  let state = shoppingReducer(initialShoppingState, { type: "send", text: "Headphones for commuting under SGD300, comfort first" });
  state = shoppingReducer(state, { type: "send", text: "Find the cheapest Echo Quiet offer" });
  expect(state.result?.decision?.product.id).toBe("echo-quiet");
  state = shoppingReducer(state, { type: "send", text: "Longer returns first" });
  expect(state.choice?.productId).toBe("echo-quiet");
  expect(state.result?.decision?.product.id).toBe("echo-quiet");
  expect(state.result?.decision?.offer.id).toBe("echo-quiet-northline");
  state = shoppingReducer(state, { type: "send", text: "Longer returns first" });
  expect(state.choice?.productId).toBe("echo-quiet");
  expect(state.result?.decision?.product.id).toBe("echo-quiet");
  state = shoppingReducer(state, { type: "edit", key: "sellerPreference", fact: { value: "lowest price", source: "confirmed", hard: false } });
  state = shoppingReducer(state, { type: "compare" });
  expect(state.result?.decision?.offer.id).toBe("echo-quiet-everyday");
  expect(restoreShoppingState(saveShoppingState(state)).choice?.productId).toBe("echo-quiet");
});

test("comparison history survives follow-ups and refresh without reusing later comparison evidence", () => {
  const first = shoppingReducer(initialShoppingState, { type: "send", text: request });
  const snapshot = first.messages.at(-1)!.comparison!;
  expect(snapshot.activity).toEqual(first.result!.activity);
  expect(snapshot.summary).toContain("Echo Quiet");
  const question = shoppingReducer(first, { type: "send", text: "What do reviews say?" });
  expect(question.messages.filter(message => message.comparison)).toHaveLength(1);
  const next = shoppingReducer(question, { type: "send", text: "Actually, comfort matters more" });
  const restored = restoreShoppingState(saveShoppingState(next));
  const comparisons = restored.messages.filter(message => message.comparison);
  expect(comparisons).toHaveLength(2);
  expect(comparisons[0].comparison).toEqual(snapshot);
  expect(comparisons[1].comparison!.summary).toContain("Luma Air");
  const legacy = JSON.parse(saveShoppingState(first));
  legacy.messages.forEach((message: { comparison?: unknown }) => delete message.comparison);
  expect(restoreShoppingState(JSON.stringify(legacy)).result!.decision!.product.id).toBe(first.result!.decision!.product.id);
});

test("unrecognized evidence in stored comparison history is rejected", () => {
  const state = shoppingReducer(initialShoppingState, { type: "send", text: request });
  const saved = JSON.parse(saveShoppingState(state));
  saved.messages.at(-1).comparison.activity[0].evidence = ["invented-record"];
  const restored = restoreShoppingState(JSON.stringify(saved));
  expect(restored.messages).toEqual([]);
  expect(restored.selected).toBe(false);
  expect(restored.notice).toContain("invalid");
});
