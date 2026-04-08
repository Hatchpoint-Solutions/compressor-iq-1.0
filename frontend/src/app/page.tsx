"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  type DashboardSummary,
  type ServiceEvent,
  type DashboardServiceEvent,
  type FleetEventSortField,
  type CompressorDropdownItem,
  type AssetDetail,
  type AssetIssueFrequency,
  type HealthAssessment,
  type RecommendationListItem,
} from "@/lib/api";
import {
  formatDate,
  formatCurrency,
  formatNumber,
  categoryLabel,
  categoryBadgeClass,
  confidenceColor,
} from "@/lib/utils";

function healthColor(health: string): string {
  if (health === "good") return "text-emerald-600";
  if (health === "fair") return "text-amber-600";
  if (health === "warning") return "text-orange-600";
  return "text-red-600";
}

function healthBg(health: string): string {
  if (health === "good") return "bg-emerald-50 border-emerald-200";
  if (health === "fair") return "bg-amber-50 border-amber-200";
  if (health === "warning") return "bg-orange-50 border-orange-200";
  return "bg-red-50 border-red-200";
}

function severityBadge(severity: string): string {
  if (severity === "critical") return "bg-red-100 text-red-900";
  if (severity === "high") return "bg-orange-100 text-orange-900";
  if (severity === "medium") return "bg-amber-100 text-amber-900";
  return "bg-blue-100 text-blue-900";
}

function criticalityLabel(rank: number): string {
  if (rank >= 4) return "High";
  if (rank === 3) return "Elevated";
  if (rank === 2) return "Moderate";
  if (rank === 1) return "Low";
  return "—";
}

const FLEET_SORT_FIELDS: FleetEventSortField[] = [
  "event_date",
  "severity",
  "criticality",
  "technician",
  "manager",
];

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentEvents, setRecentEvents] = useState<DashboardServiceEvent[]>([]);
  const [fleetSortBy, setFleetSortBy] = useState<FleetEventSortField>("event_date");
  const [fleetOrder, setFleetOrder] = useState<"asc" | "desc">("desc");
  const [fleetSecondaryBy, setFleetSecondaryBy] = useState<FleetEventSortField>("severity");
  const [fleetSecondaryOrder, setFleetSecondaryOrder] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedCompressor, setSelectedCompressor] = useState<string>("");
  const [compressorDetail, setCompressorDetail] = useState<AssetDetail | null>(null);
  const [compressorTimeline, setCompressorTimeline] = useState<ServiceEvent[]>([]);
  const [compressorIssues, setCompressorIssues] = useState<AssetIssueFrequency[]>([]);
  const [compressorRecs, setCompressorRecs] = useState<RecommendationListItem[]>([]);
  const [assessment, setAssessment] = useState<HealthAssessment | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [assessmentLoading, setAssessmentLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api.dashboard
      .summary()
      .then((sum) => {
        if (!cancelled) setSummary(sum);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
          setSummary(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.dashboard
      .recentEvents(50, fleetSortBy, fleetOrder, fleetSecondaryBy, fleetSecondaryOrder)
      .then((events) => {
        if (!cancelled) setRecentEvents(events);
      })
      .catch(() => {
        if (!cancelled) setRecentEvents([]);
      });

    return () => {
      cancelled = true;
    };
  }, [fleetSortBy, fleetOrder, fleetSecondaryBy, fleetSecondaryOrder]);

  useEffect(() => {
    const allowed = FLEET_SORT_FIELDS.filter((x) => x !== fleetSortBy);
    if (!allowed.includes(fleetSecondaryBy)) {
      setFleetSecondaryBy(allowed[0] ?? "event_date");
    }
  }, [fleetSortBy, fleetSecondaryBy]);

  const loadCompressorDetail = useCallback((compressorId: string) => {
    if (!compressorId) {
      setCompressorDetail(null);
      setCompressorTimeline([]);
      setCompressorIssues([]);
      setCompressorRecs([]);
      setAssessment(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);

    Promise.all([
      api.assets.get(compressorId),
      api.assets.timeline(compressorId, 50),
      api.assets.issues(compressorId),
      api.recommendations.forMachine(compressorId),
    ])
      .then(([detail, timeline, issues, recs]) => {
        if (!cancelled) {
          setCompressorDetail(detail);
          setCompressorTimeline(timeline);
          setCompressorIssues(issues);
          setCompressorRecs(recs);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCompressorDetail(null);
          setCompressorTimeline([]);
          setCompressorIssues([]);
          setCompressorRecs([]);
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (selectedCompressor) {
      loadCompressorDetail(selectedCompressor);
    } else {
      setCompressorDetail(null);
      setCompressorTimeline([]);
      setCompressorIssues([]);
      setCompressorRecs([]);
      setAssessment(null);
    }
  }, [selectedCompressor, loadCompressorDetail]);

  const runAssessment = useCallback(() => {
    if (!selectedCompressor) return;
    setAssessmentLoading(true);
    setAssessment(null);
    api.recommendations
      .assess(selectedCompressor)
      .then(setAssessment)
      .catch(() => setAssessment(null))
      .finally(() => setAssessmentLoading(false));
  }, [selectedCompressor]);

  if (loading) {
    return (
      <div className="flex flex-1 flex-col gap-8 p-6 md:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 rounded bg-slate-200" />
          <div className="h-4 w-72 rounded bg-slate-200" />
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="stat-card h-28 bg-slate-50" />
            ))}
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

  const compressors: CompressorDropdownItem[] = summary?.compressors ?? [];

  return (
    <div className="flex flex-1 flex-col gap-8 p-6 md:p-8">
      {/* Header */}
      <header className="border-b border-slate-200 pb-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
          CompressorIQ
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Fleet overview and compressor intelligence
        </p>
      </header>

      {/* Fleet Stats */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="stat-card border-l-4 border-l-slate-400">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Total Compressors
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
            {summary?.total_compressors ?? 0}
          </p>
        </div>
        <div className="stat-card border-l-4 border-l-blue-500">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Fleet Run Hours
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
            {formatNumber(summary?.total_fleet_run_hours ?? 0)}
          </p>
        </div>
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
      </section>

      {/* Compressor Selector */}
      <section className="stat-card border-l-4 border-l-amber-500">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Select Compressor
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Choose a compressor to view detailed history, issues, and AI-powered recommendations
            </p>
          </div>
          <div className="w-full sm:w-80">
            <select
              value={selectedCompressor}
              onChange={(e) => setSelectedCompressor(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-900 shadow-sm transition focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
            >
              <option value="">— All Fleet (Overview) —</option>
              {compressors.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.unit_id}
                  {c.compressor_type ? ` — ${c.compressor_type}` : ""}
                  {c.current_run_hours != null ? ` (${formatNumber(c.current_run_hours)} hrs)` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Conditional content: Fleet overview vs Compressor detail */}
      {!selectedCompressor ? (
        <FleetOverview
          summary={summary}
          recentEvents={recentEvents}
          sortBy={fleetSortBy}
          sortOrder={fleetOrder}
          onSortByChange={setFleetSortBy}
          onSortOrderChange={setFleetOrder}
          secondarySortBy={fleetSecondaryBy}
          secondaryOrder={fleetSecondaryOrder}
          onSecondarySortByChange={setFleetSecondaryBy}
          onSecondaryOrderChange={setFleetSecondaryOrder}
        />
      ) : detailLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="stat-card h-24 bg-slate-50" />
            ))}
          </div>
          <div className="stat-card h-64 bg-slate-50" />
          <div className="stat-card h-48 bg-slate-50" />
        </div>
      ) : compressorDetail ? (
        <CompressorDetailView
          detail={compressorDetail}
          timeline={compressorTimeline}
          issues={compressorIssues}
          recommendations={compressorRecs}
          assessment={assessment}
          assessmentLoading={assessmentLoading}
          onRunAssessment={runAssessment}
        />
      ) : (
        <div className="stat-card text-center py-8">
          <p className="text-sm text-slate-500">Unable to load compressor details. Please try another unit.</p>
        </div>
      )}
    </div>
  );
}


/* ────────────────────────────────────────────────────────────────────────── */
/* Fleet Overview (default view)                                              */
/* ────────────────────────────────────────────────────────────────────────── */

function FleetOverview({
  summary,
  recentEvents,
  sortBy,
  sortOrder,
  onSortByChange,
  onSortOrderChange,
  secondarySortBy,
  secondaryOrder,
  onSecondarySortByChange,
  onSecondaryOrderChange,
}: {
  summary: DashboardSummary | null;
  recentEvents: DashboardServiceEvent[];
  sortBy: FleetEventSortField;
  sortOrder: "asc" | "desc";
  onSortByChange: (v: FleetEventSortField) => void;
  onSortOrderChange: (v: "asc" | "desc") => void;
  secondarySortBy: FleetEventSortField;
  secondaryOrder: "asc" | "desc";
  onSecondarySortByChange: (v: FleetEventSortField) => void;
  onSecondaryOrderChange: (v: "asc" | "desc") => void;
}) {
  const router = useRouter();
  const secondaryOptions = FLEET_SORT_FIELDS.filter((f) => f !== sortBy);
  const secondaryValue = secondaryOptions.includes(secondarySortBy)
    ? secondarySortBy
    : secondaryOptions[0] ?? "severity";

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <div className="table-container">
          <div className="flex flex-col gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Service events
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Primary and secondary sort — e.g. severity first, then date within the same severity.
              </p>
            </div>
            <div className="flex w-full max-w-3xl flex-col gap-3 sm:items-end">
              <div className="flex w-full flex-wrap items-center gap-2 sm:justify-end">
                <span className="w-full text-[11px] font-semibold uppercase tracking-wide text-slate-500 sm:w-auto">
                  Primary
                </span>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="whitespace-nowrap">Sort by</span>
                  <select
                    value={sortBy}
                    onChange={(e) => onSortByChange(e.target.value as FleetEventSortField)}
                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                  >
                    <option value="event_date">Recent date</option>
                    <option value="severity">Issue severity</option>
                    <option value="criticality">Criticality (category)</option>
                    <option value="technician">Technician</option>
                    <option value="manager">Manager (review)</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="whitespace-nowrap">Order</span>
                  <select
                    value={sortOrder}
                    onChange={(e) => onSortOrderChange(e.target.value as "asc" | "desc")}
                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                  >
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                </label>
              </div>
              <div className="flex w-full flex-wrap items-center gap-2 sm:justify-end">
                <span className="w-full text-[11px] font-semibold uppercase tracking-wide text-slate-500 sm:w-auto">
                  Then by
                </span>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="whitespace-nowrap">Column</span>
                  <select
                    value={secondaryValue}
                    onChange={(e) => {
                      const v = e.target.value as FleetEventSortField;
                      if (v !== sortBy) onSecondarySortByChange(v);
                    }}
                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                  >
                    {secondaryOptions.map((f) => (
                      <option key={f} value={f}>
                        {f === "event_date"
                          ? "Recent date"
                          : f === "severity"
                            ? "Issue severity"
                            : f === "criticality"
                              ? "Criticality (category)"
                              : f === "technician"
                                ? "Technician"
                                : "Manager (review)"}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="whitespace-nowrap">Order</span>
                  <select
                    value={secondaryOrder}
                    onChange={(e) => onSecondaryOrderChange(e.target.value as "asc" | "desc")}
                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                  >
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                </label>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-white text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Order #</th>
                  <th className="px-4 py-3 font-medium">Description</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Criticality</th>
                  <th className="px-4 py-3 font-medium">Technician</th>
                  <th className="px-4 py-3 font-medium">Manager</th>
                  <th className="px-4 py-3 font-medium text-right">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentEvents.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-5 py-8 text-center text-slate-500">
                      No service events loaded.
                    </td>
                  </tr>
                ) : (
                  recentEvents.map((ev) => (
                    <tr
                      key={ev.id}
                      role="button"
                      tabIndex={0}
                      onClick={() =>
                        router.push(`/service-records?event=${encodeURIComponent(ev.id)}`)
                      }
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          router.push(`/service-records?event=${encodeURIComponent(ev.id)}`);
                        }
                      }}
                      className="group cursor-pointer transition-colors hover:bg-slate-50/80"
                    >
                      <td className="px-4 py-3.5 text-slate-700">
                        <span className="text-amber-700 underline-offset-2 group-hover:underline">
                          {formatDate(ev.event_date)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="font-mono text-sm text-slate-900">
                          {ev.order_number || "—"}
                        </span>
                      </td>
                      <td className="max-w-[220px] px-4 py-3.5 text-slate-700">
                        <span className="line-clamp-2">
                          {ev.order_description || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={categoryBadgeClass(ev.event_category)}>
                          {categoryLabel(ev.event_category)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        {ev.issue_severity ? (
                          <span
                            className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${severityBadge(ev.issue_severity)}`}
                          >
                            {ev.issue_severity}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-slate-700">
                        {ev.criticality_rank > 0 ? criticalityLabel(ev.criticality_rank) : "—"}
                      </td>
                      <td className="max-w-[140px] px-4 py-3.5 text-slate-700">
                        <span className="line-clamp-2 text-sm">
                          {ev.primary_technician_name || "—"}
                        </span>
                      </td>
                      <td className="max-w-[140px] px-4 py-3.5 text-slate-700">
                        <span className="line-clamp-2 text-sm">
                          {ev.manager_name || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right font-medium tabular-nums text-slate-900">
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
          <h2 className="text-base font-semibold text-slate-900">Top Issue Categories</h2>
          <p className="mt-0.5 text-xs text-slate-500">Share of recorded issues by category</p>
          <ul className="mt-4 space-y-4">
            {(summary?.top_issues ?? []).length === 0 ? (
              <li className="text-sm text-slate-500">No issue data yet.</li>
            ) : (
              (summary?.top_issues ?? []).map((issue) => (
                <li key={issue.category}>
                  <Link
                    href={`/service-records?category=${encodeURIComponent(issue.category)}`}
                    className="block rounded-lg outline-none ring-amber-400/0 transition hover:bg-amber-50/80 focus-visible:ring-2"
                  >
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
                        style={{ width: `${Math.min(100, Math.max(0, issue.percentage))}%` }}
                        role="progressbar"
                        aria-valuenow={issue.percentage}
                        aria-valuemin={0}
                        aria-valuemax={100}
                      />
                    </div>
                  </Link>
                </li>
              ))
            )}
          </ul>
        </div>

        <div className="stat-card">
          <h2 className="text-base font-semibold text-slate-900">Machines Needing Attention</h2>
          <p className="mt-0.5 text-xs text-slate-500">Units with elevated recent activity</p>
          <ul className="mt-4 divide-y divide-slate-100">
            {(summary?.machines_needing_attention ?? []).length === 0 ? (
              <li className="py-2 text-sm text-slate-500">All clear — no flagged units.</li>
            ) : (
              (summary?.machines_needing_attention ?? []).map((m) => (
                <li key={m.compressor_id} className="first:pt-0 last:pb-0">
                  <Link
                    href={`/service-records?compressor_id=${encodeURIComponent(m.compressor_id)}&unit=${encodeURIComponent(m.unit_id)}`}
                    className="flex flex-col gap-1 rounded-lg py-3 outline-none ring-amber-400/0 transition hover:bg-slate-50 focus-visible:ring-2"
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
                  </Link>
                </li>
              ))
            )}
          </ul>
        </div>
      </aside>
    </div>
  );
}


/* ────────────────────────────────────────────────────────────────────────── */
/* Compressor Detail View (selected compressor)                               */
/* ────────────────────────────────────────────────────────────────────────── */

function CompressorDetailView({
  detail,
  timeline,
  issues,
  recommendations,
  assessment,
  assessmentLoading,
  onRunAssessment,
}: {
  detail: AssetDetail;
  timeline: ServiceEvent[];
  issues: AssetIssueFrequency[];
  recommendations: RecommendationListItem[];
  assessment: HealthAssessment | null;
  assessmentLoading: boolean;
  onRunAssessment: () => void;
}) {
  const sortedTimeline = [...timeline].sort((a, b) => {
    const ta = a.event_date ? new Date(a.event_date).getTime() : 0;
    const tb = b.event_date ? new Date(b.event_date).getTime() : 0;
    return tb - ta;
  });

  return (
    <div className="space-y-6">
      {/* Compressor header */}
      <div className="stat-card border-l-4 border-l-slate-700">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Selected Compressor
            </p>
            <h2 className="mt-1 font-mono text-2xl font-bold text-slate-900">
              {detail.unit_id}
            </h2>
            {detail.equipment_number && (
              <p className="mt-1 text-sm text-slate-600">
                Equipment #<span className="font-mono font-medium text-slate-800">{detail.equipment_number}</span>
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-900">
              {detail.status}
            </span>
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm tabular-nums text-slate-800">
              <span className="text-slate-500">Run hours </span>
              <span className="font-semibold">{formatNumber(detail.current_run_hours)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="stat-card border-l-4 border-l-slate-500">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Total events</p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{detail.total_events}</p>
        </div>
        <div className="stat-card border-l-4 border-l-red-500">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Corrective</p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-red-700">{detail.corrective_events}</p>
        </div>
        <div className="stat-card border-l-4 border-l-green-600">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Preventive</p>
          <p className="mt-2 text-2xl font-bold tabular-nums text-green-700">{detail.preventive_events}</p>
        </div>
        <div className="stat-card border-l-4 border-l-amber-500">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Last service</p>
          <p className="mt-2 text-lg font-semibold text-slate-900">{formatDate(detail.last_service_date)}</p>
        </div>
      </section>

      {/* AI Health Assessment */}
      <section className="stat-card">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900">AI Health Assessment</h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Proactive analysis combining maintenance history and AI prediction
            </p>
          </div>
          <button
            type="button"
            onClick={onRunAssessment}
            disabled={assessmentLoading}
            className="shrink-0 rounded-lg bg-slate-800 px-5 py-2.5 text-sm font-medium text-amber-400 shadow-sm transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {assessmentLoading ? "Analyzing…" : assessment ? "Re-assess" : "Run Assessment"}
          </button>
        </div>

        {assessmentLoading && (
          <div className="mt-4 flex items-center gap-3 text-sm text-slate-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-amber-500" />
            Analyzing compressor data and generating recommendations…
          </div>
        )}

        {!assessmentLoading && assessment && (
          <div className="mt-5 space-y-4">
            <div className={`rounded-lg border p-4 ${healthBg(assessment.overall_health)}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`text-2xl font-bold ${healthColor(assessment.overall_health)}`}>
                    {assessment.health_score.toFixed(0)}
                  </div>
                  <div>
                    <p className={`text-sm font-semibold capitalize ${healthColor(assessment.overall_health)}`}>
                      {assessment.overall_health}
                    </p>
                    <p className="text-xs text-slate-500">Health Score</p>
                  </div>
                </div>
                {assessment.ai_powered && (
                  <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800">
                    AI-Powered
                  </span>
                )}
              </div>
              <p className="mt-3 text-sm text-slate-700 leading-relaxed">
                {assessment.summary}
              </p>
            </div>

            {assessment.work_orders_created && assessment.work_orders_created.length > 0 && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                <p className="font-semibold">System work orders opened</p>
                <p className="mt-1 text-emerald-800">
                  {assessment.work_orders_created.length} corrective work order(s) were created from
                  high-severity alerts. Review and assign them on{" "}
                  <Link href="/work-orders" className="font-medium underline underline-offset-2">
                    Work orders
                  </Link>
                  .
                </p>
              </div>
            )}

            {assessment.alerts.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-slate-900">
                  Alerts & Recommendations ({assessment.alerts.length})
                </h4>
                {assessment.alerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="flex items-start gap-3">
                      <span className={`mt-0.5 shrink-0 rounded px-2 py-0.5 text-xs font-semibold uppercase ${severityBadge(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-slate-900">{alert.title}</p>
                        <p className="mt-1 text-sm text-slate-600">{alert.description}</p>
                        <div className="mt-2 rounded-md bg-slate-50 px-3 py-2">
                          <p className="text-xs font-medium text-slate-500 uppercase">Recommended Action</p>
                          <p className="mt-0.5 text-sm text-slate-800">{alert.recommended_action}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Issue Frequency */}
      {issues.length > 0 && (
        <section className="table-container">
          <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
            <h3 className="text-base font-semibold text-slate-900">Issue Frequency</h3>
            <p className="mt-0.5 text-xs text-slate-500">Categories, counts, and run-hour context</p>
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
                {issues.map((row) => (
                  <tr key={row.category} className="hover:bg-slate-50/80">
                    <td className="px-5 py-3.5 font-medium text-slate-900">
                      {categoryLabel(row.category)}
                    </td>
                    <td className="px-5 py-3.5 text-right tabular-nums text-slate-800">{row.count}</td>
                    <td className="px-5 py-3.5 text-slate-700">{formatDate(row.last_occurrence)}</td>
                    <td className="px-5 py-3.5 text-right tabular-nums text-slate-800">
                      {formatNumber(row.avg_run_hours)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Recommendations History */}
      <section className="stat-card">
        <h3 className="text-base font-semibold text-slate-900">Recommendation History</h3>
        <p className="mt-0.5 text-xs text-slate-500">Past AI and rule-based recommendations for this unit</p>

        {recommendations.length === 0 ? (
          <p className="mt-4 text-sm text-slate-500">
            No recommendations generated yet. Run a health assessment above or generate from a service event.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {recommendations.slice(0, 10).map((rec) => (
              <Link
                key={rec.id}
                href={`/workflow/${rec.id}`}
                className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-amber-300 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-900">
                      {rec.recommended_action || "Recommendation"}
                    </p>
                    {rec.likely_issue_category && (
                      <p className="mt-1 text-xs text-slate-500">
                        Issue: {categoryLabel(rec.likely_issue_category)}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-slate-400">
                      {formatDate(rec.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span className={`text-sm font-bold tabular-nums ${confidenceColor(rec.confidence_score)}`}>
                      {(rec.confidence_score * 100).toFixed(0)}%
                    </span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      {rec.status}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Service Timeline */}
      <section className="table-container">
        <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-900">Service Timeline</h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Complete maintenance history (newest first)
          </p>
        </div>
        <ul className="divide-y divide-slate-100">
          {sortedTimeline.length === 0 ? (
            <li className="px-5 py-8 text-center text-sm text-slate-500">
              No service events recorded.
            </li>
          ) : (
            sortedTimeline.slice(0, 20).map((ev) => (
              <li
                key={ev.id}
                className="flex flex-col gap-2 px-5 py-4 transition hover:bg-slate-50/80 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
              >
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/service-records?event=${encodeURIComponent(ev.id)}`}
                    className="text-sm font-medium text-slate-900 hover:text-amber-700"
                  >
                    {ev.order_description || ev.order_number || "Service event"}
                  </Link>
                  <p className="mt-1 font-mono text-xs text-slate-500">{ev.order_number}</p>
                  {ev.run_hours_at_event != null && (
                    <p className="mt-0.5 text-xs text-slate-400">
                      Run hours: {formatNumber(ev.run_hours_at_event)}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2 sm:flex-col sm:items-end">
                  <span className="text-sm tabular-nums text-slate-700">
                    {formatDate(ev.event_date)}
                  </span>
                  <span className={categoryBadgeClass(ev.event_category)}>
                    {categoryLabel(ev.event_category)}
                  </span>
                  {ev.order_cost != null && (
                    <span className="text-xs tabular-nums text-slate-500">
                      {formatCurrency(ev.order_cost)}
                    </span>
                  )}
                </div>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}
