import type {Session, Preferences, Scenario} from './contracts';
const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(base + path, {method, headers: {'Content-Type': 'application/json'}, ...(body !== undefined ? {body: JSON.stringify(body)} : {})});
  if (!res.ok) { const data = await res.json().catch(() => ({})); throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${res.status}). Check your input and try again.`); }
  return res.status === 204 ? undefined as T : res.json();
}
export const api = {
  create: () => request<Session>('/sessions', 'POST'),
  reset: (id: string) => request<void>(`/sessions/${id}`, 'DELETE'),
  preferences: (id: string, p: Preferences) => request<Session>(`/sessions/${id}/preferences`, 'PUT', p),
  chat: (id: string, text: string, scenario: Scenario) => request<Session>(`/sessions/${id}/messages`, 'POST', {text, scenario}),
  decide: (id: string, pid: string, action: 'approve' | 'reject' | 'refine', note = '') => request<Session>(`/sessions/${id}/proposals/${pid}/decision`, 'POST', {action, note}),
};
