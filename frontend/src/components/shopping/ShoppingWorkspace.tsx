"use client";
import { useEffect, useReducer, useRef, useState } from "react";
import type { NeedKey } from "@/lib/decision";
import { initialShoppingState, restoreShoppingState, saveShoppingState, shoppingReducer } from "@/lib/shoppingSession";
import { Recommendation } from "./Recommendation";
import { NeedsSummary } from "./NeedsSummary";
import { ComparisonActivity } from "./ComparisonActivity";
import { PurchaseComposer } from "./PurchaseComposer";
import { InfoIcon, UserCircleIcon } from "./ShoppingIcons";
import "./shopping.css";

export function ShoppingWorkspace() {
  const [text, setText] = useState("");
  const [state, dispatch] = useReducer(shoppingReducer, initialShoppingState);
  const [loaded, setLoaded] = useState(false);
  const [storageNotice, setStorageNotice] = useState("");
  const [requestedField, setRequestedField] = useState<{ key: NeedKey }>();
  const [source, setSource] = useState<{ id: string }>();
  const history = useRef<HTMLDivElement>(null);
  const decision = state.result?.decision;
  const stale = state.comparedRevision !== state.revision;
  const hasBlockedOffer = !stale && decision?.concerns.some(concern => concern.blocked);
  const started = state.messages.length > 0 || !!Object.keys(state.needs).length;
  function send(value: string) {
    dispatch({ type: "send", text: value }); setText(""); setRequestedField(undefined); setSource(undefined);
  }
  function reset() {
    dispatch({ type: "reset" }); setRequestedField(undefined); setText(""); setSource(undefined);
  }
  useEffect(() => {
    try { dispatch({ type: "restore", state: restoreShoppingState(localStorage.getItem("beany-cui-needs")) }); }
    catch { setStorageNotice("Browser storage is unavailable. You can shop, but this decision will not survive refresh."); }
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (!loaded) return;
    try { localStorage.setItem("beany-cui-needs", saveShoppingState(state)); }
    catch { setStorageNotice("Browser storage is unavailable. You can shop, but this decision will not survive refresh."); }
  }, [state, loaded]);
  useEffect(() => {
    if (history.current) history.current.scrollTop = history.current.scrollHeight;
  }, [state.messages.at(-1)?.id]);
  const edit = (key: NeedKey) => setRequestedField({ key });
  const latestReply = state.messages.filter(message => message.role === "assistant").at(-1);
  const sourceIds = new Set(decision ? [...decision.comparedProducts.map(product => product.id), ...decision.comparedOffers.map(offer => offer.id)] : []);
  return <div className="shell cui-shell">
    <a className="cui-skip" href="#shopping-main">Skip to shopping</a>
    <header><a className="brand" href="/shop">beany.</a><nav aria-label="Shopping navigation"><a href="/">Classic simulation</a><button onClick={reset}>Start fresh</button></nav></header>
    <main className="cui-workspace" id="shopping-main">
      <h1 className="sr-only">Shopping decision assistant</h1>
      {!!Object.keys(state.needs).length ? <NeedsSummary key={state.revision} needs={state.needs} requestedField={requestedField} edit={(key, fact) => {
        if (key === "category" && fact) send(fact.value);
        else dispatch({ type: "edit", key, fact });
        setRequestedField(undefined);
      }} /> : <div className="cui-empty-brief"><strong>Your needs</strong><span>Start with what you’re buying. You can refine the details together.</span></div>}
      <nav aria-label="Workspace sections" className="cui-mobile-jumps"><a href="#shopping-conversation">Conversation</a><a href="#shopping-decision">Current decision</a></nav>
      <div className="cui-columns">
        <section className="cui-conversation" id="shopping-conversation" aria-label="Shopping conversation">
          {!started && <div className="cui-welcome"><p className="eyebrow">A little help choosing</p><h2>What are you shopping for?</h2><p>Tell me what you need. We’ll compare the options, look at the trade-offs, and keep you in control.</p><p className="cui-source">Compare headphones or running shoes from fictional local records.</p></div>}
          {storageNotice && <p className="cui-notice cui-notice--review">{storageNotice}</p>}
          {state.notice && <p className="cui-notice">{state.notice}</p>}
          <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">{state.notice} {latestReply?.text || (state.clarification ? state.clarification.reply : stale && state.result ? "Your needs changed. Compare again to update this recommendation." : decision ? `Recommendation ready: ${decision.product.name} from ${decision.offer.merchant}.` : "Ready to compare headphones or running shoes.")}{hasBlockedOffer ? " A seller offer was blocked for an outside-checkout payment request. The recommended offer remains selectable." : ""}</p>
          <div ref={history} className="cui-conversation-history" role="region" aria-label="Conversation history" tabIndex={started ? 0 : undefined}>
            {state.messages.map(message => <div key={message.id} className={`cui-turn cui-turn--${message.role}`}>
              <span className="cui-avatar" aria-hidden="true">{message.role === "user" ? <UserCircleIcon weight="fill" /> : "b."}</span>
              <div className="cui-turn-body"><span className="sr-only">{message.role === "user" ? "You" : "Beany"}</span><p>{message.text}</p>
                {message.id === latestReply?.id && !!message.evidence.length && <div className="cui-message-sources">{message.evidence.filter(id => sourceIds.has(id) && !stale).map(id => <button key={id} className="cui-link" onClick={() => setSource({ id })}>View {decision?.comparedProducts.find(product => product.id === id)?.name || decision?.comparedOffers.find(offer => offer.id === id)?.merchant} evidence</button>)}</div>}
              </div>
            </div>)}
          </div>
          {decision && !stale && <p className="cui-comparison-story">{decision.reasons.find(reason => reason.id === "comparison")?.text} {decision.reasons.find(reason => reason.id === "seller")?.text}</p>}
          {state.clarification && <section aria-label="Purchase clarification" className="cui-clarification"><p>{state.clarification.reply}</p><div className="cui-actions">{state.clarification.options.map(option => <button key={option} onClick={() => send(option)}>{option}</button>)}</div></section>}
          {state.change && !stale && <section aria-label="What changed" className="cui-change"><p>{state.change}</p></section>}
          {state.result && !stale && <ComparisonActivity activity={state.result.activity} excludedCount={decision?.concerns.filter(concern => concern.blocked).length || 0} />}
          {decision && !stale && <div className="cui-participate"><InfoIcon weight="fill" aria-hidden="true" /><p>{decision.needs.sellerPreference?.value === "lowest price" ? "Price comes first. You can choose longer returns instead." : "Longer returns are the current tie-breaker. You can put price first."}</p><button onClick={() => send(decision.needs.sellerPreference?.value === "lowest price" ? "Longer returns first" : "Prefer lowest price")}>{decision.needs.sellerPreference?.value === "lowest price" ? "Prefer longer returns" : "Prefer lowest price"}</button></div>}
          <PurchaseComposer text={text} setText={setText} send={send} loaded={loaded} started={started} />
        </section>
        <section className="cui-decision-column" id="shopping-decision" aria-label="Current decision">
          {!state.result && <div className="cui-decision-empty"><h2>Your current match</h2><p>Your comparison will appear here.</p><p className="cui-source">See why an option fits, what you give up, and which seller terms need attention.</p></div>}
          {state.result && !decision && !stale && <section className="cui-result cui-decision-error" data-severity="error" aria-label={state.result.status === "error" ? "Comparison unavailable" : "No matching offer"}>
            <p className="cui-error-label">{state.result.status === "error" ? "Comparison failed" : "Decision blocked · constraints conflict"}</p><h2>{state.result.status === "error" ? "Comparison unavailable" : "No matching offer"}</h2><p>{state.result.message}</p>
            <div className="cui-actions"><button onClick={() => dispatch({ type: "compare" })}>Retry comparison</button>{state.choice && <><button onClick={() => dispatch({ type: "compare", currentSeller: true })}>Keep current product</button><button onClick={() => dispatch({ type: "compare", allProducts: true })}>Compare other products</button></>}<button onClick={() => edit("budget")}>Change spending limit</button><button onClick={() => send(state.needs.category?.value === "Headphones" ? "Running shoes" : "Headphones")}>Explore another category</button></div>
          </section>}
          {decision && <Recommendation key={`${decision.revision}-${decision.offer.id}`} decision={decision} stale={stale} edit={edit} selected={state.selected} reviseSeller={send} updatedSteps={state.updatedSteps} source={source} select={() => dispatch({ type: "select", revision: decision.revision })} />}
          {state.selected && decision && !stale && <section className="cui-result cui-selection" aria-label="Selected offer"><h2>{state.finished ? "Decision complete" : "Your selected offer"}</h2><p><strong>{decision.product.name}</strong> · {decision.offer.merchant} · SGD{decision.offer.price}</p><p>Variant: {decision.product.variant}. Priority: {state.needs.priority?.value}.</p><p>{decision.reasons.find(reason => reason.id === "tradeoff")?.text}</p><p>No order or payment has been created. You can revise this choice or finish.</p><div className="cui-actions">{!state.finished && <button className="primary" onClick={() => dispatch({ type: "finish" })}>Finish decision</button>}<button onClick={() => edit("priority")}>Revise needs</button></div></section>}
          {state.revision > 0 && stale && <button onClick={() => dispatch({ type: "compare" })}>Compare current needs</button>}
          <p className="cui-source cui-disclosure">Fictional catalogue · No websites visited · No real orders or payments</p>
        </section>
      </div>
    </main>
  </div>;
}
