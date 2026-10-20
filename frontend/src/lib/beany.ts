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
export type Product = {
  id: string;
  name: string;
  category: string;
  brand: string;
  price: number;
  currency: string;
  merchant: string;
  attributes: string[];
  sizes: string[];
  description: string;
  trust: string;
};
export type Action = {
  id: string;
  product: Product;
  fingerprint: string;
  status: string;
  decision: "ALLOW" | "REVIEW" | "BLOCK";
  rules: { rule_id: string; decision: string; explanation: string }[];
  payment_method: string;
  shares_personal_data: boolean;
};
export type Session = {
  id: string;
  participant: string;
  created_at: string;
  mode: string;
  stage: string;
  brief: Record<string, Fact>;
  permissions: Permissions;
  messages: { role: string; text: string }[];
  recommendations: Product[];
  proposals: Action[];
  receipts: { id: string; product: Product; status: string }[];
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
