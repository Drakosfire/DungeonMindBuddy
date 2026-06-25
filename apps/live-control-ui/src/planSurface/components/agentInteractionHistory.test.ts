import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AgentInteractionThread, AgentInteractionTrace } from "../../api/types";
import {
  activeThreadStorageKey,
  createAgentInteractionThread,
  deleteAgentThread,
  loadAgentThreadById,
  loadAgentThreadIndex,
  persistAgentThread,
  persistAgentThreadIndex,
  renameAgentThread,
  safeTraceForPersistence,
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
});
