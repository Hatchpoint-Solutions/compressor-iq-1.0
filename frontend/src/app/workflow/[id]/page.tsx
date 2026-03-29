"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useRecommendation } from "@/hooks/useRecommendation";
import {
  RecommendationCard,
  SimilarCasesTable,
  WorkflowStepper,
  TechnicianFeedbackForm,
} from "@/components/workflow";

export default function WorkflowRecommendationPage() {
  const params = useParams();
  const id =
    typeof params.id === "string"
      ? params.id
      : Array.isArray(params.id)
        ? params.id[0]
        : "";

  const {
    recommendation: rec,
    loading,
    error,
    stepBusyId,
    statusBusy,
    feedbackSubmitting,
    feedbackSuccess,
    feedbackError,
    completeStep,
    addStepNotes,
    updateStatus,
    submitFeedback,
  } = useRecommendation(id);

  // ── Loading skeleton ────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 md:p-8">
        <div className="mx-auto max-w-4xl animate-pulse space-y-4">
          <div className="h-8 w-56 rounded bg-slate-200" />
          <div className="h-44 rounded-xl bg-slate-100" />
          <div className="h-32 rounded-xl bg-slate-100" />
          <div className="h-56 rounded-xl bg-slate-100" />
        </div>
      </div>
    );
  }

  // ── Error state ─────────────────────────────────────────────────────
  if (error || !rec) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 md:p-8">
        <div className="mx-auto max-w-lg rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center shadow-sm">
          <p className="text-sm font-semibold text-red-900">
            Recommendation unavailable
          </p>
          <p className="mt-2 text-sm text-red-800">
            {error ?? "Not found."}
          </p>
          <Link
            href="/service-records"
            className="mt-4 inline-block text-sm font-medium text-slate-800 underline underline-offset-2"
          >
            Back to service records
          </Link>
        </div>
      </div>
    );
  }

  // ── Main workflow view ──────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Page header */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <header>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
              CompressorIQ &middot; Technician Workflow
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
              Recommendation
            </h1>
            <p className="mt-1 font-mono text-xs text-slate-500">
              {rec.machine_id ?? rec.compressor_id} &middot; {rec.id.slice(0, 8)}
            </p>
          </header>
          <Link
            href="/service-records"
            className="text-sm font-medium text-slate-600 underline decoration-slate-300 underline-offset-2 hover:text-slate-900"
          >
            &larr; Service records
          </Link>
        </div>

        {/* 1 — Recommendation card (issue, confidence, evidence) */}
        <RecommendationCard recommendation={rec} />

        {/* 2 — Similar historical cases */}
        <SimilarCasesTable cases={rec.similar_cases} />

        {/* 3 — Prescribed workflow */}
        <WorkflowStepper
          steps={rec.workflow_steps}
          busyStepId={stepBusyId}
          onComplete={completeStep}
          onAddNotes={addStepNotes}
        />

        {/* 4 — Technician feedback */}
        <TechnicianFeedbackForm
          hasServiceEvent={!!rec.service_event_id}
          submitting={feedbackSubmitting}
          success={feedbackSuccess}
          error={feedbackError}
          onSubmit={submitFeedback}
        />

        {/* 5 — Status actions */}
        <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Recommendation status
            </p>
            <p className="mt-1 text-sm text-slate-700">
              Current:{" "}
              <StatusBadge status={rec.status} />
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {rec.status !== "accepted" && (
              <button
                type="button"
                disabled={statusBusy}
                onClick={() => updateStatus("accepted")}
                className="rounded-lg bg-green-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-green-800 disabled:opacity-50"
              >
                Accept
              </button>
            )}
            {rec.status !== "completed" && (
              <button
                type="button"
                disabled={statusBusy}
                onClick={() => updateStatus("completed")}
                className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-50"
              >
                Mark complete
              </button>
            )}
            {rec.status !== "rejected" && (
              <button
                type="button"
                disabled={statusBusy}
                onClick={() => updateStatus("rejected")}
                className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-900 transition hover:bg-red-100 disabled:opacity-50"
              >
                Reject
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-slate-100 text-slate-700",
    accepted: "bg-green-100 text-green-800",
    completed: "bg-blue-100 text-blue-800",
    rejected: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${
        styles[status] ?? styles.pending
      }`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
