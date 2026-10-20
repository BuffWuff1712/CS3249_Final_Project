"use client";
import { useState } from "react";
import { base, request, Session } from "@/lib/beany";
type Scenario = {
  id: string;
  name: string;
  user_goal: string;
  expected_decision: string | null;
};
export default function Research() {
  const [key, setKey] = useState(""),
    [scenarios, setScenarios] = useState<Scenario[]>([]),
    [session, setSession] = useState<Session | null>(null),
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
  return (
    <main className="research" style={{ display: "block" }}>
      <a href="/">← Beany participant interface</a>
      <h1>Study workspace</h1>
      <p>
        Researcher controls. Use fictional participant IDs and obtain consent
        before each session.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void run(async () =>
            setScenarios(
              await request<Scenario[]>(
                "/research/scenarios",
                "GET",
                undefined,
                key,
              ),
            ),
          );
        }}
      >
        <label>
          Researcher key
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoComplete="off"
          />
        </label>
        <button disabled={busy}>Unlock scenarios</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {scenarios.map((s) => (
        <section className="panel" key={s.id}>
          <h2>{s.name}</h2>
          <p>{s.user_goal}</p>
          <p>Expected policy: {s.expected_decision || "Conversation-driven"}</p>
          <button
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const result = await request<Session>(
                  `/research/scenarios/${s.id}/sessions`,
                  "POST",
                  {},
                  key,
                );
                setSession(result);
                localStorage.setItem("beany-session", result.id);
              })
            }
          >
            Start fresh participant
          </button>
        </section>
      ))}
      {session && (
        <section className="panel">
          <h2>{session.participant}</h2>
          <p>
            Open the participant interface in another tab. Refresh this
            workspace’s session after the task.
          </p>
          <a href="/" target="_blank" rel="noreferrer">
            Open participant interface ↗
          </a>
          <div className="decisions">
            <button
              disabled={busy}
              onClick={() =>
                void run(async () =>
                  setSession(
                    await request<Session>(
                      `/research/sessions/${session.id}/trigger`,
                      "POST",
                      {},
                      key,
                    ),
                  ),
                )
              }
            >
              Trigger scenario condition
            </button>
            <button
              disabled={busy}
              onClick={() =>
                void run(async () =>
                  setSession(await request<Session>(`/sessions/${session.id}`)),
                )
              }
            >
              Refresh results
            </button>
            <button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const res = await fetch(
                    `${base}/research/sessions/${session.id}/export`,
                    { headers: { "X-Research-Key": key } },
                  );
                  if (!res.ok) throw Error("Export failed");
                  const url = URL.createObjectURL(await res.blob());
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "beany-events.csv";
                  a.click();
                  URL.revokeObjectURL(url);
                })
              }
            >
              Export anonymous CSV
            </button>
          </div>
          <p>
            Clarifications: {session.clarification_count} · Interventions:{" "}
            {session.intervention_count}
          </p>
          <details>
            <summary>
              Detailed local research log (may contain conversation text)
            </summary>
            <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              {JSON.stringify(session.events, null, 2)}
            </pre>
          </details>
        </section>
      )}
    </main>
  );
}
