"use client";
import { useState } from "react";
import { Fact, Session } from "@/lib/beany";
const fields = [
  "category",
  "usage",
  "budget",
  "currency",
  "preferred_brands",
  "excluded_brands",
  "size",
  "features",
  "merchants",
  "other",
];
export function Brief({
  session,
  busy,
  edit,
}: {
  session: Session;
  busy: boolean;
  edit: (field: string, fact: Fact | null) => Promise<void>;
}) {
  const [field, setField] = useState("category"),
    [value, setValue] = useState(""),
    [hard, setHard] = useState(false);
  return (
    <>
      <section className="panel boundaries">
        <div className="eyebrow">YOUR LIVING SHOPPING BRIEF</div>
        <h2>What matters to you</h2>
        <p className="muted">
          Edit a value below. Confirmed constraints stay yours to change.
        </p>
        <dl>
          {fields.filter(f => ["category", "usage", "budget", "currency"].includes(f) || session.brief[f]).map((f) => (
            <div className="brief-row" key={f}>
              <dt>{f.replaceAll("_", " ")}</dt>
              <dd>
                {session.brief[f]?.value || "Not specified"}{" "}
                <span className="tag">
                  {session.brief[f]?.source || "unspecified"}
                  {session.brief[f]?.hard ? " · hard" : ""}
                </span>
                {session.brief[f] && (
                  <div className="row">
                    <button
                      disabled={busy}
                      onClick={() => {
                        setField(f);
                        setValue(session.brief[f].value);
                        setHard(session.brief[f].hard);
                      }}
                    >
                      Edit {f.replaceAll("_", " ")}
                    </button>
                    <button
                      disabled={busy}
                      aria-label={`Remove ${f}`}
                      onClick={() => void edit(f, null)}
                    >
                      Remove
                    </button>
                  </div>
                )}
              </dd>
            </div>
          ))}
        </dl>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await edit(field, { value, source: "confirmed", hard });
          }}
        >
          <fieldset disabled={busy}>
            <label>
              Preference
              <select
                value={field}
                onChange={(e) => {
                  setField(e.target.value);
                  setValue(session.brief[e.target.value]?.value || "");
                }}
              >
                {fields.map((f) => (
                  <option key={f} value={f}>
                    {f.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Value
              <input
                required
                value={value}
                maxLength={500}
                onChange={(e) => setValue(e.target.value)}
                placeholder={
                  field === "category"
                    ? "Running shoes, Headphones or Backpacks"
                    : "Enter a value"
                }
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={hard}
                onChange={(e) => setHard(e.target.checked)}
              />
              Hard constraint
            </label>
            <button className="primary">Save preference</button>
          </fieldset>
        </form>
      </section>

    </>
  );
}
