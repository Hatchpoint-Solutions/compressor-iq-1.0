"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  type AnalyticsEntityOption,
  type FleetCompareResponse,
  type FleetMaintenanceOverview,
} from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/utils";

const PIE_COLORS = ["#dc2626", "#16a34a", "#64748b"];

/** Must stay in sync with backend `FLEET_COMPARE_MAX_ENTITIES`. */
const MAX_COMPARE_ENTITIES = 12;

function defaultDateRange(): { from: string; to: string } {
  const end = new Date();
  const start = new Date();
  start.setFullYear(start.getFullYear() - 1);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

export default function AnalyticsPage() {
  const defaults = useMemo(() => defaultDateRange(), []);
  const [dateFrom, setDateFrom] = useState(defaults.from);
  const [dateTo, setDateTo] = useState(defaults.to);
  const [granularity, setGranularity] = useState<"month" | "year">("month");

  const [overview, setOverview] = useState<FleetMaintenanceOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  const [entityKind, setEntityKind] = useState<"compressor" | "site">("compressor");
  const [entityOptions, setEntityOptions] = useState<AnalyticsEntityOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [compareResult, setCompareResult] = useState<FleetCompareResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const loadOverview = useCallback(() => {
    setOverviewLoading(true);
    setOverviewError(null);
    api.analytics
      .fleetOverview({
        date_from: dateFrom,
        date_to: dateTo,
        granularity,
      })
      .then(setOverview)
      .catch((e: unknown) => {
        setOverviewError(e instanceof Error ? e.message : "Failed to load analytics.");
        setOverview(null);
      })
      .finally(() => setOverviewLoading(false));
  }, [dateFrom, dateTo, granularity]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    api.analytics
      .fleetEntities(entityKind)
      .then(setEntityOptions)
      .catch(() => setEntityOptions([]));
    setSelectedIds(new Set());
    setCompareResult(null);
  }, [entityKind]);

  const toggleEntity = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < MAX_COMPARE_ENTITIES) {
        next.add(id);
      }
      return next;
    });
    setCompareError(null);
  };

  const resetComparison = () => {
    setSelectedIds(new Set());
    setCompareResult(null);
    setCompareError(null);
  };

  const runCompare = () => {
    if (selectedIds.size < 2) {
      setCompareError("Select at least two entities (up to four).");
      return;
    }
    setCompareLoading(true);
    setCompareError(null);
    api.analytics
      .fleetCompare({
        entity_type: entityKind,
        entity_ids: Array.from(selectedIds),
        date_from: dateFrom,
        date_to: dateTo,
      })
      .then(setCompareResult)
      .catch((e: unknown) => {
        setCompareError(e instanceof Error ? e.message : "Comparison failed.");
        setCompareResult(null);
      })
      .finally(() => setCompareLoading(false));
  };

  const pieRows = overview
    ? [
        { name: "Corrective", value: overview.corrective_cost },
        { name: "Preventive", value: overview.preventive_cost },
        { name: "Other", value: overview.other_cost },
      ].filter((r) => r.value > 0)
    : [];

  const compareChartData =
    compareResult?.entities.map((e) => ({
      label: e.label.length > 24 ? `${e.label.slice(0, 22)}…` : e.label,
      fullLabel: e.label,
      corrective: e.corrective_cost,
      preventive: e.preventive_cost,
      other: e.other_cost,
    })) ?? [];

  const compareChartHeight = useMemo(() => {
    const n = compareChartData.length;
    if (n === 0) return 320;
    return Math.min(640, Math.max(280, n * 48));
  }, [compareChartData.length]);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Fleet analytics</h1>
        <p className="text-slate-600 mt-1 max-w-3xl">
          Maintenance spend over time, corrective versus preventive cost, fleet utilization snapshots,
          and side-by-side comparison for compressors or sites over a configurable period.
        </p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-800 mb-3">Time horizon</h2>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            From
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            To
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            Bucket
            <select
              value={granularity}
              onChange={(e) => setGranularity(e.target.value as "month" | "year")}
              className="rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900 min-w-[120px]"
            >
              <option value="month">By month</option>
              <option value="year">By year</option>
            </select>
          </label>
          <button
            type="button"
            onClick={loadOverview}
            className="rounded-md bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium px-4 py-2"
          >
            Apply range
          </button>
        </div>
      </section>

      {overviewLoading && (
        <p className="text-slate-500 text-sm">Loading fleet metrics…</p>
      )}
      {overviewError && (
        <p className="text-red-600 text-sm" role="alert">
          {overviewError}
        </p>
      )}

      {overview && !overviewLoading && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Total maintenance (period)
              </div>
              <div className="text-2xl font-semibold text-slate-900 mt-1">
                {formatCurrency(overview.total_maintenance_cost)}
              </div>
              <div className="text-xs text-slate-500 mt-2">
                {formatDateLabel(overview.date_from)} — {formatDateLabel(overview.date_to)}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Corrective vs preventive (events)
              </div>
              <div className="text-sm text-slate-800 mt-2 space-y-1">
                <div>
                  Corrective:{" "}
                  <span className="font-medium">{formatNumber(overview.corrective_event_count)}</span>
                </div>
                <div>
                  Preventive:{" "}
                  <span className="font-medium">{formatNumber(overview.preventive_event_count)}</span>
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Fleet snapshot (current)
              </div>
              <div className="text-sm text-slate-800 mt-2 space-y-1">
                <div>Units: {formatNumber(overview.fleet_run_hours_snapshot.compressor_count)}</div>
                <div>
                  Avg run hours:{" "}
                  {overview.fleet_run_hours_snapshot.avg_current_run_hours != null
                    ? formatNumber(overview.fleet_run_hours_snapshot.avg_current_run_hours)
                    : "—"}
                </div>
                <div>
                  Avg age (years):{" "}
                  {overview.fleet_run_hours_snapshot.avg_age_years != null
                    ? `${overview.fleet_run_hours_snapshot.avg_age_years.toFixed(1)} yrs`
                    : "—"}
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                Notes
              </div>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                Aging trend uses average run hours recorded on work orders in each period. Costs use
                order totals where available; categories follow corrective and preventive maintenance
                labels in your data.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">
                Maintenance cost ({granularity === "month" ? "monthly" : "annual"})
              </h3>
              <div className="h-72 w-full">
                {overview.cost_series.length === 0 ? (
                  <p className="text-sm text-slate-500">No cost data in this range.</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={overview.cost_series}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200" />
                      <XAxis dataKey="period" tick={{ fontSize: 11 }} className="text-slate-600" />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v) => `$${Number(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
                      />
                      <Tooltip
                        formatter={(value: number | undefined) => formatCurrency(value ?? 0)}
                        labelFormatter={(label) => `Period: ${label}`}
                      />
                      <Bar dataKey="total_cost" name="Maintenance cost" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">
                Cost split: corrective vs preventive
              </h3>
              <div className="h-72 w-full flex items-center justify-center">
                {pieRows.length === 0 ? (
                  <p className="text-sm text-slate-500">No categorized cost in this range.</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieRows}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        label={({ name, percent }) =>
                          `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                      >
                        {pieRows.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number | undefined) => formatCurrency(value ?? 0)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-800 mb-4">
              Fleet wear proxy: avg run hours at service
            </h3>
            <div className="h-72 w-full">
              {overview.fleet_aging_series.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No run-hour readings on events in this range. Upload or enrich events with run hours
                  to see this trend.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={overview.fleet_aging_series}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200" />
                    <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(value: number | null | undefined) =>
                        value != null ? `${formatNumber(value)} hrs` : "—"
                      }
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="avg_run_hours_at_service"
                      name="Avg run hours (at event)"
                      stroke="#0ea5e9"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Comparison</h2>
          <p className="text-sm text-slate-600 mt-1">
            Pick at least two {entityKind === "compressor" ? "compressors" : "sites"} (up to{" "}
            {MAX_COMPARE_ENTITIES}), then compare costs for the same date range as above. Use Reset to
            clear and choose different entities.
          </p>
        </div>

        <div className="flex flex-wrap gap-4 items-center">
          <label className="text-sm text-slate-700">
            Entity type{" "}
            <select
              value={entityKind}
              onChange={(e) => setEntityKind(e.target.value as "compressor" | "site")}
              className="ml-2 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            >
              <option value="compressor">Compressor</option>
              <option value="site">Site</option>
            </select>
          </label>
          <span className="text-sm text-slate-500">
            Selected: {selectedIds.size} / {MAX_COMPARE_ENTITIES}
          </span>
          <button
            type="button"
            onClick={runCompare}
            disabled={compareLoading || selectedIds.size < 2}
            className="rounded-md bg-slate-800 hover:bg-slate-900 disabled:opacity-50 text-white text-sm font-medium px-4 py-2"
          >
            {compareLoading ? "Comparing…" : "Compare"}
          </button>
          <button
            type="button"
            onClick={resetComparison}
            disabled={compareLoading}
            className="rounded-md border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-50 text-slate-800 text-sm font-medium px-4 py-2"
          >
            Reset
          </button>
        </div>

        {compareError && (
          <p className="text-red-600 text-sm" role="alert">
            {compareError}
          </p>
        )}

        <div className="max-h-56 overflow-y-auto rounded-md border border-slate-200 divide-y divide-slate-100">
          {entityOptions.length === 0 ? (
            <p className="p-3 text-sm text-slate-500">No entities loaded.</p>
          ) : (
            entityOptions.map((opt) => {
              const on = selectedIds.has(opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => toggleEntity(opt.id)}
                  className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-slate-50 ${
                    on ? "bg-amber-50 text-amber-950" : "text-slate-800"
                  }`}
                >
                  <span
                    className={`inline-flex h-4 w-4 shrink-0 rounded border ${
                      on ? "bg-amber-500 border-amber-600" : "border-slate-300"
                    }`}
                    aria-hidden
                  />
                  <span className="font-mono text-xs text-slate-500">{opt.id.slice(0, 8)}…</span>
                  <span>{opt.label}</span>
                </button>
              );
            })
          )}
        </div>

        {compareResult && compareChartData.length > 0 && (
          <div className="space-y-4 pt-2">
            <h3 className="text-sm font-semibold text-slate-800">Total maintenance by entity</h3>
            <div className="w-full" style={{ height: compareChartHeight }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={compareChartData} layout="vertical" margin={{ left: 16, right: 16 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200" />
                  <XAxis type="number" tickFormatter={(v) => `$${v >= 1000 ? `${v / 1000}k` : v}`} />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={120}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(value: number | undefined, name: string) => [
                      formatCurrency(value ?? 0),
                      name,
                    ]}
                    labelFormatter={(_, payload) =>
                      payload?.[0]?.payload?.fullLabel ?? ""
                    }
                  />
                  <Legend />
                  <Bar dataKey="corrective" name="Corrective" stackId="a" fill="#dc2626" />
                  <Bar dataKey="preventive" name="Preventive" stackId="a" fill="#16a34a" />
                  <Bar dataKey="other" name="Other" stackId="a" fill="#64748b" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-700">
                  <tr>
                    <th className="text-left p-2 font-medium">Entity</th>
                    <th className="text-right p-2 font-medium">Events</th>
                    <th className="text-right p-2 font-medium">Total</th>
                    <th className="text-right p-2 font-medium">Corrective</th>
                    <th className="text-right p-2 font-medium">Preventive</th>
                    <th className="text-right p-2 font-medium">Avg order</th>
                    <th className="text-right p-2 font-medium">Avg run hrs</th>
                  </tr>
                </thead>
                <tbody>
                  {compareResult.entities.map((e) => (
                    <tr key={e.entity_id} className="border-t border-slate-100">
                      <td className="p-2 text-slate-900">{e.label}</td>
                      <td className="p-2 text-right">{formatNumber(e.event_count)}</td>
                      <td className="p-2 text-right">{formatCurrency(e.total_cost)}</td>
                      <td className="p-2 text-right">{formatCurrency(e.corrective_cost)}</td>
                      <td className="p-2 text-right">{formatCurrency(e.preventive_cost)}</td>
                      <td className="p-2 text-right">{formatCurrency(e.avg_order_cost)}</td>
                      <td className="p-2 text-right">
                        {e.avg_run_hours_at_event != null ? formatNumber(e.avg_run_hours_at_event) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function formatDateLabel(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
