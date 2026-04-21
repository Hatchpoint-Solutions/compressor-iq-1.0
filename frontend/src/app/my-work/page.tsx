"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import {
  api,
  type TechnicianListItem,
  type WorkOrderDetail,
  type WorkOrderListItem,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";

const STORAGE_KEY = "ciq_technician_id";

export default function MyWorkPage() {
  const [technicians, setTechnicians] = useState<TechnicianListItem[]>([]);
  const [techId, setTechId] = useState<string>("");
  const [rows, setRows] = useState<WorkOrderListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WorkOrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [stepBusy, setStepBusy] = useState<string | null>(null);
  const detailLoadGen = useRef(0);

  useEffect(() => {
    api.technicians.list().then((list) => {
      setTechnicians(list);
      const saved = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
      if (saved && list.some((t) => t.id === saved)) {
        setTechId(saved);
      } else if (list.length === 1) {
        setTechId(list[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (techId && typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, techId);
    }
  }, [techId]);

  const refresh = useCallback(() => {
    if (!techId) {
      setRows([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api.workOrders
      .list({ assigned_technician_id: techId, limit: 100 })
      .then((list) =>
        list.filter((w) => w.status !== "completed" && w.status !== "cancelled")
      )
      .then(setRows)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load work orders.")
      )
      .finally(() => setLoading(false));
  }, [techId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    const gen = ++detailLoadGen.current;
    setDetailLoading(true);
    api.workOrders
      .get(selectedId)
      .then((d) => {
        if (gen === detailLoadGen.current) setDetail(d);
      })
      .catch(() => {
        if (gen === detailLoadGen.current) setDetail(null);
      })
      .finally(() => {
        if (gen === detailLoadGen.current) setDetailLoading(false);
      });
  }, [selectedId]);

  const toggleStep = async (stepId: string, next: boolean) => {
    if (!detail) return;
    setStepBusy(stepId);
    try {
      const updated = await api.workOrders.updateStep(detail.id, stepId, {
        is_completed: next,
      });
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              steps: prev.steps.map((s) => (s.id === stepId ? updated : s)),
              status:
                prev.status === "open" && next ? "in_progress" : prev.status,
            }
          : prev
      );
      refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not update step.");
    } finally {
      setStepBusy(null);
    }
  };

  const markWoComplete = async () => {
    if (!detail) return;
    try {
      await api.workOrders.update(detail.id, { status: "completed" });
      setSelectedId(null);
      refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not complete work order.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">
          Field technician
        </p>
        <h1 className="text-2xl font-bold text-slate-900">My work</h1>
        <p className="mt-1 max-w-xl text-sm text-slate-600">
          Work orders assigned to you. Open a row for full step-by-step instructions and mark steps
          complete as you go.
        </p>
      </header>

      <div className="mb-6 max-w-md">
        <label className="block text-xs font-medium text-slate-600">
          You are
          <select
            value={techId}
            onChange={(e) => {
              setTechId(e.target.value);
              setSelectedId(null);
            }}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-900"
          >
            <option value="">Select your name…</option>
            {technicians.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        {technicians.length === 0 && (
          <p className="mt-2 text-xs text-amber-800">
            No technicians in the directory yet. Import service data so technicians appear, or add
            records in the database.
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {!techId ? (
        <p className="text-sm text-slate-500">Choose your profile to see assigned work.</p>
      ) : loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="stat-card max-w-lg">
          <p className="text-sm text-slate-600">
            No open work orders assigned to you. Your manager assigns jobs from{" "}
            <span className="font-medium text-slate-800">Work orders</span>, or they are created
            from recommendations.
          </p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <section className="lg:col-span-2">
            <div className="table-container overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">Assigned to me</h2>
              </div>
              <ul className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(r.id)}
                      className={`flex w-full flex-col items-start gap-1 px-4 py-3 text-left transition hover:bg-slate-50 ${
                        selectedId === r.id ? "bg-emerald-50/80" : ""
                      }`}
                    >
                      <span className="font-medium text-slate-900">{r.title}</span>
                      <span className="font-mono text-xs text-slate-600">{r.unit_id}</span>
                      <span className="text-xs text-slate-500">
                        {r.source.replace("_", " ")} · {formatDate(r.created_at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="lg:col-span-3">
            <div className="stat-card">
              {!selectedId && (
                <p className="text-sm text-slate-500">Select a work order to view instructions.</p>
              )}
              {selectedId && detailLoading && (
                <p className="animate-pulse text-sm text-slate-500">Loading…</p>
              )}
              {detail && !detailLoading && (
                <>
                  <div className="border-b border-slate-100 pb-4">
                    <h2 className="text-lg font-semibold text-slate-900">{detail.title}</h2>
                    <p className="mt-1 font-mono text-sm text-slate-600">{detail.unit_id}</p>
                    {detail.description && (
                      <p className="mt-2 text-sm text-slate-700">{detail.description}</p>
                    )}
                  </div>
                  <ol className="mt-6 space-y-4">
                    {detail.steps
                      .slice()
                      .sort((a, b) => a.step_number - b.step_number)
                      .map((s) => (
                        <li
                          key={s.id}
                          className={`rounded-lg border p-4 ${
                            s.is_completed
                              ? "border-emerald-200 bg-emerald-50/50"
                              : "border-slate-200 bg-white"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <input
                              type="checkbox"
                              checked={s.is_completed}
                              disabled={stepBusy === s.id}
                              onChange={(e) => void toggleStep(s.id, e.target.checked)}
                              className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-600"
                            />
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-medium text-slate-500">
                                Step {s.step_number}
                              </p>
                              <p className="mt-1 whitespace-pre-wrap text-sm text-slate-900">
                                {s.instruction}
                              </p>
                              {s.rationale && (
                                <p className="mt-2 text-xs text-slate-600">{s.rationale}</p>
                              )}
                              {s.required_evidence && (
                                <p className="mt-2 text-xs font-medium text-amber-900">
                                  Evidence: {s.required_evidence}
                                </p>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                  </ol>
                  <div className="mt-8 flex flex-wrap gap-2 border-t border-slate-100 pt-6">
                    <button
                      type="button"
                      onClick={() => void markWoComplete()}
                      className="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700"
                    >
                      Mark work order complete
                    </button>
                  </div>
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
