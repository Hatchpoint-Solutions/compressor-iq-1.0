const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
/** Default request timeout (ms). Prevents the UI from hanging indefinitely if the API is down or unreachable. */
const DEFAULT_FETCH_TIMEOUT_MS = Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS) || 45_000;

function authHeaders(): Record<string, string> {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

type FetchAPIOptions = RequestInit & { timeoutMs?: number };

async function fetchAPI<T>(path: string, options?: FetchAPIOptions): Promise<T> {
  const { timeoutMs: timeoutOverride, ...rest } = options ?? {};
  const timeoutMs = timeoutOverride ?? DEFAULT_FETCH_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...rest.headers,
      },
    });
  } catch (e: unknown) {
    const name = e && typeof e === "object" && "name" in e ? String((e as { name: string }).name) : "";
    if (name === "AbortError") {
      throw new Error(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s (${API_BASE}). Is the API running and NEXT_PUBLIC_API_URL correct?`
      );
    }
    throw new Error(
      e instanceof Error
        ? `${e.message} (${API_BASE})`
        : `Network error (${API_BASE})`
    );
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

// ── Shared types ────────────────────────────────────────────────────────

export interface CompressorDropdownItem {
  id: string;
  unit_id: string;
  status: string;
  current_run_hours: number | null;
  equipment_number: string | null;
  compressor_type: string | null;
}

export interface DashboardSummary {
  total_events: number;
  total_compressors: number;
  total_fleet_run_hours: number;
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
  compressors: CompressorDropdownItem[];
}

export interface HealthAlertItem {
  severity: string;
  title: string;
  description: string;
  recommended_action: string;
}

export interface HealthAssessment {
  compressor_id: string;
  unit_id: string;
  overall_health: string;
  health_score: number;
  summary: string;
  alerts: HealthAlertItem[];
  recent_event_count_30d: number;
  recent_event_count_90d: number;
  total_events: number;
  current_run_hours: number | null;
  last_service_date: string | null;
  top_issues: string[];
  ai_powered: boolean;
  assessed_at: string | null;
  work_orders_created?: string[];
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

/** Dashboard fleet table row — includes derived sort/display fields from the API. */
export interface DashboardServiceEvent extends ServiceEvent {
  issue_severity: string | null;
  criticality_rank: number;
  primary_technician_name: string | null;
  manager_name: string | null;
}

export type FleetEventSortField =
  | "event_date"
  | "severity"
  | "criticality"
  | "technician"
  | "manager";

export interface TechnicianListItem {
  id: string;
  name: string;
  event_count: number;
}

export interface ManagerListItem {
  id: string;
  name: string;
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

// ── Work orders ─────────────────────────────────────────────────────────

export interface WorkOrderStep {
  id: string;
  work_order_id: string;
  step_number: number;
  instruction: string;
  rationale: string | null;
  required_evidence: string | null;
  is_completed: boolean;
  completed_at: string | null;
  notes: string | null;
}

export interface WorkOrderListItem {
  id: string;
  title: string;
  description: string | null;
  compressor_id: string;
  unit_id: string;
  source: string;
  status: string;
  assigned_technician_id: string | null;
  assigned_technician_name: string | null;
  recommendation_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
}

export interface WorkOrderDetail extends WorkOrderListItem {
  steps: WorkOrderStep[];
}

export interface WorkOrderCreatePayload {
  compressor_id: string;
  title: string;
  description?: string | null;
  source?: string;
  recommendation_id?: string | null;
  issue_category?: string | null;
  assigned_technician_id?: string | null;
}

export interface WorkOrderUpdatePayload {
  status?: string;
  assigned_technician_id?: string | null;
  clear_assigned_technician?: boolean;
  title?: string;
  description?: string | null;
}

// ── Fleet analytics ─────────────────────────────────────────────────────

export interface FleetCostPeriodPoint {
  period: string;
  total_cost: number;
  event_count: number;
}

export interface FleetAgingPoint {
  period: string;
  avg_run_hours_at_service: number | null;
  events_with_run_hours: number;
}

export interface FleetRunHoursSnapshot {
  compressor_count: number;
  avg_current_run_hours: number | null;
  median_current_run_hours: number | null;
  avg_age_years: number | null;
}

export interface FleetMaintenanceOverview {
  granularity: "month" | "year";
  date_from: string;
  date_to: string;
  cost_series: FleetCostPeriodPoint[];
  total_maintenance_cost: number;
  corrective_cost: number;
  preventive_cost: number;
  other_cost: number;
  corrective_event_count: number;
  preventive_event_count: number;
  other_event_count: number;
  fleet_aging_series: FleetAgingPoint[];
  fleet_run_hours_snapshot: FleetRunHoursSnapshot;
}

export interface AnalyticsEntityOption {
  id: string;
  label: string;
}

export interface CompareEntityMetrics {
  entity_id: string;
  label: string;
  total_cost: number;
  event_count: number;
  corrective_cost: number;
  preventive_cost: number;
  other_cost: number;
  avg_order_cost: number | null;
  avg_run_hours_at_event: number | null;
}

export interface FleetCompareResponse {
  entity_type: "compressor" | "site";
  date_from: string;
  date_to: string;
  entities: CompareEntityMetrics[];
}

export interface NotificationItem {
  id: string;
  category: string;
  title: string;
  body: string | null;
  compressor_id: string | null;
  work_order_id: string | null;
  technician_id: string | null;
  read_at: string | null;
  created_at: string | null;
}

// ── API client ──────────────────────────────────────────────────────────

export const api = {
  dashboard: {
    summary: () => fetchAPI<DashboardSummary>("/api/dashboard/summary"),
    recentEvents: (
      limit = 50,
      sortBy: FleetEventSortField = "event_date",
      order: "asc" | "desc" = "desc",
      secondarySortBy?: FleetEventSortField,
      secondaryOrder: "asc" | "desc" = "desc"
    ) => {
      const q = new URLSearchParams({
        limit: String(limit),
        sort_by: sortBy,
        order,
        secondary_order: secondaryOrder,
      });
      if (secondarySortBy) {
        q.set("secondary_sort_by", secondarySortBy);
      }
      return fetchAPI<DashboardServiceEvent[]>(
        `/api/dashboard/recent-events?${q.toString()}`
      );
    },
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
      fetchAPI<RecommendationListItem[]>(`/api/recommendations/machine/${machineId}`),
    assess: (compressorId: string) =>
      fetchAPI<HealthAssessment>(`/api/recommendations/assess/${compressorId}`, {
        method: "POST",
      }),
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
      const controller = new AbortController();
      /** Large imports can run minutes on the server; override with NEXT_PUBLIC_UPLOAD_TIMEOUT_MS. */
      const uploadTimeout =
        Number(process.env.NEXT_PUBLIC_UPLOAD_TIMEOUT_MS) || 600_000;
      const timer = setTimeout(() => controller.abort(), uploadTimeout);
      let res: Response;
      try {
        res = await fetch(`${API_BASE}/api/ingestion/upload`, {
          method: "POST",
          body: formData,
          headers: authHeaders(),
          signal: controller.signal,
        });
      } catch (e: unknown) {
        const name = e && typeof e === "object" && "name" in e ? String((e as { name: string }).name) : "";
        if (name === "AbortError") {
          throw new Error(
            `Upload timed out after ${Math.round(uploadTimeout / 1000)}s (${API_BASE}). ` +
              `Increase NEXT_PUBLIC_UPLOAD_TIMEOUT_MS if imports are very large.`
          );
        }
        const raw = e instanceof Error ? e.message : "Network error";
        throw new Error(
          `${raw} — cannot reach API at ${API_BASE}. ` +
            `Start the backend (e.g. from the project backend folder: python -m uvicorn app.main:app --host 127.0.0.1 --port 8001). ` +
            `Open ${API_BASE}/health in the browser to verify. If the UI runs on a port other than 3000, set API CORS or match NEXT_PUBLIC_API_URL.`
        );
      } finally {
        clearTimeout(timer);
      }
      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        throw new Error(
          `Upload failed (${res.status}): ${detail || res.statusText || "no details"}`
        );
      }
      return res.json();
    },
    list: () => fetchAPI<unknown[]>("/api/ingestion/uploads"),
  },

  technicians: {
    list: (limit = 200) =>
      fetchAPI<TechnicianListItem[]>(`/api/technicians/?limit=${limit}`),
    create: (name: string) =>
      fetchAPI<TechnicianListItem>("/api/technicians/", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    remove: (id: string) =>
      fetchAPI<void>(`/api/technicians/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
  },

  managers: {
    list: (limit = 500) =>
      fetchAPI<ManagerListItem[]>(`/api/managers/?limit=${limit}`),
    create: (name: string) =>
      fetchAPI<ManagerListItem>("/api/managers/", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    remove: (id: string) =>
      fetchAPI<void>(`/api/managers/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
    suggestions: (limit = 100) =>
      fetchAPI<string[]>(
        `/api/managers/suggestions?limit=${encodeURIComponent(String(limit))}`
      ),
  },

  workOrders: {
    list: (params?: {
      status?: string;
      compressor_id?: string;
      assigned_technician_id?: string;
      limit?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.status) q.set("status", params.status);
      if (params?.compressor_id) q.set("compressor_id", params.compressor_id);
      if (params?.assigned_technician_id)
        q.set("assigned_technician_id", params.assigned_technician_id);
      if (params?.limit) q.set("limit", String(params.limit));
      const qs = q.toString();
      return fetchAPI<WorkOrderListItem[]>(
        `/api/work-orders${qs ? `?${qs}` : ""}`
      );
    },
    get: (id: string) => fetchAPI<WorkOrderDetail>(`/api/work-orders/${id}`),
    create: (data: WorkOrderCreatePayload) =>
      fetchAPI<WorkOrderDetail>("/api/work-orders/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: WorkOrderUpdatePayload) =>
      fetchAPI<WorkOrderDetail>(`/api/work-orders/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    updateStep: (
      workOrderId: string,
      stepId: string,
      data: { is_completed?: boolean; notes?: string | null }
    ) =>
      fetchAPI<WorkOrderStep>(
        `/api/work-orders/${workOrderId}/steps/${stepId}`,
        { method: "PATCH", body: JSON.stringify(data) }
      ),
  },

  analytics: {
    fleetOverview: (params?: {
      date_from?: string;
      date_to?: string;
      granularity?: "month" | "year";
    }) => {
      const q = new URLSearchParams();
      if (params?.date_from) q.set("date_from", params.date_from);
      if (params?.date_to) q.set("date_to", params.date_to);
      if (params?.granularity) q.set("granularity", params.granularity);
      const qs = q.toString();
      return fetchAPI<FleetMaintenanceOverview>(
        `/api/analytics/fleet/overview${qs ? `?${qs}` : ""}`
      );
    },
    fleetEntities: (kind: "compressor" | "site" = "compressor") =>
      fetchAPI<AnalyticsEntityOption[]>(
        `/api/analytics/fleet/entities?kind=${encodeURIComponent(kind)}`
      ),
    fleetCompare: (params: {
      entity_type: "compressor" | "site";
      entity_ids: string[];
      date_from: string;
      date_to: string;
    }) => {
      const q = new URLSearchParams();
      q.set("entity_type", params.entity_type);
      for (const id of params.entity_ids) {
        q.append("entity_ids", id);
      }
      q.set("date_from", params.date_from);
      q.set("date_to", params.date_to);
      return fetchAPI<FleetCompareResponse>(
        `/api/analytics/fleet/compare?${q.toString()}`
      );
    },
  },

  notifications: {
    list: (params?: {
      technician_id?: string;
      unread_only?: boolean;
      limit?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.technician_id) q.set("technician_id", params.technician_id);
      if (params?.unread_only) q.set("unread_only", "true");
      if (params?.limit) q.set("limit", String(params.limit));
      const qs = q.toString();
      return fetchAPI<NotificationItem[]>(
        `/api/notifications${qs ? `?${qs}` : ""}`
      );
    },
    markRead: (id: string) =>
      fetchAPI<{ id: string; read_at: string | null }>(
        `/api/notifications/${id}/read`,
        { method: "PATCH" }
      ),
    markAllRead: (technicianId?: string) => {
      const q = technicianId
        ? `?technician_id=${encodeURIComponent(technicianId)}`
        : "";
      return fetchAPI<{ marked_count: number }>(
        `/api/notifications/mark-all-read${q}`,
        { method: "POST" }
      );
    },
  },
};
