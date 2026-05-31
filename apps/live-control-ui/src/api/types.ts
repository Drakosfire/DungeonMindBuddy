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

export type ProjectionTargetType =
  | "event"
  | "roll_table"
  | "npc"
  | "location"
  | "runbook_section"
  | "job"
  | "open_loop"
  | "source_packet";

export type ProjectionSourceStatus =
  | "derived"
  | "authoritative"
  | "live_only"
  | "stale"
  | "missing"
  | "unknown";

export type TimelineStatus = "projected" | "active" | "played" | "skipped" | "blocked" | "unknown";

export interface PlanViewRef {
  target_type: ProjectionTargetType;
  target_id: string;
  label: string;
  source_status: ProjectionSourceStatus;
  role?: string | null;
}

export interface PlanViewStateLinks {
  event_ids: string[];
  job_ids: string[];
  open_loop_ids: string[];
}

export interface PlanViewTimelineRow {
  id: string;
  label: string;
  status: TimelineStatus;
  time_hint?: string | null;
  summary: string;
  table_ready_prompt?: string | null;
  refs: PlanViewRef[];
  state_links: PlanViewStateLinks;
}

export interface PlanViewProjection {
  schema_version: string;
  campaign_id: string;
  session: number;
  authoritative: false;
  generated_at: string;
  derived_from: string[];
  timeline: PlanViewTimelineRow[];
}

export type ArtifactKind = "event" | "roll_table";

export type ArtifactContentType = "application/json" | "text/markdown";

export interface ProjectionTarget {
  target_type: ProjectionTargetType;
  target_id: string;
  label: string;
  source_status: ProjectionSourceStatus;
  metadata?: Record<string, unknown>;
}

export interface ArtifactReadProvenance {
  source_path: string | null;
  source_role: string | null;
  generated_by: string;
  notes: string | null;
}

export interface ArtifactReadPayload {
  content_type: ArtifactContentType;
  data: Record<string, unknown> | null;
  text: string | null;
}

export interface ArtifactReadResponse {
  schema_version: string;
  target: ProjectionTarget;
  artifact_kind: ArtifactKind;
  title: string;
  read_only: true;
  file_state_token: string | null;
  payload: ArtifactReadPayload;
  provenance: ArtifactReadProvenance;
  metadata: Record<string, unknown>;
}

export type ProjectionCommandType =
  | "append_observation"
  | "queue_canon_patch"
  | "patch_artifact"
  | "create_open_loop"
  | "update_open_loop"
  | "pin_scene_state"
  | "update_job_status"
  | "record_ruling"
  | "request_retrieval_refresh"
  | "update_layout";

export type ProjectionWriteLane =
  | "observed_play"
  | "canon_patch"
  | "prep_note"
  | "live_state_pin"
  | "job_queue"
  | "retrieval_curation"
  | "layout_config"
  | "rules_ruling";

export type ProjectionRiskLevel = "low" | "medium" | "high";

export interface ProjectionCapability {
  command_type: ProjectionCommandType;
  label: string;
  lane: ProjectionWriteLane;
  enabled: boolean;
  required_fields: string[];
  risk_level: ProjectionRiskLevel;
  disabled_reason: string | null;
  metadata: Record<string, unknown>;
}

export interface CapabilityReadResponse {
  schema_version: string;
  target: ProjectionTarget;
  capabilities: ProjectionCapability[];
  metadata: Record<string, unknown>;
}

export type ProjectionRequesterType = "human_ui" | "agent" | "system";

export interface ProjectionCommandRequester {
  requester_type: ProjectionRequesterType;
  requester_id: string | null;
}

export interface ProjectionEvidenceRef {
  target: ProjectionTarget;
  note: string | null;
}

export interface ProjectionCommand {
  command_type: ProjectionCommandType;
  target: ProjectionTarget;
  lane: ProjectionWriteLane;
  payload: Record<string, unknown>;
  evidence: ProjectionEvidenceRef[];
  requested_by: ProjectionCommandRequester;
  idempotency_key: string | null;
}

export interface ProjectionInvalidation {
  projection_key: string;
  target: ProjectionTarget | null;
  reason: string;
}

export type ProjectionWriteStatus = "accepted" | "rejected" | "conflict" | "noop";

export interface ProjectionConflict {
  conflict_type: string;
  message: string;
  target: ProjectionTarget | null;
  recoverable: boolean;
}

export interface ProjectionWriteResult {
  write_id: string;
  status: ProjectionWriteStatus;
  events_appended: string[];
  jobs_queued: string[];
  artifacts_changed: ProjectionTarget[];
  invalidations: ProjectionInvalidation[];
  conflicts: ProjectionConflict[];
  diagnostics: string[];
  metadata: Record<string, unknown>;
}

export interface PatchArtifactMetadata {
  patch?: {
    dry_run?: boolean;
    source_path?: string;
    file_state_token_before?: string;
    file_state_token_after?: string;
    old_text_length?: number;
    new_text_length?: number;
    replacement_count?: number;
    unified_diff?: string;
  };
}

export interface CommandRefreshResult {
  status: "refreshed" | "refresh_failed";
  artifact?: ArtifactReadResponse | null;
  error?: string | null;
}

export interface TurnClassification {
  latency_mode: string;
  event_type: string;
  intent?: string;
  confidence?: string;
  table_id?: string | null;
  roll?: number | null;
  skill_check?: Record<string, unknown> | null;
}

export interface LiveQueryCitation {
  evidence_id: string;
  path: string;
  line_start: number | null;
  line_end: number | null;
  source_role: string;
  authority: string;
}

export interface LiveContextEvidenceRef {
  evidence_id?: string;
  path: string;
  source_role: string;
  authority: string;
  unit_id?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  text_excerpt?: string | null;
  routes?: string[];
  forbidden_uses?: string[];
}

export interface LiveContextRejectedRef {
  rejection_id?: string;
  reason_code: string;
  evidence: LiveContextEvidenceRef;
}

export interface LiveContextPacket {
  schema: string;
  question_id: string;
  intent_class: string;
  admitted_evidence: LiveContextEvidenceRef[];
  rejected_evidence: LiveContextRejectedRef[];
  claims?: Array<Record<string, unknown>>;
  planning_implications?: string[];
  capability_status?: Record<string, unknown>;
}

export interface LiveQueryResponse {
  schema?: string;
  query_id?: string;
  session?: number;
  mode?: string;
  status?: string;
  answer: string;
  classification: TurnClassification;
  events_written: string[];
  jobs_queued: string[];
  next_suggestions: string[];
  diagnostics: unknown;
  provenance: Record<string, unknown>;
  citations?: LiveQueryCitation[];
  context_packet?: LiveContextPacket | null;
  warnings?: string[];
  mutations?: unknown[];
}

export interface LiveEvent {
  schema_version: string;
  id: string;
  created_at: string;
  campaign_id: string;
  session: number;
  event_type: string;
  latency_mode: string | null;
  event_origin: string;
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

export type RecapIngestOperation =
  | "stage_preview"
  | "apply_normalize"
  | "materialize_session_memory"
  | "inspect_status";

export interface RecapIngestRequest {
  operation: RecapIngestOperation;
  campaign_id: string;
  session: number;
  raw_text?: string;
  slug?: string;
  title?: string;
  force_stage?: boolean;
  force_recap?: boolean;
  check?: boolean;
}

export interface RecapIngestStatus {
  schema: "dmb_raw_recap_ingest_status_v1";
  campaign_id: string;
  session: number;
  status: string;
  states: string[];
  paths: Record<string, string | null>;
  authority: Record<string, string>;
  warnings: string[];
  errors: string[];
  next_actions: string[];
  ingest_report: Record<string, unknown>;
  entity_spelling_audit: Array<Record<string, unknown>>;
}
