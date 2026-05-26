import type {
  LiveEvent,
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
    module_id: "sources",
    title: "Sources",
    default_slot: "overlay",
    required: false,
    enabled_by_default: false,
    description: "Provenance",
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
  enabled_surface_modules: ["chat", "record", "roll_stack"],
  queued_job_count: 0,
  recent_event_count: 0,
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
  diagnostics: {},
  provenance: {},
};

export const mockContextResponse: LiveQueryResponse = {
  answer: "Context lookup path; retrieval UI deferred.",
  classification: {
    latency_mode: "context_lookup",
    event_type: "context_question",
  },
  events_written: ["evt-ctx-1"],
  jobs_queued: [],
  next_suggestions: [],
  diagnostics: { note: "stub" },
  provenance: { mode: "context_lookup" },
};
