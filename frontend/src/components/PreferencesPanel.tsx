'use client';
import {useState} from 'react';
import type {Preferences} from '@/lib/contracts';
export function PreferencesPanel({value, busy, onSave}: {value: Preferences; busy: boolean; onSave: (p: Preferences) => Promise<void>}) {
  const [draft, setDraft] = useState(value);
  const set = <K extends keyof Preferences>(key: K, val: Preferences[K]) => setDraft(d => ({...d, [key]: val}));
  return <aside className="panel boundaries"><div className="eyebrow">YOUR GUARDRAILS</div><h2>Boundaries & permissions</h2><p className="muted">You set the limits. Your copilot checks every proposal.</p>
    <form onSubmit={e => {e.preventDefault(); void onSave(draft);}}><fieldset disabled={busy}>
    <label>Maximum budget<div className="budget-row"><select aria-label="Currency" value={draft.currency} onChange={e => set('currency', e.target.value as Preferences['currency'])}><option>SGD</option><option>USD</option></select><input aria-label="Maximum budget" type="number" required min="1" max="100000" step="0.01" value={draft.budget} onChange={e => set('budget', Number(e.target.value))}/></div></label>
    <label>Allowed merchants<input value={draft.allowed_merchants.join(', ')} onChange={e => set('allowed_merchants', e.target.value.split(',').map(s => s.trim()))}/><small>Comma-separated, exact names</small></label>
    <label>Restricted merchants<input value={draft.restricted_merchants.join(', ')} onChange={e => set('restricted_merchants', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}/><small>Restrictions take precedence</small></label>
    <div className="field-title">Fictional payment permissions</div>{(['Demo Visa', 'Demo Wallet'] as const).map(method => <label className="check" key={method}><input type="checkbox" checked={draft.payment_methods.includes(method)} onChange={e => set('payment_methods', e.target.checked ? [...draft.payment_methods, method] : draft.payment_methods.filter(m => m !== method))}/>{method}</label>)}
    <label className="check"><input type="checkbox" checked={draft.substitutions} onChange={e => set('substitutions', e.target.checked)}/>Allow product substitutions</label>
    <label className="check"><input type="checkbox" checked={draft.share_personal_data} onChange={e => set('share_personal_data', e.target.checked)}/>Allow simulated data sharing</label>
    <label>Intervention preference<select value={draft.autonomy} onChange={e => set('autonomy', e.target.value as Preferences['autonomy'])}><option value="guided">Guided · review each step</option><option value="balanced">Balanced · compare, then review</option></select></label><small>Both modes require approval. Guided shows each activity step; balanced groups the comparison.</small>
    <button className="primary save" type="submit">Save boundaries</button><p className="muted tiny">Changes apply after saving. Pending proposals are checked again.</p></fieldset></form>
  </aside>;
}
