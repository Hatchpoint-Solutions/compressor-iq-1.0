"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import {
  api,
  type FeedbackCreate,
  type Recommendation,
  type WorkflowStep,
} from "@/lib/api";

// ── State shape ─────────────────────────────────────────────────────────

interface State {
  recommendation: Recommendation | null;
  loading: boolean;
  error: string | null;
  stepBusyId: string | null;
  statusBusy: boolean;
  feedbackSubmitting: boolean;
  feedbackSuccess: boolean;
  feedbackError: string | null;
}

const initialState: State = {
  recommendation: null,
  loading: true,
  error: null,
  stepBusyId: null,
  statusBusy: false,
  feedbackSubmitting: false,
  feedbackSuccess: false,
  feedbackError: null,
};

// ── Actions ─────────────────────────────────────────────────────────────

type Action =
  | { type: "FETCH_START" }
  | { type: "FETCH_SUCCESS"; payload: Recommendation }
  | { type: "FETCH_ERROR"; payload: string }
  | { type: "STEP_BUSY"; payload: string | null }
  | { type: "STEP_UPDATED"; payload: WorkflowStep }
  | { type: "STATUS_BUSY"; payload: boolean }
  | { type: "STATUS_UPDATED"; payload: string }
  | { type: "FEEDBACK_START" }
  | { type: "FEEDBACK_SUCCESS" }
  | { type: "FEEDBACK_ERROR"; payload: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "FETCH_START":
      return { ...state, loading: true, error: null };
    case "FETCH_SUCCESS":
      return { ...state, loading: false, recommendation: action.payload };
    case "FETCH_ERROR":
      return {
        ...state,
        loading: false,
        error: action.payload,
        recommendation: null,
      };
    case "STEP_BUSY":
      return { ...state, stepBusyId: action.payload };
    case "STEP_UPDATED": {
      if (!state.recommendation) return state;
      const steps = state.recommendation.workflow_steps.map((s) =>
        s.id === action.payload.id ? action.payload : s
      );
      return {
        ...state,
        stepBusyId: null,
        recommendation: { ...state.recommendation, workflow_steps: steps },
      };
    }
    case "STATUS_BUSY":
      return { ...state, statusBusy: action.payload };
    case "STATUS_UPDATED":
      return {
        ...state,
        statusBusy: false,
        recommendation: state.recommendation
          ? { ...state.recommendation, status: action.payload }
          : null,
      };
    case "FEEDBACK_START":
      return {
        ...state,
        feedbackSubmitting: true,
        feedbackError: null,
      };
    case "FEEDBACK_SUCCESS":
      return {
        ...state,
        feedbackSubmitting: false,
        feedbackSuccess: true,
      };
    case "FEEDBACK_ERROR":
      return {
        ...state,
        feedbackSubmitting: false,
        feedbackError: action.payload,
      };
    default:
      return state;
  }
}

// ── Hook ────────────────────────────────────────────────────────────────

export function useRecommendation(id: string) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const fetchGen = useRef(0);

  useEffect(() => {
    if (!id) {
      dispatch({ type: "FETCH_ERROR", payload: "Missing recommendation ID." });
      return;
    }
    const gen = ++fetchGen.current;
    dispatch({ type: "FETCH_START" });

    api.recommendations
      .get(id)
      .then((r) => {
        if (gen === fetchGen.current) dispatch({ type: "FETCH_SUCCESS", payload: r });
      })
      .catch((err: unknown) => {
        if (gen !== fetchGen.current) return;
        dispatch({
          type: "FETCH_ERROR",
          payload:
            err instanceof Error ? err.message : "Failed to load recommendation.",
        });
      });
  }, [id]);

  const completeStep = useCallback(
    async (step: WorkflowStep) => {
      if (step.is_completed) return;
      dispatch({ type: "STEP_BUSY", payload: step.id });
      try {
        const updated = await api.recommendations.updateStep(step.id, {
          is_completed: true,
        });
        dispatch({ type: "STEP_UPDATED", payload: updated });
      } catch (e) {
        dispatch({ type: "STEP_BUSY", payload: null });
        throw e;
      }
    },
    []
  );

  const addStepNotes = useCallback(
    async (step: WorkflowStep, notes: string) => {
      dispatch({ type: "STEP_BUSY", payload: step.id });
      try {
        const updated = await api.recommendations.updateStep(step.id, { notes });
        dispatch({ type: "STEP_UPDATED", payload: updated });
      } catch (e) {
        dispatch({ type: "STEP_BUSY", payload: null });
        throw e;
      }
    },
    []
  );

  const updateStatus = useCallback(
    async (status: string) => {
      if (!id) return;
      dispatch({ type: "STATUS_BUSY", payload: true });
      try {
        await api.recommendations.updateStatus(id, status);
        dispatch({ type: "STATUS_UPDATED", payload: status });
      } catch (e) {
        dispatch({ type: "STATUS_BUSY", payload: false });
        throw e;
      }
    },
    [id]
  );

  const submitFeedback = useCallback(
    async (data: Omit<FeedbackCreate, "service_event_id" | "recommendation_id">) => {
      const rec = state.recommendation;
      if (!rec?.service_event_id) {
        dispatch({
          type: "FEEDBACK_ERROR",
          payload: "No linked service event — feedback cannot be submitted.",
        });
        return;
      }
      dispatch({ type: "FEEDBACK_START" });
      try {
        await api.feedback.submit({
          service_event_id: rec.service_event_id,
          recommendation_id: rec.id,
          ...data,
        });
        dispatch({ type: "FEEDBACK_SUCCESS" });
      } catch (err: unknown) {
        dispatch({
          type: "FEEDBACK_ERROR",
          payload: err instanceof Error ? err.message : "Submission failed.",
        });
      }
    },
    [state.recommendation]
  );

  return {
    ...state,
    completeStep,
    addStepNotes,
    updateStatus,
    submitFeedback,
  };
}
