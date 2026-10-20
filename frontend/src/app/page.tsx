"use client";
import { useEffect, useRef, useState } from "react";
import { request, Session, Action } from "@/lib/beany";
import { MerchantDetails } from "@/components/MerchantDetails";
import { Brief } from "@/components/Brief";
const starters = [
  "Find me running shoes under $200.",
  "I need headphones but don’t know which ones to buy.",
  "Help me choose a backpack for university.",
  "What can you help me shop for?",
];
export default function Home() {
  const [session, setSession] = useState<Session | null>(null),
    [busy, setBusy] = useState(true),
    [error, setError] = useState(""),
    [text, setText] = useState("");
  const started = useRef(false);
  const bottom = useRef<HTMLDivElement>(null);
  function keep(s: Session) {
    setSession(s);
    localStorage.setItem("beany-session", s.id);
  }
  async function run(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }
  async function init() {
    const sid = localStorage.getItem("beany-session");
    if (sid) {
      try {
        keep(await request<Session>(`/sessions/${sid}`));
        return;
      } catch {
        localStorage.removeItem("beany-session");
      }
    }
    keep(await request<Session>("/sessions", "POST"));
  }
  useEffect(() => {
    if (!started.current) {
      started.current = true;
      void run(init);
    }
  }, []);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [session?.messages.length]);
  async function send(message = text) {
    if (!session || !message.trim()) return;
    await run(async () => {
      keep(
        await request<Session>(`/sessions/${session.id}/messages`, "POST", {
          text: message,
        }),
      );
      setText("");
    });
  }
  async function decide(a: Action, action: string) {
    await run(async () =>
      keep(
        await request<Session>(
          `/sessions/${session!.id}/proposals/${a.id}/decision`,
          "POST",
          { action, fingerprint: a.fingerprint },
        ),
      ),
    );
  }
  const a = session?.proposals.at(-1);
  return (
    <div className="shell">
      <header>
        <a className="brand" href="/">
          <span className="brand-icon">b</span>Beany
          <span className="brand-dot">.</span>
        </a>
        <div className="header-right">
          <span className="demo-badge">● SIMULATED SHOPPING</span>
          <button
            disabled={busy}
            onClick={() =>
              void run(async () => {
                if (session) await request(`/sessions/${session.id}`, "DELETE");
                localStorage.removeItem("beany-session");
                keep(await request<Session>("/sessions", "POST"));
              })
            }
          >
            Fresh session
          </button>
        </div>
      </header>
      <div className="intro">
        <div>
          <div className="eyebrow">YOUR SHOPPING COPILOT</div>
          <h1>
            AI does the shopping.
            <br />
            <span>You stay in control.</span>
          </h1>
          <p>Start with an idea. Shape it together. Decide with confidence.</p>
        </div>
        <div className="promise">
          <span>✓</span>
          <div>
            <strong>Your boundaries come first</strong>
            <p>Change your mind, edit your brief, or stop at any time.</p>
          </div>
        </div>
      </div>
      <div className="demo-note">
        SANDBOX{" "}
        <span>
          Fictional products and simulated checkout.{" "}
          {session?.mode === "mock"
            ? "MOCK LLM MODE — offline test responses."
            : "Conversation via your configured NUS model."}
        </span>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
          <button disabled={busy} onClick={() => void run(init)}>
            Reconnect
          </button>
        </div>
      )}
      <main>
        <section className="panel conversation">
          <div className="panel-heading">
            <div>
              <h2>Let’s find your fit</h2>
              <p className="muted">
                You don’t need to know all the details yet.
              </p>
            </div>
            <span className="online">
              {session?.mode === "mock" ? "Mock LLM" : "Beany"}
            </span>
          </div>
          <div className="messages" aria-live="polite">
            {session?.messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>
                <span className="avatar">
                  {m.role === "user" ? "You" : "b"}
                </span>
                <div>
                  <span className="message-label">
                    {m.role === "user" ? "You" : "Beany"}
                  </span>
                  <p>{m.text}</p>
                </div>
              </div>
            ))}
            {(!session || session.messages.length === 1) && (
              <div className="starter-grid">
                {starters.map((t) => (
                  <button
                    key={t}
                    disabled={busy || !session}
                    onClick={() => void send(t)}
                  >
                    {t} ↗
                  </button>
                ))}
              </div>
            )}
            {a && (
              <article className="product-card">
                <div className="row">
                  <span className="tag">{a.product.category} · fictional</span>
                  <span className="tag">{a.status}</span>
                </div>
                <h3>{a.product.name}</h3>
                <p>
                  {a.product.brand} · {a.product.merchant}
                </p>
                <div className="price">
                  {a.product.currency} {a.product.price.toFixed(2)}
                </div>
                <div className="attributes">
                  {a.product.attributes.map((x) => (
                    <span key={x}>{x}</span>
                  ))}
                </div>
                <p>{a.product.description}</p>
                <MerchantDetails action={a} />
                <small>
                  Payment: {a.payment_method} · Data sharing:{" "}
                  {a.shares_personal_data ? "requested" : "none"}
                </small>
                <div
                  className={`review ${a.decision === "BLOCK" ? "warning" : "safe"}`}
                >
                  <strong>
                    {a.decision === "BLOCK"
                      ? "Blocked by your boundaries"
                      : a.decision === "REVIEW"
                        ? "Your review is needed"
                        : "Within your permissions"}
                  </strong>
                  <ul>
                    {a.rules.map((r) => (
                      <li key={r.rule_id}>{r.explanation}</li>
                    ))}
                  </ul>
                </div>
                {a.status === "pending" && (
                  <div className="decisions">
                    <button
                      className="primary"
                      disabled={busy || a.decision === "BLOCK"}
                      onClick={() => void decide(a, "approve")}
                    >
                      Approve simulated checkout
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => void decide(a, "reject")}
                    >
                      Reject
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => {
                        setText("Change my request: ");
                        document.getElementById("chat-input")?.focus();
                      }}
                    >
                      Refine
                    </button>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void run(async () =>
                          keep(
                            await request<Session>(
                              `/sessions/${session!.id}/alternative`,
                              "POST",
                            ),
                          ),
                        )
                      }
                    >
                      Find another merchant
                    </button>
                  </div>
                )}
              </article>
            )}
            {session?.receipts.map((r) => (
              <div className="notice" key={r.id}>
                <strong>Simulated receipt</strong>
                <p>
                  {r.product.name} · {r.product.currency}{" "}
                  {r.product.price.toFixed(2)}
                </p>
                <small>{r.id} · No real payment or order.</small>
              </div>
            ))}
            {session && session.recommendations.length > 1 && (
              <details>
                <summary>
                  Compare {session.recommendations.length} matching products
                </summary>
                <div className="comparison">
                  {session.recommendations.map((p) => (
                    <div key={p.id}>
                      <strong>{p.name}</strong>
                      <p>
                        {p.currency} {p.price.toFixed(2)} · {p.merchant}
                      </p>
                      <p>{p.attributes.join(" · ")}</p>
                      <button
                        disabled={busy}
                        onClick={() =>
                          void run(async () =>
                            keep(
                              await request<Session>(
                                `/sessions/${session!.id}/products/${p.id}/propose`,
                                "POST",
                              ),
                            ),
                          )
                        }
                      >
                        Choose this product
                      </button>
                    </div>
                  ))}
                </div>
              </details>
            )}
            {busy && <p role="status">Beany is working…</p>}
            <div ref={bottom} />
          </div>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <button
              type="button"
              disabled={busy || !session}
              onClick={() =>
                void run(async () =>
                  keep(
                    await request<Session>(
                      `/sessions/${session!.id}/cancel`,
                      "POST",
                    ),
                  ),
                )
              }
            >
              Cancel shopping task
            </button>
            <div className="scenarios">
              {session?.suggestions.map((t, i) => (
                <button
                  type="button"
                  disabled={busy}
                  key={i}
                  onClick={() => void send(t)}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="input-wrap">
              <textarea
                id="chat-input"
                aria-label="Message Beany"
                rows={2}
                maxLength={2000}
                disabled={busy || !session}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Tell me what you’re looking for…"
              />
              <button
                className="primary"
                disabled={busy || !session || !text.trim()}
              >
                Send ↗
              </button>
            </div>
            <small>
              Ask questions, revise your preferences, or say “cancel this task”.
            </small>
          </form>
        </section>
        <aside className="sidebar">
          {session && (
            <Brief
              key={session.id}
              session={session}
              busy={busy}
              edit={async (field, fact) =>
                run(async () =>
                  keep(
                    await request<Session>(
                      `/sessions/${session.id}/brief`,
                      "PUT",
                      { field, fact },
                    ),
                  ),
                )
              }
              permissions={async (p) =>
                run(async () =>
                  keep(
                    await request<Session>(
                      `/sessions/${session.id}/permissions`,
                      "PUT",
                      p,
                    ),
                  ),
                )
              }
            />
          )}
          <section className="panel activity">
            <div className="eyebrow">SHOPPING OVERSIGHT</div>
            <h2>{session?.stage.replaceAll("_", " ") || "Connecting"}</h2>
            <ol>
              {session?.events
                .filter((e) =>
                  [
                    "search",
                    "intervention",
                    "approve",
                    "reject",
                    "simulated_checkout",
                    "cancel",
                    "brief_edit",
                  ].includes(e.kind),
                )
                .slice(-6)
                .map((e) => (
                  <li key={e.id}>
                    {(
                      {
                        search: "Compared matching products",
                        intervention: "Requested your review",
                        approve: "You approved this action",
                        reject: "You rejected this action",
                        simulated_checkout: "Created a simulated receipt",
                        cancel: "Shopping task cancelled",
                        brief_edit: "Updated your shopping brief",
                      } as Record<string, string>
                    )[e.kind] || e.kind.replaceAll("_", " ")}
                  </li>
                ))}
            </ol>
          </section>
        </aside>
      </main>
      <footer>
        Beany · CS3249 Conversational User Interface
        <span>All products and transactions are fictional.</span>
      </footer>
    </div>
  );
}
