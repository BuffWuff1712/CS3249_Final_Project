import { base, type Action, type Fact, type Merchant, type MerchantRisk, type Product, type Session } from "./beany";

export type OfferPreview = {
  product: Product; model_key: string; merchant: Merchant | null;
  risk: MerchantRisk | null; decision: "ALLOW" | "REVIEW" | "BLOCK"; rules: Action["rules"];
};
export type ShopActivity = { id: string; label: string; state: "completed" | "unavailable"; evidence: string[] };
export type ShopView = {
  cart_review: { action: Action; error: string }[];
  session: Session; revision: number; offers: OfferPreview[]; current: Action | null;
  current_model_key: string | null; current_error: string; selected: Action | null; selection_error: string;
  seller_preference: "longer returns" | "lowest price";
  history: { message_index: number; proposal_id: string; activity: ShopActivity[] }[];
};
export class ShopRequestError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
export async function shopRequest(path = "", method = "GET", body?: unknown, signal?: AbortSignal): Promise<ShopView> {
  const response = await fetch(`${base}/shop/sessions${path}`, {
    method, signal, headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ShopRequestError(typeof data.detail === "string" ? data.detail : "The workspace request failed. Reload its state before trying again.", response.status);
  if (!data.session?.id || !["catalogue", "browser_use"].includes(data.session.search_provider) || !Array.isArray(data.offers)) throw new Error("The backend returned an invalid shopping workspace.");
  return data as ShopView;
}
export const shopFields = ["category", "usage", "budget", "currency", "features", "size", "preferred_brands", "excluded_brands", "merchants", "other"] as const;
export type ShopField = typeof shopFields[number];
export type ShopBrief = Record<string, Fact>;
export function money(product: Product) {
  return new Intl.NumberFormat("en-SG", { style: "currency", currencyDisplay: "code", currency: product.currency }).format(product.price);
}

export const SHOP_KEY = "beany-shop-backend-session";
export function rememberShop(view: ShopView) {
  localStorage.setItem(SHOP_KEY, view.session.id);
  localStorage.setItem("beany-session", view.session.id);
  let history: string[] = [];
  try { const saved = JSON.parse(localStorage.getItem("beany-history") || "[]"); if (Array.isArray(saved)) history = saved.filter(id => typeof id === "string"); } catch { /* Replace malformed browser history, not backend records. */ }
  localStorage.setItem("beany-history", JSON.stringify([...new Set([...history, view.session.id])]));
}
export async function activeShop() {
  const id = localStorage.getItem("beany-session") || localStorage.getItem(SHOP_KEY);
  if (!id) throw new Error("Start a shopping session before changing permissions or reviewing its cart.");
  const view = await shopRequest(`/${encodeURIComponent(id)}/adopt`, "POST", {});
  rememberShop(view);
  return view;
}

export type LiveShopActivity = Omit<ShopActivity, "state"> & { state: "running" | "completed" | "unavailable" };
export async function shopStream(path: string, body: unknown, signal: AbortSignal, onActivity: (activity: LiveShopActivity) => void): Promise<ShopView> {
  const response = await fetch(`${base}/shop/sessions${path}/stream`, {
    method: "POST", signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ShopRequestError(typeof data.detail === "string" ? data.detail : "The request could not start.", response.status);
  }
  if (!response.body) throw new Error("Live progress is unavailable. Reload the workspace before trying again.");
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = "", result: ShopView | undefined;
  function read(line: string) {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === "error") throw new Error(event.message || "The request could not finish.");
    if (event.type === "activity") {
      const activity = event.activity;
      if (typeof activity?.id !== "string" || typeof activity.label !== "string" || !["running", "completed", "unavailable"].includes(activity.state) || !Array.isArray(activity.evidence)) throw new Error("Invalid progress update. Reload the workspace.");
      onActivity(activity);
    }
    if (event.type === "result") {
      if (!event.view?.session?.id || !Array.isArray(event.view.offers)) throw new Error("Invalid workspace result.");
      result = event.view;
    }
  }
  try {
    while (true) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value, { stream: !chunk.done });
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) { read(buffer.slice(0, newline)); buffer = buffer.slice(newline + 1); }
      if (chunk.done) { read(buffer); break; }
    }
    if (!result) throw new Error("The connection ended before a result was confirmed. Reload the workspace before trying again.");
    return result;
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
