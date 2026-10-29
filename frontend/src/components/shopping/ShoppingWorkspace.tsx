"use client";
import { useEffect, useReducer, useRef, useState } from "react";
import type { NeedKey } from "@/lib/decision";
import { restoreShoppingState, saveShoppingState, type ShoppingAction } from "@/lib/shoppingSession";
import { initialPresentationState, presentationReducer, presentationSchedule, presentationStatus } from "@/lib/shoppingPresentation";
import { Recommendation } from "./Recommendation";
import { NeedsSummary } from "./NeedsSummary";
import { ComparisonActivity } from "./ComparisonActivity";
import { PurchaseComposer, PurchaseExamples } from "./PurchaseComposer";
import { ComparisonProgress } from "./ComparisonProgress";
import { InfoIcon, UserCircleIcon } from "./ShoppingIcons";
import "./shopping.css";

export function ShoppingWorkspace() {
  const [text, setText] = useState("");
  const [presentation, present] = useReducer(presentationReducer, initialPresentationState);
  const state = presentation.shown;
  const pending = presentation.pending;
  const busy = !!pending;
  function dispatch(action: ShoppingAction) { present({ type: "action", action }); }
  const [loaded, setLoaded] = useState(false);
  const [storageNotice, setStorageNotice] = useState("");
  const [requestedField, setRequestedField] = useState<{ key: NeedKey }>();
  const [source, setSource] = useState<{ id: string }>();
  const history = useRef<HTMLDivElement>(null);
  const selection = useRef<HTMLElement>(null);
  const decision = state.result?.decision;
  const stale = state.comparedRevision !== state.revision || (busy && presentation.current.revision !== state.revision);
  const hasBlockedOffer = !stale && decision?.concerns.some(concern => concern.blocked);
  const started = state.messages.length > 0 || !!Object.keys(state.needs).length;
  function send(value: string) {
    if (busy) return;
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
    try { localStorage.setItem("beany-cui-needs", saveShoppingState(presentation.current)); }
    catch { setStorageNotice("Browser storage is unavailable. You can shop, but this decision will not survive refresh."); }
  }, [presentation.current, loaded]);
  useEffect(() => {
    const container = history.current;
    if (!container) return;
    const target = busy ? container.querySelector(".cui-progress") : container.querySelector(".cui-conversation-history .cui-turn:last-child");
    if (target) container.scrollTop += target.getBoundingClientRect().top - container.getBoundingClientRect().top;
    else container.scrollTop = 0;
  }, [state.messages.at(-1)?.id, pending?.step]);
  useEffect(() => {
    if (!pending) return;
    const timers = presentationSchedule(pending).map(tick => window.setTimeout(() => present({ type: "tick", id: pending.id, step: tick.step }), tick.afterMs));
    return () => timers.forEach(timer => window.clearTimeout(timer));
  }, [pending?.id]);
  useEffect(() => {
    if (state.selected) selection.current?.scrollIntoView({ block: "nearest" });
  }, [state.selected, state.finished]);
  const edit = (key: NeedKey) => setRequestedField({ key });
  const latestReply = state.messages.filter(message => message.role === "assistant").at(-1);
  const sourceIds = new Set(decision ? [...decision.comparedProducts.map(product => product.id), ...decision.comparedOffers.map(offer => offer.id)] : []);
  return <div className="shell cui-shell">
    <a className="cui-skip" href="#shopping-main">Skip to shopping</a>
    <header><a className="brand" href="/shop">beany.</a><nav aria-label="Shopping navigation"><a href="/">Classic simulation</a><button onClick={reset}>Start fresh</button></nav></header>
    <main className="cui-workspace" id="shopping-main">
      <h1 className="sr-only">Shopping decision assistant</h1>
      <NeedsSummary key={state.revision} needs={state.needs} requestedField={requestedField} disabled={busy} edit={(key, fact) => {
        if (key === "category" && fact) send(fact.value);
        else dispatch({ type: "edit", key, fact });
        setRequestedField(undefined);
      }} />
      <nav aria-label="Workspace sections" className="cui-mobile-jumps"><a href="#shopping-conversation">Conversation</a><a href="#shopping-decision">Current decision</a></nav>
      <div className="cui-columns">
        <section className="cui-conversation" id="shopping-conversation" aria-label="Shopping conversation">
          <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">{busy ? presentationStatus(presentation) : `${state.notice} ${latestReply?.text || presentationStatus(presentation)}`}{!busy && hasBlockedOffer ? " A seller offer was blocked for an outside-checkout payment request. The recommended offer remains selectable." : ""}</p>
          <div ref={history} className="cui-chat-scroll" role="region" aria-label="Conversation history" tabIndex={0}>
            <div className="cui-turn cui-turn--assistant cui-greeting"><span className="cui-avatar" aria-hidden="true">b.</span><div className="cui-turn-body"><span className="sr-only">Beany</span><p>What are you shopping for? Tell me your budget and what matters most. We can compare headphones or running shoes.</p></div></div>
            {!started && <PurchaseExamples disabled={!loaded} choose={value => { setText(value); document.getElementById("cui-message")?.focus(); }} />}
            {storageNotice && <p className="cui-notice cui-notice--review">{storageNotice}</p>}
            {state.notice && <p className="cui-notice">{state.notice}</p>}
          <div className="cui-conversation-history">
            {state.messages.map(message => <div key={message.id} className={`cui-turn cui-turn--${message.role}`}>
              <span className="cui-avatar" aria-hidden="true">{message.role === "user" ? <UserCircleIcon weight="fill" /> : "b."}</span>
              <div className="cui-turn-body"><span className="sr-only">{message.role === "user" ? "You" : "Beany"}</span><p>{message.text}</p>
                {message.id === latestReply?.id && !!message.evidence.length && <div className="cui-message-sources">{message.evidence.filter(id => sourceIds.has(id) && !stale).map(id => <button key={id} className="cui-link" disabled={busy} onClick={() => setSource({ id })}>View {decision?.comparedProducts.find(product => product.id === id)?.name || decision?.comparedOffers.find(offer => offer.id === id)?.merchant} evidence</button>)}</div>}
              </div>
            </div>)}
          </div>
          {busy && <ComparisonProgress presentation={presentation} />}
          {!busy && decision && !stale && <p className="cui-comparison-story">{decision.reasons.find(reason => reason.id === "comparison")?.text} {decision.reasons.find(reason => reason.id === "seller")?.text}</p>}
          {!busy && state.clarification && <section aria-label="Purchase clarification" className="cui-clarification"><p>{state.clarification.reply}</p><div className="cui-actions">{state.clarification.options.map(option => <button key={option} onClick={() => send(option)}>{option}</button>)}</div></section>}
          {!busy && state.change && !stale && <section aria-label="What changed" className="cui-change"><p>{state.change}</p></section>}
          {!busy && state.result && !stale && <ComparisonActivity activity={state.result.activity} excludedCount={decision?.concerns.filter(concern => concern.blocked).length || 0} />}
          {!busy && decision && !stale && <div className="cui-participate"><InfoIcon weight="fill" aria-hidden="true" /><p>{decision.needs.sellerPreference?.value === "lowest price" ? "Price comes first. You can choose longer returns instead." : "Longer returns are the current tie-breaker. You can put price first."}</p><button onClick={() => send(decision.needs.sellerPreference?.value === "lowest price" ? "Longer returns first" : "Prefer lowest price")}>{decision.needs.sellerPreference?.value === "lowest price" ? "Prefer longer returns" : "Prefer lowest price"}</button></div>}
          </div>
          <PurchaseComposer busy={busy} text={text} setText={setText} send={send} loaded={loaded} started={started} />
        </section>
        <section className="cui-decision-column" id="shopping-decision" aria-label="Current decision">
          <fieldset className="cui-decision-frame" disabled={busy} aria-busy={busy}>
          {!state.result && <div className="cui-decision-empty"><h2>Your current match</h2><p>{busy ? "Your local comparison is being prepared." : "Your comparison will appear here."}</p><p className="cui-source">See why an option fits, what you give up, and which seller terms need attention.</p></div>}
          {state.result && !decision && !stale && <section className="cui-result cui-decision-error" data-severity="error" aria-label={state.result.status === "error" ? "Comparison unavailable" : "No matching offer"}>
            <p className="cui-error-label">{state.result.status === "error" ? "Comparison failed" : "Decision blocked · constraints conflict"}</p><h2>{state.result.status === "error" ? "Comparison unavailable" : "No matching offer"}</h2><p>{state.result.message}</p>
            <div className="cui-actions"><button onClick={() => dispatch({ type: "compare" })}>Retry comparison</button>{state.choice && <><button onClick={() => dispatch({ type: "compare", currentSeller: true })}>Keep current product</button><button onClick={() => dispatch({ type: "compare", allProducts: true })}>Compare other products</button></>}<button onClick={() => edit("budget")}>Change spending limit</button><button onClick={() => send(state.needs.category?.value === "Headphones" ? "Running shoes" : "Headphones")}>Explore another category</button></div>
          </section>}
          {decision && <Recommendation key={`${decision.revision}-${decision.offer.id}`} decision={decision} stale={stale} edit={edit} selected={state.selected} reviseSeller={send} updatedSteps={state.updatedSteps} source={source} select={() => dispatch({ type: "select", revision: decision.revision })} />}
          {state.selected && decision && !stale && <section ref={selection} className="cui-result cui-selection" aria-label="Selected offer"><h2>{state.finished ? "Decision complete" : "Your selected offer"}</h2><p><strong>{decision.product.name}</strong> · {decision.offer.merchant} · SGD{decision.offer.price}</p><p>Variant: {decision.product.variant}. Priority: {state.needs.priority?.value}.</p><p>{decision.reasons.find(reason => reason.id === "tradeoff")?.text}</p><p>No order or payment has been created. You can revise this choice or finish.</p><div className="cui-actions">{!state.finished && <button className="primary" onClick={() => dispatch({ type: "finish" })}>Finish decision</button>}<button onClick={() => edit("priority")}>Revise needs</button></div></section>}
          {state.revision > 0 && stale && <button onClick={() => dispatch({ type: "compare" })}>Compare current needs</button>}
          </fieldset>
          <p className="cui-source cui-disclosure">Fictional catalogue · No websites visited · No real orders or payments</p>
        </section>
      </div>
    </main>
  </div>;
}
