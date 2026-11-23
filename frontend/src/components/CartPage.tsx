"use client";
import { productTitle } from "@/lib/productTitle";
import { useEffect, useRef, useState } from "react";
import { Action } from "@/lib/beany";
import { activeShop, rememberShop, shopRequest, SHOP_KEY, type ShopView } from "@/lib/shopBackend";
import { MerchantDetails } from "@/components/MerchantDetails";

type Row = { action: Action; error: string };
export function CartPage({ checkout = false }: { checkout?: boolean }) {
  const [workspace, setWorkspace] = useState<ShopView | null>(null);
  const [sid, setSid] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const carousel = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState(0);
  const drag = useRef<{ x: number; scrollLeft: number } | null>(null);
  function moveTo(index: number) {
    const list = carousel.current;
    const items = list?.querySelectorAll<HTMLElement>(".cart-card");
    if (!list || !items?.[index]) return;
    list.scrollTo({ left: items[index].offsetLeft - items[0].offsetLeft, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }
  useEffect(() => { if (position > Math.max(0, rows.length - 1)) setPosition(Math.max(0, rows.length - 1)); }, [rows.length, position]);
  async function load(id: string) {
    const next = await activeShop();
    if (next.session.id !== id) throw new Error("Session changed. Reload this page.");
    setWorkspace(next);
    let data = next.cart_review;
    const item = checkout ? new URLSearchParams(window.location.search).get("item") : null;
    if (item) data = data.filter(r => r.action.id === item);
    setRows(data);
  }
  useEffect(() => {
    const id = localStorage.getItem("beany-session") || localStorage.getItem(SHOP_KEY);
    if (!id) { setBusy(false); return; }
    setSid(id);
    void load(id).catch(e => setError(e.message)).finally(() => setBusy(false));
  }, []);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError("");
    try {
      if ((localStorage.getItem("beany-session") || localStorage.getItem(SHOP_KEY)) !== sid) throw new Error("Session changed. Reload this page.");
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
    <header><a className="brand" href="/">Beany</a><nav className="header-actions" aria-label="Shopping navigation"><a className="header-action cart-action" href="/shop">Keep shopping</a><a className="header-action history-action" href="/cart">Cart</a><a className="header-action history-action" href="/receipts">Purchase history</a></nav></header>
    <main className="settings-page">
      <h1>{checkout ? "Review checkout" : "Your cart"}</h1>
      <p>All purchases are simulated. Each item keeps the shopping requirements used when it was added. Current permissions apply at checkout. Budgets are per item, not a combined cart limit.</p>
      {error && <div role="alert" className="error">{error}<button disabled={busy} onClick={() => void act(() => load(sid))}>Reload cart</button></div>}
      {busy && <p role="status">Updating cart…</p>}
      {done && <div role="status" className="notice"><p>Simulated checkout complete. No real payment or order was made.</p><a className="action-link" href="/receipts">View receipts</a></div>}
      {!busy && !rows.length && !done && <div><p>Your cart has no items to review.</p><a className="action-link primary" href="/">Find something with Beany</a></div>}
      {!!rows.length && <div className="cart-carousel">
        {rows.length > 1 && <div className="cart-carousel-controls">
          <button aria-label="Previous item" disabled={busy || position === 0} onClick={() => moveTo(position - 1)}>←</button>
          <p className="cart-carousel-position" aria-live="polite">Item {position + 1} of {rows.length}</p>
          <button aria-label="Next item" disabled={busy || position >= rows.length - 1} onClick={() => moveTo(position + 1)}>→</button>
        </div>}
        <div ref={carousel} className="cart-carousel-track" role="region" aria-label="Cart items" tabIndex={0}
          onPointerDown={event => {
            if (rows.length < 2 || event.pointerType !== "mouse" || event.button !== 0 || (event.target as HTMLElement).closest("button, a, summary, input, select")) return;
            drag.current = { x: event.clientX, scrollLeft: event.currentTarget.scrollLeft };
            event.currentTarget.setPointerCapture(event.pointerId);
            event.currentTarget.dataset.dragging = "true";
            event.currentTarget.focus({ preventScroll: true });
            event.preventDefault();
          }}
          onPointerMove={event => { if (drag.current) event.currentTarget.scrollLeft = drag.current.scrollLeft + drag.current.x - event.clientX; }}
          onPointerUp={event => { drag.current = null; delete event.currentTarget.dataset.dragging; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); }}
          onLostPointerCapture={event => { drag.current = null; delete event.currentTarget.dataset.dragging; }}
          onPointerCancel={event => { drag.current = null; delete event.currentTarget.dataset.dragging; }}
          onKeyDown={event => {
            if (event.target !== event.currentTarget || rows.length < 2) return;
            const next = event.key === "ArrowRight" ? Math.min(rows.length - 1, position + 1) : event.key === "ArrowLeft" ? Math.max(0, position - 1) : event.key === "Home" ? 0 : event.key === "End" ? rows.length - 1 : null;
            if (next !== null) { event.preventDefault(); moveTo(next); }
          }}
          onScroll={event => {
            const list = event.currentTarget;
            const items = Array.from(list.querySelectorAll<HTMLElement>(".cart-card"));
            if (!items.length) return;
            const nearest = items.reduce((best, item, index) => Math.abs(item.offsetLeft - items[0].offsetLeft - list.scrollLeft) < Math.abs(items[best].offsetLeft - items[0].offsetLeft - list.scrollLeft) ? index : best, 0);
            setPosition(nearest);
          }}>
          {rows.map(({action: a, error: issue}) => <article className="panel boundaries cart-card" key={a.id} aria-current={rows[position]?.action.id === a.id ? "true" : undefined}>
            <h2>{productTitle(a.product)}</h2><p>{a.product.merchant} · Quantity: 1</p>
            <p className="price">{a.product.currency} {a.product.price.toFixed(2)}</p>
            <p>Payment: {a.payment_method} · Data sharing: {a.shares_personal_data ? "requested" : "none"}</p>
            <MerchantDetails action={a} replay={!!workspace?.session.search_replay} />
            <ul>{a.rules.map(r => <li key={r.rule_id}>{r.explanation}</li>)}</ul>
            {issue
              ? <div className="error" role="alert"><p>{issue}</p><button className="primary" disabled={busy} onClick={() => void act(async () => {
                  const next = await shopRequest(`/${sid}/cart/${a.id}`, "DELETE", { revision: workspace!.revision }); rememberShop(next); await load(sid);
                })}>Remove from cart</button></div>
              : <button disabled={busy} onClick={() => void act(async () => {
                  const next = await shopRequest(`/${sid}/cart/${a.id}`, "DELETE", { revision: workspace!.revision }); rememberShop(next); await load(sid);
                })}>Remove from cart</button>}
          </article>)}
        </div>
      </div>}
      {!!rows.length && <section className="panel boundaries">
        <h2>Total ({rows.length} items)</h2>
        {Object.entries(totals).map(([currency, total]) => <p key={currency}>{currency} {total.toFixed(2)}</p>)}
        <p>Catalogue prices only; no real shipping or tax calculation.</p>
        <button className="primary" disabled={busy || rows.some(r => !!r.error)} onClick={() => {
          if (!checkout) { window.location.assign("/checkout"); return; }
          void act(async () => {
            const next = await shopRequest(`/${sid}/cart/checkout`, "POST", {revision: workspace!.revision, items: rows.map(r => ({proposal_id: r.action.id, fingerprint: r.action.fingerprint}))});
            rememberShop(next); setDone(true); await load(sid);
          });
        }}>{checkout ? "Confirm simulated checkout" : "Review checkout"}</button>
      </section>}
    </main>
  </div>;
}
