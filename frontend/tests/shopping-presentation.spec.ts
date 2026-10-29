import { test, expect } from "@playwright/test";
import { initialPresentationState, presentationReducer, presentationSchedule, presentationStatus, type PresentationState } from "../src/lib/shoppingPresentation";
import { initialShoppingState, restoreShoppingState, saveShoppingState, shoppingReducer, type ShoppingAction } from "../src/lib/shoppingSession";

const request = "Headphones for my train commute, under SGD300. Noise cancellation first.";
const act = (state: PresentationState, action: ShoppingAction) => presentationReducer(state, { type: "action", action });
const send = (state: PresentationState, text: string) => act(state, { type: "send", text });
function finish(state: PresentationState): PresentationState {
  return state.pending ? presentationReducer(state, { type: "tick", id: state.pending.id, step: 4 }) : state;
}

test("comparison is computed once but user message appears before needs and result", () => {
  const pending = send(initialPresentationState, request);
  expect(pending.pending).toEqual({ id: 1, kind: "comparison", step: 0 });
  expect(pending.current.result?.decision?.product.id).toBe("echo-quiet");
  expect(pending.shown.result).toBeNull();
  expect(pending.shown.needs).toEqual({});
  expect(pending.shown.messages.map(message => message.role)).toEqual(["user"]);
  expect(pending.shown.messages[0].text).toBe(request);
  expect(presentationSchedule(pending.pending)).toEqual([
    { afterMs: 400, step: 1 }, { afterMs: 1000, step: 2 }, { afterMs: 1600, step: 3 }, { afterMs: 2000, step: 4 },
  ]);
  const needs = presentationReducer(pending, { type: "tick", id: 1, step: 1 });
  expect(needs.shown.needs.budget?.value).toBe("300");
  expect(needs.shown.result).toBeNull();
  const models = presentationReducer(needs, { type: "tick", id: 1, step: 2 });
  expect(presentationStatus(models)).toContain("Compared 2 fictional product records");
  const sellers = presentationReducer(models, { type: "tick", id: 1, step: 3 });
  expect(presentationStatus(sellers)).toContain("Reviewed 3 seller records");
  const complete = finish(sellers);
  expect(complete.pending).toBeUndefined();
  expect(complete.shown).toBe(complete.current);
  expect(complete.shown.messages.map(message => message.role)).toEqual(["user", "assistant"]);
});

test("ticks are request-bound and monotonic, and reset prevents old results reappearing", () => {
  const first = send(initialPresentationState, request);
  const progressed = presentationReducer(first, { type: "tick", id: first.pending!.id, step: 2 });
  expect(presentationReducer(progressed, { type: "tick", id: first.pending!.id, step: 1 })).toBe(progressed);
  expect(presentationReducer(first, { type: "tick", id: first.pending!.id + 10, step: 4 })).toBe(first);
  const reset = act(progressed, { type: "reset" });
  expect(reset.pending).toBeUndefined();
  expect(reset.shown.result).toBeNull();
  const second = send(reset, request);
  expect(second.pending!.id).not.toBe(first.pending!.id);
  expect(presentationReducer(second, { type: "tick", id: first.pending!.id, step: 4 })).toBe(second);
  expect(presentationSchedule(undefined)).toEqual([]);
});

test("all mutating actions except reset or restore are rejected while presenting", () => {
  const pending = send(initialPresentationState, request);
  const actions: ShoppingAction[] = [
    { type: "send", text: "Comfort first" }, { type: "compare" },
    { type: "edit", key: "budget", fact: { value: "1", source: "confirmed", hard: true } },
    { type: "select", revision: pending.current.revision }, { type: "finish" },
  ];
  for (const action of actions) expect(act(pending, action)).toBe(pending);
  expect(pending.current.selected).toBe(false);
});

test("constraint changes invalidate selection immediately without exposing a replacement", () => {
  let state = finish(send(initialPresentationState, request));
  state = act(state, { type: "select", revision: state.current.revision });
  state = act(state, { type: "finish" });
  const pending = send(state, "Actually, comfort matters more");
  expect(pending.shown.result?.decision?.product.id).toBe("echo-quiet");
  expect(pending.current.result?.decision?.product.id).toBe("luma-air");
  expect(pending.shown.selected).toBe(false);
  expect(pending.shown.finished).toBe(false);
  expect(finish(pending).shown.result?.decision?.product.id).toBe("luma-air");
});

test("read-only questions use the short reply schedule and preserve approval and result", () => {
  let state = finish(send(initialPresentationState, request));
  state = act(state, { type: "select", revision: state.current.revision });
  const before = state.current;
  const pending = send(state, "Why this one, what do the reviews say, and can I return it?");
  expect(pending.pending?.kind).toBe("reply");
  expect(presentationSchedule(pending.pending)).toEqual([{ afterMs: 300, step: 4 }]);
  expect(presentationStatus(pending)).toBe("Preparing your reply…");
  for (const key of ["needs", "result", "revision", "choice", "selected", "finished"] as const) expect(pending.current[key]).toBe(before[key]);
  expect(pending.shown.selected).toBe(true);
  expect(pending.shown.messages.at(-1)?.role).toBe("user");
  expect(presentationReducer(pending, { type: "tick", id: pending.pending!.id, step: 1 })).toBe(pending);
  expect(finish(pending).shown.messages.at(-1)?.text).toContain("30-day returns");
});

test("clarification is quick and does not invent model or seller checks", () => {
  const pending = send(initialPresentationState, "Headphones");
  expect(pending.pending?.kind).toBe("reply");
  expect(pending.shown.messages).toHaveLength(1);
  expect(pending.shown.clarification).toBeNull();
  const done = finish(pending);
  expect(done.shown.clarification?.reply).toContain("mainly use");
  expect(done.shown.result).toBeNull();
});

test("no-match uses only recorded checks and preserves hard budget", () => {
  const pending = send(initialPresentationState, "Headphones for commuting, under SGD1. Comfort first.");
  expect(pending.pending?.kind).toBe("comparison");
  expect(pending.current.result?.status).toBe("no-match");
  const step = presentationReducer(pending, { type: "tick", id: pending.pending!.id, step: 3 });
  expect(presentationStatus(step)).toContain("0 models have a selectable offer within SGD1");
  expect(presentationStatus(step)).not.toContain("Reviewed");
  expect(finish(step).shown.needs.budget?.value).toBe("1");
});

test("error status never claims fabricated successful checks", () => {
  const state: PresentationState = {
    current: { ...initialShoppingState, result: { status: "error", decision: null, activity: [{ id: "comparison", state: "unavailable", label: "No result was verified.", evidence: [] }], message: "Comparison is unavailable." } },
    shown: initialShoppingState, nextId: 2, pending: { id: 1, kind: "comparison", step: 2 },
  };
  expect(presentationStatus(state)).toBe("Comparison is unavailable.");
});

test("restore cancels pending timing and shows the revalidated domain state immediately", () => {
  let saved = shoppingReducer(initialShoppingState, { type: "send", text: request });
  saved = shoppingReducer(saved, { type: "select", revision: saved.revision });
  const validated = restoreShoppingState(saveShoppingState(saved));
  const pending = send(initialPresentationState, request);
  const restored = act(pending, { type: "restore", state: validated });
  expect(restored.pending).toBeUndefined();
  expect(restored.current).toBe(validated);
  expect(restored.shown).toBe(validated);
  expect(restored.shown.selected).toBe(true);
  expect(presentationReducer(restored, { type: "tick", id: pending.pending!.id, step: 4 })).toBe(restored);
});

test("invalid or blank submission creates no presentation timer", () => {
  for (const text of ["", "   ", "a".repeat(2001)]) expect(send(initialPresentationState, text)).toBe(initialPresentationState);
  const state = act(initialPresentationState, { type: "edit", key: "budget", fact: { value: "-1", source: "confirmed", hard: true } });
  expect(state.pending).toBeUndefined();
  expect(state.shown.notice).toContain("positive budget");
});


test("refresh during presentation restores canonical completed output without presentation metadata", () => {
  const pending = send(initialPresentationState, request);
  const serialized = saveShoppingState(pending.current);
  expect(serialized).not.toContain('"pending"');
  const restored = act(pending, { type: "restore", state: restoreShoppingState(serialized) });
  expect(restored.pending).toBeUndefined();
  expect(restored.shown.result?.decision?.product.id).toBe("echo-quiet");
  expect(restored.shown.messages.at(-1)?.role).toBe("assistant");
});
