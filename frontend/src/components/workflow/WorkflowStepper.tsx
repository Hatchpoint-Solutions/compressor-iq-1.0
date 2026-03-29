"use client";

import { useState } from "react";
import type { WorkflowStep } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface WorkflowStepperProps {
  steps: WorkflowStep[];
  busyStepId: string | null;
  onComplete: (step: WorkflowStep) => Promise<void>;
  onAddNotes: (step: WorkflowStep, notes: string) => Promise<void>;
}

export function WorkflowStepper({
  steps,
  busyStepId,
  onComplete,
  onAddNotes,
}: WorkflowStepperProps) {
  const sorted = [...steps].sort((a, b) => a.step_number - b.step_number);
  const completedCount = sorted.filter((s) => s.is_completed).length;
  const progress =
    sorted.length > 0 ? Math.round((completedCount / sorted.length) * 100) : 0;

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Prescribed workflow
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Complete each step as work is performed in the field
          </p>
        </div>
        <div className="text-right">
          <span className="text-lg font-bold tabular-nums text-slate-900">
            {completedCount}/{sorted.length}
          </span>
          <p className="text-xs text-slate-500">steps done</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-green-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <ol className="mt-5 space-y-2">
        {sorted.length === 0 ? (
          <li className="py-4 text-center text-sm text-slate-500">
            No workflow steps defined.
          </li>
        ) : (
          sorted.map((step, idx) => (
            <StepItem
              key={step.id}
              step={step}
              index={idx}
              isBusy={busyStepId === step.id}
              isLast={idx === sorted.length - 1}
              onComplete={onComplete}
              onAddNotes={onAddNotes}
            />
          ))
        )}
      </ol>
    </div>
  );
}

// ── Individual step ─────────────────────────────────────────────────────

function StepItem({
  step,
  index,
  isBusy,
  isLast,
  onComplete,
  onAddNotes,
}: {
  step: WorkflowStep;
  index: number;
  isBusy: boolean;
  isLast: boolean;
  onComplete: (step: WorkflowStep) => Promise<void>;
  onAddNotes: (step: WorkflowStep, notes: string) => Promise<void>;
}) {
  const done = step.is_completed;
  const [showNotes, setShowNotes] = useState(false);
  const [noteDraft, setNoteDraft] = useState(step.notes ?? "");
  const [savingNote, setSavingNote] = useState(false);

  async function handleCheck() {
    if (done || isBusy) return;
    try {
      await onComplete(step);
    } catch {
      /* parent handles */
    }
  }

  async function handleSaveNotes() {
    if (!noteDraft.trim()) return;
    setSavingNote(true);
    try {
      await onAddNotes(step, noteDraft.trim());
      setShowNotes(false);
    } catch {
      /* parent handles */
    } finally {
      setSavingNote(false);
    }
  }

  return (
    <li className="relative flex gap-3">
      {/* Vertical connector line */}
      {!isLast && (
        <div
          className={`absolute left-[15px] top-[32px] bottom-0 w-px ${
            done ? "bg-green-300" : "bg-slate-200"
          }`}
        />
      )}

      {/* Circle / check indicator */}
      <button
        type="button"
        onClick={handleCheck}
        disabled={done || isBusy}
        className={`relative z-10 mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold transition-all ${
          done
            ? "border-green-500 bg-green-500 text-white"
            : isBusy
              ? "border-slate-300 bg-slate-100 text-slate-400"
              : "border-slate-300 bg-white text-slate-500 hover:border-green-400 hover:text-green-600"
        }`}
        aria-label={done ? `Step ${step.step_number} completed` : `Complete step ${step.step_number}`}
      >
        {done ? (
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        ) : isBusy ? (
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
        ) : (
          <span>{index + 1}</span>
        )}
      </button>

      {/* Content */}
      <div
        className={`min-w-0 flex-1 rounded-lg border px-4 py-3 ${
          done
            ? "border-green-200 bg-green-50/50"
            : "border-slate-200 bg-white"
        }`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-slate-500">
              Step {step.step_number}
            </p>
            <p
              className={`mt-1 text-sm leading-relaxed ${
                done
                  ? "text-green-900 line-through decoration-green-600/40"
                  : "text-slate-800"
              }`}
            >
              {step.instruction}
            </p>
          </div>
        </div>

        {step.rationale && (
          <p className="mt-2 text-xs italic text-slate-500">
            {step.rationale}
          </p>
        )}

        {step.required_evidence && (
          <p className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-500">
            <span className="shrink-0 font-semibold uppercase tracking-wide text-slate-400">
              Evidence:
            </span>
            {step.required_evidence}
          </p>
        )}

        {done && step.completed_at && (
          <p className="mt-2 text-xs text-green-700">
            Completed {formatDate(step.completed_at)}
          </p>
        )}

        {step.notes && !showNotes && (
          <p className="mt-2 rounded bg-slate-100 px-3 py-2 text-xs text-slate-700">
            {step.notes}
          </p>
        )}

        {/* Notes toggle */}
        {!showNotes ? (
          <button
            type="button"
            onClick={() => setShowNotes(true)}
            className="mt-2 text-xs font-medium text-slate-500 underline-offset-2 hover:text-slate-700 hover:underline"
          >
            {step.notes ? "Edit notes" : "Add notes"}
          </button>
        ) : (
          <div className="mt-3 space-y-2">
            <textarea
              value={noteDraft}
              onChange={(e) => setNoteDraft(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
              placeholder="Step notes…"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSaveNotes}
                disabled={savingNote || !noteDraft.trim()}
                className="rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50"
              >
                {savingNote ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                onClick={() => setShowNotes(false)}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </li>
  );
}
