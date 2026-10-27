"use client";
import { useState } from "react";
import type { ShoppingDecision } from "@/lib/decision";
import { referenceDecision } from "@/lib/shoppingScenario";
import { Recommendation } from "./Recommendation";
import "./shopping.css";

export function ShoppingWorkspace() {
  const [text, setText] = useState("");
  const [decision, setDecision] = useState<ShoppingDecision | null>(null);
  const [request, setRequest] = useState("");
  return <div className="shell cui-shell">
    <header><a className="brand" href="/shop">beany.</a><a href="/">Classic simulation</a></header>
    <main className="cui-workspace">
      <h1>A considered choice, less research.</h1>
      <p className="muted">Tell me what matters. I’ll compare options and explain the choice for you.</p>
      <p className="cui-source">Fictional catalogue · No websites visited · No real orders or payments</p>
      {request && <p className="cui-request"><strong>You</strong><br />{request}</p>}
      {decision && <Recommendation decision={decision} />}
      <form className="cui-composer" onSubmit={e => {
        e.preventDefault();
        if (!text.trim()) return;
        setRequest(text.trim()); setDecision(referenceDecision()); setText("");
      }}>
        <label htmlFor="cui-message">Message Beany</label>
        <div className="cui-compose-row"><textarea id="cui-message" rows={2} maxLength={2000} value={text} onChange={e => setText(e.target.value)} required placeholder="Headphones for my train commute, under SGD300. Noise cancellation first." /><button className="primary">Send</button></div>
      </form>
    </main>
  </div>;
}
