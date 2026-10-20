"use client";
import { useState } from "react";
import { base, request, Session } from "@/lib/beany";
type Profile = { id: string; name: string };
type Row = {
  proposal_id: string;
  merchant_id: string;
  predicted_risk: string;
  ground_truth: string;
  policy_decision: string;
  understood: boolean | null;
  responded_appropriately: boolean | null;
};
type Report = { rows: Row[]; metrics: unknown; active_configuration: unknown };
export function RiskResearch({
  session,
  researchKey,
  onUpdated,
}: {
  session: Session;
  researchKey: string;
  onUpdated: (s: Session) => void;
}) {
  const [profiles, setProfiles] = useState<Profile[]>([]),
    [profile, setProfile] = useState("standard"),
    [config, setConfig] = useState(""),
    [report, setReport] = useState<Report | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function inspect() {
    setReport(
      await request<Report>(
        `/research/sessions/${session.id}/risk-report`,
        "GET",
        undefined,
        researchKey,
      ),
    );
  }
  return (
    <section className="risk-research">
      <h2>Merchant-risk experiment</h2>
      <p>
        These controls and hidden labels are available only to researchers.
        Observations of participant understanding must be entered by the
        researcher.
      </p>
      {error && <p role="alert">{error}</p>}
      <button
        disabled={busy}
        onClick={() =>
          void run(async () => {
            const data = await request<{
              profiles: Profile[];
              risk_config: unknown;
            }>("/research/profiles", "GET", undefined, researchKey);
            setProfiles(data.profiles);
            setConfig(JSON.stringify(data.risk_config, null, 2));
            await inspect();
          })
        }
      >
        Load risk configuration
      </button>
      {config && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              onUpdated(
                await request<Session>(
                  `/research/sessions/${session.id}/configuration`,
                  "PUT",
                  { profile_id: profile, risk_config: JSON.parse(config) },
                  researchKey,
                ),
              );
              await inspect();
            });
          }}
        >
          <label>
            Experimental profile
            <select
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Risk rules and thresholds (JSON)
            <textarea
              rows={16}
              value={config}
              onChange={(e) => setConfig(e.target.value)}
              style={{ width: "100%", fontFamily: "monospace" }}
            />
          </label>
          <button disabled={busy}>Apply to this session</button>
          <small>
            Changing configuration invalidates pending proposals. Trigger the
            scenario again afterward. Mandatory safeguards cannot be disabled.
          </small>
        </form>
      )}
      <div className="decisions">
        <button disabled={busy} onClick={() => void run(inspect)}>
          Inspect risk results
        </button>
        <button
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const response = await fetch(
                `${base}/research/sessions/${session.id}/risk-export`,
                { headers: { "X-Research-Key": researchKey } },
              );
              if (!response.ok) throw Error("Risk export failed");
              const url = URL.createObjectURL(await response.blob());
              const a = document.createElement("a");
              a.href = url;
              a.download = "beany-risk-results.csv";
              a.click();
              URL.revokeObjectURL(url);
            })
          }
        >
          Export researcher risk CSV
        </button>
        <button
          disabled={busy || !session.scenario_id}
          onClick={() =>
            void run(async () => {
              let fresh = await request<Session>(
                `/research/scenarios/${session.scenario_id}/sessions`,
                "POST",
                {},
                researchKey,
              );
              if (config)
                fresh = await request<Session>(
                  `/research/sessions/${fresh.id}/configuration`,
                  "PUT",
                  { profile_id: profile, risk_config: JSON.parse(config) },
                  researchKey,
                );
              localStorage.setItem("beany-session", fresh.id);
              onUpdated(fresh);
              setReport(null);
            })
          }
        >
          New participant, same scenario
        </button>
      </div>
      {report && (
        <>
          <pre style={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(report.metrics, null, 2)}
          </pre>
          {report.rows.map((row) => (
            <div key={row.proposal_id} className="panel">
              <h3>{row.merchant_id}</h3>
              <p>
                Predicted: {row.predicted_risk} · Hidden ground truth:{" "}
                {row.ground_truth} · Policy: {row.policy_decision}
              </p>
              {(["understood", "responded_appropriately"] as const).map(
                (field) => (
                  <label key={field}>
                    {field.replaceAll("_", " ")}
                    <select
                      disabled={busy}
                      value={
                        row[field] === null ? "unknown" : String(row[field])
                      }
                      onChange={(e) => {
                        const value = e.target.value;
                        void run(async () => {
                          await request(
                            `/research/sessions/${session.id}/observation`,
                            "PUT",
                            {
                              proposal_id: row.proposal_id,
                              understood: row.understood,
                              responded_appropriately:
                                row.responded_appropriately,
                              [field]:
                                value === "unknown" ? null : value === "true",
                            },
                            researchKey,
                          );
                          await inspect();
                        });
                      }}
                    >
                      <option value="unknown">Not assessed</option>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </label>
                ),
              )}
            </div>
          ))}
          <details>
            <summary>Full researcher assessment</summary>
            <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
        </>
      )}
    </section>
  );
}
