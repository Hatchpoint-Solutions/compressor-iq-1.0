"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import {
  api,
  type Asset,
  type RecommendationListItem,
  type TechnicianListItem,
  type WorkOrderDetail,
  type WorkOrderListItem,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";

const SOURCES = [
  { value: "predictive", label: "Predictive" },
  { value: "system", label: "System-generated" },
  { value: "ad_hoc", label: "Ad hoc" },
] as const;

function statusBadge(status: string) {
  const s = status.toLowerCase();
  if (s === "completed") return "bg-emerald-100 text-emerald-900";
  if (s === "cancelled") return "bg-slate-200 text-slate-700";
  if (s === "in_progress") return "bg-amber-100 text-amber-900";
  return "bg-sky-100 text-sky-900";
}

export default function WorkOrdersManagerPage() {
  const [compressors, setCompressors] = useState<Asset[]>([]);
  const [technicians, setTechnicians] = useState<TechnicianListItem[]>([]);
  const [rows, setRows] = useState<WorkOrderListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterCompressor, setFilterCompressor] = useState<string>("");

  const [modalOpen, setModalOpen] = useState(false);
  const [createCompressor, setCreateCompressor] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createSource, setCreateSource] = useState<string>("ad_hoc");
  const [createIssueCategory, setCreateIssueCategory] = useState("");
  const [createRecId, setCreateRecId] = useState("");
  const [createAssignee, setCreateAssignee] = useState("");
  const [recsForMachine, setRecsForMachine] = useState<RecommendationListItem[]>([]);
  const [saving, setSaving] = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WorkOrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const detailLoadGen = useRef(0);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    api.workOrders
      .list({
        status: filterStatus || undefined,
        compressor_id: filterCompressor || undefined,
        limit: 150,
      })
      .then(setRows)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load work orders.")
      )
      .finally(() => setLoading(false));
  }, [filterStatus, filterCompressor]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    api.assets.list().then(setCompressors).catch(() => setCompressors([]));
    api.technicians.list().then(setTechnicians).catch(() => setTechnicians([]));
  }, []);

  useEffect(() => {
    if (!createCompressor) {
      setRecsForMachine([]);
      setCreateRecId("");
      return;
    }
    api.recommendations
      .forMachine(createCompressor)
      .then(setRecsForMachine)
      .catch(() => setRecsForMachine([]));
  }, [createCompressor]);

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

  const openCreate = () => {
    setCreateCompressor(compressors[0]?.id ?? "");
    setCreateTitle("");
    setCreateDesc("");
    setCreateSource("ad_hoc");
    setCreateIssueCategory("");
    setCreateRecId("");
    setCreateAssignee("");
    setModalOpen(true);
  };

  const submitCreate = async () => {
    if (!createCompressor || !createTitle.trim()) return;
    setSaving(true);
    try {
      await api.workOrders.create({
        compressor_id: createCompressor,
        title: createTitle.trim(),
        description: createDesc.trim() || null,
        source: createSource,
        recommendation_id: createRecId || null,
        issue_category: createIssueCategory.trim() || null,
        assigned_technician_id: createAssignee || null,
      });
      setModalOpen(false);
      refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Create failed.");
    } finally {
      setSaving(false);
    }
  };

  const updateDetailAssign = async (technicianId: string | null) => {
    if (!selectedId) return;
    await api.workOrders.update(selectedId, {
      ...(technicianId
        ? { assigned_technician_id: technicianId, clear_assigned_technician: false }
        : { clear_assigned_technician: true }),
    });
    const d = await api.workOrders.get(selectedId);
    setDetail(d);
    refresh();
  };

  const updateDetailStatus = async (status: string) => {
    if (!selectedId) return;
    await api.workOrders.update(selectedId, { status });
    const d = await api.workOrders.get(selectedId);
    setDetail(d);
    refresh();
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-amber-700">
            Service manager
          </p>
          <h1 className="text-2xl font-bold text-slate-900">Work orders</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">
            Create and assign corrective work from predictions, system alerts, or ad hoc requests.
            Technicians execute steps on the My work page.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white shadow hover:bg-amber-600"
        >
          New work order
        </button>
      </header>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Status
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
        <label className="flex min-w-[200px] flex-col gap-1 text-xs font-medium text-slate-600">
          Compressor
          <select
            value={filterCompressor}
            onChange={(e) => setFilterCompressor(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          >
            <option value="">All units</option>
            {compressors.map((c) => (
              <option key={c.id} value={c.id}>
                {c.unit_id}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <div className="table-container overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-900">Fleet queue</h2>
            </div>
            {loading ? (
              <div className="p-8 text-center text-sm text-slate-500">Loading…</div>
            ) : rows.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                No work orders yet. Create one to assign field work.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-slate-100 bg-white text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-4 py-2">Title</th>
                      <th className="px-4 py-2">Unit</th>
                      <th className="px-4 py-2">Source</th>
                      <th className="px-4 py-2">Status</th>
                      <th className="px-4 py-2">Assignee</th>
                      <th className="px-4 py-2">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {rows.map((r) => (
                      <tr
                        key={r.id}
                        onClick={() => setSelectedId(r.id)}
                        className={`cursor-pointer transition hover:bg-slate-50 ${
                          selectedId === r.id ? "bg-amber-50/80" : ""
                        }`}
                      >
                        <td className="px-4 py-3 font-medium text-slate-900">{r.title}</td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-700">{r.unit_id}</td>
                        <td className="px-4 py-3 capitalize text-slate-600">{r.source.replace("_", " ")}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-md px-2 py-0.5 text-xs font-medium ${statusBadge(r.status)}`}
                          >
                            {r.status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {r.assigned_technician_name ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          {formatDate(r.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        <aside className="lg:col-span-2">
          <div className="stat-card min-h-[320px]">
            <h2 className="text-base font-semibold text-slate-900">Detail</h2>
            {!selectedId && (
              <p className="mt-4 text-sm text-slate-500">Select a work order to assign and update status.</p>
            )}
            {selectedId && detailLoading && (
              <p className="mt-4 animate-pulse text-sm text-slate-500">Loading…</p>
            )}
            {detail && !detailLoading && (
              <div className="mt-4 space-y-4">
                <div>
                  <p className="text-xs font-medium uppercase text-slate-500">Title</p>
                  <p className="text-sm font-semibold text-slate-900">{detail.title}</p>
                  {detail.description && (
                    <p className="mt-1 text-sm text-slate-600">{detail.description}</p>
                  )}
                </div>
                <label className="block text-xs font-medium text-slate-600">
                  Assign technician
                  <select
                    value={detail.assigned_technician_id ?? ""}
                    onChange={(e) =>
                      updateDetailAssign(e.target.value ? e.target.value : null)
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Unassigned</option>
                    {technicians.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-medium text-slate-600">
                  Status
                  <select
                    value={detail.status}
                    onChange={(e) => updateDetailStatus(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="open">Open</option>
                    <option value="in_progress">In progress</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </label>
                <div>
                  <p className="text-xs font-medium uppercase text-slate-500">Workflow steps</p>
                  <ol className="mt-2 max-h-64 list-decimal space-y-2 overflow-y-auto pl-4 text-sm text-slate-700">
                    {detail.steps.map((s) => (
                      <li key={s.id}>
                        <span className={s.is_completed ? "line-through opacity-60" : ""}>
                          {s.instruction.slice(0, 120)}
                          {s.instruction.length > 120 ? "…" : ""}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">New work order</h3>
            <div className="mt-4 space-y-3">
              <label className="block text-xs font-medium text-slate-600">
                Compressor
                <select
                  value={createCompressor}
                  onChange={(e) => setCreateCompressor(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">Select unit</option>
                  {compressors.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.unit_id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Title
                <input
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  placeholder="e.g. Investigate high vibration"
                />
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Description (optional)
                <textarea
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                  rows={2}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Source
                <select
                  value={createSource}
                  onChange={(e) => setCreateSource(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  {SOURCES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs font-medium text-slate-600">
                Link to recommendation (optional)
                <select
                  value={createRecId}
                  onChange={(e) => setCreateRecId(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  disabled={!createCompressor}
                >
                  <option value="">None — use issue category below</option>
                  {recsForMachine.map((r) => (
                    <option key={r.id} value={r.id}>
                      {(r.likely_issue_category ?? "Issue").slice(0, 40)} ·{" "}
                      {r.confidence_label}
                    </option>
                  ))}
                </select>
              </label>
              {!createRecId && (
                <label className="block text-xs font-medium text-slate-600">
                  Issue category (for generated steps)
                  <input
                    value={createIssueCategory}
                    onChange={(e) => setCreateIssueCategory(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    placeholder="e.g. oil_leak, detonation, or leave blank for general"
                  />
                </label>
              )}
              <label className="block text-xs font-medium text-slate-600">
                Assign now (optional)
                <select
                  value={createAssignee}
                  onChange={(e) => setCreateAssignee(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">Later</option>
                  {technicians.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={saving || !createCompressor || !createTitle.trim()}
                onClick={() => void submitCreate()}
                className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {saving ? "Saving…" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
