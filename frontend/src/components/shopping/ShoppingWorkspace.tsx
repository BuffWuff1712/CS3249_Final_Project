"use client";
import { Fragment, useEffect, useRef, useState } from "react";
import { shopRequest, ShopRequestError, money, rememberShop, type ShopField, type ShopView } from "@/lib/shopBackend";
import type { Action, Fact } from "@/lib/beany";
import { BackendNeedsSummary } from "./BackendNeedsSummary";
import { BackendCurrentOffer, BackendProductEvidence, BackendRisk } from "./BackendOffer";
import { ComparisonActivity } from "./ComparisonActivity";
import { PurchaseComposer } from "./PurchaseComposer";
import { UserCircleIcon } from "./ShoppingIcons";
import { DotsThreeIcon } from "@phosphor-icons/react/dist/csr/DotsThree";
import "./shopping.css";

const STORAGE_KEY = "beany-shop-backend-session";
const examples = [
  ["Try headphones", "Find wireless noise-cancelling headphones under SGD200 for my commute."],
  ["Try running shoes", "Find cushioned running shoes under SGD200, size 42."],
  ["Try backpacks", "Find a backpack for university under SGD100."],
];
export function ShoppingWorkspace() {
  const [view, setView] = useState<ShopView | null>(null), [text, setText] = useState(""), [busy, setBusy] = useState(true);
  const [error, setError] = useState(""), [storageNotice, setStorageNotice] = useState(""), [uncertain, setUncertain] = useState(false);
  const [pendingText, setPendingText] = useState(""), [requested, setRequested] = useState<{ field: ShopField }>();
  const [allOffersOpen, setAllOffersOpen] = useState(false);
  const [historical, setHistorical] = useState<Action | null>(null), [evidenceId, setEvidenceId] = useState(0);
  const generation = useRef(0), controller = useRef<AbortController | null>(null), viewRef = useRef<ShopView | null>(null);
  const selection = useRef<HTMLElement>(null);
  const history = useRef<HTMLDivElement>(null), panel = useRef<HTMLElement>(null), currentRef = useRef<ShopView | null>(null);
  function keep(next: ShopView) {
    viewRef.current = next; setView(next);
    try { rememberShop(next); }
    catch { setStorageNotice("Browser storage is unavailable. Keep this page open; this session cannot be automatically restored."); }
  }
  async function load(fresh = false) {
    const id = ++generation.current; controller.current?.abort(); const abort = new AbortController(); controller.current = abort;
    setBusy(true); setError(""); setPendingText(""); setHistorical(null); setRequested(undefined); if (fresh) setText("");
    try {
      let sid: string | null = null; let legacy = false;
      if (!fresh) {
        try { sid = localStorage.getItem("beany-session") || localStorage.getItem(STORAGE_KEY); legacy = !!sid && sid !== localStorage.getItem(STORAGE_KEY); }
        catch { setStorageNotice("Browser storage is unavailable. A temporary workspace will be used."); }
      }
      let next: ShopView;
      if (sid) {
        try { next = await shopRequest(`/${encodeURIComponent(sid)}${legacy ? "/adopt" : ""}`, legacy ? "POST" : "GET", legacy ? {} : undefined, abort.signal); }
        catch (error) {
          if (!(error instanceof ShopRequestError) || error.status !== 404) throw error;
          next = await shopRequest("", "POST", {}, abort.signal);
        }
      } else next = await shopRequest("", "POST", {}, abort.signal);
      if (id !== generation.current) return;
      keep(next); setUncertain(false);
    } catch (error) {
      if (id === generation.current && !abort.signal.aborted) { setError(error instanceof Error ? error.message : "Cannot connect to the backend."); setUncertain(true); }
    } finally { if (id === generation.current) setBusy(false); }
  }
  useEffect(() => { void load(); return () => { generation.current++; controller.current?.abort(); }; }, []);
  async function mutate(path: string, data: Record<string, unknown> = {}, method = "POST", submitted = "") {
    if (busy || uncertain || !viewRef.current) return false;
    const before = viewRef.current; const id = ++generation.current;
    const abort = new AbortController(); controller.current = abort;
    setBusy(true); setError(""); setHistorical(null); setPendingText(submitted); setRequested(undefined);
    if (submitted) setText("");
    try {
      const next = await shopRequest(`/${before.session.id}/${path}`, method, { ...data, revision: before.revision }, abort.signal);
      if (id !== generation.current) return false;
      keep(next); setUncertain(false); return true;
    } catch (error) {
      if (id === generation.current && !abort.signal.aborted) {
        setError(error instanceof Error ? error.message : "The request failed. Reload the workspace state before trying again.");
        setUncertain(true); if (submitted) setText(current => current || submitted);
      }
      return false;
    } finally { if (id === generation.current) { setBusy(false); setPendingText(""); } }
  }
  const session = view?.session;
  const current = view?.current;
  const disabled = busy || uncertain;
  const selected = !!view?.selected;
  useEffect(() => {
    const region = history.current;
    if (!region) return;
    let target = busy ? region.querySelector(".cui-progress") : region.querySelector(".cui-conversation-history > .cui-turn:last-child");
    if (!busy && target?.previousElementSibling?.classList.contains("cui-activity")) target = target.previousElementSibling;
    if (target) region.scrollTop += target.getBoundingClientRect().top - region.getBoundingClientRect().top;
  }, [session?.messages.length, busy]);
  useEffect(() => {
    if (view?.current?.id && currentRef.current?.current?.id !== view.current.id && panel.current) panel.current.scrollTop = 0;
    currentRef.current = view;
  }, [view]);
  useEffect(() => { if (view?.selected) selection.current?.scrollIntoView({ block: "nearest" }); }, [view?.selected?.id]);
  const latestReply = session?.messages.filter(message => message.role === "assistant").at(-1)?.text;
  const alternativesByModel = new Map<string, NonNullable<ShopView["offers"]>[number]>();
  for (const offer of view?.offers || []) {
    if (offer.model_key === view?.current_model_key) continue;
    const previous = alternativesByModel.get(offer.model_key);
    if (!previous || previous.decision === "BLOCK" && offer.decision !== "BLOCK") alternativesByModel.set(offer.model_key, offer);
  }
  const alternativeModels = [...alternativesByModel.values()];
  const sellers = (view?.offers || []).filter(offer => offer.model_key === view?.current_model_key && offer.product.id !== current?.product.id);
  const receipt = session?.stage === "completed" ? session.receipts.at(-1) : undefined;
  const inspect = (action: Action) => { setHistorical(action); if (panel.current) panel.current.scrollTop = 0; };
  const finish = () => { if (view?.selected) void mutate("finish", { proposal_id: view.selected.id, fingerprint: view.selected.fingerprint }); };
  return <div className="shell cui-shell">
    <a className="cui-skip" href="#shopping-main">Skip to shopping</a>
    <header><a className="brand" href="/">beany.</a><nav aria-label="Shopping navigation"><a href="/cart">Cart ({session?.cart.length || 0})</a><a href="/receipts">Purchase history</a><button disabled={disabled || !session} aria-label="Open settings" onClick={() => window.location.assign("/settings")}>Settings</button><button onClick={() => void load(true)}>Start fresh</button></nav></header>
    <main className="cui-workspace" id="shopping-main"><h1 className="sr-only">Shopping decision assistant</h1>
      <BackendNeedsSummary brief={session?.brief || {}} busy={disabled} requested={requested} edit={(field: ShopField, fact: Fact | null) => mutate("brief", { field, fact }, "PUT")} />
      <nav className="cui-mobile-jumps" aria-label="Workspace sections"><a href="#shopping-conversation">Conversation</a><a href="#shopping-decision">Current decision</a></nav>
      <div className="cui-columns"><section className="cui-conversation" id="shopping-conversation" aria-label="Shopping conversation">
        <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">{busy ? "Working on your request with the configured product source…" : error || latestReply || "Ready to compare products."}</p>
        <div ref={history} className="cui-chat-scroll" role="region" aria-label="Conversation history" tabIndex={0}>
          {storageNotice && <p className="cui-notice cui-notice--review">{storageNotice}</p>}
          {error && <div role="alert" className="cui-input-error"><p>{error}</p><p>Your last confirmed server state is shown. Selection and checkout are paused until it is reloaded.</p><button disabled={busy} onClick={() => void load()}>Reload workspace</button></div>}
          <div className="cui-conversation-history">
            {session?.messages.slice(-60).map((message, offset) => {
              const index = Math.max(0, session.messages.length - 60) + offset;
              const comparison = view?.history.find(item => item.message_index === index);
              const source = comparison && session.proposals.find(action => action.id === comparison.proposal_id);
              return <Fragment key={`${session.id}-${index}`}>
                {comparison && <ComparisonActivity activity={comparison.activity} />}
                <div className={`cui-turn cui-turn--${message.role}`}><span className="cui-avatar" aria-hidden="true">{message.role === "user" ? <UserCircleIcon weight="fill" /> : "b."}</span><div className="cui-turn-body"><span className="sr-only">{message.role === "user" ? "You" : "Beany"}</span><p>{message.text}</p>{source && <button className="cui-link cui-history-source" onClick={() => inspect(source)}>View evidence for this comparison</button>}</div></div>
              </Fragment>;
            })}
          </div>
          {!busy && session?.messages.length === 1 && <div className="cui-examples"><span>Editable examples</span>{examples.map(([label, example]) => <button key={label} disabled={disabled} onClick={() => { setText(example); document.getElementById("cui-message")?.focus(); }}>{label}</button>)}</div>}
          {pendingText && <div className="cui-turn cui-turn--user"><span className="cui-avatar" aria-hidden="true"><UserCircleIcon /></span><div className="cui-turn-body"><span className="sr-only">You</span><p>{pendingText}</p></div></div>}
          {busy && <div className="cui-turn cui-progress" aria-label="Backend request in progress"><span className="cui-avatar" aria-hidden="true">b.</span><div className="cui-turn-body"><p className="cui-progress-label"><DotsThreeIcon className="cui-typing" aria-hidden="true" />Working on your request…</p><small>Waiting for the backend. Completed checks appear only after it responds.</small></div></div>}
          {!busy && !!session?.suggestions.length && <div className="cui-actions cui-suggestions" aria-label="Suggested replies">{session.suggestions.map(suggestion => <button key={suggestion} disabled={disabled} onClick={() => void mutate("messages", { text: suggestion }, "POST", suggestion)}>{suggestion}</button>)}</div>}
          {!busy && session && !current && !receipt && !!session.brief.category && <div className="cui-actions"><button disabled={disabled} onClick={() => void mutate("compare")}>Compare current needs</button></div>}
        </div>
        {session && <div className="cui-actions"><button disabled={disabled || session.stage === "cancelled"} onClick={() => void mutate("cancel")}>Cancel shopping task</button></div>}
        <PurchaseComposer text={text} setText={setText} send={value => void mutate("messages", { text: value }, "POST", value)} loaded={!!session} busy={disabled} started={!!session && session.messages.length > 1} />
      </section>
      <section ref={panel} className="cui-decision-column" id="shopping-decision" aria-label="Current decision">
        <fieldset className="cui-decision-frame" disabled={disabled} aria-busy={busy}>
          {historical ? <section aria-label="Historical comparison evidence"><h2>Evidence from this comparison</h2><p className="cui-source">Historical proposal snapshot. This is not a current selectable offer.</p><button onClick={() => setHistorical(null)}>Back to current decision</button><BackendRisk merchant={historical.merchant_details} risk={historical.risk} decision={historical.decision} rules={historical.rules} /><BackendProductEvidence replay={!!session?.search_replay} product={historical.product} merchant={historical.merchant_details} /></section> : <>
          {!current && <div className="cui-decision-empty"><h2>Your current match</h2><p>{busy ? "Waiting for the backend's comparison." : session?.stage === "no_match" ? "No eligible offer was proposed. Your constraints were kept." : receipt ? "Your simulated decision is complete." : "Your comparison will appear here."}</p><p className="cui-source">Compare products, inspect seller terms and website reputation, then choose explicitly.</p></div>}
          {view?.current_error && <div className="cui-stale" role="alert"><p>{view.current_error}</p><button disabled={disabled} onClick={() => void mutate("compare")}>Compare current needs</button></div>}
          {current && <BackendCurrentOffer replay={!!session?.search_replay} action={current} selected={selected} disabled={disabled} selectionInvalid={!!view?.current_error} evidenceId={evidenceId} select={() => void mutate("select", { proposal_id: current.id, fingerprint: current.fingerprint })} seller={() => void mutate("seller")} addCart={() => void mutate("cart", { proposal_id: current.id, fingerprint: current.fingerprint })} reject={() => void mutate("reject", { proposal_id: current.id, fingerprint: current.fingerprint })} alternative={() => void mutate("alternative")} edit={() => setRequested({ field: "features" })} />}
          {selected && <section ref={selection} className="cui-selection" aria-label="Selected offer"><h2>Your selected offer</h2><p>{view?.selected?.product.name} · {view?.selected && money(view.selected.product)}</p><p>No receipt, order or payment has been created. Review the backend's terms and risk findings before finishing.</p>{view?.selection_error && <p role="alert">{view.selection_error}</p>}<button className="primary" disabled={disabled || !!view?.selection_error} onClick={finish}>Finish decision</button></section>}
          {receipt && <section className="cui-selection" aria-label="Simulated receipt"><h2>Decision complete</h2><p>{receipt.product.name} · {money(receipt.product)}</p><p>Receipt: {receipt.id}</p><p>No real order or payment was created.</p></section>}
          {current && <section className="cui-seller-reason" aria-label="Seller preference"><p>Compare sellers of this exact model and variant.</p><div className="cui-actions">{(["longer returns", "lowest price"] as const).map(preference => <button key={preference} disabled={disabled} aria-pressed={view?.seller_preference === preference} onClick={() => void mutate("seller", { preference })}>{preference === "longer returns" ? "Prefer longer returns" : "Prefer lowest price"}</button>)}</div></section>}
          {current && !!alternativeModels.length && <section className="cui-alternative" aria-label={session?.search_provider === "browser_use" ? "Other listings" : "Other models"}><h2>{session?.search_provider === "browser_use" ? "Other listings" : "Other models"}</h2>{alternativeModels.slice(0, 3).map(offer => <div className="cui-catalogue-offer" key={offer.product.id}><h3>{offer.product.name}</h3><p>{money(offer.product)} · {offer.product.merchant}</p><p className="cui-source">{session?.search_provider === "browser_use" ? "Separate listing; model and variant identity need checking. Captured claims are unverified." : "Different model. Specifications are catalogue claims; no subjective fit guarantee."}</p><button disabled={disabled || offer.decision === "BLOCK"} onClick={() => void mutate("propose", { product_id: offer.product.id })}>Compare {offer.product.name}</button></div>)}</section>}
          {!!sellers.length && <section className="cui-alternative" aria-label="Sellers of the same model"><h2>Other sellers of this model</h2>{sellers.map(offer => <div className="cui-catalogue-offer" key={offer.product.id}><h3>{offer.product.merchant}</h3><p>{money(offer.product)}</p><BackendRisk merchant={offer.merchant} risk={offer.risk} decision={offer.decision} rules={offer.rules} /><button disabled={disabled || offer.decision === "BLOCK"} onClick={() => void mutate("propose", { product_id: offer.product.id })}>Compare offer from {offer.product.merchant}</button></div>)}</section>}
          {!!view?.offers.length && <details onToggle={event => setAllOffersOpen(event.currentTarget.open)}><summary>Compare all {view.offers.length} eligible offers</summary>{allOffersOpen && view.offers.map(offer => <section key={offer.product.id} className="cui-catalogue-offer" aria-label={`Catalogue offer ${offer.product.id}`}><h3>{offer.product.name}</h3><p>{money(offer.product)} · {offer.product.merchant}</p><BackendRisk merchant={offer.merchant} risk={offer.risk} decision={offer.decision} rules={offer.rules} /><details><summary>View product and seller evidence</summary><BackendProductEvidence replay={!!session?.search_replay} product={offer.product} merchant={offer.merchant} /></details><button disabled={disabled || offer.decision === "BLOCK"} onClick={() => void mutate("propose", { product_id: offer.product.id })}>Compare this offer</button></section>)}</details>}
          </>}
          {session && <details className="cui-oversight"><summary>Shopping activity · {session.stage.replaceAll("_", " ")}</summary><ol>{session.events.filter(event => ["search", "intervention", "approve", "reject", "simulated_checkout", "cancel", "brief_edit", "permissions", "cart_added", "cart_removed", "cart_checkout"].includes(event.kind)).slice(-12).map(event => <li key={event.id}>{({ search: "Compared matching products", intervention: "Requested your review", approve: "You approved this action", reject: "You rejected this action", simulated_checkout: "Created a simulated receipt", cancel: "Shopping task cancelled", brief_edit: "Updated your shopping brief", permissions: "Updated permissions", cart_added: "Saved an item to cart", cart_removed: "Removed an item from cart", cart_checkout: "Checked out a cart item" } as Record<string, string>)[event.kind]}</li>)}</ol></details>}
        </fieldset>
        <p className="cui-source cui-disclosure">{session ? session.search_replay ? "Saved study listing replay · No websites visited" : session.search_provider === "browser_use" ? "Browser Use live search · Unverified listings" : "Local fictional catalogue · No websites visited" : "Connecting to backend"} · {session?.mode === "mock" ? "Mock LLM: offline test responses" : "Configured backend model conversation"} · No real orders or payments</p>
      </section></div>
    </main>
  </div>;
}
