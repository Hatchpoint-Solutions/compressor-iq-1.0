"use client";

import { api, type Asset, type AssetDetail, type ServiceEvent, type AssetIssueFrequency } from "@/lib/api";
import { formatDate, formatNumber, categoryLabel, categoryBadgeClass } from "@/lib/utils";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";

function statusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("active") || s.includes("run")) return "bg-emerald-100 text-emerald-900";
  if (s.includes("down") || s.includes("fault") || s.includes("alarm"))
    return "bg-red-100 text-red-900";
  if (s.includes("idle") || s.includes("standby")) return "bg-amber-100 text-amber-900";
  return "bg-slate-100 text-slate-800";
}

function timelineSort(events: ServiceEvent[]): ServiceEvent[] {
  return [...events].sort((a, b) => {
    const ta = a.event_date ? new Date(a.event_date).getTime() : 0;
    const tb = b.event_date ? new Date(b.event_date).getTime() : 0;
    return ta - tb;
  });
}

export default function MachinesPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [issues, setIssues] = useState<AssetIssueFrequency[]>([]);
  const [timeline, setTimeline] = useState<ServiceEvent[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const listLoadGen = useRef(0);
  const detailLoadGen = useRef(0);

  useEffect(() => {
    const gen = ++listLoadGen.current;
    setListLoading(true);
    setListError(null);
    api.assets
      .list()
      .then((list) => {
        if (gen === listLoadGen.current) setAssets(list);
      })
      .catch((err: unknown) => {
        if (gen === listLoadGen.current) {
          setListError(err instanceof Error ? err.message : "Failed to load assets.");
          setAssets([]);
        }
      })
      .finally(() => {
        if (gen === listLoadGen.current) setListLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setIssues([]);
      setTimeline([]);
      setDetailError(null);
      return;
    }
    const gen = ++detailLoadGen.current;
    setDetailLoading(true);
    setDetailError(null);
    Promise.all([
      api.assets.get(selectedId),
      api.assets.issues(selectedId),
      api.assets.timeline(selectedId, 20),
    ])
      .then(([d, iss, tl]) => {
        if (gen !== detailLoadGen.current) return;
        setDetail(d);
        setIssues(iss);
        setTimeline(timelineSort(tl));
      })
      .catch((err: unknown) => {
        if (gen !== detailLoadGen.current) return;
        setDetailError(err instanceof Error ? err.message : "Failed to load asset detail.");
        setDetail(null);
        setIssues([]);
        setTimeline([]);
      })
      .finally(() => {
        if (gen === detailLoadGen.current) setDetailLoading(false);
      });
  }, [selectedId]);

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <header>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
              CompressorIQ
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
              Machines
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Compressor assets, issue history, and service timeline.
            </p>
          </header>
          <Link
            href="/"
            className="text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-2 hover:text-slate-900"
          >
            ← Home
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-4 xl:col-span-3">
            <div className="table-container">
              <div className="border-b border-slate-200 bg-slate-800 px-4 py-3">
                <h2 className="text-sm font-semibold text-white">Asset list</h2>
                <p className="mt-0.5 text-xs text-slate-300">
                  Select a unit to view detail
                </p>
              </div>
              <div className="max-h-[min(70vh,560px)] overflow-y-auto">
                {listLoading && (
                  <p className="px-4 py-8 text-center text-sm text-slate-500">Loading assets…</p>
                )}
                {!listLoading && listError && (
                  <p className="px-4 py-8 text-center text-sm text-red-600">{listError}</p>
                )}
                {!listLoading && !listError && assets.length === 0 && (
                  <p className="px-4 py-8 text-center text-sm text-slate-500">No assets found.</p>
                )}
                {!listLoading &&
                  !listError &&
                  assets.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setSelectedId(a.id)}
                      className={`flex w-full flex-col gap-1 border-b border-slate-100 px-4 py-3.5 text-left transition hover:bg-slate-50 ${
                        selectedId === a.id ? "bg-amber-50/80 ring-1 ring-inset ring-amber-200" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-mono text-sm font-semibold text-slate-900">
                          {a.unit_id}
                        </span>
                        <span
                          className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${statusBadgeClass(a.status)}`}
                        >
                          {a.status}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600">
                        Eq. {a.equipment_number ?? "—"}
                      </div>
                      <div className="flex items-center justify-between text-xs tabular-nums text-slate-500">
                        <span>Run hours</span>
                        <span className="font-medium text-slate-800">
                          {formatNumber(a.current_run_hours)}
                        </span>
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-8 xl:col-span-9">
            {!selectedId && (
              <div className="stat-card flex min-h-[280px] flex-col items-center justify-center border-dashed border-slate-300 bg-slate-50/50 text-center">
                <p className="text-sm font-medium text-slate-700">No asset selected</p>
                <p className="mt-2 max-w-sm text-sm text-slate-500">
                  Choose a compressor from the list to load unit detail, issue frequency, and the
                  service timeline.
                </p>
              </div>
            )}

            {selectedId && detailLoading && (
              <div className="stat-card animate-pulse space-y-4">
                <div className="h-8 w-48 rounded bg-slate-200" />
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-20 rounded-lg bg-slate-100" />
                  ))}
                </div>
                <div className="h-40 rounded-lg bg-slate-100" />
                <div className="h-64 rounded-lg bg-slate-100" />
              </div>
            )}

            {selectedId && !detailLoading && detailError && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-center shadow-sm">
                <p className="text-sm font-semibold text-red-900">Unable to load asset</p>
                <p className="mt-2 text-sm text-red-800">{detailError}</p>
              </div>
            )}

            {selectedId && !detailLoading && !detailError && detail && (
              <div className="space-y-6">
                <div className="stat-card border-l-4 border-l-slate-700">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Unit
                      </p>
                      <h2 className="mt-1 font-mono text-2xl font-bold text-slate-900">
                        {detail.unit_id}
                      </h2>
                      <p className="mt-1 text-sm text-slate-600">
                        Equipment #{" "}
                        <span className="font-mono font-medium text-slate-800">
                          {detail.equipment_number ?? "—"}
                        </span>
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-md px-3 py-1 text-sm font-medium ${statusBadgeClass(detail.status)}`}
                      >
                        {detail.status}
                      </span>
                      <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm tabular-nums text-slate-800">
                        <span className="text-slate-500">Run hours </span>
                        <span className="font-semibold">{formatNumber(detail.current_run_hours)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="stat-card border-l-4 border-l-slate-500">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Total events
                    </p>
                    <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">
                      {detail.total_events}
                    </p>
                  </div>
                  <div className="stat-card border-l-4 border-l-red-500">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Corrective
                    </p>
                    <p className="mt-2 text-2xl font-bold tabular-nums text-red-700">
                      {detail.corrective_events}
                    </p>
                  </div>
                  <div className="stat-card border-l-4 border-l-green-600">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Preventive
                    </p>
                    <p className="mt-2 text-2xl font-bold tabular-nums text-green-700">
                      {detail.preventive_events}
                    </p>
                  </div>
                  <div className="stat-card border-l-4 border-l-amber-500">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Last service
                    </p>
                    <p className="mt-2 text-lg font-semibold text-slate-900">
                      {formatDate(detail.last_service_date)}
                    </p>
                  </div>
                </section>

                <section className="table-container">
                  <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
                    <h3 className="text-base font-semibold text-slate-900">Issue frequency</h3>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Categories, counts, and run-hour context
                    </p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[640px] text-left text-sm">
                      <thead>
                        <tr className="border-b border-slate-200 bg-white text-xs uppercase tracking-wide text-slate-500">
                          <th className="px-5 py-3 font-medium">Category</th>
                          <th className="px-5 py-3 font-medium text-right">Count</th>
                          <th className="px-5 py-3 font-medium">Last occurrence</th>
                          <th className="px-5 py-3 font-medium text-right">Avg run hours</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {issues.length === 0 ? (
                          <tr>
                            <td colSpan={4} className="px-5 py-8 text-center text-slate-500">
                              No issue frequency data for this asset.
                            </td>
                          </tr>
                        ) : (
                          issues.map((row) => (
                            <tr key={row.category} className="hover:bg-slate-50/80">
                              <td className="px-5 py-3.5 font-medium text-slate-900">
                                {categoryLabel(row.category)}
                              </td>
                              <td className="px-5 py-3.5 text-right tabular-nums text-slate-800">
                                {row.count}
                              </td>
                              <td className="px-5 py-3.5 text-slate-700">
                                {formatDate(row.last_occurrence)}
                              </td>
                              <td className="px-5 py-3.5 text-right tabular-nums text-slate-800">
                                {formatNumber(row.avg_run_hours)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="table-container">
                  <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
                    <h3 className="text-base font-semibold text-slate-900">Service timeline</h3>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Recent events in chronological order (oldest → newest)
                    </p>
                  </div>
                  <ul className="divide-y divide-slate-100">
                    {timeline.length === 0 ? (
                      <li className="px-5 py-8 text-center text-sm text-slate-500">
                        No service events in this window.
                      </li>
                    ) : (
                      timeline.map((ev) => (
                        <li
                          key={ev.id}
                          className="flex flex-col gap-2 px-5 py-4 transition hover:bg-slate-50/80 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-slate-900">
                              {ev.order_description || ev.order_number || "Service event"}
                            </p>
                            <p className="mt-1 font-mono text-xs text-slate-500">
                              {ev.order_number}
                            </p>
                          </div>
                          <div className="flex shrink-0 flex-wrap items-center gap-2 sm:flex-col sm:items-end">
                            <span className="text-sm tabular-nums text-slate-700">
                              {formatDate(ev.event_date)}
                            </span>
                            <span className={categoryBadgeClass(ev.event_category)}>
                              {categoryLabel(ev.event_category)}
                            </span>
                          </div>
                        </li>
                      ))
                    )}
                  </ul>
                </section>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
