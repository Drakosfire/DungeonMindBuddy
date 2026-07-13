import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AgentInteractionThread, AgentInteractionTrace, AgentWorldGraphQueryContext } from "../../api/types";
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
