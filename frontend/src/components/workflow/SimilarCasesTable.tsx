"use client";

import type { SimilarCase } from "@/lib/api";
import { formatDate, categoryLabel } from "@/lib/utils";

interface SimilarCasesTableProps {
  cases: SimilarCase[];
}

function pct(score: number, digits = 1): string {
  const v = score > 1 ? score : score * 100;
  return `${v.toFixed(digits)}%`;
}

function matchBadge(score: number): string {
  const pctVal = score > 1 ? score : score * 100;
  if (pctVal >= 70) return "bg-green-100 text-green-800";
  if (pctVal >= 40) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

export function SimilarCasesTable({ cases }: SimilarCasesTableProps) {
  if (cases.length === 0) {
    return (
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-slate-900">
          Similar historical cases
        </h3>
        <p className="mt-3 text-center text-sm text-slate-500">
          No similar cases found.
        </p>
      </div>
    );
  }

  const sorted = [...cases].sort(
    (a, b) => b.similarity_score - a.similarity_score
  );

  return (
    <div className="stat-card p-0 overflow-hidden">
      <div className="px-5 pt-5 pb-3">
        <h3 className="text-sm font-semibold text-slate-900">
          Similar historical cases
        </h3>
        <p className="mt-0.5 text-xs text-slate-500">
          Top {sorted.length} matches used as evidence
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-y border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <th className="px-5 py-2.5">Match</th>
              <th className="px-5 py-2.5">Event ID</th>
              {sorted.some((c) => c.event_date) && (
                <th className="px-5 py-2.5">Date</th>
              )}
              {sorted.some((c) => c.event_category || c.issue_category) && (
                <th className="px-5 py-2.5">Category</th>
              )}
              {sorted.some((c) => c.action_summary) && (
                <th className="px-5 py-2.5">Action</th>
              )}
              <th className="px-5 py-2.5">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sorted.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50/60">
                <td className="px-5 py-3">
                  <span
                    className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${matchBadge(c.similarity_score)}`}
                  >
                    {pct(c.similarity_score)}
                  </span>
                </td>
                <td className="px-5 py-3 font-mono text-xs text-slate-600">
                  {c.service_event_id.length > 12
                    ? `${c.service_event_id.slice(0, 8)}…`
                    : c.service_event_id}
                </td>
                {sorted.some((sc) => sc.event_date) && (
                  <td className="px-5 py-3 text-xs text-slate-600">
                    {formatDate(c.event_date)}
                  </td>
                )}
                {sorted.some(
                  (sc) => sc.event_category || sc.issue_category
                ) && (
                  <td className="px-5 py-3 text-xs text-slate-700">
                    {categoryLabel(
                      c.issue_category ?? c.event_category ?? null
                    )}
                  </td>
                )}
                {sorted.some((sc) => sc.action_summary) && (
                  <td className="px-5 py-3 text-xs text-slate-700">
                    {c.action_summary ?? "—"}
                  </td>
                )}
                <td className="max-w-xs px-5 py-3 text-xs text-slate-600">
                  {c.match_reason ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
