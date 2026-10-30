"use client";
import { useEffect, useState } from "react";
import { request, Session } from "@/lib/beany";
export default function Receipts() {
  const [receipts, setReceipts] = useState<Session["receipts"]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    async function load() {
      const ids: string[] = JSON.parse(localStorage.getItem("beany-history") || "[]");
      const current = localStorage.getItem("beany-shop-backend-session") || localStorage.getItem("beany-session");
      if (current) ids.push(current);
      const results = await Promise.allSettled([...new Set(ids)].map(id => request<Session>(`/sessions/${id}`)));
      setReceipts(results.flatMap(r => r.status === "fulfilled" ? r.value.receipts : []).sort((a,b) => b.timestamp.localeCompare(a.timestamp)));
      if (results.some(r => r.status === "rejected")) setError("Some saved sessions could not be loaded. Your history may be incomplete.");
    }
    void load().catch(() => setError("Could not load purchase history.")).finally(() => setBusy(false));
  }, []);
  return <div className="shell">
    <header><a className="brand" href="/">Beany</a><nav className="header-actions" aria-label="Shopping navigation"><a className="header-action cart-action" href="/shop">Keep shopping</a><a className="header-action history-action" href="/cart">Cart</a></nav></header>
    <main className="settings-page"><h1>Purchase history</h1>
      <p>Simulated purchases from sessions saved in this browser. No real orders or payments were made.</p>
      {busy && <p role="status">Loading receipts…</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {!busy && !receipts.length && <p>No receipts yet.</p>}
      {receipts.map(r => <article className="panel boundaries" key={r.id}>
        <h2>Simulated receipt</h2><h3>{r.product.name}</h3><p>{r.product.merchant} · Quantity: 1</p>
        <p>{r.product.currency} {r.product.price.toFixed(2)}</p>
        <p>{new Date(r.timestamp).toLocaleString()}</p><p className="receipt-id">Receipt: {r.id}</p>
      </article>)}
    </main>
  </div>;
}
