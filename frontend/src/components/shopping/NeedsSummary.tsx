"use client";
import { useEffect, useRef, useState } from "react";
import type { Fact } from "@/lib/beany";
import type { Needs, NeedKey } from "@/lib/decision";
import { validateNeed } from "@/lib/shoppingNeeds";
import { CoinsIcon, HeadphonesIcon, PencilSimpleIcon, SlidersHorizontalIcon, SneakerIcon, TrainIcon } from "./ShoppingIcons";

export function NeedsSummary({ needs, edit, requestedField }: { needs: Needs; edit: (key: NeedKey, fact: Fact | null) => void; requestedField?: { key: NeedKey } }) {
  const [field, setField] = useState<NeedKey>("budget");
  const [value, setValue] = useState(needs.budget?.value || "");
  const [hard, setHard] = useState(needs.budget?.hard ?? false);
  const [error, setError] = useState("");
  const details = useRef<HTMLDetailsElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const labels: Partial<Record<NeedKey, string>> = { category: "Buying", usage: "For", budget: "Spending limit", priority: "Most important", sellerPreference: "Seller preference" };
  function openField(key: NeedKey) {
    setField(key); setValue(needs[key]?.value || ""); setHard(needs[key]?.hard ?? false); setError("");
    if (details.current) details.current.open = true;
    input.current?.focus();
  }
  useEffect(() => {
    if (!requestedField) return;
    const key = requestedField.key;
    setField(key); setValue(needs[key]?.value || ""); setHard(needs[key]?.hard ?? false);
    if (details.current) details.current.open = true;
    input.current?.focus();
  }, [requestedField, needs]);
  return <section className="cui-needs" aria-label="Purchase needs">
    <h2 aria-label="Your purchase intent">Your needs</h2>
    <dl className="cui-intent-grid">{Object.entries(needs).filter(([key]) => !["currency", "sellerPreference"].includes(key)).map(([key, fact]) => <div key={key} className={key === "priority" ? "cui-intent-priority" : undefined}>
      <dt className="sr-only">{labels[key as NeedKey]}</dt><dd><button type="button" className="cui-need-chip" onClick={() => openField(key as NeedKey)} aria-label={`Edit ${labels[key as NeedKey]?.toLowerCase()}: ${fact.value}`}>
        {key === "category" ? needs.category?.value === "Running shoes" ? <SneakerIcon aria-hidden="true" /> : <HeadphonesIcon aria-hidden="true" /> : key === "usage" ? needs.category?.value === "Running shoes" ? <SneakerIcon aria-hidden="true" /> : <TrainIcon aria-hidden="true" /> : key === "budget" ? <CoinsIcon aria-hidden="true" /> : <SlidersHorizontalIcon aria-hidden="true" />}
        <span>{key === "budget" ? `Up to ${needs.currency?.value || "SGD"}${fact.value}` : key === "priority" ? `${fact.value} first` : fact.value}</span><PencilSimpleIcon aria-hidden="true" className="cui-edit-icon" />
      </button></dd>
      {fact.source !== "confirmed" && <small>Assumption · editable</small>}
    </div>)}</dl>
    {needs.currency && <p className="cui-source cui-currency">Currency: {needs.currency.value}{needs.currency.source !== "confirmed" ? " (assumed; you can correct it)" : " (confirmed)"}{!needs.budget ? " · No spending limit is confirmed" : ""}.</p>}
    <details ref={details}><summary>Edit purchase needs</summary>
      <form onSubmit={e => {
        e.preventDefault();
        const nextValue = ["priority", "sellerPreference"].includes(field) ? value.trim().toLowerCase() : value.trim();
        const problem = validateNeed(field, nextValue, needs);
        if (problem) { setError(problem); return; }
        setError(""); edit(field, { value: nextValue, source: "confirmed", hard });
      }}>
        <label>Purchase field<select value={field} onChange={e => {
          const key = e.target.value as NeedKey;
          setField(key); setValue(needs[key]?.value || ""); setHard(needs[key]?.hard ?? false); setError("");
        }}><option value="category">Category</option><option value="budget">Spending limit</option><option value="usage">Use case</option><option value="priority">Priority</option><option value="sellerPreference">Seller preference</option></select></label>
        <label>Preference value<input ref={input} name="preference" autoComplete="off" maxLength={120} value={value} onChange={e => setValue(e.target.value)} aria-invalid={!!error} aria-describedby={error ? "cui-need-error" : undefined} /></label>
        <label className="check"><input type="checkbox" checked={hard} onChange={e => setHard(e.target.checked)} />Must have</label>
        <p className="cui-source">A stated spending limit is always respected. Comparative priorities guide the choice; they do not guarantee comfort or fit.</p>
        {error && <p role="alert" className="cui-input-error" id="cui-need-error"><strong>Cannot save this need.</strong> {error}</p>}
        <div className="decisions"><button type="submit">Save need</button><button type="button" onClick={() => edit(field, null)}>Remove need</button></div>
      </form>
    </details>
  </section>;
}
