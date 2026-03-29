const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

// ── Shared types ────────────────────────────────────────────────────────

export interface DashboardSummary {
  total_events: number;
  total_compressors: number;
  recent_events_count: number;
  corrective_count: number;
  preventive_count: number;
  avg_cost: number | null;
  top_issues: { category: string; count: number; percentage: number }[];
  machines_needing_attention: {
    compressor_id: string;
    unit_id: string;
    recent_event_count: number;
    last_event_category: string | null;
    last_event_date: string | null;
  }[];
}

export interface ServiceEvent {
  id: string;
  compressor_id: string;
  order_number: string;
  order_description: string | null;
  event_date: string | null;
  event_date_estimated?: boolean;
  event_category: string | null;
  maintenance_activity_type: string | null;
  order_status: string | null;
  run_hours_at_event: number | null;
  order_cost: number | null;
  plant_code: string | null;
  customer_name: string | null;
}

export interface ServiceEventDetail extends ServiceEvent {
  technician_notes_raw: string | null;
  technician_notes_clean: string | null;
  actions: ServiceEventAction[];
  notes: ServiceEventNote[];
  measurements: ServiceEventMeasurement[];
}

export interface ServiceEventAction {
  id: string;
  service_event_id: string;
  action_type_id: string | null;
  action_type_raw: string | null;
  component: string | null;
  description: string | null;
  technician_id: string | null;
  technician_name_raw: string | null;
  action_date: string | null;
  run_hours_at_action: number | null;
  sequence_number: number;
}

export interface ServiceEventNote {
  id: string;
  service_event_id: string;
  note_type: string;
  raw_text: string;
  cleaned_text: string | null;
  author_name: string | null;
  note_date: string | null;
  sequence_number: number;
}

export interface ServiceEventMeasurement {
  id: string;
  service_event_id: string;
  measurement_type: string;
  value: number;
  unit: string | null;
  measured_at: string | null;
  source: string | null;
}

export interface MaintenanceAction {
  id: string;
  service_event_id: string;
  action_type: string | null;
  component: string | null;
  description: string | null;
  technician_name: string | null;
  action_date: string | null;
  run_hours_at_action: number | null;
}

export interface Asset {
  id: string;
  unit_id: string;
  equipment_number: string | null;
  compressor_type: string | null;
  manufacturer: string | null;
  model: string | null;
  status: string;
  site_id: string | null;
  current_run_hours: number | null;
  first_seen_date: string | null;
  created_at: string | null;
}

export interface AssetDetail extends Asset {
  total_events: number;
  corrective_events: number;
  preventive_events: number;
  last_service_date: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface EventStats {
  by_category: Record<string, number>;
  by_month: Record<string, number>;
  by_activity_type: Record<string, number>;
  total_cost: number | null;
  avg_cost: number | null;
}

export interface AssetIssueFrequency {
  category: string;
  count: number;
  last_occurrence: string | null;
  avg_run_hours: number | null;
}

// ── Recommendation engine types ─────────────────────────────────────────

export interface WorkflowStep {
  id: string;
  recommendation_id: string;
  step_number: number;
  instruction: string;
  rationale: string | null;
  required_evidence: string | null;
  is_completed: boolean;
  completed_at: string | null;
  notes: string | null;
}

export interface SimilarCase {
  id: string;
  service_event_id: string;
  similarity_score: number;
  match_reason: string | null;
  event_date?: string | null;
  machine_id?: string | null;
  machine_unit_id?: string | null;
  issue_category?: string | null;
  event_category?: string | null;
  action_summary?: string | null;
  resolution_status?: string | null;
}

export interface EvidenceSummary {
  similar_case_count: number;
  top_action: string | null;
  top_action_label: string | null;
  top_action_frequency: number;
  resolution_rate: number | null;
  recent_events_last_30_days: number;
  recent_events_last_90_days: number;
  recurrence_signal_count: number;
  avg_days_between_events: number | null;
}

export interface RecurrenceSignal {
  signal_type: string;
  description: string;
  event_count: number;
  severity: string;
}

export interface RecommendationListItem {
  id: string;
  compressor_id: string;
  likely_issue_category: string | null;
  recommended_action: string | null;
  confidence_score: number;
  confidence_label: string;
  similar_case_count: number;
  status: string;
  created_at: string | null;
}

export interface Recommendation {
  id: string;
  service_event_id: string | null;
  compressor_id: string;
  machine_id: string | null;
  issue_category_id?: string | null;
  likely_issue_category: string | null;
  recommended_action: string | null;
  confidence_score: number;
  confidence_label: string;
  reasoning: string | null;
  evidence_summary: EvidenceSummary | null;
  recurrence_signals: RecurrenceSignal[] | null;
  suggested_parts_or_checks: string[] | null;
  similar_case_count: number;
  most_frequent_action: string | null;
  resolution_rate: number | null;
  fallback_note: string | null;
  status: string;
  created_at: string | null;
  workflow_steps: WorkflowStep[];
  similar_cases: SimilarCase[];
}

export interface FeedbackCreate {
  service_event_id: string;
  recommendation_id?: string | null;
  actual_action_taken?: string | null;
  issue_resolved?: boolean | null;
  resolution_notes?: string | null;
  parts_used?: string | null;
  technician_name?: string | null;
}

export interface FeedbackResponse {
  id: string;
  service_event_id: string;
  recommendation_id: string | null;
  actual_action_taken: string | null;
  issue_resolved: boolean | null;
  resolution_notes: string | null;
  parts_used: string | null;
  feedback_date: string | null;
  technician_name: string | null;
  created_at: string | null;
}

// ── API client ──────────────────────────────────────────────────────────

export const api = {
  dashboard: {
    summary: () => fetchAPI<DashboardSummary>("/api/dashboard/summary"),
    recentEvents: (limit = 10) =>
      fetchAPI<ServiceEvent[]>(`/api/dashboard/recent-events?limit=${limit}`),
    recurringIssues: () =>
      fetchAPI<{ category: string; count: number; percentage: number }[]>(
        "/api/dashboard/recurring-issues"
      ),
  },

  events: {
    list: (params: Record<string, string>) => {
      const qs = new URLSearchParams(params).toString();
      return fetchAPI<PaginatedResponse<ServiceEvent>>(
        `/api/service-events/?${qs}`
      );
    },
    get: (id: string) => fetchAPI<ServiceEventDetail>(`/api/service-events/${id}`),
    categories: () => fetchAPI<string[]>("/api/service-events/categories"),
    stats: (compressorId?: string) =>
      fetchAPI<EventStats>(
        `/api/service-events/stats${compressorId ? `?compressor_id=${compressorId}` : ""}`
      ),
  },

  assets: {
    list: () => fetchAPI<Asset[]>("/api/compressors/"),
    get: (id: string) => fetchAPI<AssetDetail>(`/api/compressors/${id}`),
    timeline: (id: string, limit = 100) =>
      fetchAPI<ServiceEvent[]>(`/api/compressors/${id}/timeline?limit=${limit}`),
    issues: (id: string) =>
      fetchAPI<AssetIssueFrequency[]>(`/api/compressors/${id}/issues`),
  },

  recommendations: {
    list: (limit = 50) =>
      fetchAPI<RecommendationListItem[]>(
        `/api/recommendations/?limit=${limit}`
      ),
    generate: (eventId: string) =>
      fetchAPI<Recommendation>(`/api/recommendations/generate/${eventId}`, {
        method: "POST",
      }),
    get: (id: string) =>
      fetchAPI<Recommendation>(`/api/recommendations/${id}`),
    forMachine: (machineId: string) =>
      fetchAPI<Recommendation[]>(`/api/recommendations/machine/${machineId}`),
    updateStatus: (id: string, status: string) =>
      fetchAPI<{ id: string; status: string }>(
        `/api/recommendations/${id}/status?status=${status}`,
        { method: "PUT" }
      ),
    updateStep: (
      stepId: string,
      data: { is_completed?: boolean; notes?: string }
    ) =>
      fetchAPI<WorkflowStep>(
        `/api/recommendations/workflow-step/${stepId}`,
        { method: "PUT", body: JSON.stringify(data) }
      ),
  },

  feedback: {
    submit: (data: FeedbackCreate) =>
      fetchAPI<FeedbackResponse>("/api/feedback/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    forEvent: (eventId: string) =>
      fetchAPI<FeedbackResponse>(`/api/feedback/event/${eventId}`),
  },

  ingestion: {
    upload: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/api/ingestion/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json();
    },
    list: () => fetchAPI<unknown[]>("/api/ingestion/uploads"),
  },
};
