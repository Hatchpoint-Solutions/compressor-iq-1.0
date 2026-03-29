"use client";

import type { Recommendation } from "@/lib/api";
import { categoryLabel } from "@/lib/utils";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface RecommendationCardProps {
  recommendation: Recommendation;
}

export function RecommendationCard({ recommendation: rec }: RecommendationCardProps) {
  const category = rec.likely_issue_category ?? rec.issue_category_id;
  const evidence = rec.evidence_summary;

  return (
    <div className="stat-card space-y-6 border-l-4 border-l-slate-700">
      {/* Header: Issue Category + Recommended Action */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Likely issue
          </p>
          <h2 className="mt-1 text-xl font-bold text-slate-900">
            {category ? categoryLabel(category) : "Unclassified"}
          </h2>
          {rec.recommended_action && (
            <p className="mt-2 text-sm font-medium text-amber-700">
              {rec.recommended_action}
            </p>
          )}
        </div>
        <div className="shrink-0">
          <ConfidenceBadge
            score={rec.confidence_score}
            label={rec.confidence_label}
          />
        </div>
      </div>

      {/* Reasoning */}
      {rec.reasoning?.trim() && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Explanation
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {rec.reasoning}
          </p>
        </div>
      )}

      {rec.fallback_note && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-sm text-amber-800">{rec.fallback_note}</p>
        </div>
      )}

      {/* Evidence summary grid */}
      <div className="grid gap-3 sm:grid-cols-3">
        <EvidenceCell
          label="Similar cases"
          value={String(rec.similar_case_count)}
        />
        <EvidenceCell
          label="Most frequent action"
          value={rec.most_frequent_action ?? "—"}
          span={2}
        />
        <EvidenceCell
          label="Resolution rate"
          value={
            rec.resolution_rate != null
              ? `${((rec.resolution_rate > 1 ? rec.resolution_rate : rec.resolution_rate * 100)).toFixed(1)}%`
              : "—"
          }
        />
        {evidence && (
          <>
            <EvidenceCell
              label="Events (30 days)"
              value={String(evidence.recent_events_last_30_days)}
            />
            <EvidenceCell
              label="Avg interval"
              value={
                evidence.avg_days_between_events != null
                  ? `${Math.round(evidence.avg_days_between_events)} days`
                  : "—"
              }
            />
          </>
        )}
      </div>

      {/* Suggested parts / checks */}
      {rec.suggested_parts_or_checks && rec.suggested_parts_or_checks.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Suggested parts / checks
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {rec.suggested_parts_or_checks.map((item, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-300"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recurrence signals */}
      {rec.recurrence_signals && rec.recurrence_signals.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recurrence signals
          </p>
          <ul className="mt-2 space-y-1.5">
            {rec.recurrence_signals.map((s, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-slate-700"
              >
                <SeverityDot severity={s.severity} />
                <span>{s.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function EvidenceCell({
  label,
  value,
  span = 1,
}: {
  label: string;
  value: string;
  span?: number;
}) {
  return (
    <div
      className={`rounded-lg border border-slate-200 bg-slate-50/80 px-4 py-3 ${
        span === 2 ? "sm:col-span-2" : ""
      }`}
    >
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold tabular-nums text-slate-900">
        {value}
      </dd>
    </div>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const color =
    severity === "high"
      ? "bg-red-500"
      : severity === "medium"
        ? "bg-amber-500"
        : "bg-slate-400";
  return (
    <span
      className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${color}`}
      aria-label={`${severity} severity`}
    />
  );
}
