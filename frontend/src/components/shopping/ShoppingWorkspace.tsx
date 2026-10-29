"use client";
import { useEffect, useReducer, useState } from "react";
import type { NeedKey } from "@/lib/decision";
import { initialShoppingState, restoreShoppingState, saveShoppingState, shoppingReducer } from "@/lib/shoppingSession";
import { SCENARIO_VERSION } from "@/lib/shoppingFixtures";
import { Recommendation } from "./Recommendation";
import { NeedsSummary } from "./NeedsSummary";
import { ComparisonActivity } from "./ComparisonActivity";
import { PurchaseComposer } from "./PurchaseComposer";
import "./shopping.css";

export function ShoppingWorkspace() {
  const [text, setText] = useState("");
  const [state, dispatch] = useReducer(shoppingReducer, initialShoppingState);
  const [loaded, setLoaded] = useState(false);
  const [storageNotice, setStorageNotice] = useState("");
  const [requestedField, setRequestedField] = useState<{ key: NeedKey }>();
  const decision = state.result?.decision;
  const stale = state.comparedRevision !== state.revision;
  const hasBlockedOffer = !stale && decision?.concerns.some(concern => concern.blocked);
  function send(value: string) {
    dispatch({ type: "send", text: value });
    setText("");
    setRequestedField(undefined);
  }
  useEffect(() => {
    try {
      dispatch({ type: "restore", state: restoreShoppingState(localStorage.getItem("beany-cui-needs")) });
    } catch {
      setStorageNotice("Browser storage is unavailable. You can shop, but this decision will not survive refresh.");
    }
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (!loaded) return;
    try { localStorage.setItem("beany-cui-needs", saveShoppingState(state)); }
    catch { setStorageNotice("Browser storage is unavailable. You can shop, but this decision will not survive refresh."); }
  }, [state, loaded]);
  const edit = (key: NeedKey) => setRequestedField({ key });
  return <div className="shell cui-shell">
    <header><a className="brand" href="/shop">beany.</a><nav aria-label="Shopping navigation"><a href="/">Classic simulation</a><button onClick={() => { dispatch({ type: "reset" }); setRequestedField(undefined); setText(""); }}>Start fresh</button></nav></header>
    <main className="cui-workspace" id="shopping-main">
      <p className="eyebrow">SHOPPING DECISION ASSISTANT</p>
      <h1>Choose a product. Understand the decision.</h1>
      <p className="cui-purpose">Tell me your purchase intent. I’ll compare the product fit, spending limit and seller terms, explain the trade-off, and flag offers you should avoid.</p>
      <p className="cui-source">Fictional catalogue · No websites visited · No real orders or payments</p>
      <PurchaseComposer text={text} setText={setText} send={send} loaded={loaded} />
      {storageNotice && <p className="cui-notice cui-notice--review">{storageNotice}</p>}
      {state.notice && <p className="cui-notice">{state.notice}</p>}
      <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">{state.notice || (state.clarification ? state.clarification.reply : stale && state.result ? "Your needs changed. Compare again to update this recommendation." : state.change || (decision ? `Recommendation ready: ${decision.product.name} from ${decision.offer.merchant}.` : state.result?.message || "Ready to compare headphones or running shoes."))}{hasBlockedOffer ? " A seller offer was blocked for an outside-checkout payment request. The recommended offer remains selectable." : ""}</p>
      {!!Object.keys(state.needs).length && <NeedsSummary key={state.revision} needs={state.needs} requestedField={requestedField} edit={(key, fact) => {
        dispatch({ type: "edit", key, fact }); setRequestedField(undefined);
      }} />}
      {state.request && <p className="cui-request"><strong>You</strong><br />{state.request}</p>}
      {state.clarification && <section aria-label="Purchase clarification" className="cui-result">
        <p>{state.clarification.reply}</p>
        <div className="cui-actions">{state.clarification.options.map(option => <button key={option} onClick={() => send(option)}>{option}</button>)}</div>
      </section>}
      {state.change && !stale && <section aria-label="What changed" className="cui-change"><p>{state.change}</p></section>}
      {state.result && !stale && <ComparisonActivity activity={state.result.activity} />}
      {state.result && !decision && !stale && <section className="cui-result cui-decision-error" data-severity="error" aria-label={state.result.status === "error" ? "Comparison unavailable" : "No matching offer"}>
        <p className="cui-error-label">{state.result.status === "error" ? "Comparison failed" : "Decision blocked · constraints conflict"}</p>
        <h2>{state.result.status === "error" ? "Comparison unavailable" : "No matching offer"}</h2><p>{state.result.message}</p>
        <div className="cui-actions">
          <button onClick={() => dispatch({ type: "compare" })}>Retry comparison</button>
          {state.choice && <><button onClick={() => dispatch({ type: "compare", currentSeller: true })}>Keep current product</button><button onClick={() => dispatch({ type: "compare", allProducts: true })}>Compare other products</button></>}
          <button onClick={() => edit("budget")}>Change spending limit</button><button onClick={() => send(state.needs.category?.value === "Headphones" ? "Running shoes" : "Headphones")}>Explore another category</button>
        </div>
      </section>}
      {decision && <Recommendation key={`${decision.revision}-${decision.offer.id}`} decision={decision} stale={stale} edit={edit} selected={state.selected} reviseSeller={send} updatedSteps={state.updatedSteps} select={() => dispatch({ type: "select", revision: decision.revision })} />}
      {state.selected && decision && !stale && <section className="cui-result cui-selection" aria-label="Selected offer">
        <h2>{state.finished ? "Decision complete" : "Your selected offer"}</h2>
        <p><strong>{decision.product.name}</strong> · {decision.offer.merchant} · SGD{decision.offer.price}</p>
        <p>Variant: {decision.product.variant}. Priority: {state.needs.priority?.value}.</p>
        <p>{decision.reasons.find(reason => reason.id === "tradeoff")?.text}</p>
        {decision.concerns.filter(concern => concern.offerId === decision.offer.id).map(concern => <p key={concern.offerId}>{concern.observation} {concern.consequence}</p>)}
        <p>No order or payment has been created. You can revise this choice or finish.</p>
        <div className="cui-actions">{!state.finished && <button className="primary" onClick={() => dispatch({ type: "finish" })}>Finish decision</button>}<button onClick={() => edit("priority")}>Revise needs</button></div>
      </section>}
      {state.revision > 0 && stale && <button onClick={() => dispatch({ type: "compare" })}>Compare current needs</button>}
      <p className="cui-source">Scenario {SCENARIO_VERSION}. Headphone standard/new and running-shoe EU42/blue/new variants only. No fit, authenticity or safety certification is implied.</p>
    </main>
  </div>;
}
