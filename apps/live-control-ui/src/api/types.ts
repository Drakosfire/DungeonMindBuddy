export type SurfaceSlot = "main" | "sidebar" | "bottom" | "overlay";

export interface SurfaceModuleDefinition {
  module_id: string;
  title: string;
  default_slot: SurfaceSlot;
  required: boolean;
  enabled_by_default: boolean;
  description: string;
  config_schema: unknown;
}

export interface SurfaceModuleInstance {
  module_id: string;
  slot: SurfaceSlot;
  order: number;
  enabled: boolean;
  collapsed: boolean;
  size: string | null;
  config: Record<string, unknown>;
}

export interface SurfaceLayout {
  schema_version: string;
  layout_version: number;
  updated_at: string;
  campaign_id: string;
  session: number;
  modules: SurfaceModuleInstance[];
}

export interface LiveNowState {
  day_label: string;
  party_position: string;
  route_intent: string;
  active_weather: string | null;
  next_suggested_beat: string;
}

export interface LiveState {
  schema_version: string;
  campaign_id: string;
  session: number;
  derived: boolean;
  authoritative: boolean;
  derived_from: string[];
  generated_at: string;
  now: LiveNowState;
  open_loop_count: number;
  pending_roll_tables: string[];
  enabled_surface_modules: string[];
  queued_job_count: number;
  recent_event_count: number;
}

export interface LiveSurfaceResponse {
  catalog: SurfaceModuleDefinition[];
  layout: SurfaceLayout;
  state: LiveState;
}

export interface LiveEventsResponse {
  events: LiveEvent[];
}

export interface LiveJobsResponse {
  jobs: LiveJob[];
}

export interface TurnClassification {
  latency_mode: string;
  event_type: string;
  table_id?: string | null;
  roll?: number | null;
  skill_check?: Record<string, unknown> | null;
}

export interface LiveQueryResponse {
  answer: string;
  classification: TurnClassification;
  events_written: string[];
  jobs_queued: string[];
  next_suggestions: string[];
  diagnostics: Record<string, unknown>;
  provenance: Record<string, unknown>;
}

export interface LiveEvent {
  schema_version: string;
  id: string;
  created_at: string;
  campaign_id: string;
  session: number;
  event_type: string;
  latency_mode: string;
  origin: string;
  summary: string;
  input_text?: string;
  derived_fields?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
}

export interface LiveJob {
  schema_version: string;
  id: string;
  created_at: string;
  campaign_id: string;
  session: number;
  job_type: string;
  status: string;
  source_event_id?: string;
  payload?: Record<string, unknown>;
}

export interface ResolvedRollResponse {
  table_id: string;
  roll: number;
  title: string;
  row_text: string;
  row_locator: string;
  source_path: string;
  provenance: Record<string, unknown>;
}
