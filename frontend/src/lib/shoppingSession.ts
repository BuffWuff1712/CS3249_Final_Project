import type { Fact } from "./beany";
import type { ComparisonResult, NeedKey, Needs, Priority, SellerChoice, ShoppingDecision } from "./decision";
import { interpretPurchase, type IntentResult } from "./purchaseIntent";
import { compareNeeds } from "./shoppingScenario";
import { SCENARIO_VERSION, shoppingScenario } from "./shoppingFixtures";
import { categoryOf, priorities, validateNeed } from "./shoppingNeeds";

export type ShoppingState = {
  needs: Needs; revision: number; comparedRevision: number; questions: number;
  result: ComparisonResult | null; choice?: SellerChoice;
  clarification: IntentResult | null; request: string; change: string;
  selected: boolean; finished: boolean; notice: string;
  updatedSteps: string[];
};
export type ShoppingAction =
  | { type: "send"; text: string }
  | { type: "edit"; key: NeedKey; fact: Fact | null }
  | { type: "compare"; allProducts?: boolean; currentSeller?: boolean }
  | { type: "select"; revision: number }
  | { type: "finish" }
  | { type: "reset" }
  | { type: "restore"; state: ShoppingState };
export const initialShoppingState: ShoppingState = {
  needs: {}, revision: 0, comparedRevision: 0, questions: 0, result: null,
  clarification: null, request: "", change: "", selected: false, finished: false, notice: "",
  updatedSteps: [],
};

function explainChange(previous: ShoppingDecision | null | undefined, next: ShoppingDecision | null): string {
  if (!previous || !next) return "";
  const priority = next.needs.priority?.value as Priority;
  const advantage = next.product.advantages[priority] || "remains the closest represented fit";
  if (previous.product.id !== next.product.id) {
    const cause = next.productFixed ? "You requested this model for the seller comparison." : previous.needs.priority?.value !== next.needs.priority?.value ? `${next.needs.priority?.value} now comes first.` : "Your spending limit changed the eligible choices.";
    return `Updated: ${cause} I changed from ${previous.product.name} to ${next.product.name}.${next.productFixed ? "" : ` It ${advantage}.`}`;
  }
  if (previous.offer.id !== next.offer.id) return `Kept ${next.product.name}, variant ${next.product.variant}. Changed seller from ${previous.offer.merchant} to ${next.offer.merchant} at SGD${next.offer.price}, using your current needs and seller preference.`;
  return `${next.product.name} still wins for ${priority}: it ${advantage}. ${next.needs.budget ? `The SGD${next.offer.price} offer still fits your SGD${next.needs.budget.value} limit.` : "No spending limit is confirmed."}`;
}

function compare(state: ShoppingState, needs: Needs, revision: number, choice?: SellerChoice): ShoppingState {
  const category = categoryOf(needs);
  if (category && !needs.priority) needs = { ...needs, priority: { value: priorities[category][0], source: "suggested", hard: false } };
  const result = compareNeeds(needs, revision, choice);
  const previous = state.result?.decision;
  const next = result.decision;
  const updatedSteps = previous && next ? next.reasons.filter(reason => previous.reasons.find(old => old.id === reason.id)?.text !== reason.text).map(reason => reason.id) : [];
  if (previous && next && previous.needs.budget?.value !== next.needs.budget?.value) updatedSteps.push("eligibility");
  if (previous && next && (previous.product.id !== next.product.id || previous.offer.id !== next.offer.id || updatedSteps.includes("tradeoff"))) updatedSteps.push("choice");
  return {
    ...state, needs, revision, comparedRevision: revision, choice, result,
    clarification: null, change: explainChange(state.result?.decision, result.decision), selected: false, finished: false,
    notice: state.selected ? "Your previous selection was cleared. Review the updated result and select again." : "",
    updatedSteps,
  };
}

export function shoppingReducer(state: ShoppingState, action: ShoppingAction): ShoppingState {
  switch (action.type) {
    case "send": {
      const text = action.text.trim();
      if (!text || text.length > 2000) return state;
      if (/^(?:cancel|start over|fresh session)$/i.test(text)) return { ...initialShoppingState, notice: "Started a fresh decision." };
      const intent = interpretPurchase(text, state.needs, state.questions);
      const revision = state.revision + 1;
      if (!intent.ready) return {
        ...state, needs: intent.needs, revision, request: text, clarification: intent,
        questions: (intent.newTask ? 0 : state.questions) + 1, selected: false, finished: false, change: "", updatedSteps: [],
        notice: state.selected ? "Your previous selection was cleared while these needs are being clarified." : "",
      };
      const currentDecision = state.result?.decision;
      const namedProduct = shoppingScenario.products.find(product => text.toLowerCase().includes(product.name.toLowerCase()));
      const productId = namedProduct?.id || currentDecision?.product.id;
      const choice = intent.seller && productId && !intent.newTask ? {
        productId,
        ...(intent.seller === "another" && currentDecision ? { excludeOfferId: currentDecision.offer.id } : {}),
      } : undefined;
      return { ...compare(state, intent.needs, revision, choice), request: text, questions: intent.newTask ? 0 : state.questions };
    }
    case "edit": {
      if (action.fact) {
        const error = validateNeed(action.key, action.fact.value, state.needs);
        if (error) return { ...state, notice: error };
      }
      const needs = { ...state.needs };
      if (action.fact) needs[action.key] = action.fact;
      else delete needs[action.key];
      return { ...state, needs, revision: state.revision + 1, selected: false, finished: false, choice: undefined, clarification: null, change: "", updatedSteps: [],
        notice: state.selected ? "Your previous selection was cleared. Compare your updated needs and select again." : "" };
    }
    case "compare": return compare(state, state.needs, state.revision, action.allProducts ? undefined : action.currentSeller && state.choice ? { productId: state.choice.productId } : state.choice);
    case "select": {
      if (action.revision !== state.revision || state.comparedRevision !== state.revision || !state.result?.decision) return { ...state, notice: "That recommendation is no longer current. Compare your updated needs before selecting." };
      const checked = compareNeeds(state.needs, state.revision, state.choice).decision;
      if (!checked || checked.offer.id !== state.result.decision.offer.id || checked.offer.price !== state.result.decision.offer.price) return { ...state, selected: false, notice: "The offer changed. Compare again before selecting." };
      return { ...state, selected: true, finished: false, notice: "Offer selected. No order or payment has been created." };
    }
    case "finish": return state.selected && state.comparedRevision === state.revision ? { ...state, finished: true, notice: "Decision complete. No order or payment has been created." } : state;
    case "reset": return { ...initialShoppingState, notice: "Started a fresh decision." };
    case "restore": return action.state;
  }
}

export function saveShoppingState(state: ShoppingState): string {
  return JSON.stringify({
    version: SCENARIO_VERSION, needs: state.needs, revision: state.revision,
    compared: state.comparedRevision === state.revision && !!state.result,
    choice: state.choice, selectedOfferId: state.selected ? state.result?.decision?.offer.id : undefined,
    finished: state.finished,
    request: state.request,
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}
function readNeeds(value: unknown): Needs | null {
  if (!isRecord(value)) return null;
  const needs: Needs = {};
  const keys: NeedKey[] = ["category", "usage", "budget", "currency", "priority", "sellerPreference"];
  for (const [key, fact] of Object.entries(value)) {
    if (!keys.includes(key as NeedKey) || !isRecord(fact) || typeof fact.value !== "string" || typeof fact.hard !== "boolean" || !["confirmed", "suggested", "unspecified"].includes(String(fact.source))) return null;
    needs[key as NeedKey] = { value: fact.value, hard: fact.hard, source: fact.source as Fact["source"] };
  }
  for (const key of keys) {
    const fact = needs[key];
    // A pending USD clarification is a draft, never an eligible comparison.
    if (fact && !(key === "currency" && fact.value === "USD") && validateNeed(key, fact.value, needs)) return null;
  }
  return needs;
}

export function restoreShoppingState(serialized: string | null): ShoppingState {
  if (!serialized) return initialShoppingState;
  try {
    const saved: unknown = JSON.parse(serialized);
    if (!isRecord(saved) || !Number.isSafeInteger(saved.revision) || Number(saved.revision) < 0) throw new Error("Invalid saved revision");
    const needs = readNeeds(saved.needs);
    if (!needs) throw new Error("Invalid saved needs");
    const state = { ...initialShoppingState, needs, revision: Number(saved.revision), request: typeof saved.request === "string" ? saved.request.slice(0, 2000) : "" };
    if (saved.version !== SCENARIO_VERSION) return { ...state, notice: "The catalogue was updated. Compare your needs again; previous selections were cleared." };
    let choice: SellerChoice | undefined;
    if (saved.choice !== undefined) {
      const storedChoice = saved.choice;
      if (!isRecord(storedChoice) || typeof storedChoice.productId !== "string" || !shoppingScenario.products.some(product => product.id === storedChoice.productId)) throw new Error("Invalid product choice");
      const productId = storedChoice.productId;
      if (storedChoice.excludeOfferId !== undefined && (typeof storedChoice.excludeOfferId !== "string" || !shoppingScenario.offers.some(offer => offer.id === storedChoice.excludeOfferId && offer.productId === productId))) throw new Error("Invalid seller choice");
      choice = { productId, excludeOfferId: storedChoice.excludeOfferId as string | undefined };
    }
    if (!saved.compared) return { ...state, notice: state.revision ? "Restored your needs. Compare again to use the current catalogue." : "" };
    const restored = compare(state, needs, state.revision, choice);
    const selected = !!restored.result?.decision && saved.selectedOfferId === restored.result.decision.offer.id;
    return { ...restored, selected, finished: selected && saved.finished === true };
  } catch {
    return { ...initialShoppingState, notice: "Saved shopping state was invalid. Started a fresh decision." };
  }
}
