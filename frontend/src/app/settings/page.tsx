"use client";
import { useEffect, useState } from "react";
import { PermissionSettings } from "@/components/PermissionSettings";
import { Permissions, Session } from "@/lib/beany";
import { activeShop, rememberShop, shopRequest, SHOP_KEY, type ShopView } from "@/lib/shopBackend";

export default function SettingsPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [workspace, setWorkspace] = useState<ShopView | null>(null);
  const [saved, setSaved] = useState(false);

  async function load() {
    setBusy(true);
    setError("");
    try {
      const next = await activeShop(); setWorkspace(next); setSession(next.session);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load settings.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function save(permissions: Permissions) {
    if (!session || !workspace) return;
    setBusy(true);
    setSaved(false);
    setError("");
    try {
      if ((localStorage.getItem("beany-session") || localStorage.getItem(SHOP_KEY)) !== session.id) {
        throw new Error("Your shopping session changed. Reload settings before saving.");
      }
      const next = await shopRequest(`/${session.id}/permissions`, "PUT", { revision: workspace.revision, permissions });
      rememberShop(next); setWorkspace(next); setSession(next.session);
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
          <button disabled={busy} onClick={() => void load()}>Retry</button>
        </div>}
        {saved && <div className="notice" role="status">Permissions saved. Pending proposals have been cleared; request a new proposal when you return.</div>}
        {busy && <p role="status">{session ? "Saving permissions…" : "Loading settings…"}</p>}
        {session && <PermissionSettings key={`${session.id}-${workspace?.revision}`} initial={session.permissions} busy={busy} save={save} />}
      </main>
    </div>
  );
}
