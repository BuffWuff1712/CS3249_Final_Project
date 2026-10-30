"use client";
import { useEffect, useRef, useState } from "react";
import { shopFields, type ShopBrief, type ShopField } from "@/lib/shopBackend";
import type { Fact } from "@/lib/beany";
import { CoinsIcon, HeadphonesIcon, PencilSimpleIcon, SlidersHorizontalIcon, SneakerIcon, TrainIcon } from "./ShoppingIcons";
import { BackpackIcon } from "@phosphor-icons/react/dist/csr/Backpack";

const labels: Record<string, string> = { category: "Buying", usage: "For", budget: "Spending limit", features: "Features / priorities" };
export function BackendNeedsSummary({ brief, busy, edit, requested }: { brief: ShopBrief; busy: boolean; edit: (field: ShopField, fact: Fact | null) => Promise<boolean>; requested?: { field: ShopField } }) {
  const [field, setField] = useState<ShopField>("budget"), [value, setValue] = useState(""), [hard, setHard] = useState(false), [error, setError] = useState("");
  const details = useRef<HTMLDetailsElement>(null), input = useRef<HTMLInputElement>(null);
  function choose(key: ShopField) { setField(key); setValue(brief[key]?.value || ""); setHard(!!brief[key]?.hard); setError(""); }
  function open(key: ShopField) { choose(key); if (details.current) details.current.open = true; input.current?.focus(); }
  useEffect(() => { if (requested && !busy) open(requested.field); }, [requested]);
  return <section className="cui-needs" aria-label="Purchase needs">
    <h2 aria-label="Your purchase intent">Your needs</h2>
    <dl className="cui-intent-grid">{(["category", "usage", "budget", "features"] as ShopField[]).map(key => <div key={key}>
      <dt className="sr-only">{labels[key]}</dt><dd><button className={`cui-need-chip ${!brief[key] ? "cui-need-chip--empty" : ""}`} disabled={busy} onClick={() => open(key)} aria-label={`Edit ${labels[key].toLowerCase()}: ${brief[key]?.value || "not set"}`}>
        {key === "category" ? brief.category?.value === "Running shoes" ? <SneakerIcon aria-hidden="true" /> : brief.category?.value === "Backpacks" ? <BackpackIcon aria-hidden="true" /> : <HeadphonesIcon aria-hidden="true" /> : key === "usage" ? <TrainIcon aria-hidden="true" /> : key === "budget" ? <CoinsIcon aria-hidden="true" /> : <SlidersHorizontalIcon aria-hidden="true" />}
        <span>{key === "budget" && brief.budget ? `${brief.budget.hard ? "Up to" : "Target"} ${brief.currency?.value || "SGD"}${brief.budget.value}` : brief[key]?.value || `${labels[key]} not set`}</span><PencilSimpleIcon aria-hidden="true" className="cui-edit-icon" />
      </button></dd><small className="cui-fact-status">{brief[key] && brief[key].source !== "confirmed" ? "Assumption · editable" : ""}</small>
    </div>)}</dl>
    <p className="cui-source cui-currency">{brief.currency ? `Currency: ${brief.currency.value} (${brief.currency.source}).` : "Catalogue prices show their currency; no conversion is performed."}{!brief.budget && " No spending limit is confirmed."}</p>

    <details ref={details}><summary>Edit purchase needs</summary>{!!Object.keys(brief).length && <details className="cui-all-needs"><summary>All saved needs ({Object.keys(brief).length})</summary><dl className="cui-spec-grid">{Object.entries(brief).map(([key, fact]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{fact.value} · {fact.source} · {fact.hard ? "Must have" : "Preference"}</dd></div>)}</dl></details>}<form onSubmit={async event => {
      event.preventDefault(); const text = value.trim();
      if (!text || text.length > 500) { setError("Enter a value between 1 and 500 characters."); return; }
      if (field === "budget" && (!Number.isFinite(Number(text)) || Number(text) <= 0)) { setError("Enter a positive spending limit."); return; }
      setError(""); if (await edit(field, { value: text, source: "confirmed", hard })) { if (details.current) details.current.open = false; }
    }}><fieldset disabled={busy}>
      <label>Purchase field<select value={field} onChange={event => choose(event.target.value as ShopField)}>{shopFields.map(key => <option key={key} value={key}>{labels[key] || key.replaceAll("_", " ")}</option>)}</select></label>
      <label>Preference value<input ref={input} name="preference" autoComplete="off" maxLength={500} value={value} onChange={event => setValue(event.target.value)} aria-invalid={!!error} /></label>
      <label className="check"><input type="checkbox" checked={hard} onChange={event => setHard(event.target.checked)} />Must have</label>
      <p className="cui-source">Must have marks a hard constraint. Other needs guide the comparison; the backend applies the saved choice. Missing terms remain unknown.</p>
      {error && <p role="alert">{error}</p>}
      <div className="decisions"><button>Save need</button><button type="button" onClick={async () => { if (await edit(field, null)) { if (details.current) details.current.open = false; } }}>Remove need</button></div>
    </fieldset></form></details>
  </section>;
}
