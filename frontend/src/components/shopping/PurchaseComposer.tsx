"use client";
import { useRef } from "react";

const examples = [
  { label: "Try headphones", text: "Headphones for my daily train commute, under SGD300. Noise cancellation first." },
  { label: "Try running shoes", text: "Running shoes for daily road runs, under SGD200. Cushioning first." },
  { label: "Try a risk example", text: "Headphones for my train commute, under SGD300. Noise cancellation first. Find the cheapest Echo Quiet offer." },
];

export function PurchaseComposer({ text, setText, send, loaded }: {
  text: string; setText: (text: string) => void; send: (text: string) => void; loaded: boolean;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  return <section className="cui-entry" aria-label="Describe your purchase">
    <div className="cui-section-heading"><span className="cui-step-number">1</span><h2>What are you buying?</h2></div>
    <p id="cui-intent-help">Tell me the product, what you’ll use it for, your budget and what matters most. Unsure? Start with just the product.</p>
    <form className="cui-composer" onSubmit={event => { event.preventDefault(); send(text); }}>
      <label htmlFor="cui-message">Message Beany</label>
      <div className="cui-compose-row"><textarea ref={input} id="cui-message" rows={3} maxLength={2000} value={text} onChange={event => setText(event.target.value)} required disabled={!loaded} aria-describedby="cui-intent-help" placeholder="I need headphones for my train commute, under SGD300. Noise cancellation matters most." /><button className="primary" disabled={!loaded}>Send</button></div>
    </form>
    <div className="cui-examples"><span>Editable examples</span>{examples.map(example => <button key={example.label} disabled={!loaded} onClick={() => { setText(example.text); input.current?.focus(); }}>{example.label}</button>)}</div>
  </section>;
}
