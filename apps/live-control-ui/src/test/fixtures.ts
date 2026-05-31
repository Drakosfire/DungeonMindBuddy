import type {
  ArtifactReadResponse,
  CapabilityReadResponse,
  LiveEvent,
  PlanViewProjection,
  ProjectionCommand,
  ProjectionCapability,
  ProjectionWriteResult,
  LiveQueryResponse,
  LiveState,
  SurfaceLayout,
  SurfaceModuleDefinition,
} from "../api/types";

export const mockCatalog: SurfaceModuleDefinition[] = [
  {
    module_id: "chat",
    title: "Chat",
    default_slot: "main",
    required: true,
    enabled_by_default: true,
    description: "Live query",
    config_schema: null,
  },
  {
    module_id: "record",
    title: "Record",
    default_slot: "sidebar",
    required: true,
    enabled_by_default: true,
    description: "Event stream",
    config_schema: null,
  },
  {
    module_id: "roll_stack",
    title: "Roll stack",
    default_slot: "bottom",
    required: false,
    enabled_by_default: true,
    description: "Pending tables",
    config_schema: null,
  },
  {
    module_id: "timeline",
    title: "Timeline",
    default_slot: "bottom",
    required: false,
    enabled_by_default: true,
    description: "Projected beats",
    config_schema: null,
  },
  {
    module_id: "sources",
    title: "Corpus & sources",
    default_slot: "sidebar",
    required: false,
    enabled_by_default: true,
    description: "On-disk recap ingest ladder and planning readiness.",
    config_schema: null,
  },
  {
    module_id: "ingestion",
    title: "Ingestion",
    default_slot: "sidebar",
    required: false,
    enabled_by_default: false,
    description: "Raw recap ingest operator pane.",
    config_schema: null,
  },
  {
    module_id: "future_panel",
    title: "Future panel",
    default_slot: "overlay",
    required: false,
    enabled_by_default: false,
    description: "Not implemented",
    config_schema: null,
  },
];

export const mockLayout: SurfaceLayout = {
  schema_version: "0.1.0",
  layout_version: 1,
  updated_at: "2026-05-25T00:00:00Z",
  campaign_id: "longmont-c2",
  session: 22,
  modules: [
    {
      module_id: "chat",
      slot: "main",
      order: 0,
      enabled: true,
      collapsed: false,
      size: "2fr",
      config: {},
    },
    {
      module_id: "record",
      slot: "sidebar",
      order: 0,
      enabled: true,
      collapsed: false,
      size: "1fr",
      config: {},
    },
    {
      module_id: "roll_stack",
      slot: "bottom",
      order: 0,
      enabled: true,
      collapsed: false,
      size: null,
      config: {},
    },
    {
      module_id: "timeline",
      slot: "bottom",
      order: 1,
      enabled: true,
      collapsed: false,
      size: null,
      config: {},
    },
    {
      module_id: "ingestion",
      slot: "sidebar",
      order: 3,
      enabled: false,
      collapsed: true,
      size: null,
      config: {},
    },
    {
      module_id: "sources",
      slot: "overlay",
      order: 0,
      enabled: false,
      collapsed: true,
      size: null,
      config: {},
    },
    {
      module_id: "future_panel",
      slot: "overlay",
      order: 1,
      enabled: false,
      collapsed: false,
      size: null,
      config: {},
    },
  ],
};

export const mockState: LiveState = {
  schema_version: "0.1.0",
  campaign_id: "longmont-c2",
  session: 22,
  derived: true,
  authoritative: false,
  derived_from: ["live_packet.json"],
  generated_at: "2026-05-25T00:00:00Z",
  now: {
    day_label: "Session 22 start",
    party_position: "North of Mossford",
    route_intent: "Toward Mireward",
    active_weather: null,
    next_suggested_beat: "T-WX storm weather roll",
  },
  open_loop_count: 1,
  pending_roll_tables: ["T-WX", "R5"],
  enabled_surface_modules: ["chat", "record", "roll_stack", "timeline"],
  queued_job_count: 0,
  recent_event_count: 0,
};

export const mockPlanView: PlanViewProjection = {
  schema_version: "0.1.0",
  campaign_id: "longmont-c2",
  session: 22,
  authoritative: false,
  generated_at: "2026-05-28T00:00:00Z",
  derived_from: ["live_packet.json", "event_log.jsonl", "job_queue.jsonl"],
  timeline: [
    {
      id: "beat-day1-weather-front",
      label: "Travel Day 1 weather/front beat",
      status: "projected",
      time_hint: "Day 1",
      summary: "Weather and march pressure establish the day-one travel frame.",
      table_ready_prompt: "Roll T-WX and narrate immediate travel consequences.",
      refs: [
        {
          target_type: "roll_table",
          target_id: "T-WX",
          label: "Travel weather table",
          source_status: "authoritative",
          role: "next_roll",
        },
      ],
      state_links: {
        event_ids: [],
        job_ids: [],
        open_loop_ids: [],
      },
    },
  ],
};

export const mockRollEvent: LiveEvent = {
  schema_version: "0.1.0",
  id: "evt-roll-1",
  created_at: "2026-05-25T12:00:00Z",
  campaign_id: "longmont-c2",
  session: 22,
  event_type: "roll_result",
  latency_mode: "fast_live",
  event_origin: "user_input",
  summary: "Resolved T-WX roll 7: Hail dent.",
  derived_fields: { table_id: "T-WX", roll: 7, headline: "Hail dent" },
};

export const mockQueryResponse: LiveQueryResponse = {
  schema: "dmb_live_query_response_v1",
  query_id: "live-query-fast-001",
  session: 22,
  mode: "live_turn",
  status: "ok",
  answer: "Storm weather (T-WX 7): Hail dent — ...",
  classification: {
    latency_mode: "fast_live",
    event_type: "roll_result",
    table_id: "T-WX",
    roll: 7,
  },
  events_written: ["evt-roll-1"],
  jobs_queued: ["job-1"],
  next_suggestions: ["Road encounter R5 when travel beat triggers."],
  diagnostics: [],
  provenance: {},
  citations: [],
  context_packet: null,
  warnings: [],
  mutations: [],
};

export const mockContextResponse: LiveQueryResponse = {
  schema: "dmb_live_query_response_v1",
  query_id: "live-query-context-001",
  session: 22,
  mode: "context_lookup",
  status: "ok",
  answer:
    "The party remains pointed toward the swamp as the likely source of Mirathorn pressure [ev-a1b2c3d4e5].",
  classification: {
    latency_mode: "context_lookup",
    event_type: "context_question",
  },
  events_written: [],
  jobs_queued: [],
  next_suggestions: [],
  diagnostics: [],
  provenance: { mode: "context_lookup" },
  citations: [
    {
      evidence_id: "ev-a1b2c3d4e5",
      path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
      line_start: 24,
      line_end: 24,
      source_role: "play_recap",
      authority: "canon_play",
    },
  ],
  context_packet: {
    schema: "dmb_enriched_planning_context_packet_v1",
    question_id: "live-query-context-001",
    intent_class: "play_fact_retrieval",
    admitted_evidence: [
      {
        evidence_id: "ev-a1b2c3d4e5",
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
        source_role: "play_recap",
        authority: "canon_play",
        line_start: 24,
        line_end: 24,
        text_excerpt: "The group decides to continue toward the swamp.",
      },
    ],
    rejected_evidence: [
      {
        rejection_id: "rej-001",
        reason_code: "authority_forbidden_for_play_fact",
        evidence: {
          evidence_id: "ev-ffffeeee11",
          path: "corpus/.../_ingest_staging/session_22_raw_notes.md",
          source_role: "table_notes",
          authority: "pre_canonical_evidence",
          text_excerpt: "staging only",
        },
      },
    ],
  },
  warnings: [],
  mutations: [],
};

export function makeEventArtifact(
  overrides: Partial<ArtifactReadResponse> = {},
): ArtifactReadResponse {
  return {
    schema_version: "0.1.0",
    target: {
      target_type: "event",
      target_id: "evt-roll-1",
      label: "Weather roll resolved",
      source_status: "authoritative",
      metadata: {},
    },
    artifact_kind: "event",
    title: "Weather roll resolved",
    read_only: true,
    file_state_token: "evt-token-1",
    payload: {
      content_type: "application/json",
      data: {
        id: "evt-roll-1",
        event_type: "roll_result",
        created_at: "2026-05-25T12:00:00Z",
        summary: "Weather resolved to 16.",
        latency_mode: "fast_live",
        event_origin: "user_input",
        input_text: "Weather 16.",
        derived_fields: { table_id: "T-WX", roll: 16 },
      },
      text: null,
    },
    provenance: {
      source_path: "event_log.jsonl",
      source_role: "event_log",
      generated_by: "live_control_server",
      notes: null,
    },
    metadata: {
      event_type: "roll_result",
    },
    ...overrides,
  };
}

export function makeRollTableArtifact(
  overrides: Partial<ArtifactReadResponse> = {},
): ArtifactReadResponse {
  return {
    schema_version: "0.1.0",
    target: {
      target_type: "roll_table",
      target_id: "T-WX",
      label: "Storm weather",
      source_status: "authoritative",
      metadata: {},
    },
    artifact_kind: "roll_table",
    title: "Storm weather",
    read_only: true,
    file_state_token: "table-token-1",
    payload: {
      content_type: "text/markdown",
      data: null,
      text: "## 1-4\nCalm skies\n## 5-8\nHail and crosswind",
    },
    provenance: {
      source_path:
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_storm_weather_d20.md",
      source_role: "known_roll_table",
      generated_by: "live_control_server",
      notes: null,
    },
    metadata: {
      table_id: "T-WX",
      title: "Storm weather",
      dice: "d20",
      status: "pending",
      default_latency_mode: "fast_live",
      parsed_summary: { shape: "band", band_count: 2, row_count: 8 },
    },
    ...overrides,
  };
}

export function makeCapabilityResponse(
  overrides: Partial<CapabilityReadResponse> = {},
): CapabilityReadResponse {
  const capabilities: ProjectionCapability[] = [
    {
      command_type: "patch_artifact",
      label: "Patch artifact",
      lane: "prep_note",
      enabled: true,
      required_fields: ["expected_file_state_token", "old_text", "new_text"],
      risk_level: "medium",
      disabled_reason: null,
      metadata: {
        patch_kind: "replace_text",
        requires_file_state_token: true,
        supports_dry_run: true,
      },
    },
    {
      command_type: "append_observation",
      label: "Append observation",
      lane: "observed_play",
      enabled: true,
      required_fields: ["observation"],
      risk_level: "low",
      disabled_reason: null,
      metadata: { supported_in_pr: 85 },
    },
  ];
  return {
    schema_version: "0.1.0",
    target: {
      target_type: "roll_table",
      target_id: "T-WX",
      label: "Storm weather",
      source_status: "authoritative",
      metadata: {},
    },
    capabilities,
    metadata: {},
    ...overrides,
  };
}

export function makeAppendObservationCommand(
  overrides: Partial<ProjectionCommand> = {},
): ProjectionCommand {
  return {
    command_type: "append_observation",
    target: {
      target_type: "roll_table",
      target_id: "T-WX",
      label: "Storm weather",
      source_status: "authoritative",
      metadata: {},
    },
    lane: "observed_play",
    payload: {
      observation: "Remember this as wagon axle pressure.",
      session_clock: "live-control",
      visibility: "live_note",
    },
    evidence: [],
    requested_by: {
      requester_type: "human_ui",
      requester_id: "live-control-ui",
    },
    idempotency_key: "ui-append-observation:roll_table:T-WX:test-id",
    ...overrides,
  };
}

export function makeWriteResult(
  overrides: Partial<ProjectionWriteResult> = {},
): ProjectionWriteResult {
  return {
    write_id: "write-test-1",
    status: "accepted",
    events_appended: ["evt-observation-1"],
    jobs_queued: [],
    artifacts_changed: [],
    invalidations: [
      {
        projection_key: "live.events",
        target: null,
        reason: "append_observation appended live event",
      },
    ],
    conflicts: [],
    diagnostics: [],
    metadata: {},
    ...overrides,
  };
}
