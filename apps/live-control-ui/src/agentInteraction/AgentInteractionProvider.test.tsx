import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { createAgentInteractionThread, threadStorageKey } from "./agentInteractionStorage";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { useAgentInteraction } from "./useAgentInteraction";

function wrapper({ children }: { children: ReactNode }) {
  return <AgentInteractionProvider>{children}</AgentInteractionProvider>;
}

describe("AgentInteractionProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("publishes bounded surface context above /plan", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.publishSurfaceContext({
        surfaceId: "plan",
        label: "Plan",
        campaignId: "longmont-c2",
        sessionNumber: 23,
        ambientSummary: "small display summary",
        sourceEnvelope: {
          schema: "dmb_agent_interaction_source_envelope_v1",
          unitIds: ["unit-1"],
          locators: [{ kind: "source_unit", value: "unit-1" }],
          evidenceRole: "supporting_context",
        },
      });
    });

    expect(result.current.activeSurfaceContext).toMatchObject({
      surfaceId: "plan",
      label: "Plan",
      campaignId: "longmont-c2",
      sessionNumber: 23,
      ambientSummary: "small display summary",
    });
    expect(result.current.activeSurfaceContext?.sourceEnvelope?.unitIds).toEqual(["unit-1"]);
  });

  it("persists and rehydrates provider-owned active thread continuity", () => {
    const thread = createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Gate prep");
    thread.turns = [{
      turnId: "turn-1",
      askedAt: "2026-06-27T00:00:00.000Z",
      completedAt: "2026-06-27T00:00:01.000Z",
      question: "What guards the north gate?",
      answer: "A source-grounded answer pointer.",
      backend: "hermes",
      status: "ok",
      citations: [{ evidence_id: "e1", path: "corpus/session.md", source_role: "play_recap", authority: "canon_play" }],
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
      corpusFreshness: { status: "unknown", checked_at: "2026-06-27T00:00:02.000Z", diagnostics: [], warnings: [] },
    }];

    const first = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => first.result.current.persistThread(thread));
    first.unmount();

    const second = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      second.result.current.hydrateSurface("longmont-c2", "plan");
    });

    expect(second.result.current.activeThread?.threadId).toBe(thread.threadId);
    expect(second.result.current.activeThread?.turns[0].question).toBe("What guards the north gate?");
    expect(second.result.current.activeThread?.turns[0].retrievalFreshness?.decision).toBe("fresh_retrieval");
    expect(second.result.current.activeThread?.turns[0].corpusFreshness?.status).toBe("unknown");
  });

  it("resets selected source on thread switch", () => {
    const one = createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "One");
    const two = createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Two");
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.persistThread(one);
      result.current.persistThread(two);
      result.current.setSelectedSource({ citationKey: "corpus/a.md::e1", status: "ready", error: null, response: null });
      result.current.switchThread("longmont-c2", "plan", one.threadId);
    });

    expect(result.current.activeThread?.threadId).toBe(one.threadId);
    expect(result.current.selectedSource.status).toBe("idle");
    expect(result.current.selectedSource.citationKey).toBeNull();
  });

  it("keeps persisted thread payload bounded without prompt previews or source excerpts", () => {
    const thread = createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Bounded");
    thread.turns = [{
      turnId: "turn-1",
      askedAt: "2026-06-27T00:00:00.000Z",
      question: "Question?",
      answer: "Answer text is allowed.",
      backend: "hermes",
      status: "ok",
      citations: [{ evidence_id: "e1", path: "corpus/session.md", source_role: "play_recap", authority: "canon_play" }],
      trace: { trace_id: "trace-1", prompt_preview: "prompt preview should not persist", artifact_refs: [{ kind: "file", label: "secret", path: "/tmp/raw.json" }] } as never,
      warnings: [],
    }];

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.persistThread(thread));

    const stored = localStorage.getItem(threadStorageKey("longmont-c2", thread.threadId)) ?? "";
    expect(stored).toContain("Answer text is allowed.");
    expect(stored).not.toContain("prompt preview should not persist");
    expect(stored).not.toContain("text_excerpt");
    expect(stored).not.toContain("/tmp/raw.json");
  });
});
