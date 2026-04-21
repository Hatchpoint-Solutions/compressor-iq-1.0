"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import {
  api,
  type ManagerListItem,
  type TechnicianListItem,
} from "@/lib/api";

export default function ConfigurationPage() {
  const [technicians, setTechnicians] = useState<TechnicianListItem[]>([]);
  const [managers, setManagers] = useState<ManagerListItem[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [techName, setTechName] = useState("");
  const [mgrName, setMgrName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const loadGen = useRef(0);

  const refresh = useCallback(async () => {
    setError(null);
    const [t, m, s] = await Promise.all([
      api.technicians.list(500),
      api.managers.list(500),
      api.managers.suggestions(100),
    ]);
    setTechnicians(t);
    setManagers(m);
    setSuggestions(s);
  }, []);

  useEffect(() => {
    const gen = ++loadGen.current;
    setLoading(true);
    refresh()
      .catch((e: unknown) => {
        if (gen === loadGen.current) {
          setError(e instanceof Error ? e.message : "Failed to load directory.");
        }
      })
      .finally(() => {
        if (gen === loadGen.current) setLoading(false);
      });
  }, [refresh]);

  async function addTechnician(e: React.FormEvent) {
    e.preventDefault();
    const name = techName.trim();
    if (!name || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.technicians.create(name);
      setTechName("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not add technician.");
    } finally {
      setBusy(false);
    }
  }

  async function addManager(e: React.FormEvent) {
    e.preventDefault();
    const name = mgrName.trim();
    if (!name || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.managers.create(name);
      setMgrName("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not add manager.");
    } finally {
      setBusy(false);
    }
  }

  async function addSuggestedManager(name: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.managers.create(name);
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not add manager.");
    } finally {
      setBusy(false);
    }
  }

  async function removeTechnician(id: string) {
    if (busy || !confirm("Remove this technician from the directory?")) return;
    setBusy(true);
    setError(null);
    try {
      await api.technicians.remove(id);
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not remove technician.");
    } finally {
      setBusy(false);
    }
  }

  async function removeManager(id: string) {
    if (busy || !confirm("Remove this manager from the directory?")) return;
    setBusy(true);
    setError(null);
    try {
      await api.managers.remove(id);
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not remove manager.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col gap-6 p-6 md:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 rounded bg-slate-200" />
          <div className="h-40 rounded-lg bg-slate-100" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-8 p-6 md:p-8">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
          Configuration
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
          Technicians &amp; managers
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Technicians are populated automatically from imported service data; you can add or remove
          names here for assignments and reference. Managers are maintained here; the dashboard can
          show review authors from records as &quot;manager&quot; when present.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="stat-card">
          <h2 className="text-base font-semibold text-slate-900">Technicians</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Names from parsed service actions and manual entries ({technicians.length} total)
          </p>
          <form onSubmit={addTechnician} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={techName}
              onChange={(e) => setTechName(e.target.value)}
              placeholder="Add technician name"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
              disabled={busy}
            />
            <button
              type="submit"
              disabled={busy || !techName.trim()}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-amber-400 transition hover:bg-slate-700 disabled:opacity-50"
            >
              Add
            </button>
          </form>
          <ul className="mt-4 max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
            {technicians.length === 0 ? (
              <li className="px-4 py-6 text-center text-sm text-slate-500">No technicians yet.</li>
            ) : (
              technicians.map((t) => (
                <li
                  key={t.id}
                  className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm text-slate-800"
                >
                  <span>
                    {t.name}
                    {t.event_count > 0 ? (
                      <span className="ml-2 text-xs tabular-nums text-slate-400">
                        ({t.event_count} refs)
                      </span>
                    ) : null}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeTechnician(t.id)}
                    disabled={busy}
                    className="shrink-0 text-xs font-medium text-red-600 hover:underline disabled:opacity-50"
                  >
                    Remove
                  </button>
                </li>
              ))
            )}
          </ul>
        </section>

        <section className="stat-card">
          <h2 className="text-base font-semibold text-slate-900">Managers</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Directory for supervisor names ({managers.length} total). Suggested names come from
            review-comment authors in your data that are not already listed.
          </p>
          <form onSubmit={addManager} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={mgrName}
              onChange={(e) => setMgrName(e.target.value)}
              placeholder="Add manager name"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
              disabled={busy}
            />
            <button
              type="submit"
              disabled={busy || !mgrName.trim()}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-amber-400 transition hover:bg-slate-700 disabled:opacity-50"
            >
              Add
            </button>
          </form>

          {suggestions.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-slate-600">Suggestions from records</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestions.map((name) => (
                  <button
                    key={name}
                    type="button"
                    disabled={busy}
                    onClick={() => addSuggestedManager(name)}
                    className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-900 transition hover:bg-amber-100 disabled:opacity-50"
                  >
                    + {name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <ul className="mt-4 max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
            {managers.length === 0 ? (
              <li className="px-4 py-6 text-center text-sm text-slate-500">No managers listed yet.</li>
            ) : (
              managers.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm text-slate-800"
                >
                  <span>{m.name}</span>
                  <button
                    type="button"
                    onClick={() => removeManager(m.id)}
                    disabled={busy}
                    className="shrink-0 text-xs font-medium text-red-600 hover:underline disabled:opacity-50"
                  >
                    Remove
                  </button>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>
    </div>
  );
}
