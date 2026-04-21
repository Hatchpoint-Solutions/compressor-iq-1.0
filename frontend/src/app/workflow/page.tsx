"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { api, type RecommendationListItem } from "@/lib/api";

function confidenceBadgeClass(label: string): string {
  switch (label) {
    case "high":
      return "bg-green-100 text-green-800";
    case "medium":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "accepted":
      return "bg-green-100 text-green-800";
    case "completed":
      return "bg-blue-100 text-blue-800";
    case "rejected":
      return "bg-red-100 text-red-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function WorkflowIndexPage() {
  const [recommendations, setRecommendations] = useState<
    RecommendationListItem[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadGen = useRef(0);

  useEffect(() => {
    const gen = ++loadGen.current;
    setLoading(true);
    setError(null);
    api.recommendations
      .list(50)
      .then((items) => {
        if (gen === loadGen.current) setRecommendations(items);
      })
      .catch((err: unknown) => {
        if (gen === loadGen.current)
          setError(
            err instanceof Error ? err.message : "Failed to load recommendations."
          );
      })
      .finally(() => {
        if (gen === loadGen.current) setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <header>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
              CompressorIQ
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
              Workflows
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              AI-generated maintenance recommendations and prescribed workflows.
            </p>
          </header>
          <Link
            href="/"
            className="text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-2 hover:text-slate-900"
          >
            ← Home
          </Link>
        </div>

        {recommendations.length === 0 && !loading && !error && (
          <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white px-8 py-16 text-center">
            <p className="text-lg font-semibold text-slate-700">
              No recommendations yet
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Go to{" "}
              <Link
                href="/service-records"
                className="font-medium text-amber-700 underline underline-offset-2"
              >
                Service Records
              </Link>{" "}
              and click &ldquo;Get Recommendation&rdquo; on any event to generate
              your first AI-powered workflow.
            </p>
          </div>
        )}

        {loading && (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-xl bg-slate-100" />
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-center shadow-sm">
            <p className="text-sm font-semibold text-red-900">
              Unable to load recommendations
            </p>
            <p className="mt-2 text-sm text-red-800">{error}</p>
          </div>
        )}

        {!loading && !error && recommendations.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80">
                    <th className="px-5 py-3 font-semibold text-slate-700">
                      Date
                    </th>
                    <th className="px-5 py-3 font-semibold text-slate-700">
                      Issue Category
                    </th>
                    <th className="px-5 py-3 font-semibold text-slate-700">
                      Recommended Action
                    </th>
                    <th className="px-5 py-3 font-semibold text-slate-700 text-center">
                      Confidence
                    </th>
                    <th className="px-5 py-3 font-semibold text-slate-700 text-center">
                      Similar Cases
                    </th>
                    <th className="px-5 py-3 font-semibold text-slate-700 text-center">
                      Status
                    </th>
                    <th className="px-5 py-3 font-semibold text-slate-700">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {recommendations.map((rec) => (
                    <tr
                      key={rec.id}
                      className="border-b border-slate-100 transition hover:bg-slate-50/80"
                    >
                      <td className="whitespace-nowrap px-5 py-3.5 text-slate-700">
                        {formatDate(rec.created_at)}
                      </td>
                      <td className="px-5 py-3.5 font-medium text-slate-900">
                        {rec.likely_issue_category
                          ? rec.likely_issue_category
                              .replace(/_/g, " ")
                              .replace(/\b\w/g, (c) => c.toUpperCase())
                          : "—"}
                      </td>
                      <td className="max-w-[260px] px-5 py-3.5 text-slate-700">
                        {rec.recommended_action
                          ? rec.recommended_action.length > 80
                            ? `${rec.recommended_action.slice(0, 80)}…`
                            : rec.recommended_action
                          : "—"}
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${confidenceBadgeClass(
                            rec.confidence_label
                          )}`}
                        >
                          {Math.round(rec.confidence_score * 100)}%{" "}
                          {rec.confidence_label}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-center tabular-nums text-slate-800">
                        {rec.similar_case_count}
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${statusBadgeClass(
                            rec.status
                          )}`}
                        >
                          {rec.status.charAt(0).toUpperCase() +
                            rec.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/workflow/${rec.id}`}
                          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-slate-900"
                        >
                          Open Workflow
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
