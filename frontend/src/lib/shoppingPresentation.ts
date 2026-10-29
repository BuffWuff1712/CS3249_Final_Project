import { initialShoppingState, shoppingReducer, type ShoppingAction, type ShoppingState } from "./shoppingSession";

export type PresentationState = {
  current: ShoppingState;
  shown: ShoppingState;
  pending?: { id: number; kind: "comparison" | "reply"; step: 0 | 1 | 2 | 3 };
  nextId: number;
};
export type PresentationAction =
  | { type: "action"; action: ShoppingAction }
  | { type: "tick"; id: number; step: 1 | 2 | 3 | 4 };

export const initialPresentationState: PresentationState = {
  current: initialShoppingState, shown: initialShoppingState, nextId: 1,
};

/** Timings describe presentation pacing, not the duration of a web search. */
export function presentationSchedule(pending: PresentationState["pending"]): { afterMs: number; step: 1 | 2 | 3 | 4 }[] {
  if (!pending) return [];
  return pending.kind === "reply" ? [{ afterMs: 300, step: 4 }] : [
    { afterMs: 400, step: 1 }, { afterMs: 1000, step: 2 },
    { afterMs: 1600, step: 3 }, { afterMs: 2000, step: 4 },
  ];
}

export function presentationReducer(state: PresentationState, action: PresentationAction): PresentationState {
  if (action.type === "tick") {
    if (!state.pending || action.id !== state.pending.id || action.step <= state.pending.step) return state;
    if (state.pending.kind === "reply" && action.step !== 4) return state;
    if (action.step === 4) return { ...state, shown: state.current, pending: undefined };
    return {
      ...state,
      shown: action.step >= 1 ? { ...state.shown, needs: state.current.needs, revision: state.current.revision } : state.shown,
      pending: { ...state.pending, step: action.step },
    };
  }
  const domainAction = action.action;
  if (state.pending && domainAction.type !== "reset" && domainAction.type !== "restore") return state;
  const current = shoppingReducer(state.current, domainAction);
  if (current === state.current) return state;
  const nextId = state.nextId + 1;
  if (domainAction.type === "reset" || domainAction.type === "restore") return { current, shown: current, nextId };
  const previousIds = new Set(state.current.messages.map(message => message.id));
  const newReplies = current.messages.some(message => message.role === "assistant" && !previousIds.has(message.id));
  if (!["send", "compare"].includes(domainAction.type) || !newReplies) return { current, shown: current, nextId };
  const comparison = current.result !== state.current.result && current.result !== null && current.comparedRevision === current.revision;
  return {
    current,
    shown: {
      ...state.current,
      messages: current.messages.filter(message => message.role === "user" || previousIds.has(message.id)),
      request: current.request,
      selected: current.selected,
      finished: current.finished,
      notice: "", change: "", clarification: null,
    },
    pending: { id: state.nextId, kind: comparison ? "comparison" : "reply", step: 0 },
    nextId,
  };
}

export function presentationStatus(state: PresentationState): string {
  const pending = state.pending;
  if (!pending) return state.current.messages.filter(message => message.role === "assistant").at(-1)?.text || state.current.notice || "Ready to compare headphones or running shoes.";
  if (pending.kind === "reply") return "Preparing your reply…";
  if (pending.step === 0) return "Preparing your local comparison…";
  if (pending.step === 1) return "Using your purchase needs and displayed assumptions.";
  const result = state.current.result;
  if (result?.status === "error") return result.message;
  const step = result?.activity.find(item => item.id === (pending.step === 2 ? "products" : "sellers"))
    || result?.activity.find(item => item.id === "eligibility");
  return step?.label || result?.message || "Preparing the comparison outcome…";
}
