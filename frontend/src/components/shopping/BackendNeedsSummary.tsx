"use client";
import { useEffect, useRef, useState } from "react";
import { shopFields, type ShopBrief, type ShopField } from "@/lib/shopBackend";
import type { Fact } from "@/lib/beany";
import { CoinsIcon, HeadphonesIcon, PencilSimpleIcon, SlidersHorizontalIcon, SneakerIcon, TrainIcon } from "./ShoppingIcons";
import { BackpackIcon } from "@phosphor-icons/react/dist/csr/Backpack";

const primaryFields: ShopField[] = ["category", "usage", "budget", "features"];
const extraFields = shopFields.filter(key => !primaryFields.includes(key));
const categories = ["Headphones", "Running shoes", "Backpacks"];
const labels: Record<string, string> = { category: "Buying", usage: "For", budget: "Budget", features: "Features / priorities" };
const uses: Record<string, string[]> = {
  Headphones: ["Daily commute", "Home listening", "Work and calls"],
  "Running shoes": ["Daily road runs", "Gym training", "Everyday wear"],
  Backpacks: ["University", "Daily commute", "Travel"],
};
const features: Record<string, string[]> = {
  Headphones: ["Noise cancelling", "Wireless", "Lightweight", "Over-ear"],
  "Running shoes": ["Cushioned", "Lightweight", "Breathable"],
  Backpacks: ["Laptop sleeve", "Water resistant", "Lightweight"],
};

export function BackendNeedsSummary({ brief, busy, edit, requested }: { brief: ShopBrief; busy: boolean; edit: (field: ShopField, fact: Fact | null) => Promise<boolean>; requested?: { field: ShopField } }) {
  const [field, setField] = useState<ShopField | null>(null), [value, setValue] = useState(""), [hard, setHard] = useState(false);
  const [currency, setCurrency] = useState("SGD"), [error, setError] = useState("");
  const root = useRef<HTMLElement>(null);
  function open(key: ShopField) {
    setField(key); setValue(brief[key]?.value || ""); setHard(brief[key]?.hard ?? key === "budget");
    setCurrency(brief.currency?.value || "SGD"); setError("");
  }
  function close() { setField(null); setError(""); }
  useEffect(() => { if (requested) open(requested.field); }, [requested]);
  useEffect(() => {
    if (!field) return;
    const editor = root.current?.querySelector<HTMLElement>(".cui-need-editor input, .cui-need-editor select");
    editor?.focus();
    function dismiss(event: PointerEvent) { if (!busy && event.target instanceof Node && !root.current?.contains(event.target)) close(); }
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [field, busy]);
  function toggleFeature(feature: string) {
    const selected = value.split(",").map(item => item.trim()).filter(Boolean);
    setValue(selected.some(item => item.toLowerCase() === feature.toLowerCase()) ? selected.filter(item => item.toLowerCase() !== feature.toLowerCase()).join(", ") : [...selected, feature].join(", "));
  }
  function editor() {
    if (!field) return null;
    const name = labels[field] || field.replaceAll("_", " ");
    return <form id="cui-need-editor" className="cui-need-editor" aria-label={`Edit ${name}`} onKeyDown={event => { if (event.key === "Escape" && !busy) { event.stopPropagation(); close(); } }} onSubmit={async event => {
      event.preventDefault(); const text = value.trim();
      if (!text || text.length > 500) { setError("Enter a value between 1 and 500 characters."); return; }
      if (field === "budget" && (!Number.isFinite(Number(text)) || Number(text) <= 0)) { setError("Enter a positive budget."); return; }
      setError("");
      if (field === "budget" && (brief.currency?.value !== currency || brief.currency?.source !== "confirmed")) {
        if (!await edit("currency", { value: currency, source: "confirmed", hard: brief.currency?.hard || false })) return;
      }
      if (await edit(field, { value: text, source: "confirmed", hard })) close();
    }}><fieldset disabled={busy}><legend>{name}</legend>
      {field === "category" ? <label>Category<select value={value} onChange={event => setValue(event.target.value)} required>
        <option value="" disabled>Choose what you’re buying</option>
        {value && !categories.includes(value) && <option value={value}>{value}</option>}
        {categories.map(category => <option key={category}>{category}</option>)}
      </select></label> : field === "budget" ? <>
        <div className="cui-budget-fields"><label>Amount<input type="number" min="0.01" step="0.01" value={value} onChange={event => setValue(event.target.value)} required /></label><label>Currency<select value={currency} onChange={event => setCurrency(event.target.value)}><option>SGD</option><option>USD</option></select></label></div>
        <label>Budget type<select value={hard ? "maximum" : "preferred"} onChange={event => setHard(event.target.value === "maximum")}><option value="maximum">Maximum — must stay within</option><option value="preferred">Preferred — some flexibility</option></select></label>
      </> : <>
        {(field === "usage" || field === "features") && <div className="cui-need-suggestions">{(field === "usage" ? uses : features)[brief.category?.value || "Headphones"]?.map(suggestion => <button type="button" key={suggestion} aria-pressed={field === "usage" ? value === suggestion : value.split(",").some(item => item.trim().toLowerCase() === suggestion.toLowerCase())} onClick={() => field === "usage" ? setValue(suggestion) : toggleFeature(suggestion)}>{suggestion}</button>)}</div>}
        <label>{field === "features" ? "Features, separated by commas" : field === "usage" ? "Use or occasion" : "Value"}<input autoComplete="off" maxLength={500} value={value} onChange={event => setValue(event.target.value)} required /></label>
      </>}
      {field !== "budget" && <label className="check"><input type="checkbox" checked={hard} onChange={event => setHard(event.target.checked)} />Must have</label>}
      {error && <p role="alert" className="cui-input-error">{error}</p>}
      <div className="cui-need-actions"><button className="primary">Save</button><button type="button" onClick={close}>Cancel</button><button type="button" disabled={!brief[field]} onClick={async () => { if (await edit(field, null)) close(); }}>Clear</button></div>
    </fieldset></form>;
  }
  return <section ref={root} className="cui-needs cui-needs--individual" aria-label="Purchase needs">
    <h2 aria-label="Your purchase intent">Your needs</h2>
    <dl className="cui-intent-grid">{primaryFields.map(key => <div key={key} className="cui-need-anchor">
      <dt className="sr-only">{labels[key]}</dt><dd><button className={`cui-need-chip ${!brief[key] ? "cui-need-chip--empty" : ""}`} disabled={busy} aria-expanded={field === key} aria-controls={field === key ? "cui-need-editor" : undefined} onClick={() => field === key ? close() : open(key)} aria-label={`Edit ${labels[key].toLowerCase()}: ${brief[key]?.value || "not set"}`}>
        {key === "category" ? brief.category?.value === "Running shoes" ? <SneakerIcon aria-hidden="true" /> : brief.category?.value === "Backpacks" ? <BackpackIcon aria-hidden="true" /> : <HeadphonesIcon aria-hidden="true" /> : key === "usage" ? <TrainIcon aria-hidden="true" /> : key === "budget" ? <CoinsIcon aria-hidden="true" /> : <SlidersHorizontalIcon aria-hidden="true" />}
        <span>{key === "budget" && brief.budget ? `${brief.budget.hard ? "Up to" : "Target"} ${brief.currency?.value || "SGD"}${brief.budget.value}` : brief[key]?.value || `${labels[key]} not set`}</span><PencilSimpleIcon aria-hidden="true" className="cui-edit-icon" />
      </button>{field === key && editor()}</dd><small className="cui-fact-status">{brief[key] && brief[key].source !== "confirmed" ? "Assumption · editable" : ""}</small>
    </div>)}</dl>
    <p className="cui-source cui-currency">{brief.currency ? `Currency: ${brief.currency.value} (${brief.currency.source}).` : "Prices show their currency; no conversion is performed."}{!brief.budget && " No budget is confirmed."}</p>
    <div className="cui-more-needs"><button className="cui-link-button" disabled={busy} aria-expanded={!!field && extraFields.includes(field as typeof extraFields[number])} onClick={() => field && !primaryFields.includes(field) ? close() : open("size")}>More needs</button>
      {field && !primaryFields.includes(field) && <div className="cui-extra-editor"><label>Additional need<select disabled={busy} value={field} onChange={event => open(event.target.value as ShopField)}>{extraFields.map(key => <option key={key} value={key}>{key.replaceAll("_", " ")}</option>)}</select></label>{editor()}</div>}
    </div>
  </section>;
}
