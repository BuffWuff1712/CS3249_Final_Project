"use client";
import { useRef } from "react";

const examples = [
  { label: "Try headphones", text: "Headphones for my daily train commute, under SGD300. Noise cancellation first." },
  { label: "Try running shoes", text: "Running shoes for daily road runs, under SGD200. Cushioning first." },
  { label: "Try a risk example", text: "Headphones for my train commute, under SGD300. Noise cancellation first. Find the cheapest Echo Quiet offer." },
];

export function PurchaseComposer({ text, setText, send, loaded, started = false }: {
  text: string; setText: (text: string) => void; send: (text: string) => void; loaded: boolean; started?: boolean;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  return <section className="cui-entry" aria-label="Describe your purchase">
    <form className="cui-composer" onSubmit={event => { event.preventDefault(); if (text.trim()) send(text); }}>
      <label className="sr-only" htmlFor="cui-message">Message Beany</label>
      <p className="sr-only" id="cui-intent-help">Describe headphones or running shoes, change your needs, or ask about the current comparison.</p>
      <div className="cui-compose-row"><textarea ref={input} id="cui-message" name="message" autoComplete="off" rows={1} maxLength={2000} value={text} onChange={event => setText(event.target.value)} required disabled={!loaded} aria-describedby="cui-intent-help" placeholder={started ? "Change what matters, or ask about a trade-off…" : "Headphones for my train commute, under SGD300…"} /><button className="primary" disabled={!loaded}>Send</button></div>
    </form>
    {!started && <div className="cui-examples"><span>Editable examples</span>{examples.map(example => <button key={example.label} disabled={!loaded} onClick={() => { setText(example.text); input.current?.focus(); }}>{example.label}</button>)}</div>}
  </section>;
}
