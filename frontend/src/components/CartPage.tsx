"use client";
import { useEffect, useState } from "react";
import { Action, request, Session } from "@/lib/beany";
import { MerchantDetails } from "@/components/MerchantDetails";

type Row = { action: Action; error: string };
export function CartPage({ checkout = false }: { checkout?: boolean }) {
  const [sid, setSid] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  async function load(id: string) {
    let data = await request<Row[]>(`/sessions/${id}/cart/review`);
    const item = checkout ? new URLSearchParams(window.location.search).get("item") : null;
    if (item) data = data.filter(r => r.action.id === item);
    setRows(data);
  }
  useEffect(() => {
    const id = localStorage.getItem("beany-session");
    if (!id) { setBusy(false); return; }
    setSid(id);
    void load(id).catch(e => setError(e.message)).finally(() => setBusy(false));
  }, []);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError("");
    try {
      if (localStorage.getItem("beany-session") !== sid) throw new Error("Session changed. Reload this page.");
      await work();
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { setBusy(false); }
  }
  const totals = rows.reduce<Record<string, number>>((out, r) => {
    const p = r.action.product;
    out[p.currency] = Math.round(((out[p.currency] || 0) + p.price) * 100) / 100;
    return out;
  }, {});
  return <div className="shell">
    <header><a className="brand" href="/">Beany</a><nav className="header-actions" aria-label="Shopping navigation"><a className="header-action cart-action" href="/">Keep shopping</a><a className="header-action history-action" href="/cart">Cart</a><a className="header-action history-action" href="/receipts">Purchase history</a></nav></header>
    <main className="settings-page">
      <h1>{checkout ? "Review checkout" : "Your cart"}</h1>
      <p>All purchases are simulated. Each item keeps the shopping requirements used when it was added. Current permissions apply at checkout. Budgets are per item, not a combined cart limit.</p>
      {error && <p role="alert" className="error">{error}</p>}
      {busy && <p role="status">Updating cart…</p>}
      {done && <div role="status" className="notice"><p>Simulated checkout complete. No real payment or order was made.</p><a className="action-link" href="/receipts">View receipts</a></div>}
      {!busy && !rows.length && !done && <div><p>Your cart has no items to review.</p><a className="action-link primary" href="/">Find something with Beany</a></div>}
      {rows.map(({action: a, error: issue}) => <article className="panel boundaries" key={a.id}>
        <h2>{a.product.name}</h2><p>{a.product.merchant} · Quantity: 1</p>
        <p className="price">{a.product.currency} {a.product.price.toFixed(2)}</p>
        <p>Payment: {a.payment_method} · Data sharing: {a.shares_personal_data ? "requested" : "none"}</p>
        <MerchantDetails action={a} />
        <ul>{a.rules.map(r => <li key={r.rule_id}>{r.explanation}</li>)}</ul>
        {issue && <p className="error" role="alert">{issue}</p>}
        <button disabled={busy} onClick={() => void act(async () => {
          await request(`/sessions/${sid}/cart/${a.id}`, "DELETE"); await load(sid);
        })}>Remove {a.product.name}</button>
      </article>)}
      {!!rows.length && <section className="panel boundaries">
        <h2>Total ({rows.length} items)</h2>
        {Object.entries(totals).map(([currency, total]) => <p key={currency}>{currency} {total.toFixed(2)}</p>)}
        <p>Catalogue prices only; no real shipping or tax calculation.</p>
        <button className="primary" disabled={busy || rows.some(r => !!r.error)} onClick={() => {
          if (!checkout) { window.location.assign("/checkout"); return; }
          void act(async () => {
            await request<Session>(`/sessions/${sid}/cart/checkout`, "POST", {items: rows.map(r => ({proposal_id: r.action.id, fingerprint: r.action.fingerprint}))});
            setDone(true); await load(sid);
          });
        }}>{checkout ? "Confirm simulated checkout" : "Review checkout"}</button>
      </section>}
    </main>
  </div>;
}
