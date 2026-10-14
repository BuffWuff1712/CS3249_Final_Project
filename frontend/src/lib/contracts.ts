// Mirrors backend/app/models.py. FastAPI /openapi.json is the canonical schema.
export type Preferences = {
  budget: number; currency: 'SGD' | 'USD'; allowed_merchants: string[]; restricted_merchants: string[];
  payment_methods: ('Demo Visa' | 'Demo Wallet')[]; substitutions: boolean; share_personal_data: boolean; autonomy: 'guided' | 'balanced';
};
export type Scenario = 'normal' | 'budget' | 'substitution' | 'merchant';
export type Proposal = { id: string; product: {id: string; name: string; price: number; currency: string; merchant: string; category: string; attributes: string[]; substitute: boolean}; payment_method: string; shares_personal_data: boolean; status: 'pending' | 'approved' | 'rejected' | 'superseded'; violations: string[]; explanation: string };
export type Session = { id: string; preferences: Preferences; messages: {role: 'user' | 'assistant'; text: string}[]; proposals: Proposal[]; activity: string[]; audit: {id: string; timestamp: string; kind: string; detail: string}[] };
