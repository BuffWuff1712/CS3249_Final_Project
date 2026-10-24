"use client";
import { useEffect, useState } from "react";
import { PermissionSettings } from "@/components/PermissionSettings";
import { Permissions, request, Session } from "@/lib/beany";

export default function SettingsPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  async function load() {
    setBusy(true);
    setError("");
    try {
      const id = localStorage.getItem("beany-session");
      if (!id) throw new Error("Start a shopping session before changing permissions.");
      setSession(await request<Session>(`/sessions/${id}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load settings.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function save(permissions: Permissions) {
    if (!session) return;
    setBusy(true);
    setSaved(false);
    setError("");
    try {
      if (localStorage.getItem("beany-session") !== session.id) {
        throw new Error("Your shopping session changed. Reload settings before saving.");
      }
      setSession(await request<Session>(`/sessions/${session.id}/permissions`, "PUT", permissions));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save permissions.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header>
        <a className="brand" href="/">
          <span className="brand-icon">b</span>Beany<span className="brand-dot">.</span>
        </a>
        <button disabled={busy} onClick={() => window.location.assign("/")}>Back to shopping</button>
      </header>
      <main className="settings-page">
        <div>
          <h1>Settings</h1>
        </div>
        {error && <div className="error" role="alert">{error}
          {!session && <button disabled={busy} onClick={() => void load()}>Retry</button>}
        </div>}
        {saved && <div className="notice" role="status">Permissions saved. Pending proposals have been cleared; request a new proposal when you return.</div>}
        {busy && <p role="status">{session ? "Saving permissions…" : "Loading settings…"}</p>}
        {session && <PermissionSettings key={session.id} initial={session.permissions} busy={busy} save={save} />}
      </main>
    </div>
  );
}
