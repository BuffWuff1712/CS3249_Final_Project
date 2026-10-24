"use client";
import { useState } from "react";
import { Permissions } from "@/lib/beany";
export function PermissionSettings({ initial, busy, save }: {
  initial: Permissions;
  busy: boolean;
  save: (permissions: Permissions) => Promise<void>;
}) {
  const [p, setP] = useState(initial);
  const [restricted, setRestricted] = useState(initial.restricted_merchants.join(", "));
  return (
      <section className="panel boundaries">
        <h2>Permissions</h2>
        <p className="muted">
          Only these controls can grant authority. All checkout is simulated.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void save({ ...p, restricted_merchants: restricted.split(",").map(x => x.trim()).filter(Boolean) });
          }}
        >
          <fieldset disabled={busy}>
            {(
              [
                "require_approval",
                "substitutions",
                "share_personal_data",
              ] as const
            ).map((k) => (
              <label className="check" key={k}>
                <input
                  type="checkbox"
                  checked={p[k]}
                  onChange={(e) => setP({ ...p, [k]: e.target.checked })}
                />
                {k.replaceAll("_", " ")}
              </label>
            ))}
            <label>
              Autonomy
              <select
                value={p.autonomy}
                onChange={(e) =>
                  setP({
                    ...p,
                    autonomy: e.target.value as Permissions["autonomy"],
                  })
                }
              >
                <option value="guided">Guided · always review</option>
                <option value="balanced">Balanced · follow permissions</option>
              </select>
            </label>
            <label>
              Restricted merchants (comma separated)
              <input
                value={restricted}
                onChange={(e) => setRestricted(e.target.value)}
              />
            </label>
            {["Demo Visa", "Demo Wallet"].map((m) => (
              <label className="check" key={m}>
                <input
                  type="checkbox"
                  checked={p.payment_methods.includes(m)}
                  onChange={(e) =>
                    setP({
                      ...p,
                      payment_methods: e.target.checked
                        ? [...p.payment_methods, m]
                        : p.payment_methods.filter((x) => x !== m),
                    })
                  }
                />
                {m} (fictional)
              </label>
            ))}
            <button className="primary">Save Permissions</button>
          </fieldset>
        </form>
      </section>
  );
}
