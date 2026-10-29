export type Review = { rating: number; title: string; text: string; date: string };
export type Merchant = {
  id: string;
  name: string;
  website: string;
  description: string;
  payment_methods: string[];
  return_policy: string;
  contact: string;
  review_count: number;
  review_rating: number | null;
  verified_business: boolean;
  requested_information: string[];
  external_payment: boolean;
  merchant_reviews?: Review[];
  checkout_note?: string;
};
export type MerchantRisk = {
  merchant_id: string;
  level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  score: number;
  explanation: string;
  evidence: { rule_id: string; evidence: string; weight: number }[];
  recommended_decision: string;
  config_version: string;
  config_hash: string;
};
export type Fact = {
  value: string;
  source: "confirmed" | "suggested" | "unspecified";
  hard: boolean;
};
export type Permissions = {
  require_approval: boolean;
  substitutions: boolean;
  share_personal_data: boolean;
  payment_methods: string[];
  restricted_merchants: string[];
  autonomy: "guided" | "balanced";
};
export type WebEvidence = {
  seller: {
    name: string;
    page_url: string;
    about: string;
    badges: string[];
    rating: string;
    business_name: string;
    registration_number: string;
    address: string;
    email: string;
    phone: string;
    ships_from: string;
  };
  return_policy: string;
  return_policy_url: string;
  refund_claims: string[];
  warranty: string;
  payment_methods: string[];
  off_platform_payment: string[];
  personal_data_requests: string[];
  urgency_claims: string[];
  agent_directed_text: string[];
  shipping: string;
  notices: string[];
};
export type Product = {
  source?: "catalogue" | "browser_use";
  source_url?: string;
  observed_at?: string;
  web_evidence?: WebEvidence | null;
  id: string;
  name: string;
  category: string;
  brand: string;
  price: number;
  currency: string;
  merchant: string;
  merchant_id: string;
  specifications: Record<string, string>;
  attributes: string[];
  sizes: string[];
  description: string;
  trust: string;
  rating?: number | null;
  rating_count?: number;
  reviews?: Review[];
};
export type Action = {
  id: string;
  product: Product;
  merchant_details: Merchant | null;
  risk: MerchantRisk | null;
  fingerprint: string;
  status: string;
  decision: "ALLOW" | "REVIEW" | "BLOCK";
  rules: { rule_id: string; decision: string; explanation: string }[];
  payment_method: string;
  shares_personal_data: boolean;
};
export type Session = {
  search_provider: "catalogue" | "browser_use";
  search_replay?: string;
  id: string;
  participant: string;
  scenario_id: string | null;
  created_at: string;
  mode: string;
  stage: string;
  brief: Record<string, Fact>;
  permissions: Permissions;
  messages: { role: string; text: string }[];
  recommendations: Product[];
  proposals: Action[];
  cart: { action: Action; brief: Record<string, Fact>; added_at: string }[];
  receipts: { id: string; proposal_id: string; timestamp: string; product: Product; status: string }[];
  events: { id: string; timestamp: string; kind: string; detail: string }[];
  suggestions: string[];
  clarification_count: number;
  intervention_count: number;
};
export const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
  key?: string,
): Promise<T> {
  const response = await fetch(base + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(key ? { "X-Research-Key": key } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw Error(
      typeof error.detail === "string"
        ? error.detail
        : "Please check your input and try again.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
