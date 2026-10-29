"use client";
import { useEffect, useState } from "react";
import { choiceError, type PublicCatalogue } from "@/lib/publicCatalogue";
import "./shopping.css";

export function ComparisonBaseline() {
  const [catalogue, setCatalogue] = useState<PublicCatalogue>();
  const [category, setCategory] = useState("Headphones");
  const [ceiling, setCeiling] = useState("");
  const [selected, setSelected] = useState<string>();
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/study/catalogue", { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error("The comparison catalogue is unavailable. Retry to continue.");
      setCatalogue(await response.json()); setError("");
    }).catch(problem => { if (!controller.signal.aborted) setError(problem.message); });
    return () => controller.abort();
  }, [retry]);
  const products = catalogue?.products.filter(product => product.category === category) || [];
  const offer = catalogue?.offers.find(item => item.id === selected);
  const product = products.find(item => item.id === offer?.productId);
  let visible = 0;
  return <div className="shell cui-shell"><header><a href="/compare" className="brand">beany.</a><span>Product comparison</span></header>
    <main className="cui-workspace"><h1>Compare products and offers</h1><p className="cui-source">Fictional records · SGD · No real orders or payments</p>
      <section className="cui-entry" aria-label="Comparison filters"><h2>Filters</h2>
        <label>Category<select value={category} onChange={event => { setCategory(event.target.value); setSelected(undefined); setError(""); }}><option>Headphones</option><option>Running shoes</option></select></label>
        <label>Maximum price (SGD)<input type="number" min="0.01" step="0.01" value={ceiling} onChange={event => { setCeiling(event.target.value); setSelected(undefined); setError(""); }} /></label>
      </section>
      {error && <p role="alert" className="cui-input-error">{error}</p>}
      {!catalogue && <button onClick={() => setRetry(retry + 1)}>Retry catalogue</button>}
      {products.map(item => {
        const offers = catalogue!.offers.filter(candidate => candidate.productId === item.id && (!ceiling || candidate.price <= Number(ceiling)));
        visible += offers.length;
        if (!offers.length) return null;
        return <article key={item.id} className="cui-result"><h2>{item.name}</h2><p>Variant: {item.variant}</p>
          <dl>{Object.entries(item.specifications).map(([key, value]) => <div key={key}><dt><strong>{key}</strong></dt><dd>{value}</dd></div>)}</dl>
          <p>{item.rating ?? "Unknown rating"}/5 · {item.rating_count ?? "Unknown count"} product reviews</p>
          <details><summary>Product review excerpts for {item.name}</summary>{item.reviews?.length ? item.reviews.map(review => <blockquote key={review.title}><strong>{review.title}</strong><p>{review.text}</p></blockquote>) : <p>Unknown; not supplied</p>}</details>
          {offers.map(candidate => <section key={candidate.id} className="cui-source-record" aria-label={`Offer ${candidate.id}`}><h3>{candidate.merchant} · SGD{candidate.price}</h3>
            <p>{candidate.rating ?? "Unknown rating"}/5 · {candidate.reviewCount} seller reviews</p>
            <p>Returns: {candidate.returnsDays === null ? "Unknown; not supplied" : `${candidate.returnsDays} days`}</p><p>{candidate.payment}</p>
            <button onClick={() => { const problem = choiceError(catalogue!, candidate.id, category, ceiling); setError(problem || ""); if (!problem) setSelected(candidate.id); }}>Choose {item.name} from {candidate.merchant}</button>
          </section>)}
        </article>;
      })}
      {catalogue && visible === 0 && <p>No offers match these filters.</p>}
      {offer && product && <section className="cui-result cui-selection" aria-label="Selected offer"><h2>Your choice</h2><p>{product.name} · {offer.merchant} · SGD{offer.price}</p><p>No order or payment has been created.</p></section>}
    </main></div>;
}
