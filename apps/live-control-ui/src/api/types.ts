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
  query_signals?: {
    asks_for_last_or_final?: boolean;
    asks_for_play_event?: boolean;
    session_numbers?: number[];
  };
}

export type LiveQueryBackend = "live" | "hermes";

export interface AgentInteractionTraceUsage {
  available: boolean;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
}

export interface AgentInteractionTraceStep {
  name: string;
  summary: string;
}

export interface AgentInteractionTraceArtifactRef {
  kind: string;
  path: string;
  label?: string | null;
}

export interface AgentInteractionContextSummary {
  admitted_count?: number;
  rejected_count?: number;
  admitted_excerpt_char_count?: number;
  admitted_excerpt_token_estimate?: number;
  rejected_excerpt_char_count?: number;
  rejected_excerpt_token_estimate?: number;
  total_excerpt_char_count?: number;
  total_excerpt_token_estimate?: number;
  context_payload_kind?: string | null;
  manifest_path?: string | null;
  answerable_now?: boolean | null;
  intent_class?: string | null;
  suggested_route_count?: number;
  verdict?: string | null;
}

export interface AgentInteractionAdmittedContextItem {
  path?: string;
  source_role?: string;
  authority?: string;
  line_start?: number | null;
  line_end?: number | null;
  text_excerpt: string;
}

export type RetrievalFreshnessDecisionKind = "fresh_retrieval" | "thread_context" | "blended" | "insufficient_grounding";

export interface RetrievalFreshnessDecision {
  schema: "dmb_retrieval_freshness_decision_v1";
  decision: RetrievalFreshnessDecisionKind;
  used_fresh_retrieval: boolean;
  used_thread_context: boolean;
  admitted_evidence_count: number;
  rejected_evidence_count: number;
  prior_turn_count: number;
  reason: string;
  warnings: string[];
}

export interface AgentInteractionTrace {
  trace_id: string;
  runtime: string;
  backend: string;
  mode: string;
  provider?: string | null;
  model?: string | null;
  started_at: string;
  completed_at: string;
  elapsed_ms: number;
  status: string;
  toolset?: string | null;
  command_summary?: string | null;
  prompt_preview?: string | null;
  prompt_char_count?: number | null;
  prompt_token_estimate?: number | null;
  usage: AgentInteractionTraceUsage;
  steps: AgentInteractionTraceStep[];
  context_summary: AgentInteractionContextSummary;
  artifact_refs: AgentInteractionTraceArtifactRef[];
  warnings: string[];
}


export interface HermesSessionHandle {
  sessionId: string;
  title?: string | null;
  runtime: "cli" | "api" | "in_process" | "unknown" | string;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export type CitationFreshnessStatus = "current" | "changed" | "unknown" | "unavailable";

export interface AgentEvidenceSnapshot {
  schema: "dmb_agent_evidence_snapshot_v1";
  evidence_id: string;
  path: string;
  line_start?: number | null;
  line_end?: number | null;
  source_role?: string | null;
  authority?: string | null;
  fingerprint: string;
  fingerprint_algorithm: "sha256:locator-v1" | "sha256:source-lines-v1" | "locator-v1";
  captured_at: string;
}

export interface CitationFreshnessCheckResult {
  status: CitationFreshnessStatus;
  checked_at: string;
  diagnostics: string[];
  warnings: string[];
}

export interface AgentInteractionTurn {
  turnId: string;
  askedAt: string;
  completedAt?: string | null;
  question: string;
  answer: string;
  backend: LiveQueryBackend;
  status: "ok" | "error" | "partial" | string;
  contextSummary?: AgentInteractionContextSummary;
  citations?: LiveQueryCitation[];
  trace?: AgentInteractionTrace | null;
  warnings?: string[];
  retrievalFreshness?: RetrievalFreshnessDecision | null;
  evidenceSnapshots?: AgentEvidenceSnapshot[];
  corpusFreshness?: CitationFreshnessCheckResult | null;
}

export interface AgentInteractionThread {
  threadId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  campaignId: string;
  session?: number | null;
  surfaceId: "plan" | "play" | "build" | string;
  activeBackend: LiveQueryBackend;
  hermesSession?: HermesSessionHandle | null;
  turns: AgentInteractionTurn[];
  uiState?: {
    traceVisible: boolean;
    scrollAnchorTurnId?: string | null;
    newThreadSuggestionDismissed?: boolean;
  };
}

export interface AgentInteractionThreadSummary {
  threadId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  turnCount: number;
  activeBackend: LiveQueryBackend;
  hermesSessionId?: string | null;
}

export interface AgentInteractionThreadIndex {
  schema: "agent_interaction_thread_index_v1";
  campaignId: string;
  surfaceId: string;
  activeThreadId: string | null;
  threads: AgentInteractionThreadSummary[];
}

export interface LiveQueryOptions {
  agentThreadId?: string | null;
  hermesSessionId?: string | null;
  traceRequested?: boolean | null;
}

export interface AgentInteractionTurnMeta {
  id: string;
  question: string;
  answer: string;
  backend: LiveQueryBackend;
  model: string | null;
  status: string;
  askedAt: string;
  traceId: string | null;
  admittedCount: number | null;
  rejectedCount: number | null;
  runtime: string | null;
  elapsedMs: number | null;
  provider: string | null;
  stepCount: number | null;
}


export interface CitationSourceRequest {
  path: string;
  line_start?: number | null;
  line_end?: number | null;
  text_excerpt?: string | null;
}

export interface CitationFreshnessRequest {
  path: string;
  line_start?: number | null;
  line_end?: number | null;
  expected_fingerprint?: string | null;
  fingerprint_algorithm?: "sha256:source-lines-v1" | "sha256:locator-v1" | "locator-v1" | null;
}

export interface CitationFreshnessResponse {
  schema: "dmb_citation_freshness_v1";
  path: string;
  status: CitationFreshnessStatus;
  current_fingerprint?: string | null;
  expected_fingerprint?: string | null;
  fingerprint_algorithm: "sha256:source-lines-v1" | "sha256:locator-v1";
  checked_at: string;
  diagnostics: string[];
  warnings: string[];
}

export interface CitationSourceResponse {
  schema_version: "dmb_citation_source_v1";
  path: string;
  content_type: "text/markdown" | "text/plain";
  content: string;
  truncated: boolean;
  highlight: {
    line_start: number | null;
    line_end: number | null;
    text_excerpt: string | null;
    match_source: "line_range" | "excerpt_search" | "none";
  };
  diagnostics: string[];
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
  agent_trace?: AgentInteractionTrace | null;
  agent_thread_id?: string | null;
  turn_id?: string | null;
  hermes_session?: HermesSessionHandle | null;
  retrieval_freshness?: RetrievalFreshnessDecision | null;
  evidence_snapshots?: AgentEvidenceSnapshot[];
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
  | "generate_recap_memory"
  | "apply_normalize"
  | "build_frontmatter_seed"
  | "run_breadcrumb_ingest"
  | "materialize_session_memory"
  | "build_graph_preview_bundle"
  | "materialize_preview_supergraph"
  | "inspect_graph_preview"
  | "inspect_status"
  | "reconcile_normalized_recap";

export interface RecapIngestRequest {
  operation: RecapIngestOperation;
  campaign_id: string;
  session: number;
  raw_text?: string;
  slug?: string;
  title?: string;
  keep_basename?: string;
  force_stage?: boolean;
  force_recap?: boolean;
  check?: boolean;
  candidate_graph_path?: string;
  force_graph_run?: boolean;
  extract_graph?: boolean;
  graph_model_id?: string | null;
  materialize_after_extract?: boolean;
  include_graph_extraction?: boolean;
  include_legacy_breadcrumb?: boolean;
}

export interface RecapGraphPreviewReport {
  status: string;
  run_dir?: string | null;
  manifest_path?: string | null;
  candidate_graph_path?: string | null;
  preview_union_store_path?: string | null;
  preview_union_store_valid?: boolean | null;
  node_count?: number;
  edge_count?: number;
  evidence_ref_count?: number;
  extraction_mode?: string | null;
  model_id?: string | null;
  candidate_node_count?: number;
  candidate_edge_count?: number;
  candidate_beat_count?: number;
  estimated_cost_usd?: number | null;
  graph_steps?: Array<Record<string, unknown>>;
  current_graph_step?: Record<string, unknown> | null;
  pass_telemetry_path?: string | null;
  pass_outputs_path?: string | null;
  consolidation_diagnostics_path?: string | null;
  next_actions?: string[];
  can_open_union_graph?: boolean;
  blocked_reason?: string | null;
}

export interface NormalizedRecapCandidate {
  basename: string;
  relpath: string;
  size_bytes: number;
  modified_at: string;
  is_generic: boolean;
  recommended: boolean;
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

export interface StatblockWorkbenchAction {
  action_id: string;
  label: string;
  enabled: boolean;
  disabled_reason: string | null;
}

export interface StatblockBreadcrumb {
  label: string;
  source?: string | null;
  target?: string | null;
  metadata?: Record<string, unknown>;
}

export interface StatblockCombatDefaults {
  name?: string | null;
  armor_class?: number | string | null;
  hit_points?: number | string | null;
  initiative_bonus?: number | null;
  passive_perception?: number | string | null;
  speed_summary?: string | null;
  speed?: string | null;
  senses_summary?: string | null;
  primary_actions?: string[];
  suggested_tactics?: string[];
  legendary_actions?: number | null;
}

export interface StatblockReviewWarning {
  code?: string | null;
  message: string;
  severity?: string;
  path?: string | null;
}

export interface StatblockDraftArtifactView {
  artifact_id: string;
  draft_id: string;
  title: string;
  markdown: string;
  structured_statblock: Record<string, unknown>;
  combat_defaults: StatblockCombatDefaults;
  warnings: StatblockReviewWarning[];
  provenance: Record<string, unknown>;
  review_status: string;
  lifecycle_state: string;
  storage_status: string;
  corpus_status: string;
  source_refs: Array<Record<string, unknown>>;
  breadcrumbs: StatblockBreadcrumb[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface StoredStatblockDraftRecord {
  schema_version: "dmb_statblock_draft_record_v1";
  artifact_id: string;
  title: string;
  campaign_id: string;
  session: number;
  stored_at: string;
  updated_at: string;
  storage_path: string;
  corpus_relpath?: string | null;
  corpus_display_path?: string | null;
  corpus_written_at?: string | null;
  corpus_preview_token?: string | null;
  retrieval_status?: string | null;
  retrieval_manifest_path?: string | null;
  retrieval_activated_at?: string | null;
  retrieval_verified_at?: string | null;
  retrieval_query?: string | null;
  retrieval_evidence_path?: string | null;
  retrieval_evidence_score?: number | null;
  artifact: StatblockDraftArtifactView;
}

export interface StoredStatblockDraftSummary {
  artifact_id: string;
  title: string;
  draft_id: string;
  review_status: string;
  lifecycle_state: string;
  storage_status: string;
  corpus_status: string;
  stored_at: string;
  updated_at: string;
  storage_path: string;
  corpus_relpath?: string | null;
  corpus_display_path?: string | null;
  corpus_written_at?: string | null;
  corpus_preview_token?: string | null;
  retrieval_status?: string | null;
  retrieval_manifest_path?: string | null;
  retrieval_activated_at?: string | null;
  retrieval_verified_at?: string | null;
  retrieval_query?: string | null;
  retrieval_evidence_path?: string | null;
  retrieval_evidence_score?: number | null;
}

export interface StoreStatblockDraftRequest {
  artifact: StatblockDraftArtifactView;
  source: "workbench";
}

export interface StoreStatblockDraftResponse {
  schema_version: "dmb_statblock_draft_store_v1";
  record: StoredStatblockDraftRecord;
  diagnostics: string[];
}

export interface ListStatblockDraftsResponse {
  schema_version: "dmb_statblock_draft_list_v1";
  drafts: StoredStatblockDraftSummary[];
}

export interface ReadStatblockDraftResponse {
  schema_version: "dmb_statblock_draft_read_v1";
  record: StoredStatblockDraftRecord;
}


export interface GeneratedStatblockListItem {
  artifact_id: string;
  draft_id: string;
  title: string;
  campaign_id: string;
  session: number;
  review_status: string;
  lifecycle_state: string;
  storage_status: string;
  corpus_status: string;
  retrieval_status?: string | null;
  corpus_relpath: string;
  corpus_display_path: string;
  corpus_written_at?: string | null;
  retrieval_verified_at?: string | null;
  armor_class?: number | string | null;
  hit_points?: number | string | null;
  challenge_rating?: string | null;
  creature_type?: string | null;
  primary_actions: string[];
  warning_count: number;
}

export interface GeneratedStatblockListResponse {
  schema_version: "dmb_generated_statblock_list_v1";
  statblocks: GeneratedStatblockListItem[];
  diagnostics: string[];
}

export interface GeneratedStatblockDetailResponse {
  schema_version: "dmb_generated_statblock_detail_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  stored_record: StoredStatblockDraftRecord;
  corpus_relpath: string;
  corpus_display_path: string;
  corpus_markdown: string;
  corpus_markdown_bytes: number;
  corpus_file_fingerprint?: string | null;
  combat_defaults: StatblockCombatDefaults;
  warnings: StatblockReviewWarning[];
  provenance: Record<string, unknown>;
  breadcrumbs: StatblockBreadcrumb[];
  source_refs: Array<Record<string, unknown>>;
  retrieval: Record<string, unknown>;
  available_actions: StatblockWorkbenchAction[];
  diagnostics: string[];
}

export type CombatTeam = "pc" | "ally" | "enemy" | "neutral";

export interface CombatEntity {
  id: string;
  name: string;
  team: CombatTeam;
  order: number;
  init?: number | null;
  ac?: number | string | null;
  hp?: number | string | null;
  max_hp?: number | string | null;
  temp_hp?: number | null;
  defeated: boolean;
  notes: string;
  conditions: string[];
  tags: string[];
  statblock_path?: string | null;
  statblock_artifact_id?: string | null;
  statblock_title?: string | null;
  corpus_fingerprint?: string | null;
  source: "corpus" | "generated_pending" | "manual" | "imported";
  provenance: Array<Record<string, unknown>>;
}

export interface CombatEncounterState {
  schema: "dmb_combat_encounter_state_v1";
  campaign_id: string;
  session: number;
  encounter_id: string;
  title: string;
  round: number;
  active_turn_entity_id?: string | null;
  round_start_entity_id?: string | null;
  queue_model: "circular_barrel_v1";
  entities: CombatEntity[];
  groups: Array<Record<string, unknown>>;
  provenance: Array<Record<string, unknown>>;
  updated_at: string;
}


export interface CombatEntityPatchRequest {
  name?: string | null;
  team?: CombatTeam | null;
  init?: number | null;
  ac?: number | string | null;
  hp?: number | string | null;
  max_hp?: number | string | null;
  temp_hp?: number | null;
  defeated?: boolean | null;
  notes?: string | null;
  conditions?: string[] | null;
}

export interface CombatHpDeltaRequest {
  action: "damage" | "heal" | "set_temp_hp";
  amount: number;
}

export interface CombatTurnRequest {
  direction?: "next" | "previous";
}

export interface CombatSetActiveRequest {
  entity_id?: string | null;
}

export interface CombatMutationResponse {
  schema_version: "dmb_combat_mutation_v1";
  encounter: CombatEncounterState;
  diagnostics: string[];
}

export interface CombatSaveSummary {
  save_id: string;
  title: string;
  encounter_id: string;
  entity_count: number;
  round: number;
  updated_at?: string | null;
}

export interface CombatSavesListResponse {
  schema_version: "dmb_combat_saves_list_v1";
  saves: CombatSaveSummary[];
  backups: string[];
}

export interface CombatSaveSlotResponse {
  schema_version: "dmb_combat_save_slot_v1";
  encounter: CombatEncounterState;
  saves: CombatSaveSummary[];
  backups: string[];
  diagnostics: string[];
}

export interface LoadCombatSaveRequest {
  save_id: string;
}

export interface NewCombatEncounterRequest {
  title?: string | null;
  encounter_id?: string | null;
}

export interface SaveCurrentCombatRequest {
  save_id: string;
  title?: string | null;
}

export interface AddGeneratedStatblockCombatRequest {
  team?: CombatTeam;
  count?: number;
  name_override?: string | null;
  initiative?: number | null;
  insert_after_entity_id?: string | null;
  group_key?: string | null;
  notes?: string | null;
  hp_override?: number | null;
  max_hp_override?: number | null;
}

export interface AddGeneratedStatblockCombatResponse {
  schema_version: "dmb_add_generated_statblock_to_combat_v1";
  added_entities: CombatEntity[];
  encounter: CombatEncounterState;
  diagnostics: string[];
}

export interface StatblockPromotionWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "error";
}

export interface StatblockCorpusPromotionPreviewRequest {
  include_writer_allowlist_check?: boolean;
}

export interface StatblockCorpusPromotionPreviewValidation {
  ok: boolean;
  proposed_path_safe: boolean;
  writer_allowed_now?: boolean | null;
  writer_reason?: string | null;
}

export interface StatblockCorpusPromotionPreviewResponse {
  schema_version: "dmb_statblock_corpus_promotion_preview_v1";
  preview_id: string;
  artifact_id: string;
  draft_id: string;
  title: string;
  campaign_id: string;
  session: number;
  source_record_path: string;
  corpus_root_display: string;
  proposed_corpus_relpath: string;
  proposed_corpus_display_path: string;
  frontmatter: Record<string, unknown>;
  frontmatter_text: string;
  markdown_body: string;
  full_markdown: string;
  breadcrumbs: StatblockBreadcrumb[];
  source_refs: Array<Record<string, unknown>>;
  combat_defaults: StatblockCombatDefaults;
  warnings: StatblockPromotionWarning[];
  validation: StatblockCorpusPromotionPreviewValidation;
  preview_token: string;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface StatblockCorpusWritePrepareRequest {
  preview_token?: string | null;
}

export interface StatblockCorpusWritePrepareResponse {
  schema_version: "dmb_statblock_corpus_write_prepare_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  preview_token: string;
  proposed_corpus_relpath: string;
  proposed_corpus_display_path: string;
  writer_ok: boolean;
  writer_phase?: string | null;
  writer_confirm_token?: string | null;
  writer_diff?: string | null;
  new_size_bytes?: number | null;
  warnings: StatblockPromotionWarning[];
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface StatblockCorpusWriteCommitRequest {
  preview_token: string;
  writer_confirm_token: string;
}

export interface StatblockCorpusWriteCommitResponse {
  schema_version: "dmb_statblock_corpus_write_commit_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  preview_token: string;
  proposed_corpus_relpath: string;
  proposed_corpus_display_path: string;
  writer_ok: boolean;
  writer_phase?: string | null;
  bytes_written?: number | null;
  new_corpus_fingerprint?: string | null;
  stored_record: StoredStatblockDraftRecord;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface TiptapMarkdownWritePrepareRequest {
  document_id: string;
  title: string;
  target_relpath: string;
  markdown: string;
}

export interface TiptapMarkdownWritePrepareResponse {
  schema_version: "dmb_tiptap_markdown_write_prepare_v1";
  document_id: string;
  title: string;
  target_relpath: string;
  target_display_path: string;
  file_exists: boolean;
  writer_ok: boolean;
  writer_phase?: string | null;
  writer_confirm_token?: string | null;
  writer_diff?: string | null;
  existing_size_bytes?: number | null;
  new_size_bytes?: number | null;
  warnings: string[];
  diagnostics: string[];
}

export interface TiptapMarkdownWriteCommitRequest {
  document_id: string;
  title: string;
  target_relpath: string;
  markdown: string;
  writer_confirm_token: string;
}

export interface TiptapMarkdownWriteCommitResponse {
  schema_version: "dmb_tiptap_markdown_write_commit_v1";
  document_id: string;
  title: string;
  target_relpath: string;
  target_display_path: string;
  writer_ok: boolean;
  writer_phase?: string | null;
  bytes_written?: number | null;
  file_fingerprint?: string | null;
  backup_relpath?: string | null;
  diagnostics: string[];
}


export interface StatblockRetrievalActivationResponse {
  schema_version: "dmb_statblock_retrieval_activation_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  corpus_relpath: string;
  corpus_display_path: string;
  manifest_overlay_path: string;
  manifest_entry: Record<string, unknown>;
  stored_record: StoredStatblockDraftRecord;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface StatblockRetrievalVerifyRequest {
  query?: string | null;
}

export interface StatblockRetrievalVerifyResponse {
  schema_version: "dmb_statblock_retrieval_verify_v1";
  artifact_id: string;
  draft_id: string;
  title: string;
  query: string;
  status: "verified" | "retrieved_not_admitted" | "not_found";
  corpus_relpath: string;
  manifest_overlay_path: string;
  admitted_evidence: Array<Record<string, unknown>>;
  rejected_evidence: Array<Record<string, unknown>>;
  retrieval_trace: Record<string, unknown>;
  stored_record?: StoredStatblockDraftRecord | null;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export interface StatblockWorkbenchSampleResponse {
  schema_version: "dmb_statblock_workbench_sample_v1";
  mode: "sample_mock";
  artifact: StatblockDraftArtifactView;
  command_status: string;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

export type StatblockWorkbenchCommandType =
  | "statblock.draft.generate"
  | "statblock.draft.render";

export interface StatblockWorkbenchCommandRequest {
  command_type: StatblockWorkbenchCommandType;
  payload?: Record<string, unknown>;
  requested_by?: "human" | "agent" | "planning_task" | "combat_task";
  breadcrumbs?: StatblockBreadcrumb[];
  as_artifact?: boolean;
}

export interface StatblockWorkbenchCommandResponse {
  schema_version: "dmb_statblock_workbench_command_v1";
  mode: "mock_command";
  artifact: StatblockDraftArtifactView | null;
  command_status: string;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
  error?: Record<string, unknown> | null;
}

export interface OpaqueLocator {
  locatorId: string;
  scheme: "corpus_path" | "artifact_path" | "impact_proof" | "unknown";
  value: string;
  anchor?: string | null;
}

export interface SourceArtifact {
  artifactId: string;
  kind: string;
  layer: string;
  label: string;
  campaignId?: string | null;
  sessionId?: string | null;
  sessionNumber?: number | null;
  canonState: string;
  lifecycleState: string;
  evidenceRole: string;
  authorityState: string;
  visibilityState: string;
  primaryLocator: OpaqueLocator;
  relatedLocators: OpaqueLocator[];
  displaySummary?: string | null;
  metadata: Record<string, string | number | boolean | null>;
  producedBy?: string | null;
  producedAt?: string | null;
}

export interface SourceAnchor {
  anchorId: string;
  artifactId: string;
  label: string;
  anchorKind: string;
  locator: OpaqueLocator;
  canonState: string;
  lifecycleState: string;
  evidenceRole: string;
  authorityState: string;
  visibilityState: string;
  metadata: Record<string, string | number | boolean | null>;
}

export interface SourceUnit {
  unitId: string;
  artifactId: string;
  anchorId: string;
  unitKind: string;
  label: string;
  displaySummary?: string | null;
  fields: Record<string, string | number | boolean | null>;
  sourceAnchor: SourceAnchor;
  canonState: string;
  lifecycleState: string;
  evidenceRole: string;
  authorityState: string;
  visibilityState: string;
  provenance: Array<Record<string, unknown>>;
  diagnostics: Record<string, unknown>;
}

export interface IngestionSourceBundle {
  schema_version: "dmb_ingestion_source_bundle_v1";
  bundle_id: string;
  scope: string;
  generated_at?: string | null;
  corpus_root: string;
  artifacts: SourceArtifact[];
  anchors: SourceAnchor[];
  units: SourceUnit[];
  coverage: Record<string, unknown>;
  diagnostics: string[];
}

export type GraphReviewLaneRole = "gold" | "live" | "variant" | "reference";

export type GraphReviewLaneSourceKind =
  | "gold_fixture"
  | "graph_ingest_run"
  | "manual_review_variant"
  | "projection_payload";

export type GraphReviewLaneStatus =
  | "available"
  | "missing_projection"
  | "failed"
  | "stale"
  | "unknown";

export type GraphReviewVocabularyMode =
  | "none"
  | "node"
  | "edge"
  | "node_and_edge"
  | "dynamic"
  | "unknown";

export type GraphReviewLaneCounts = {
  nodes: number;
  edges: number;
  beats?: number;
  evidenceRefs?: number;
};

export type GraphReviewLaneMetadata = {
  runId?: string;
  generatedAt?: string;
  modelId?: string;
  extractionProfile?: string;
  extractionMode?: string;
  vocabularyMode?: GraphReviewVocabularyMode;
  runnerOptions?: Record<string, unknown>;
  diagnostics?: Record<string, unknown>;
};

export type GraphReviewLane = {
  laneId: string;
  role: GraphReviewLaneRole;
  sourceKind: GraphReviewLaneSourceKind;
  label: string;
  campaignId: string;
  sessionId: string;

  manifestPath?: string;
  artifactPath?: string;
  goldPath?: string;
  previewUnionPath?: string;

  status: GraphReviewLaneStatus;

  counts: GraphReviewLaneCounts;
  metadata: GraphReviewLaneMetadata;
};

export interface GraphPreviewAnchorQuoteMatch {
  quote: string;
  char_start: number;
  char_end: number;
  match_text: string;
}

export interface GraphPreviewEvidenceRef {
  source_ref_id?: string | null;
  source_artifact_id?: string | null;
  source_span_ref_id?: string | null;
  source_anchor_id?: string | null;
  label?: string | null;
  evidence_role?: string | null;
  can_open_source: boolean;
  can_highlight_span: boolean;
  anchor_quotes: string[];
  anchor_quote_matches: GraphPreviewAnchorQuoteMatch[];
  paragraph_text?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  recap_source_path?: string | null;
}

export type GraphPreviewCandidateSection =
  | "nodes"
  | "edges"
  | "beats"
  | "ignored_items"
  | "deferred_items";

export interface GraphPreviewCandidateRow {
  section: GraphPreviewCandidateSection;
  object_id: string;
  label: string;
  kind: string;
  description?: string | null;
  importance?: string | null;
  evidence_count: number;
  evidence_refs: GraphPreviewEvidenceRef[];
}

export interface GraphPreviewHealth {
  canonical_ir_valid: boolean;
  reconcile_error?: string | null;
  node_count: number;
  edge_count: number;
  beat_count: number;
  ignored_count: number;
  deferred_count: number;
  evidence_ref_count: number;
  resolvable_evidence_ref_count: number;
  model_id?: string | null;
  scenario_estimated_cost_usd?: number | null;
  node_recall?: number | null;
}

export interface GraphPreviewSurfaceResponse {
  schema_version: "dmb_graph_preview_surface_v1";
  version: string;
  run_dir: string;
  run_bundle_dir?: string | null;
  recap_source_path?: string | null;
  health: GraphPreviewHealth;
  candidates: GraphPreviewCandidateRow[];
}

export interface GraphPreviewRunSummary {
  run_dir: string;
  model_id?: string | null;
  run_index?: number | null;
  canonical_ir_valid?: boolean | null;
  scenario_estimated_cost_usd?: number | null;
}

export interface GraphPreviewRunsResponse {
  schema_version: "dmb_graph_preview_surface_v1";
  version: string;
  runs: GraphPreviewRunSummary[];
}

export interface RecapGraphRunRef {
  run_uri: string;
  model_id?: string | null;
  run_index?: number | null;
  canonical_ir_valid?: boolean | null;
  scenario_estimated_cost_usd?: number | null;
  node_recall?: number | null;
}

export interface RecapArtifactRecord {
  schema_version: "dmb_recap_artifact_record_v1";
  artifact_id: string;
  campaign_id: string;
  session_id: string;
  source_artifact_id?: string | null;
  source_recap_path: string;
  breadcrumb_seed_path?: string | null;
  session_memory_records_path?: string | null;
  run_bundle_uri: string;
  run_manifest_uri: string;
  source_span_index_uri: string;
  provenance_index_uri?: string | null;
  graph_run_refs: RecapGraphRunRef[];
  default_graph_run_uri?: string | null;
  default_projection_mode: string;
  source_sha256?: string | null;
  registered_at: string;
  updated_at: string;
  registry_source: "scan" | "explicit";
}

export interface RecapArtifactsListResponse {
  schema_version: "dmb_recap_artifacts_registry_v1";
  version: string;
  records: RecapArtifactRecord[];
}

export interface RecapGraphQuery {
  run_dir?: string;
  artifact_id?: string;
  campaign_id?: string;
  session_id?: string;
}

export interface RecapGraphChip {
  label: string;
  tone: "new" | "recurring" | "evidence" | "warning" | "neutral";
  source_session?: number | null;
}

export interface RecapGraphNode {
  object_id: string;
  label: string;
  kind: string;
  role: string;
  description?: string | null;
  evidence_count: number;
  chips: RecapGraphChip[];
}

export interface RecapGraphLink {
  href: string;
  object_id: string;
  label: string;
  source_span_ref_id: string;
  char_start: number;
  char_end: number;
  evidence_ref_ids: string[];
}

export interface RecapGraphPresentationResponse {
  schema_version: "dmb_recap_graph_presentation_v1";
  version: string;
  run_dir: string;
  recap_source_path?: string | null;
  markdown: string;
  nodes: Record<string, RecapGraphNode>;
  links: RecapGraphLink[];
}

export interface GraphIngestRunSummary {
  manifest_path: string;
  run_dir: string;
  campaign_id: string;
  session_id: string;
  status: string;
  updated_at?: string | null;
  created_at?: string | null;
  preview_union_store_path?: string | null;
  preview_union_store_valid?: boolean | null;
  node_count: number;
  edge_count: number;
  evidence_ref_count: number;
  next_actions: string[];
  run_id?: string | null;
  run_label: string;
  generated_at?: string | null;
  model_id?: string | null;
  model_provider?: string | null;
  extraction_profile?: string | null;
  extraction_mode?: string | null;
  vocabulary_mode: GraphReviewVocabularyMode;
  runner_options_summary: Record<string, string | number | boolean | null>;
  diagnostics_summary: Record<string, string | number | boolean | null>;
  preview_union_available: boolean;
}

export interface GraphIngestRunsResponse {
  schema_version: "dmb_graph_ingest_run_registry_v1";
  version: string;
  runs: GraphIngestRunSummary[];
}

export interface GraphIngestLatestRunResponse {
  schema_version: "dmb_graph_ingest_run_registry_v1";
  version: string;
  run: GraphIngestRunSummary | null;
}

export interface GoldReviewSessionSummary {
  session_id: string;
  session_number: number;
  campaign_id: string;
  gold_fixture_id: string;
  gold_manifest_path: string;
  gold_graph_path: string;
  gold_counts: Record<string, number>;
  available_runs: GraphIngestRunSummary[];
}

export interface GoldReviewSessionsResponse {
  schema_version: "dmb_graph_gold_review_sessions_v1";
  version: string;
  sessions: GoldReviewSessionSummary[];
}

export interface GoldReviewMissEntry {
  id: string;
  label: string;
}

export interface GoldReviewCompareResponse {
  schema_version: "dmb_graph_gold_review_compare_v1";
  version: string;
  session_id: string;
  campaign_id: string;
  gold_fixture_id: string;
  gold_manifest_path: string;
  gold_graph_path: string;
  live_run: GraphIngestRunSummary | null;
  comparison: {
    scores: Record<string, number>;
    coverage: Record<string, unknown>;
    soft_misses: Array<{ issue: string; detail: string; label?: string }>;
    dedup?: Record<string, number>;
  };
  object_index: {
    gold: Record<string, GoldReviewObjectIndexEntry>;
    live: Record<string, GoldReviewObjectIndexEntry>;
  };
  match_pairs: Record<string, Array<{ gold_id: string; live_id: string; score: number }>>;
}

export interface GoldReviewObjectIndexEntry {
  object_kind: string;
  object_id: string;
  label: string;
  payload: Record<string, unknown>;
}

export interface GoldReviewEvidenceResolvedRef {
  source_anchor_id?: string | null;
  source_span_ref_id?: string | null;
  label?: string | null;
  preview_snippet?: string | null;
  paragraph_text?: string | null;
  line_start?: number | null;
  line_end?: number | null;
}

export interface GoldReviewEvidenceSide {
  object_id: string;
  object_kind: string;
  label?: string | null;
  summary?: string | null;
  payload: Record<string, unknown>;
  evidence: GoldReviewEvidenceResolvedRef[];
}

export interface GoldReviewEvidenceDiffResponse {
  schema_version: "dmb_graph_gold_review_evidence_v1";
  version: string;
  session_id: string;
  campaign_id: string;
  object_kind: string;
  object_id: string;
  matched: boolean;
  match_score?: number | null;
  gold: GoldReviewEvidenceSide;
  live?: GoldReviewEvidenceSide | null;
}

export interface VocabularyAblationVariantSetup {
  variant_name: string;
  enable_node_packet: boolean;
  enable_edge_packet: boolean;
  node_count: number;
  edge_count: number;
  total_cost_usd?: number | null;
  score?: number | null;
  known_name_pickup_rate?: number | null;
  recognition_rate?: number | null;
  present_recognized?: string[];
  present_missed?: string[];
  contamination_count?: number | null;
  contamination_rate?: number | null;
  absent_contaminated?: string[];
  combat_encounter_match_count?: number | null;
  predicate_hint_match_count?: number | null;
  unsafe_cross_class_blocked_count?: number | null;
  node_kinds?: Record<string, number>;
  edge_predicates?: Record<string, number>;
}

export interface VocabularyAblationPartition {
  present_set: string[];
  absent_set: string[];
}

export interface VocabularyAblationDogfoodResponse {
  schema_version: "dmb_vocabulary_ablation_dogfood_v1";
  version: string;
  generated_at: string;
  scope: string;
  session_id: string;
  campaign_id: string;
  model_id: string;
  report_path: string;
  packet_id: string;
  source_span_count: number;
  source_files: string[];
  recommendation: string;
  comparison: Record<string, unknown>;
  variant_setup: VocabularyAblationVariantSetup[];
  partition?: VocabularyAblationPartition;
}

export interface ManualReviewBedSummary {
  bed_id: string;
  campaign_id?: string | null;
  session_id?: string | null;
  source_label?: string | null;
  variant_names: string[];
}

export interface ManualReviewBedsResponse {
  schema_version: "dmb_graph_manual_review_beds_v1";
  version: string;
  generated_at?: string | null;
  model_id?: string | null;
  beds: ManualReviewBedSummary[];
}

export interface ManualReviewNode {
  node_id: string;
  label: string;
  node_type: string;
  pass_name?: string | null;
  description?: string | null;
  confidence?: string | null;
  importance?: string | null;
  corpus_ref?: string | Record<string, unknown> | null;
  evidence_span_ids: string[];
  anchor_quotes: string[];
}

export interface ManualReviewEdge {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  from_label?: string | null;
  to_label?: string | null;
  relationship_type: string;
  predicate_family?: string | null;
  confidence?: string | null;
  evidence_span_ids: string[];
  anchor_quotes: string[];
}

export interface ManualReviewVariantDetail {
  variant_name: string;
  node_count: number;
  edge_count: number;
  cost_usd?: number | null;
  nodes: ManualReviewNode[];
  edges: ManualReviewEdge[];
  node_kinds: Record<string, number>;
  edge_predicates: Record<string, number>;
  gold_comparison: Record<string, unknown>;
  party_context: Record<string, unknown>;
}

export interface ManualReviewBedDetail {
  schema_version: "dmb_graph_manual_review_bed_v1";
  version: string;
  bed_id: string;
  campaign_id?: string | null;
  session_id?: string | null;
  source_label?: string | null;
  generated_at?: string | null;
  model_id?: string | null;
  node_prompt_contexts: Record<string, string>;
  edge_prompt_context: string;
  variant_names: string[];
  variants: Record<string, ManualReviewVariantDetail>;
}

export interface GraphFocusOverlay {
  focus_session_id?: string | null;
  focused_evidence_ref_ids: string[];
  focused_edge_ids: string[];
  focused_node_ids: string[];
}

export interface RecapProjectionSourceSpan {
  span_id: string;
  kind: string;
  ordinal?: number | null;
  text_excerpt?: string | null;
  line_start?: number | null;
  line_end?: number | null;
}

export interface GraphProjectionEvidenceBadge {
  evidence_ref_id: string;
  source_artifact_id: string;
  source_domain: string;
  evidence_role: string;
  is_focus_session_evidence: boolean;
  can_open_source: boolean;
  can_highlight_span: boolean;
  label?: string | null;
  session_id?: string | null;
  source_span_ref_id?: string | null;
}

export interface GraphProjectionAdjacencyCandidate {
  edge_id: string;
  node_id: string;
  label: string;
  kind: string;
  predicate: string;
  direction: string;
  anchored_to_focus_session: boolean;
  source_domains: string[];
  evidence_ref_ids: string[];
  edge_label?: string | null;
  session_ids?: string[];
}

export interface GraphProjectionSuggestedExpansion extends GraphProjectionAdjacencyCandidate {
  rank: number;
  rank_reason: string;
}

export interface GraphProjectionNodeView {
  node_id: string;
  label: string;
  kind: string;
  role: string;
  aliases: string[];
  source_domains: string[];
  evidence_badges: GraphProjectionEvidenceBadge[];
  adjacency: GraphProjectionAdjacencyCandidate[];
  suggested_expansions?: GraphProjectionSuggestedExpansion[];
  anchored_to_focus_session: boolean;
  summary?: string | null;
  /** Authored overlay metadata (A6+) */
  source?: string | null;
  authored?: boolean;
  assertion_id?: string | null;
  visibility?: string | null;
  graph_scope?: string[] | null;
  source_anchor_text?: string | null;
  /** Durable union identity merge provenance (A10m+) */
  merged_away_ids?: string[];
  merge_assertion_ids?: string[];
  identity_redirect_ids?: string[];
  identity_merge_record_ids?: string[];
}

export interface GraphAuthoringOverlayDiagnostic {
  code: string;
  message: string;
  assertion_id?: string | null;
  severity?: "info" | "warning" | "error";
}

export interface AuthoredOverlayProjectionSummary {
  loaded: boolean;
  overlay_path?: string | null;
  assertion_count: number;
  projected_node_count: number;
  projected_link_existing_count: number;
  projected_relationship_count: number;
  diagnostics: GraphAuthoringOverlayDiagnostic[];
}

export interface UnionSupergraphProjectionResponse {
  campaign_id: string;
  session_id: string;
  graph_id?: string | null;
  markdown?: string | null;
  focus: GraphFocusOverlay;
  node_views: Record<string, GraphProjectionNodeView>;
  source_spans?: RecapProjectionSourceSpan[];
  mentions: Array<{
    mention_id: string;
    node_id: string;
    label: string;
    start_offset?: number | null;
    end_offset?: number | null;
    evidence_ref_ids: string[];
  }>;
  authored_overlay?: AuthoredOverlayProjectionSummary;
}

export interface GoldGraphProjectionResponse extends UnionSupergraphProjectionResponse {
  source_kind: "gold_fixture";
  fixture_version?: string | null;
  gold_fixture_id: string;
  gold_fixture_relpath: string;
}

export interface GraphReviewResolverSelectedNode {
  node_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
  aliases: string[];
  summary?: string | null;
  source_domains: string[];
  adjacent_labels: string[];
  evidence_ref_ids: string[];
}

export interface GraphReviewExistingObjectResolverRequest {
  schema: "dmb_graph_review_existing_object_resolver_request_v1";
  campaign_id: string;
  session_id: string;
  lane_role: "gold" | "live";
  selected_node: GraphReviewResolverSelectedNode;
  projection_graph_id?: string | null;
  live_run_manifest_path?: string | null;
  query?: string | null;
  node_views?: Record<string, GraphProjectionNodeView> | null;
  scopes?: GraphObjectCandidateScope[] | null;
  include_authored_overlay?: boolean;
  include_current_projection?: boolean;
  include_worldbuilding?: boolean;
  include_party_pc?: boolean;
  include_gm_private?: boolean;
  include_campaign_memory?: boolean;
  max_results_per_scope?: number;
}

export type GraphObjectCandidateScope =
  | "current_recap_projection"
  | "authored_overlay"
  | "campaign_memory"
  | "worldbuilding"
  | "party_pc"
  | "gm_private";

export interface GraphObjectCandidateDiagnostic {
  code: string;
  message: string;
  scope?: GraphObjectCandidateScope | null;
  severity?: "info" | "warning" | "error";
}

export interface GraphReviewExistingObjectCandidate {
  candidate_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
  confidence: "high" | "medium" | "low";
  score: number;
  reason: string;
  source: "gold_fixture" | "live_projection" | "union_supergraph" | "manual_review_variant" | "unknown";
  suggested_action: "link_existing_later" | "create_new_later" | "manual_review_needed";
  existing_object_ref?: Record<string, string> | null;
  matched_features: string[];
  graph_scope?: GraphObjectCandidateScope | null;
  source_label?: string | null;
  source_path?: string | null;
  source_graph_id?: string | null;
  visibility?: string | null;
  aliases?: string[];
  authored?: boolean;
}

export interface GraphReviewExistingObjectResolverResponse {
  schema: "dmb_graph_review_existing_object_resolver_response_v1";
  campaign_id: string;
  session_id: string;
  selected_node_id: string;
  selected_label: string;
  candidates: GraphReviewExistingObjectCandidate[];
  warnings: string[];
  scopes_searched?: GraphObjectCandidateScope[];
  diagnostics?: GraphObjectCandidateDiagnostic[];
}


export interface PartyRegistryMemberRow {
  slug: string;
  kind: string;
  display_name: string;
  hub_rel_path: string;
  hub_resolved: boolean;
  player?: string | null;
  corpus_ref: Record<string, unknown>;
}

export interface PartyRegistrySurfaceResponse {
  schema_version: "dmb_party_registry_surface_v1";
  campaign_id: string;
  session: number;
  session_id: string;
  registry_schema?: string | null;
  registry_relpath?: string | null;
  party_names: string[];
  pc_slugs: string[];
  companion_slugs: string[];
  notable_npc_slugs: string[];
  members: PartyRegistryMemberRow[];
  warnings: string[];
  registry_summary: Record<string, unknown>;
  session_graph_context: Record<string, unknown>;
  available_session_keys: string[];
  has_session_roster: boolean;
  known_pc_slugs: string[];
  known_companion_slugs: string[];
}

export interface PartyRegistrySessionRosterWritePrepareRequest {
  campaign_id: string;
  session: number;
  pc_slugs: string[];
  companion_slugs: string[];
  copy_from_session?: number | null;
}

export interface PartyRegistrySessionRosterWritePrepareResponse {
  schema_version: "dmb_party_registry_session_roster_write_prepare_v1";
  campaign_id: string;
  session: number;
  registry_relpath: string;
  file_exists: boolean;
  writer_ok: boolean;
  writer_phase?: string | null;
  writer_confirm_token?: string | null;
  writer_diff?: string | null;
  existing_size_bytes?: number | null;
  new_size_bytes?: number | null;
  pc_slugs: string[];
  companion_slugs: string[];
  warnings: string[];
  diagnostics: string[];
}

export interface PartyRegistrySessionRosterWriteCommitRequest extends PartyRegistrySessionRosterWritePrepareRequest {
  writer_confirm_token: string;
}

export interface PartyRegistrySessionRosterWriteCommitResponse {
  schema_version: "dmb_party_registry_session_roster_write_commit_v1";
  campaign_id: string;
  session: number;
  registry_relpath: string;
  writer_ok: boolean;
  writer_phase?: string | null;
  bytes_written?: number | null;
  file_fingerprint?: string | null;
  backup_relpath?: string | null;
  diagnostics: string[];
}

export type GraphGoldAuthoringProposalStatus = "staged" | "accepted_local" | "rejected_local";
export type GraphGoldAuthoringProposalType = "node_from_span" | "node_assertion" | "relationship_assertion" | "existing_object_link_intent";
export type GraphGoldAuthoringLaneRole = "gold" | "live";

export interface GraphGoldAuthoringRelationshipNodeRef {
  lane_role: GraphGoldAuthoringLaneRole;
  node_id: string;
  label: string;
}

export interface GraphGoldAuthoringLocalProposalBase {
  proposal_id: string;
  proposal_type: GraphGoldAuthoringProposalType;
  created_at_iso: string;
  status: GraphGoldAuthoringProposalStatus;
}

export interface GraphGoldAuthoringNodeFromSpanProposal extends GraphGoldAuthoringLocalProposalBase {
  proposal_type: "node_from_span";
  lane_role: GraphGoldAuthoringLaneRole;
  source_text: string;
  source_offsets?: { start: number; end: number } | null;
  suggested_label: string;
  suggested_kind?: string | null;
}

export interface GraphGoldAuthoringNodeAssertionProposal extends GraphGoldAuthoringLocalProposalBase {
  proposal_type: "node_assertion";
  lane_role: GraphGoldAuthoringLaneRole;
  node_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
}

export interface GraphGoldAuthoringRelationshipAssertionProposal extends GraphGoldAuthoringLocalProposalBase {
  proposal_type: "relationship_assertion";
  lane_role: GraphGoldAuthoringLaneRole | "mixed";
  source_node: GraphGoldAuthoringRelationshipNodeRef;
  target_node: GraphGoldAuthoringRelationshipNodeRef;
  predicate: string;
}

export interface GraphGoldAuthoringExistingObjectLinkIntentProposal extends GraphGoldAuthoringLocalProposalBase {
  proposal_type: "existing_object_link_intent";
  selected_node: GraphGoldAuthoringRelationshipNodeRef;
  candidate: {
    candidate_id: string;
    label: string;
    source: GraphReviewExistingObjectCandidate["source"];
    confidence: GraphReviewExistingObjectCandidate["confidence"];
    score?: number | null;
  };
}

export type GraphGoldAuthoringLocalProposal =
  | GraphGoldAuthoringNodeFromSpanProposal
  | GraphGoldAuthoringNodeAssertionProposal
  | GraphGoldAuthoringRelationshipAssertionProposal
  | GraphGoldAuthoringExistingObjectLinkIntentProposal;

export interface GraphGoldAuthoringPrepareRequest {
  schema: "dmb_graph_gold_authoring_prepare_request_v1";
  campaign_id: string;
  session_id: string;
  fixture_version?: string | null;
  proposals: GraphGoldAuthoringLocalProposal[];
  include_rejected?: boolean;
}

export interface GraphGoldAuthoringPrepareDiagnostic {
  code: string;
  message: string;
  source_proposal_id?: string | null;
  severity: "error" | "warning" | "info";
}

export interface GraphGoldAuthoringProposalCounts {
  total: number;
  accepted_local: number;
  staged: number;
  rejected_local: number;
  candidate_operations: number;
  ignored: number;
  blocked: number;
}

export interface GraphGoldAuthoringNormalizedProposal {
  proposal_id: string;
  proposal_type: GraphGoldAuthoringProposalType;
  status: GraphGoldAuthoringProposalStatus;
  eligible_for_operation: boolean;
  summary: string;
  diagnostics: GraphGoldAuthoringPrepareDiagnostic[];
}

export interface GraphGoldAuthoringPreviewOperation {
  operation_id: string;
  operation_type: "add_node" | "assert_node" | "add_edge" | "link_existing_intent" | "ignored" | "blocked";
  source_proposal_id: string;
  label: string;
  summary: string;
  gold_shape_preview?: Record<string, unknown> | null;
  requires_manual_review: boolean;
  diagnostics: GraphGoldAuthoringPrepareDiagnostic[];
}

export interface GraphGoldAuthoringCommitRequest {
  schema: "dmb_graph_gold_authoring_commit_request_v1";
  campaign_id: string;
  session_id: string;
  fixture_version?: string | null;
  proposals: GraphGoldAuthoringLocalProposal[];
  expected_prepare_fingerprint?: string | null;
  expected_fixture_state_fingerprint?: string | null;
  commit_message?: string | null;
  operator_note?: string | null;
}

export interface GraphGoldAuthoringCommitChangedCounts {
  nodes_added: number;
  nodes_asserted: number;
  edges_added: number;
  link_intents_recorded: number;
  operations_skipped: number;
}

export interface GraphGoldAuthoringCommittedOperation {
  operation_id: string;
  operation_type: string;
  source_proposal_id: string;
  status: "applied" | "recorded_assertion" | "recorded_intent";
  target_id?: string | null;
  summary: string;
}

export interface GraphGoldAuthoringSkippedOperation {
  operation_id: string;
  operation_type: string;
  source_proposal_id: string;
  reason: string;
  diagnostics: GraphGoldAuthoringPrepareDiagnostic[];
}

export interface GraphGoldAuthoringCommitDiagnostic {
  code: string;
  message: string;
  source_proposal_id?: string | null;
  severity: "error" | "warning" | "info";
}

export interface GraphGoldAuthoringCommitResponse {
  schema: "dmb_graph_gold_authoring_commit_response_v1";
  campaign_id: string;
  session_id: string;
  fixture_relpath: string;
  backup_relpath?: string | null;
  event_log_relpath?: string | null;
  commit_id: string;
  committed_at_iso: string;
  commit_status: "committed" | "blocked" | "partial";
  prepare_fingerprint: string;
  applied_operations: GraphGoldAuthoringCommittedOperation[];
  skipped_operations: GraphGoldAuthoringSkippedOperation[];
  diagnostics: GraphGoldAuthoringCommitDiagnostic[];
  changed_counts: GraphGoldAuthoringCommitChangedCounts;
}

export interface GraphGoldAuthoringVerifyCommitRequest {
  schema: "dmb_graph_gold_authoring_verify_commit_request_v1";
  campaign_id: string;
  session_id: string;
  commit_id: string;
  applied_operations: GraphGoldAuthoringCommittedOperation[];
}

export interface GraphGoldAuthoringVerifiedOperation {
  operation_id: string;
  operation_type: string;
  source_proposal_id: string;
  target_id?: string | null;
  verification_status: "found_in_gold_projection" | "found_in_fixture_only" | "recorded_event_only" | "not_expected_in_projection" | "missing";
  summary: string;
}

export interface GraphGoldAuthoringVerifyDiagnostic {
  code: string;
  message: string;
  operation_id?: string | null;
  severity: "error" | "warning" | "info";
}

export interface GraphGoldAuthoringVerifyCommitResponse {
  schema: "dmb_graph_gold_authoring_verify_commit_response_v1";
  campaign_id: string;
  session_id: string;
  commit_id: string;
  verification_status: "verified" | "partial" | "missing" | "blocked";
  checked_operations: GraphGoldAuthoringVerifiedOperation[];
  diagnostics: GraphGoldAuthoringVerifyDiagnostic[];
}

export interface GraphGoldAuthoringPrepareResponse {
  schema: "dmb_graph_gold_authoring_prepare_response_v1";
  campaign_id: string;
  session_id: string;
  fixture_relpath?: string | null;
  validation_status: "ready" | "ready_with_warnings" | "blocked";
  proposal_counts: GraphGoldAuthoringProposalCounts;
  normalized_proposals: GraphGoldAuthoringNormalizedProposal[];
  proposed_operations: GraphGoldAuthoringPreviewOperation[];
  blocking_errors: GraphGoldAuthoringPrepareDiagnostic[];
  warnings: GraphGoldAuthoringPrepareDiagnostic[];
  preview_summary: string;
  prepare_fingerprint: string;
  fixture_state_fingerprint: string;
  write_performed: false;
}

export interface GraphAuthoringDiagnostic {
  code: string;
  message: string;
  local_proposal_id?: string | null;
  severity: "error" | "warning" | "info";
}

export interface GraphObjectAuthoringProposalPayload {
  localProposalId: string;
  proposalKind: "object" | "link_existing" | "relationship" | "merge_objects";
  status: "staged_local";
  selection?: Record<string, unknown> | null;
  objectRef?: Record<string, unknown> | null;
  selectedText?: string | null;
  normalizedSelectedText?: string | null;
  existingObjectRef?: Record<string, unknown> | null;
  operation?: string | null;
  aliasText?: string | null;
  sourceObjectRef?: Record<string, unknown> | null;
  targetObjectRef?: Record<string, unknown> | null;
  relationshipType?: string | null;
  relationshipLabel?: string | null;
  direction?: "directed" | "undirected" | null;
  summary?: string | null;
  survivorObjectRef?: Record<string, unknown> | null;
  mergedObjectRefs?: Record<string, unknown>[] | null;
  mergeReason?: string | null;
  matchedFeatures?: string[];
  aliasPolicy?: "preserve_all_aliases" | "manual" | null;
  relationshipPolicy?:
    | "preserve_all_relationships"
    | "manual_review_required"
    | null;
  evidencePolicy?: "preserve_all_evidence" | null;
  visibility: {
    visibility: string;
    revealState?: string;
    visibilityNote?: string | null;
  };
  graphScopes: string[];
  provenancePreview: {
    origin: "human_authored";
    authoringSurface: "memory_ingest_graph_authoring";
    sourceGraphId?: string | null;
    sourceArtifactPath?: string | null;
    operatorNote?: string | null;
  };
}

export interface GraphObjectAuthoringPrepareRequest {
  campaignId: string;
  campaignRel?: string | null;
  sessionId?: string | null;
  sourceRunId?: string | null;
  sourceGraphId?: string | null;
  sourceProjectionId?: string | null;
  proposals: GraphObjectAuthoringProposalPayload[];
  operatorNote?: string | null;
}

export interface AuthoredGraphAssertionPreview {
  assertion_id: string;
  assertion_kind: "object" | "link_existing" | "relationship";
  operation: string;
  local_proposal_id: string;
  summary: string;
}

export interface GraphAuthoringOverlaySummary {
  existing_assertion_count: number;
  proposed_assertion_count: number;
  total_assertion_count: number;
  object_count: number;
  link_existing_count: number;
  relationship_count: number;
  merge_objects_count: number;
}

export interface GraphObjectAuthoringPrepareResponse {
  prepared: boolean;
  campaign_id: string;
  overlay_path: string;
  event_log_path: string;
  current_overlay_token: string;
  proposed_assertions_digest: string;
  confirm_token: string;
  assertion_count: number;
  event_count: number;
  assertions_preview: AuthoredGraphAssertionPreview[];
  overlay_summary: GraphAuthoringOverlaySummary;
  diagnostics: GraphAuthoringDiagnostic[];
  no_mutation_guarantees: string[];
}

export interface GraphObjectAuthoringCommitRequest {
  campaignId: string;
  campaignRel?: string | null;
  sessionId?: string | null;
  sourceRunId?: string | null;
  sourceGraphId?: string | null;
  sourceProjectionId?: string | null;
  proposals: GraphObjectAuthoringProposalPayload[];
  confirmToken: string;
  currentOverlayToken: string;
  operatorNote?: string | null;
  previewUnionStorePath?: string | null;
}

export type UnionStoreMaterializationReason =
  | "no_preview_union_store_selected"
  | "no_actionable_merge_assertions"
  | "materialized"
  | "materialization_failed"
  | "event_log_failed";

export interface GraphObjectAuthoringUnionStoreMaterializationSummary {
  attempted: boolean;
  applied: boolean;
  reason: UnionStoreMaterializationReason;
  union_store_path?: string | null;
  backup_path?: string | null;
  applied_assertion_ids: string[];
  redirects_added: number;
  edges_rewired: number;
  survivor_nodes_updated: number;
  diagnostics: GraphAuthoringDiagnostic[];
}

export interface GraphObjectAuthoringCommitResponse {
  committed: boolean;
  campaign_id: string;
  overlay_path: string;
  event_log_path: string;
  backup_path?: string | null;
  assertion_count: number;
  event_count: number;
  new_overlay_token: string;
  diagnostics: GraphAuthoringDiagnostic[];
  no_mutation_guarantees: string[];
  union_store_materialization?: GraphObjectAuthoringUnionStoreMaterializationSummary | null;
}

export interface GraphMergeReconciliationDiagnostic {
  code: string;
  message: string;
  severity: "error" | "warning" | "info";
  assertion_id?: string | null;
  node_id?: string | null;
}

export interface GraphMergeReconciliationPlanSummary {
  merge_assertion_count: number;
  applicable_assertion_count: number;
  already_materialized_assertion_count: number;
  skipped_assertion_count: number;
  redirect_count: number;
  edge_rewire_count: number;
  edge_dedupe_count: number;
}

export interface GraphMergeReconciliationApplySummary {
  redirects_added: number;
  merge_records_added: number;
  survivor_nodes_created: number;
  survivor_nodes_updated: number;
  merged_away_nodes_marked: number;
  edges_rewired: number;
  edges_deduped: number;
}

export interface GraphMergeReconciliationPrepareRequest {
  campaignId: string;
  campaignRel?: string | null;
  sessionId?: string | null;
  previewUnionStorePath: string;
  materializationPassId?: string | null;
}

export interface GraphMergeReconciliationPrepareResponse {
  prepared: boolean;
  campaign_id: string;
  session_id?: string | null;
  overlay_path: string;
  union_store_path: string;
  materialization_pass_id: string;
  overlay_token: string;
  union_store_token: string;
  plan_digest: string;
  confirm_token: string;
  summary: GraphMergeReconciliationPlanSummary;
  diagnostics: GraphMergeReconciliationDiagnostic[];
  no_mutation_guarantees: string[];
}

export interface GraphMergeReconciliationApplyRequest {
  campaignId: string;
  campaignRel?: string | null;
  sessionId?: string | null;
  previewUnionStorePath: string;
  materializationPassId: string;
  confirmToken: string;
  overlayToken: string;
  unionStoreToken: string;
}

export interface GraphMergeReconciliationApplyResponse {
  applied: boolean;
  campaign_id: string;
  session_id?: string | null;
  overlay_path: string;
  union_store_path: string;
  backup_path?: string | null;
  materialization_pass_id: string;
  applied_assertion_ids: string[];
  skipped_assertion_ids: string[];
  summary: GraphMergeReconciliationApplySummary;
  diagnostics: GraphMergeReconciliationDiagnostic[];
  no_mutation_guarantees: string[];
}
