import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AgentInteractionThread,
  AgentInteractionTrace,
  AgentWorldGraphQueryContext,
  HermesGraphGrounding,
  WorldGraphAnchorCitation,
} from "../../api/types";
import {
  activeThreadStorageKey,
  buildEvidenceSnapshots,
  createAgentInteractionThread,
  deleteAgentThread,
  loadAgentThreadById,
  loadAgentThreadIndex,
  persistAgentThread,
  persistAgentThreadIndex,
  renameAgentThread,
  safeTraceForPersistence,
  turnFromResponse,
  worstCorpusFreshnessStatus,
  setActiveAgentThread,
  threadIndexStorageKey,
  threadStorageKey,
  upsertThreadInIndex,
} from "./agentInteractionHistory";

const NO_LEAK_MARKERS = [
  "/foreign/absolute/path.md",
  "foreign/private/source.md",
  "FOREIGN_WORLD_ID",
  "FOREIGN_CAMPAIGN_ID",
  "FOREIGN_REVISION_ID",
  "FOREIGN_SOURCE_ANCHOR_ID",
  "RAW_PROMPT_SECRET",
  "RAW_TOOL_ARGUMENT_SECRET",
  "RAW_SOURCE_BODY_SECRET",
  "RAW_HERMES_MESSAGE_SECRET",
  "SECRET_COMMAND_SUMMARY",
  "SECRET_CONTEXT_SUMMARY",
] as const;

const graphGrounding: HermesGraphGrounding = {
  schema: "dmb_hermes_graph_grounding_v1",
  state: "grounded",
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  focus: { kind: "session", session_id: "session-21" },
  admissibility: "gm",
  revision_id: "rev-1",
  successful_tool_count: 1,
  source_anchor_count: 1,
  diagnostic_codes: [],
  warnings: [],
};

const graphCitation: WorldGraphAnchorCitation = {
  schema: "dmb_world_graph_anchor_citation_v1",
  kind: "world_graph_anchor",
  anchor_id: "source-anchor:v1:abc",
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  focus: { kind: "session", session_id: "session-21" },
  admissibility: "gm",
  revision_id: "rev-1",
};

function makeThread(title = "Inn prep", updatedAt = "2026-06-22T00:00:00.000Z"): AgentInteractionThread {
  return {
    ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", title),
    threadId: title.toLowerCase().replace(/\s+/g, "-"),
    createdAt: "2026-06-22T00:00:00.000Z",
    updatedAt,
    turns: [{
      turnId: `${title}-turn`,
      askedAt: "2026-06-22T00:00:00.000Z",
      completedAt: "2026-06-22T00:00:01.000Z",
      question: `Question for ${title}?`,
      answer: `Secret answer body for ${title}`,
      backend: "hermes",
      status: "ok",
      contextSummary: { admitted_count: 1, rejected_count: 0 },
      citations: [{ evidence_id: "e1", path: "corpus/test.md", line_start: 1, line_end: 1, source_role: "play_recap", authority: "canon_play" }],
      trace: { trace_id: `trace-${title}`, prompt_preview: "secret prompt", artifact_refs: [{ kind: "file", label: "artifact", path: "/tmp/secret.json" }] } as AgentInteractionTrace,
      warnings: [],
      retrievalFreshness: {
        schema: "dmb_retrieval_freshness_decision_v1",
        decision: "fresh_retrieval",
        used_fresh_retrieval: true,
        used_thread_context: false,
        admitted_evidence_count: 1,
        rejected_evidence_count: 0,
        prior_turn_count: 0,
        reason: "Fresh corpus evidence was admitted for this turn.",
        warnings: [],
      },
    }],
    uiState: { traceVisible: true, scrollAnchorTurnId: `${title}-turn` },
  };
}

describe("agentInteractionHistory", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("load empty index returns valid empty index", () => {
    expect(loadAgentThreadIndex("longmont-c2", "plan")).toEqual({
      schema: "agent_interaction_thread_index_v1",
      campaignId: "longmont-c2",
      surfaceId: "plan",
      activeThreadId: null,
      threads: [],
    });
  });

  it("persists and loads an index round-trip", () => {
    const thread = makeThread();
    persistAgentThreadIndex({
      schema: "agent_interaction_thread_index_v1",
      campaignId: "longmont-c2",
      surfaceId: "plan",
      activeThreadId: thread.threadId,
      threads: [{ threadId: thread.threadId, title: thread.title, createdAt: thread.createdAt, updatedAt: thread.updatedAt, turnCount: 1, activeBackend: "hermes", hermesSessionId: null }],
    });

    expect(loadAgentThreadIndex("longmont-c2", "plan").threads).toHaveLength(1);
    expect(loadAgentThreadIndex("longmont-c2", "plan").activeThreadId).toBe(thread.threadId);
  });

  it("upsertThreadInIndex stores summary only and excludes answer, source, and trace bodies", () => {
    const thread = makeThread();
    upsertThreadInIndex(thread);

    const indexJson = localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan")) ?? "";
    expect(indexJson).toContain("Inn prep");
    expect(indexJson).toContain("turnCount");
    expect(indexJson).not.toContain("Secret answer body");
    expect(indexJson).not.toContain("corpus/test.md");
    expect(indexJson).not.toContain("secret prompt");
    expect(indexJson).not.toContain("artifact_refs");
  });

  it("migrates a legacy active thread into the index", () => {
    const thread = makeThread("Legacy prep");
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan"), thread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", thread.threadId), JSON.stringify(thread));

    const index = loadAgentThreadIndex("longmont-c2", "plan");
    expect(index.activeThreadId).toBe(thread.threadId);
    expect(index.threads[0]).toMatchObject({ title: "Legacy prep", turnCount: 1 });
  });

  it("invalid index JSON returns empty index", () => {
    localStorage.setItem(threadIndexStorageKey("longmont-c2", "plan"), "{broken");
    expect(loadAgentThreadIndex("longmont-c2", "plan").threads).toEqual([]);
  });

  it("setActiveAgentThread updates active pointer", () => {
    const thread = makeThread();
    upsertThreadInIndex(thread);
    setActiveAgentThread("longmont-c2", "plan", "next-thread");

    expect(loadAgentThreadIndex("longmont-c2", "plan").activeThreadId).toBe("next-thread");
    expect(localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"))).toBe("next-thread");
  });

  it("renameAgentThread updates title and index", () => {
    const thread = makeThread();
    persistAgentThread(thread);
    const renamed = renameAgentThread(thread, "Mireward inn prep");

    expect(renamed.title).toBe("Mireward inn prep");
    expect(loadAgentThreadIndex("longmont-c2", "plan").threads[0].title).toBe("Mireward inn prep");
  });

  it("deleteAgentThread removes body and index summary", () => {
    const thread = makeThread();
    persistAgentThread(thread);
    deleteAgentThread(thread);

    expect(loadAgentThreadById("longmont-c2", thread.threadId)).toBeNull();
    expect(loadAgentThreadIndex("longmont-c2", "plan").threads).toEqual([]);
  });

  it("delete active thread activates newest remaining thread or null", () => {
    const older = makeThread("Older", "2026-06-22T00:00:00.000Z");
    const newer = makeThread("Newer", "2026-06-23T00:00:00.000Z");
    persistAgentThread(older);
    persistAgentThread(newer);
    deleteAgentThread(newer);
    expect(loadAgentThreadIndex("longmont-c2", "plan").activeThreadId).toBe(older.threadId);

    deleteAgentThread(older);
    expect(loadAgentThreadIndex("longmont-c2", "plan").activeThreadId).toBeNull();
  });

  it("persists retrieval freshness as lightweight turn metadata only", () => {
    const thread = makeThread("Freshness prep");
    persistAgentThread(thread);

    const stored = localStorage.getItem(threadStorageKey("longmont-c2", thread.threadId)) ?? "";
    expect(stored).toContain("dmb_retrieval_freshness_decision_v1");
    expect(stored).toContain("fresh_retrieval");
    expect(stored).not.toContain("context_packet");
    expect(stored).not.toContain("text_excerpt");
    expect(stored).not.toContain("prompt_preview");
    expect(loadAgentThreadById("longmont-c2", thread.threadId)?.turns[0].retrievalFreshness?.decision).toBe("fresh_retrieval");
  });


  it("buildEvidenceSnapshots stores hashes and metadata without source excerpts", () => {
    const snapshots = buildEvidenceSnapshots([{
      evidence_id: "e1",
      path: "corpus/test.md",
      line_start: 2,
      line_end: 3,
      source_role: "play_recap",
      authority: "canon_play",
    }], "2026-06-22T00:00:00.000Z");

    expect(snapshots).toHaveLength(1);
    expect(snapshots[0]).toMatchObject({
      schema: "dmb_agent_evidence_snapshot_v1",
      evidence_id: "e1",
      path: "corpus/test.md",
      line_start: 2,
      line_end: 3,
      fingerprint_algorithm: "locator-v1",
      captured_at: "2026-06-22T00:00:00.000Z",
    });
    expect(JSON.stringify(snapshots)).not.toContain("text_excerpt");
    expect(JSON.stringify(snapshots)).not.toContain("source body");
  });

  it("worstCorpusFreshnessStatus prioritizes changed over unavailable, unknown, and current", () => {
    expect(worstCorpusFreshnessStatus(["current", "unknown", "unavailable", "changed"])).toBe("changed");
    expect(worstCorpusFreshnessStatus(["current", "unknown", "unavailable"])).toBe("unavailable");
  });

  it("safeTraceForPersistence strips prompt_preview and absolute artifact paths", () => {
    const trace = safeTraceForPersistence({
      trace_id: "trace-1",
      runtime: "cli",
      backend: "hermes",
      mode: "hermes_cli_oneshot",
      provider: "openai",
      model: "gpt",
      started_at: "2026-06-22T00:00:00.000Z",
      completed_at: "2026-06-22T00:00:01.000Z",
      elapsed_ms: 10,
      status: "ok",
      prompt_preview: "secret prompt",
      artifact_refs: [
        { kind: "file", label: "absolute", path: "/tmp/secret.json" },
        { kind: "file", label: "relative", path: "artifacts/trace.json" },
      ],
      steps: [{ name: "lookup", summary: "secret step detail" }],
      warnings: [],
    } as AgentInteractionTrace);

    expect(trace?.prompt_preview).toBeUndefined();
    expect(trace?.artifact_refs[0].path).toBe("");
    expect(trace?.artifact_refs[1].path).toBe("artifacts/trace.json");
  });

  it("persists grounding, graph citations, and sanitized tool events with reload round-trip", () => {
    const thread = makeThread("Hermes graph prep");
    const turn = turnFromResponse("Who is Lysandro?", {
      answer: "Lysandro is at the gate.",
      mode: "hermes_graph_agent",
      status: "ok",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: {},
      grounding: graphGrounding,
      citations: [graphCitation],
      agent_trace: {
        trace_id: "trace-hermes",
        runtime: "api",
        backend: "hermes",
        mode: "hermes_graph_agent",
        started_at: "2026-06-22T00:00:00.000Z",
        completed_at: "2026-06-22T00:00:01.000Z",
        elapsed_ms: 12,
        status: "ok",
        prompt_preview: "RAW_PROMPT_SECRET",
        usage: { available: true, input_tokens: 1, output_tokens: 1, total_tokens: 2 },
        steps: [],
        context_summary: {},
        artifact_refs: [{ kind: "file", label: "foreign", path: "/foreign/absolute/path.md" }],
        tool_events: [{
          tool_name: "graph_read",
          state: "completion",
          duration_ms: 8,
          world_id: "eldyrwild",
          campaign_id: "longmont-c2",
          focus: { kind: "session", session_id: "session-21" },
          admissibility: "gm",
          revision_pin: "rev-1",
          bounded_ids: { secret: "RAW_TOOL_ARGUMENT_SECRET" },
          retrieval_schema: "dmb_world_graph_projection_v1",
          outcome: "enough",
          matched_node_ids: ["node-1"],
          relationship_ids: ["edge-1"],
          source_anchor_ids: [graphCitation.anchor_id],
          diagnostic_codes: ["ok"],
        }],
        warnings: ["bounded warning"],
      } as AgentInteractionTrace,
    }, "hermes");
    thread.turns = [turn];
    persistAgentThread(thread);

    const stored = localStorage.getItem(threadStorageKey("longmont-c2", thread.threadId)) ?? "";
    for (const marker of NO_LEAK_MARKERS) {
      expect(stored).not.toContain(marker);
    }
    expect(stored).toContain("dmb_hermes_graph_grounding_v1");
    expect(stored).toContain("dmb_world_graph_anchor_citation_v1");
    expect(stored).toContain("graph_read");
    expect(stored).not.toContain("bounded_ids");
    expect(stored).not.toContain("prompt_preview");
    expect(stored).not.toContain("command_summary");
    expect(JSON.parse(stored).turns[0].trace.artifact_refs).toEqual([]);
    expect(JSON.parse(stored).turns[0].trace.steps).toEqual([]);
    expect(JSON.parse(stored).turns[0].trace.provider).toBeUndefined();
    expect(JSON.parse(stored).turns[0].trace.model).toBeUndefined();

    const reloaded = loadAgentThreadById("longmont-c2", thread.threadId);
    expect(reloaded?.turns[0].grounding?.state).toBe("grounded");
    expect(reloaded?.turns[0].citations?.[0]).toMatchObject({ kind: "world_graph_anchor", anchor_id: graphCitation.anchor_id });
    expect(reloaded?.turns[0].trace?.tool_events?.[0]).toMatchObject({
      tool_name: "graph_read",
      outcome: "enough",
      matched_node_ids: ["node-1"],
    });
    expect(reloaded?.turns[0].trace?.tool_events?.[0]).not.toHaveProperty("bounded_ids");
  });

  it("drops rejected foreign citations and non-whitelisted Hermes trace fields before persistence", () => {
    const thread = makeThread("Hermes leak guard");
    const foreignCitation = {
      ...graphCitation,
      world_id: "FOREIGN_WORLD_ID",
      campaign_id: "FOREIGN_CAMPAIGN_ID",
      revision_id: "FOREIGN_REVISION_ID",
      anchor_id: "FOREIGN_SOURCE_ANCHOR_ID",
    };
    const turn = turnFromResponse("Who is Lysandro?", {
      answer: "Lysandro is at the gate.",
      mode: "hermes_graph_agent",
      status: "ok",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: {},
      grounding: graphGrounding,
      citations: [graphCitation, foreignCitation],
      agent_trace: {
        trace_id: "trace-hermes-leak",
        runtime: "api",
        backend: "hermes",
        mode: "hermes_graph_agent",
        provider: "openai",
        model: "gpt-leak",
        toolset: "secret-tools",
        command_summary: "SECRET_COMMAND_SUMMARY",
        prompt_preview: "RAW_PROMPT_SECRET",
        prompt_char_count: 99,
        prompt_token_estimate: 12,
        started_at: "2026-06-22T00:00:00.000Z",
        completed_at: "2026-06-22T00:00:01.000Z",
        elapsed_ms: 12,
        status: "ok",
        usage: { available: true, input_tokens: 1, output_tokens: 1, total_tokens: 2 },
        steps: [{ name: "lookup", summary: "RAW_HERMES_MESSAGE_SECRET" }],
        context_summary: { verdict: "SECRET_CONTEXT_SUMMARY", manifest_path: "foreign/private/source.md" },
        artifact_refs: [{ kind: "file", label: "rel", path: "foreign/private/source.md" }],
        tool_events: [{
          tool_name: "graph_read",
          state: "completion",
          duration_ms: 8,
          world_id: "eldyrwild",
          campaign_id: "longmont-c2",
          focus: { kind: "session", session_id: "session-21" },
          admissibility: "gm",
          revision_pin: "rev-1",
          bounded_ids: { secret: "RAW_TOOL_ARGUMENT_SECRET" },
          retrieval_schema: "dmb_world_graph_projection_v1",
          outcome: "enough",
          matched_node_ids: ["node-1"],
          relationship_ids: [],
          source_anchor_ids: [graphCitation.anchor_id],
          diagnostic_codes: [],
        }],
        warnings: [],
      } as AgentInteractionTrace,
    }, "hermes");

    expect(turn.citations).toHaveLength(1);
    expect(turn.citations?.[0]).toMatchObject({ anchor_id: graphCitation.anchor_id });
    expect(turn.trace?.command_summary).toBeUndefined();
    expect(turn.trace?.steps).toEqual([]);
    expect(turn.trace?.artifact_refs).toEqual([]);
    expect(turn.trace?.context_summary).toEqual({});
    expect(turn.trace?.provider).toBeUndefined();
    expect(turn.trace?.model).toBeUndefined();
    expect(turn.trace?.toolset).toBeUndefined();

    thread.turns = [turn];
    persistAgentThread(thread);
    const stored = localStorage.getItem(threadStorageKey("longmont-c2", thread.threadId)) ?? "";
    for (const marker of NO_LEAK_MARKERS) {
      expect(stored).not.toContain(marker);
    }

    // Poison storage with a previously rejected foreign citation and rehydrate.
    const parsed = JSON.parse(stored);
    parsed.turns[0].citations.push(foreignCitation);
    parsed.turns[0].trace.command_summary = "SECRET_COMMAND_SUMMARY";
    parsed.turns[0].trace.artifact_refs = [{ kind: "file", path: "foreign/private/source.md" }];
    localStorage.setItem(threadStorageKey("longmont-c2", thread.threadId), JSON.stringify(parsed));

    const reloaded = loadAgentThreadById("longmont-c2", thread.threadId);
    const reloadedJson = JSON.stringify(reloaded);
    for (const marker of NO_LEAK_MARKERS) {
      expect(reloadedJson).not.toContain(marker);
    }
    expect(reloaded?.turns[0].citations).toHaveLength(1);
    expect(reloaded?.turns[0].trace?.artifact_refs).toEqual([]);
    expect(reloaded?.turns[0].trace?.command_summary).toBeUndefined();
  });

  it("does not build path evidence snapshots for graph citations", () => {
    const snapshots = buildEvidenceSnapshots([
      graphCitation,
      {
        evidence_id: "e1",
        path: "corpus/test.md",
        line_start: 2,
        line_end: 3,
        source_role: "play_recap",
        authority: "canon_play",
      },
    ]);

    expect(snapshots).toHaveLength(1);
    expect(snapshots[0].path).toBe("corpus/test.md");
  });

  it("caps sanitized graph tool events and string fields", () => {
    const longId = `id-${"x".repeat(600)}`;
    const trace = safeTraceForPersistence({
      trace_id: "trace-caps",
      runtime: "api",
      backend: "hermes",
      mode: "hermes_graph_agent",
      started_at: "2026-06-22T00:00:00.000Z",
      completed_at: "2026-06-22T00:00:01.000Z",
      elapsed_ms: 1,
      status: "ok",
      usage: { available: true, input_tokens: null, output_tokens: null, total_tokens: null },
      steps: [],
      context_summary: {},
      artifact_refs: [],
      warnings: Array.from({ length: 20 }, (_, index) => `warning-${index}`),
      tool_events: Array.from({ length: 30 }, (_, index) => ({
        tool_name: `tool-${index}`,
        state: "completion",
        duration_ms: index,
        world_id: "eldyrwild",
        campaign_id: "longmont-c2",
        focus: null,
        admissibility: "gm",
        revision_pin: "rev-1",
        bounded_ids: { leak: "RAW_TOOL_ARGUMENT_SECRET" },
        retrieval_schema: null,
        outcome: "enough",
        matched_node_ids: Array.from({ length: 40 }, (_, idIndex) => `node-${idIndex}`),
        relationship_ids: [],
        source_anchor_ids: [longId],
        diagnostic_codes: Array.from({ length: 40 }, (_, codeIndex) => `diag-${codeIndex}`),
      })),
    } as AgentInteractionTrace);

    expect(trace?.warnings).toHaveLength(16);
    expect(trace?.tool_events).toHaveLength(24);
    expect(trace?.tool_events?.[0].matched_node_ids).toHaveLength(32);
    expect(trace?.tool_events?.[0].diagnostic_codes).toHaveLength(32);
    expect(trace?.tool_events?.[0].source_anchor_ids[0]).toHaveLength(512);
    expect(JSON.stringify(trace)).not.toContain("bounded_ids");
    expect(JSON.stringify(trace)).not.toContain("RAW_TOOL_ARGUMENT_SECRET");
  });

  it("tolerates legacy persisted turns without grounding, kind, or tool events", () => {
    const legacyThread = makeThread("Legacy turn");
    legacyThread.turns = [{
      turnId: "legacy-turn",
      askedAt: "2026-06-22T00:00:00.000Z",
      completedAt: "2026-06-22T00:00:01.000Z",
      question: "Legacy?",
      answer: "Legacy answer",
      backend: "live",
      status: "ok",
      citations: [{
        evidence_id: "e1",
        path: "corpus/test.md",
        line_start: 1,
        line_end: 1,
        source_role: "play_recap",
        authority: "canon_play",
      }],
      trace: {
        trace_id: "legacy-trace",
        runtime: "live",
        backend: "live",
        mode: "live",
        started_at: "2026-06-22T00:00:00.000Z",
        completed_at: "2026-06-22T00:00:01.000Z",
        elapsed_ms: 1,
        status: "ok",
        usage: { available: false, input_tokens: null, output_tokens: null, total_tokens: null },
        steps: [],
        context_summary: {},
        artifact_refs: [],
        warnings: [],
      },
    }];
    localStorage.setItem(threadStorageKey("longmont-c2", legacyThread.threadId), JSON.stringify(legacyThread));

    const reloaded = loadAgentThreadById("longmont-c2", legacyThread.threadId);
    expect(reloaded?.turns[0].grounding).toBeUndefined();
    expect(reloaded?.turns[0].citations?.[0].path).toBe("corpus/test.md");
    expect(reloaded?.turns[0].trace?.tool_events).toBeUndefined();
  });

  it("persists world graph summary only and strips full graph projection detail", () => {
    const worldGraphContext: AgentWorldGraphQueryContext = {
      schema: "dmb_agent_world_graph_query_context_v1",
      status: "ready",
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      revision_id: "rev-1",
      head_revision_id: "rev-1",
      is_head: true,
      focus: { kind: "session", session_id: "session-21" },
      admissibility: "gm",
      query_text: "Who is Lysandro?",
      matched_node_ids: ["node-lysandro"],
      nodes: [{
        node_id: "node-lysandro",
        label: "Lysandro",
        kind: "npc",
        role: "antagonist",
        summary: "Gate antagonist",
        anchored_to_focus_session: true,
      }],
      relationships: [{
        edge_id: "edge-1",
        source_node_id: "node-lysandro",
        target_node_id: "node-gate",
        predicate: "located_at",
        label: "at the gate",
        direction: "outgoing",
        session_ids: ["session-21"],
      }],
      attributes: [{
        assertion_id: "assert-1",
        subject_node_id: "node-lysandro",
        predicate: "role",
        label: "Role",
        text_value: "antagonist",
      }],
      projection_truncated: false,
      diagnostics: [{ code: "ok", message: "ready", severity: "info" }],
      warning_codes: [],
      trust_boundary: {
        graph_role: "structured_campaign_memory_and_navigation",
        citation_authority: "corpus_source_evidence",
        graph_citations_permitted: false,
      },
    };

    const thread = makeThread("Graph prep");
    const turn = turnFromResponse("Who is Lysandro?", {
      answer: "Lysandro is at the gate.",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: {},
      world_graph_context: worldGraphContext,
    }, "live");
    thread.turns = [turn];
    persistAgentThread(thread);

    const stored = localStorage.getItem(threadStorageKey("longmont-c2", thread.threadId)) ?? "";
    expect(stored).toContain("dmb_agent_world_graph_context_summary_v1");
    expect(stored).toContain("node-lysandro");
    expect(stored).toContain("graph_context_detail_not_persisted");
    expect(stored).not.toContain("dmb_agent_world_graph_query_context_v1");
    expect(stored).not.toContain("prompt_preview");
    expect(stored).not.toContain("relationships");
    expect(stored).not.toContain("attributes");
    expect(stored).not.toContain("Gate antagonist");
    expect(loadAgentThreadById("longmont-c2", thread.threadId)?.turns[0].worldGraphContext).toBeUndefined();
    expect(loadAgentThreadById("longmont-c2", thread.threadId)?.turns[0].worldGraphContextSummary?.matchedNodeIds).toEqual(["node-lysandro"]);
  });
});
