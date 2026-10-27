"use client";
import { useEffect, useState } from "react";
import type { ShoppingDecision, Needs } from "@/lib/decision";
import { createDecision } from "@/lib/shoppingScenario";
import { interpretPurchase } from "@/lib/purchaseIntent";
import { Recommendation } from "./Recommendation";
import { NeedsSummary } from "./NeedsSummary";
import "./shopping.css";

export function ShoppingWorkspace() {
  const [text, setText] = useState("");
  const [decision, setDecision] = useState<ShoppingDecision | null>(null);
  const [request, setRequest] = useState("");
  const [needs, setNeeds] = useState<Needs>({});
  const [revision, setRevision] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [questions, setQuestions] = useState(0);
  const [clarification, setClarification] = useState<{ reply: string; options: string[] } | null>(null);
  function send(value: string) {
    if (!value.trim()) return;
    const result = interpretPurchase(value.trim(), needs, questions);
    setRequest(value.trim()); setNeeds(result.needs); setRevision(revision + 1); setText("");
    if (result.ready) {
      setDecision(createDecision(result.needs, revision + 1)); setClarification(null);
    } else {
      setQuestions(questions + 1); setClarification(result);
    }
  }
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("beany-cui-needs") || "null");
      if (saved && Number.isInteger(saved.revision) && saved.revision > 0 && saved.needs &&
          Object.entries(saved.needs).every(([key, v]) => ["category", "usage", "budget", "currency", "priority"].includes(key) &&
            v && typeof v === "object" && "value" in v && typeof v.value === "string" && v.value.length <= 120 &&
            "source" in v && ["confirmed", "suggested", "unspecified"].includes(String(v.source)) && "hard" in v && typeof v.hard === "boolean")) {
        setNeeds(saved.needs); setRevision(saved.revision);
        if (saved.compared) setDecision(createDecision(saved.needs, saved.revision));
      }
    } catch { /* Invalid or unavailable browser storage starts a fresh comparison. */ }
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (loaded) try { localStorage.setItem("beany-cui-needs", JSON.stringify({ needs, revision, compared: decision?.revision === revision })); } catch { /* Shopping remains available without persistence. */ }
  }, [needs, revision, decision, loaded]);
  return <div className="shell cui-shell">
    <header><a className="brand" href="/shop">beany.</a><a href="/">Classic simulation</a></header>
    <main className="cui-workspace">
      <h1>A considered choice, less research.</h1>
      <p className="muted">Tell me what matters. I’ll compare options and explain the choice for you.</p>
      <p className="cui-source">Fictional catalogue · No websites visited · No real orders or payments</p>
      {!!Object.keys(needs).length && <NeedsSummary key={revision} needs={needs} edit={(key, fact) => {
        const next = { ...needs }; if (fact) next[key] = fact; else delete next[key];
        setNeeds(next); setRevision(revision + 1);
      }} />}
      {request && <p className="cui-request"><strong>You</strong><br />{request}</p>}
      {clarification && <section aria-label="Purchase clarification" className="cui-result">
        <p role="status">{clarification.reply}</p>
        <div className="decisions">{clarification.options.map(option => <button key={option} onClick={() => send(option)}>{option}</button>)}</div>
      </section>}
      {decision && <Recommendation decision={decision} stale={decision.revision !== revision} />}
      {revision > 0 && decision?.revision !== revision && <button onClick={() => setDecision(createDecision(needs, revision))}>Compare current needs</button>}
      <form className="cui-composer" onSubmit={e => {
        e.preventDefault();
        send(text);
      }}>
        <label htmlFor="cui-message">Message Beany</label>
        <div className="cui-compose-row"><textarea id="cui-message" rows={2} maxLength={2000} value={text} onChange={e => setText(e.target.value)} required placeholder="Headphones for my train commute, under SGD300. Noise cancellation first." /><button className="primary">Send</button></div>
      </form>
    </main>
  </div>;
}
