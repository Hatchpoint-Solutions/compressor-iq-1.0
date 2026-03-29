"use client";

import { useState, type FormEvent } from "react";
import type { FeedbackCreate } from "@/lib/api";

interface TechnicianFeedbackFormProps {
  hasServiceEvent: boolean;
  submitting: boolean;
  success: boolean;
  error: string | null;
  onSubmit: (
    data: Omit<FeedbackCreate, "service_event_id" | "recommendation_id">
  ) => Promise<void>;
}

export function TechnicianFeedbackForm({
  hasServiceEvent,
  submitting,
  success,
  error,
  onSubmit,
}: TechnicianFeedbackFormProps) {
  const [actualAction, setActualAction] = useState("");
  const [partsUsed, setPartsUsed] = useState("");
  const [issueResolved, setIssueResolved] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [technicianName, setTechnicianName] = useState("");

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await onSubmit({
      actual_action_taken: actualAction.trim() || null,
      parts_used: partsUsed.trim() || null,
      issue_resolved: issueResolved,
      resolution_notes: resolutionNotes.trim() || null,
      technician_name: technicianName.trim() || null,
    });
  }

  return (
    <div className="stat-card">
      <h3 className="text-sm font-semibold text-slate-900">
        Technician feedback
      </h3>
      <p className="mt-0.5 text-xs text-slate-500">
        Record what was done on site to improve future recommendations
      </p>

      {success ? (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-4 text-center">
          <svg
            className="mx-auto h-8 w-8 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="mt-2 text-sm font-semibold text-green-900">
            Feedback submitted successfully
          </p>
          <p className="mt-1 text-xs text-green-700">
            Your input helps improve future recommendations. Thank you.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* Actual action taken */}
          <FieldGroup label="Actual action taken">
            <textarea
              value={actualAction}
              onChange={(e) => setActualAction(e.target.value)}
              rows={3}
              className="field-input"
              placeholder="Describe work performed…"
            />
          </FieldGroup>

          {/* Parts used */}
          <FieldGroup label="Parts used">
            <textarea
              value={partsUsed}
              onChange={(e) => setPartsUsed(e.target.value)}
              rows={2}
              className="field-input"
              placeholder="e.g., O-ring kit P/N 1234, valve spring, gasket set…"
            />
          </FieldGroup>

          {/* Issue resolved */}
          <div className="flex items-center gap-2.5">
            <input
              id="feedback_resolved"
              type="checkbox"
              checked={issueResolved}
              onChange={(e) => setIssueResolved(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-green-600 focus:ring-green-500"
            />
            <label
              htmlFor="feedback_resolved"
              className="text-sm font-medium text-slate-800"
            >
              Issue resolved
            </label>
          </div>

          {/* Resolution notes */}
          <FieldGroup label="Resolution notes">
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              rows={2}
              className="field-input"
              placeholder="Root cause, observations, follow-up needed…"
            />
          </FieldGroup>

          {/* Technician name */}
          <FieldGroup label="Technician name">
            <input
              type="text"
              value={technicianName}
              onChange={(e) => setTechnicianName(e.target.value)}
              className="field-input"
              placeholder="Name"
            />
          </FieldGroup>

          {error && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          {!hasServiceEvent && (
            <p className="text-sm text-amber-800">
              This recommendation has no linked service event — feedback submit
              is disabled.
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || !hasServiceEvent}
            className="rounded-lg bg-slate-800 px-6 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit feedback"}
          </button>
        </form>
      )}
    </div>
  );
}

function FieldGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-slate-600">
        {label}
      </label>
      {children}
    </div>
  );
}
