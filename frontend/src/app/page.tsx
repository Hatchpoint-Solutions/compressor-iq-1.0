"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, type DashboardSummary, type ServiceEvent } from "@/lib/api";
import {
  formatDate,
  formatCurrency,
  categoryLabel,
  categoryBadgeClass,
} from "@/lib/utils";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentEvents, setRecentEvents] = useState<ServiceEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([api.dashboard.summary(), api.dashboard.recentEvents(8)])
      .then(([sum, events]) => {
        if (!cancelled) {
          setSummary(sum);
          setRecentEvents(events);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load dashboard data."
          );
          setSummary(null);
          setRecentEvents([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex flex-1 flex-col gap-8 p-6 md:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 rounded bg-slate-200" />
          <div className="h-4 w-72 rounded bg-slate-200" />
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="stat-card h-28 bg-slate-50" />
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="table-container h-96 bg-slate-50 lg:col-span-2" />
            <div className="space-y-4">
              <div className="stat-card h-48 bg-slate-50" />
              <div className="stat-card h-48 bg-slate-50" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-center shadow-sm">
          <p className="text-sm font-semibold text-red-900">Unable to load dashboard</p>
          <p className="mt-2 text-sm text-red-800">{error}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-amber-400 transition hover:bg-slate-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-8 p-6 md:p-8">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
          CompressorIQ
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Compressor maintenance overview
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="stat-card border-l-4 border-l-slate-400">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Total Service Events
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
            {summary?.total_events ?? 0}
          </p>
        </div>
        <div className="stat-card border-l-4 border-l-red-500">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Corrective Events
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-red-700">
            {summary?.corrective_count ?? 0}
          </p>
        </div>
        <div className="stat-card border-l-4 border-l-green-600">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Preventive Events
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-green-700">
            {summary?.preventive_count ?? 0}
          </p>
        </div>
        <div className="stat-card border-l-4 border-l-amber-500">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Average Cost
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
            {formatCurrency(summary?.avg_cost ?? null)}
          </p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <div className="table-container">
            <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
              <h2 className="text-base font-semibold text-slate-900">
                Recent Service Events
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Latest maintenance activity across the fleet
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-white text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-5 py-3 font-medium">Date</th>
                    <th className="px-5 py-3 font-medium">Order #</th>
                    <th className="px-5 py-3 font-medium">Description</th>
                    <th className="px-5 py-3 font-medium">Category</th>
                    <th className="px-5 py-3 font-medium text-right">Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentEvents.length === 0 ? (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-5 py-8 text-center text-slate-500"
                      >
                        No recent service events.
                      </td>
                    </tr>
                  ) : (
                    recentEvents.map((ev) => (
                      <tr
                        key={ev.id}
                        className="transition-colors hover:bg-slate-50/80"
                      >
                        <td className="px-5 py-3.5 text-slate-700">
                          <Link
                            href={`/service-records?event=${encodeURIComponent(ev.id)}`}
                            className="block text-amber-700 underline-offset-2 hover:underline"
                          >
                            {formatDate(ev.event_date)}
                          </Link>
                        </td>
                        <td className="px-5 py-3.5">
                          <Link
                            href={`/service-records?event=${encodeURIComponent(ev.id)}`}
                            className="font-mono text-sm text-slate-900 hover:text-amber-700"
                          >
                            {ev.order_number || "—"}
                          </Link>
                        </td>
                        <td className="max-w-xs px-5 py-3.5 text-slate-700">
                          <Link
                            href={`/service-records?event=${encodeURIComponent(ev.id)}`}
                            className="line-clamp-2 hover:text-amber-700"
                          >
                            {ev.order_description || "—"}
                          </Link>
                        </td>
                        <td className="px-5 py-3.5">
                          <span
                            className={categoryBadgeClass(ev.event_category)}
                          >
                            {categoryLabel(ev.event_category)}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right font-medium tabular-nums text-slate-900">
                          {formatCurrency(ev.order_cost)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <aside className="flex flex-col gap-6">
          <div className="stat-card">
            <h2 className="text-base font-semibold text-slate-900">
              Top Issue Categories
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Share of recorded issues by category
            </p>
            <ul className="mt-4 space-y-4">
              {(summary?.top_issues ?? []).length === 0 ? (
                <li className="text-sm text-slate-500">No issue data yet.</li>
              ) : (
                (summary?.top_issues ?? []).map((issue) => (
                  <li key={issue.category}>
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="font-medium text-slate-800">
                        {categoryLabel(issue.category)}
                      </span>
                      <span className="tabular-nums text-slate-600">
                        {issue.count}{" "}
                        <span className="text-slate-400">
                          ({issue.percentage.toFixed(0)}%)
                        </span>
                      </span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-amber-500 transition-all"
                        style={{
                          width: `${Math.min(100, Math.max(0, issue.percentage))}%`,
                        }}
                        role="progressbar"
                        aria-valuenow={issue.percentage}
                        aria-valuemin={0}
                        aria-valuemax={100}
                      />
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="stat-card">
            <h2 className="text-base font-semibold text-slate-900">
              Machines Needing Attention
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Units with elevated recent activity
            </p>
            <ul className="mt-4 divide-y divide-slate-100">
              {(summary?.machines_needing_attention ?? []).length === 0 ? (
                <li className="py-2 text-sm text-slate-500">
                  All clear — no flagged units.
                </li>
              ) : (
                (summary?.machines_needing_attention ?? []).map((m) => (
                  <li
                    key={m.compressor_id}
                    className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-sm font-semibold text-slate-900">
                        {m.unit_id}
                      </span>
                      <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                        {m.recent_event_count} events
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Last event: {formatDate(m.last_event_date)}
                    </p>
                  </li>
                ))
              )}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
