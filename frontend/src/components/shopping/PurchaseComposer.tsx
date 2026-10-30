"use client";

const examples = [
  { label: "Try headphones", text: "Headphones for my daily train commute, under SGD300. Noise cancellation first." },
  { label: "Try running shoes", text: "Running shoes for daily road runs, under SGD200. Cushioning first." },
  { label: "Try a risk example", text: "Headphones for my train commute, under SGD300. Noise cancellation first. Find the cheapest Echo Quiet offer." },
];

export function PurchaseComposer({ text, setText, send, loaded, started = false, busy = false }: {
  text: string; setText: (text: string) => void; send: (text: string) => void; loaded: boolean; started?: boolean; busy?: boolean;
}) {
  return <section className="cui-entry" aria-label="Describe your purchase">
    <form className="cui-composer" onSubmit={event => { event.preventDefault(); if (!busy && text.trim()) send(text); }}>
      <label className="sr-only" htmlFor="cui-message">Message Beany</label>
      <p className="sr-only" id="cui-intent-help">Describe your purchase, change your needs, or ask about the current comparison. Enter to send; Shift+Enter for a new line.</p>
      <div className="cui-compose-row"><textarea id="cui-message" name="message" autoComplete="off" rows={1} maxLength={2000} value={text} onChange={event => setText(event.target.value)} required onKeyDown={event => {
        if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing || event.keyCode === 229) return;
        event.preventDefault();
        if (!event.repeat && !busy && loaded && text.trim()) event.currentTarget.form?.requestSubmit();
      }} disabled={!loaded} aria-describedby="cui-intent-help" placeholder={started ? "Change what matters, or ask about a trade-off…" : "Headphones for my train commute, under SGD300…"} /><button className="primary" disabled={!loaded || busy}>Send</button></div>
    </form>
  </section>;
}

export function PurchaseExamples({ choose, disabled }: { choose: (text: string) => void; disabled: boolean }) {
  return <div className="cui-examples"><span>Editable examples</span>{examples.map(example => <button key={example.label} disabled={disabled} onClick={() => choose(example.text)}>{example.label}</button>)}</div>;
}
