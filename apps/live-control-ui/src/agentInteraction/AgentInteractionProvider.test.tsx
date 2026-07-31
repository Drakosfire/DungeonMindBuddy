import { act, render, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, useMemo, useRef, type ReactNode } from "react";

import type { LiveQueryResponse } from "../api/types";
import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { referenceFromGraphNode } from "../graphReference";
import type { GraphReferenceResolution } from "../graphReference/types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  PlanReferenceProjectionBinding,
} from "../planSurface/projection/projectionBindings";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "../planSurface/projection/projectionBindings";
import type { SurfaceConfig } from "../planSurface/types";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { activeThreadStorageKey, createAgentInteractionThread, persistAgentThread, threadStorageKey } from "./agentInteractionStorage";
import { FIXTURE_DOC_ID } from "../planSurface/config/planSessionDescriptor";
import type { ProjectionSurfacePublication } from "./projectionSurfacePublication";
import { useAgentInteraction } from "./useAgentInteraction";

function wrapper({ children }: { children: ReactNode }) {
  return <AgentInteractionProvider>{children}</AgentInteractionProvider>;
}

const response: LiveQueryResponse = {
  answer: "Provider-owned answer",
  status: "ok",
  classification: {} as never,
  events_written: [],
  jobs_queued: [],
  next_suggestions: [],
  diagnostics: {},
  provenance: {},
  citations: [{ evidence_id: "e1", path: "corpus/session.md", line_start: 3, line_end: 5, source_role: "play_recap", authority: "canon_play" }],
  ["context" + "_packet"]: null,
  retrieval_freshness: {
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
};

describe("AgentInteractionProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("publishes plan surface context and appends turns into provider-owned state", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID });
      result.current.publishSurfaceContext({
        surfaceId: "plan",
        label: "Plan · Session 23",
        campaignId: "longmont-c2",
        sessionNumber: 23,
        ambientSummary: "Small bounded summary",
        sourceEnvelope: null,
        updatedAt: "2026-06-28T00:00:00.000Z",
      });
    });

    act(() => {
      result.current.appendResponseTurn("What changed?", response);
    });

    expect(result.current.activeSurfaceContext?.surfaceId).toBe("plan");
    expect(result.current.activeThread?.turns[0]).toMatchObject({ question: "What changed?", answer: "Provider-owned answer" });
    expect(result.current.activeThread?.turns[0].retrievalFreshness?.decision).toBe("fresh_retrieval");
  });

  it("rehydrates saved thread state and keeps thread turns isolated", () => {
    const first = { ...createAgentInteractionThread("longmont-c2", 23, "plan", "live", "First", FIXTURE_DOC_ID), threadId: "first" };
    const second = { ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Second", FIXTURE_DOC_ID), threadId: "second" };
    first.turns = [{ turnId: "t1", askedAt: "2026-06-28T00:00:00.000Z", question: "A?", answer: "A", backend: "live", status: "ok" }];
    second.turns = [{ turnId: "t2", askedAt: "2026-06-28T00:00:00.000Z", question: "B?", answer: "B", backend: "hermes", status: "ok", corpusFreshness: { status: "changed", checked_at: "2026-06-28T00:00:00.000Z", diagnostics: [], warnings: [] } }];
    persistAgentThread(first);
    persistAgentThread(second);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), "second");

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    expect(result.current.activeThread?.threadId).toBe("second");
    expect(result.current.turns[0].question).toBe("B?");
    expect(result.current.turns[0].corpusFreshness?.status).toBe("changed");

    act(() => {
      result.current.switchThread("first");
    });

    expect(result.current.activeThread?.threadId).toBe("first");
    expect(result.current.turns[0].question).toBe("A?");
    expect(result.current.turns[0].question).not.toBe("B?");
  });

  it("persists server-approved Hermes pointer for graph turns", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    act(() => {
      result.current.appendResponseTurn("Graph question?", {
        ...response,
        mode: "hermes_graph_agent",
        hermes_session: {
          sessionId: "hptr-server-approved",
          runtime: "process_isolated",
          title: null,
          createdAt: "2026-06-28T00:00:00.000Z",
          updatedAt: "2026-06-28T00:00:01.000Z",
        },
        agent_trace: {
          trace_id: "trace-hermes",
          runtime: "process_isolated",
          backend: "hermes",
          mode: "hermes_graph_agent",
          started_at: "2026-06-28T00:00:00.000Z",
          completed_at: "2026-06-28T00:00:01.000Z",
          elapsed_ms: 10,
          status: "ok",
          usage: { available: false, input_tokens: null, output_tokens: null, total_tokens: null },
          steps: [],
          context_summary: {},
          artifact_refs: [],
          conversation_context: {
            history_present: false,
            message_count: 0,
            pair_count: 0,
            payload_shape: "role_content_only",
            graph_metadata_in_history: false,
            hermes_session_pointer_in_request: false,
            hermes_session_pointer_status: "absent",
            worker_pid_changed: false,
            fresh_graph_revision_used: true,
          },
          warnings: [],
        } as never,
      });
    });

    expect(result.current.activeThread?.hermesSession?.sessionId).toBe("hptr-server-approved");
    expect(result.current.activeThread?.turns[0].trace?.hermes_session_id).toBeUndefined();
  });

  it("rehydrates persisted Hermes pointer with the thread", () => {
    const seeded = {
      ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Seeded", FIXTURE_DOC_ID),
      threadId: "seeded-thread",
      hermesSession: {
        sessionId: "hptr-reload",
        runtime: "process_isolated",
        title: null,
        createdAt: "2026-06-28T00:00:00.000Z",
        updatedAt: "2026-06-28T00:00:01.000Z",
      },
    };
    persistAgentThread(seeded);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), seeded.threadId);

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    expect(result.current.activeThread?.hermesSession?.sessionId).toBe("hptr-reload");
  });

  it("keeps subsequent Hermes turns forwarding the persisted pointer", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    act(() => {
      result.current.appendResponseTurn("First graph turn?", {
        ...response,
        mode: "hermes_graph_agent",
        hermes_session: {
          sessionId: "hptr-follow-up",
          runtime: "process_isolated",
          title: null,
        },
      });
    });
    act(() => {
      result.current.appendResponseTurn("Second graph turn?", {
        ...response,
        answer: "Second answer",
        mode: "hermes_graph_agent",
        hermes_session: {
          sessionId: "hptr-follow-up",
          runtime: "process_isolated",
          title: null,
        },
      });
    });

    expect(result.current.activeThread?.hermesSession?.sessionId).toBe("hptr-follow-up");
    expect(result.current.activeThread?.turns).toHaveLength(2);
    expect(result.current.activeThread?.turns[0].answer).toBe("Second answer");
  });

  it("preserves legacy Live Hermes session forwarding behavior", () => {
    const liveSession = {
      sessionId: "live-hermes-session",
      runtime: "cli",
      title: "Live session",
    };
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    act(() => {
      result.current.appendResponseTurn("Live turn?", {
        ...response,
        mode: "live",
        hermes_session: liveSession,
      });
    });

    expect(result.current.activeThread?.hermesSession).toEqual(liveSession);
  });

  it("persists bounded metadata without prompt previews or raw context packets", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));
    act(() => result.current.appendResponseTurn("Bounded?", { ...response, ["context" + "_packet"]: { admitted_evidence: [{ evidence_id: "e1", path: "corpus/session.md", source_role: "play_recap", authority: "canon_play", text_excerpt: "unbounded excerpt" }], rejected_evidence: [] }, agent_trace: { trace_id: "trace", prompt_preview: "raw" + " prompt", artifact_refs: [{ kind: "file", label: "tmp", path: "/tmp/raw.json" }] } as never }));

    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    const stored = localStorage.getItem(threadStorageKey("longmont-c2", String(activeThreadId))) ?? "";
    expect(stored).toContain("Bounded?");
    expect(stored).toContain("corpus/session.md");
    expect(stored).not.toContain("raw" + " prompt");
    expect(stored).not.toContain("unbounded excerpt");
    expect(stored).not.toContain("context" + "_packet");
    expect(stored).not.toContain("/tmp/raw.json");
  });

  it("rehydrates build scope with null sessionNumber", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.rehydrateScope({
        campaignId: "eldyrwild",
        sessionNumber: null,
        surfaceId: "build",
        documentId: FIXTURE_DOC_ID,
      });
    });

    expect(result.current.scope?.sessionNumber).toBeNull();
  });

  it("publishes projection surface with token-safe cleanup", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const publication = {
      identity: { surfaceId: "build", instanceKey: "build\u001f__new_source__" },
      config: {
        id: "build" as const,
        label: "Build",
        context: null,
        tools: [],
        canvas: { documentId: null },
        theme: {},
      },
    };

    let cleanup: (() => void) | undefined;
    act(() => {
      cleanup = result.current.publishProjectionSurface(publication);
    });
    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);

    act(() => {
      cleanup?.();
    });
    expect(result.current.projectionSurface).toBeNull();
  });

  it("rejects stale openTool after surface replacement before rerender", () => {
    const planPublication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001ftest" },
      config: {
        id: "plan" as const,
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const buildPublication = {
      identity: { surfaceId: "build", instanceKey: "build\u001f__new_source__" },
      config: {
        id: "build" as const,
        label: "Build",
        context: null,
        tools: [],
        canvas: { documentId: null },
        theme: {},
      },
    };

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(planPublication);
    });
    const staleOpenTool = result.current.openTool;
    act(() => {
      result.current.publishProjectionSurface(buildPublication);
      staleOpenTool("recap");
    });
    expect(result.current.active).toBeNull();
  });

  it("rejects stale close after surface replacement before rerender", () => {
    const planPublication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fclose-test" },
      config: {
        id: "plan" as const,
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const ingestPublication = {
      identity: { surfaceId: "ingest", instanceKey: "ingest\u001fclose-test" },
      config: {
        id: "ingest" as const,
        label: "Ingest",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Ingest",
        },
        tools: [{ id: "ingest-recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: null },
        theme: {},
      },
    };

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(planPublication);
      result.current.openTool("recap");
    });
    const staleClose = result.current.close;
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    act(() => {
      result.current.openTool("ingest-recap");
    });
    act(() => {
      staleClose();
    });
    expect(result.current.active?.key).toBe("ingest-recap");
  });

  it("does not persist projection opens to localStorage", () => {
    const publication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fpersist-test" },
      config: {
        id: "plan" as const,
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(publication);
    });
    act(() => {
      result.current.openTool("recap");
    });
    const keys = Object.keys(localStorage);
    expect(keys.some((key) => key.includes("projection"))).toBe(false);
    expect(result.current.active?.key).toBe("recap");
  });
});

describe("AgentInteractionProvider projection lease semantics", () => {
  const planIdentity = { surfaceId: "plan", instanceKey: "plan\u001flease-test" };
  const planContext = {
    campaignId: "longmont-c2",
    liveSession: 22,
    ingestSession: 21,
    headerLabel: "Plan",
  };

  function makePlanPublication(
    configOverrides: Partial<SurfaceConfig> = {},
    identityOverrides: Partial<ProjectionSurfacePublication["identity"]> = {},
  ): ProjectionSurfacePublication {
    return {
      identity: { ...planIdentity, ...identityOverrides },
      config: {
        id: "plan",
        label: "Plan",
        context: planContext,
        tools: [
          { id: "recap", label: "Recap", size: "wide" as const },
          { id: "statblock", label: "Statblock", size: "wide" as const },
        ],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
        ...configOverrides,
      },
    };
  }

  const ingestPublication: ProjectionSurfacePublication = {
    identity: { surfaceId: "ingest", instanceKey: "ingest\u001flease-test" },
    config: {
      id: "ingest",
      label: "Ingest",
      context: planContext,
      tools: [
        { id: "ingest-recap", label: "Recap", size: "wide" as const },
        { id: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, label: "Diagnostics", size: "wide" as const },
      ],
      canvas: { documentId: null },
      theme: {},
    },
  };

  function makeIngestPublication(
    identityOverrides: Partial<ProjectionSurfacePublication["identity"]> = {},
    configOverrides: Partial<SurfaceConfig> = {},
  ): ProjectionSurfacePublication {
    return {
      identity: {
        surfaceId: "ingest",
        instanceKey: "ingest\u001flease-test",
        ...identityOverrides,
      },
      config: {
        ...ingestPublication.config,
        ...configOverrides,
      },
    };
  }

  const buildPublication: ProjectionSurfacePublication = {
    identity: { surfaceId: "build", instanceKey: "build\u001flease-test" },
    config: {
      id: "build",
      label: "Build",
      context: null,
      tools: [],
      canvas: { documentId: null },
      theme: {},
    },
  };

  const bubblesNode: GraphProjectionNodeView = {
    node_id: "creature:bubbles",
    label: "Bubbles",
    kind: "creature",
    role: "creature",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    summary: null,
  };

  const resolution: GraphReferenceResolution = {
    kind: "resolved_graph",
    locator: "dmb-node:creature:bubbles",
    reference: referenceFromGraphNode(bubblesNode),
    graphObject: buildGraphObjectCardFromNodeView(bubblesNode),
    graphNodeId: "creature:bubbles",
    projectionState: "ready",
  };

  function openResolution(
    open: (args: { resolution: GraphReferenceResolution; projectionState?: "ready" }) => void,
  ) {
    open({ resolution, projectionState: "ready" });
  }

  function makePlanBinding(): PlanReferenceProjectionBinding {
    return {
      resolverState: "ready",
      resolveRelationship: vi.fn(async () => resolution),
      openResolvedReference: vi.fn(),
      openTool: vi.fn(),
    };
  }

  it("preserves an open tool across a same-identity config update", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.openTool("recap");
    });
    expect(result.current.active?.key).toBe("recap");

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({ label: "Plan (revised)", theme: { themeId: "mireward" } }),
      );
    });

    expect(result.current.active?.key).toBe("recap");
    expect(result.current.projectionSurface?.publication.config.label).toBe("Plan (revised)");
    expect(result.current.projectionSurface?.publication.config.theme.themeId).toBe("mireward");
  });

  it("clears the active tool when a same-identity update removes it", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.openTool("recap");
    });
    expect(result.current.active?.key).toBe("recap");

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({ tools: [{ id: "statblock", label: "Statblock", size: "wide" as const }] }),
      );
    });

    expect(result.current.active).toBeNull();
  });

  it("rebuilds active tool label and size when a same-identity update revises the matching tool", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.openTool("recap");
    });
    expect(result.current.active).toEqual({
      kind: "tool",
      key: "recap",
      size: "wide",
      title: "Recap",
    });

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({
          tools: [
            { id: "recap", label: "Session Memory", size: "fullscreen" as const },
            { id: "statblock", label: "Statblock", size: "wide" as const },
          ],
        }),
      );
    });

    expect(result.current.active).toEqual({
      kind: "tool",
      key: "recap",
      size: "fullscreen",
      title: "Session Memory",
    });
  });

  it("preserves valid Plan content across a same-identity update", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.active?.kind).toBe("content");
    expect(result.current.activeGraphReference?.locator).toBe(resolution.locator);

    act(() => {
      result.current.publishProjectionSurface(makePlanPublication({ label: "Plan (revised)" }));
    });

    expect(result.current.active?.kind).toBe("content");
    expect(result.current.activeGraphReference?.locator).toBe(resolution.locator);
    expect(result.current.graphReferenceProjectionState).toBe("ready");
  });

  it("invalidates Plan content when a same-identity update drops the render context", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.active?.kind).toBe("content");

    act(() => {
      result.current.publishProjectionSurface(makePlanPublication({ context: null, tools: [] }));
    });

    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
    expect(result.current.graphReferenceProjectionState).toBeNull();
  });

  it("keeps pre-publication callbacks as permanent no-ops after a surface publishes", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const staleOpenTool = result.current.openTool;
    const staleOpenContentFromChip = result.current.openContentFromChip;
    const staleOpenPlanReferenceResolution = result.current.openGraphReference;
    const staleExpandContent = result.current.expandContent;
    const staleClose = result.current.close;

    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      staleOpenTool("recap");
      staleOpenContentFromChip(
        { refType: "creature", refId: "creature:bubbles", label: "Bubbles" } as never,
        resolution,
      );
      openResolution(staleOpenPlanReferenceResolution);
      staleExpandContent();
      staleClose();
    });

    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();

    act(() => {
      result.current.openTool("recap");
    });
    expect(result.current.active?.key).toBe("recap");
  });

  it("blocks a stale Plan registrar invoked after Ingest publication before rerender", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    const staleRegister = result.current.registerGraphReferenceBinding;

    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
      staleRegister(makePlanBinding());
    });

    expect(result.current.graphReferenceBinding).toBeNull();
  });

  it("blocks a stale Plan registrar invoked after Ingest publication has rendered", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    const staleRegister = result.current.registerGraphReferenceBinding;

    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    act(() => {
      staleRegister(makePlanBinding());
    });

    expect(result.current.graphReferenceBinding).toBeNull();
  });

  it("blocks a stale diagnostics registrar invoked after Plan publication, before and after rerender", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    const staleRegisterPreRerender = result.current.registerToolProjectionPayload;
    const payload = {} as GraphReviewDiagnosticsProjectionPayload;

    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
      staleRegisterPreRerender(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    const staleRegisterPostRerender = staleRegisterPreRerender;
    act(() => {
      staleRegisterPostRerender(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
  });

  it("blocks a stale diagnostics registrar invoked after Build publication, before and after rerender", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    const staleRegister = result.current.registerToolProjectionPayload;
    const payload = {} as GraphReviewDiagnosticsProjectionPayload;

    act(() => {
      result.current.publishProjectionSurface(buildPublication);
      staleRegister(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    act(() => {
      staleRegister(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
  });

  it("rejects Plan-content actions under an exact current Ingest lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });

    act(() => {
      result.current.openContentFromChip(
        { refType: "creature", refId: "creature:bubbles", label: "Bubbles" } as never,
        resolution,
      );
      openResolution(result.current.openGraphReference);
      result.current.expandContent();
    });

    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
  });

  it("rejects a freshly supplied Plan registrar under an exact current Ingest lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });

    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });

    expect(result.current.graphReferenceBinding).toBeNull();
  });

  it("rejects a freshly supplied diagnostics registrar under an exact current Plan lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });

    act(() => {
      result.current.registerToolProjectionPayload(
        GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
        {} as GraphReviewDiagnosticsProjectionPayload,
      );
    });

    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
  });

  it("rejects a freshly supplied diagnostics registrar under an exact current Build lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(buildPublication);
    });

    act(() => {
      result.current.registerToolProjectionPayload(
        GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
        {} as GraphReviewDiagnosticsProjectionPayload,
      );
    });

    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
  });

  it("rejects diagnostics registration on Ingest when the diagnostics tool is not enabled", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(
        makeIngestPublication({}, {
          tools: [{ id: "ingest-recap", label: "Recap", size: "wide" as const }],
        }),
      );
    });

    act(() => {
      result.current.registerToolProjectionPayload(
        GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
        {} as GraphReviewDiagnosticsProjectionPayload,
      );
    });

    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
  });

  it("clears Plan binding when a same-identity update disables projections and rejects fresh registration", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({ context: null, tools: [] }),
      );
    });

    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);
    expect(result.current.graphReferenceBinding).toBeNull();

    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    expect(result.current.graphReferenceBinding).toBeNull();
  });

  it("clears diagnostics payload when a same-identity update keeps the tool but loses context", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const payload = { selectedDeltaNodeId: "npc-a" } as GraphReviewDiagnosticsProjectionPayload;
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    act(() => {
      result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toEqual(payload);

    act(() => {
      result.current.publishProjectionSurface(
        makeIngestPublication({}, {
          context: null,
          tools: [
            { id: "ingest-recap", label: "Recap", size: "wide" as const },
            { id: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, label: "Diagnostics", size: "wide" as const },
          ],
        }),
      );
    });

    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    act(() => {
      result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
  });

  it("fails closed when identity.surfaceId and config.id contradict", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface({
        identity: { surfaceId: "plan", instanceKey: "plan\u001fcontradiction" },
        config: {
          id: "ingest",
          label: "Mismatched",
          context: planContext,
          tools: [
            { id: "ingest-recap", label: "Recap", size: "wide" as const },
            { id: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, label: "Diagnostics", size: "wide" as const },
          ],
          canvas: { documentId: null },
          theme: {},
        },
      });
    });

    // Canonical validation disables contradictory publications.
    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);

    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
      result.current.registerToolProjectionPayload(
        GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
        {} as GraphReviewDiagnosticsProjectionPayload,
      );
      openResolution(result.current.openGraphReference);
      result.current.openTool("ingest-recap");
    });

    expect(result.current.graphReferenceBinding).toBeNull();
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
    expect(result.current.active).toBeNull();
  });

  it("clears an open tool when a same-identity update publishes a contradictory config with the same tool id", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.openTool("recap");
    });
    expect(result.current.active?.key).toBe("recap");

    act(() => {
      result.current.publishProjectionSurface({
        identity: planIdentity,
        config: {
          id: "ingest",
          label: "Mismatched",
          context: planContext,
          tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
          canvas: { documentId: FIXTURE_DOC_ID },
          theme: {},
        },
      });
    });

    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);
    expect(result.current.active).toBeNull();
  });

  it("lets binder effects republish a Plan binding under a new Plan instance lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({}, { instanceKey: "plan\u001finstance-a" }),
      );
    });
    let cleanup: (() => void) | undefined;
    act(() => {
      cleanup = result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({}, { instanceKey: "plan\u001finstance-b" }),
      );
    });
    expect(result.current.graphReferenceBinding).toBeNull();

    // The binder re-runs because the registrar identity changed with the lease.
    act(() => {
      cleanup?.();
      cleanup = result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();
  });

  it("lets binder effects republish diagnostics under a new Ingest instance lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const payloadA = { selectedDeltaNodeId: "a" } as GraphReviewDiagnosticsProjectionPayload;
    const payloadB = { selectedDeltaNodeId: "b" } as GraphReviewDiagnosticsProjectionPayload;

    act(() => {
      result.current.publishProjectionSurface(
        makeIngestPublication({ instanceKey: "ingest\u001finstance-a" }),
      );
    });
    let cleanup: (() => void) | undefined;
    act(() => {
      cleanup = result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payloadA);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toEqual(payloadA);

    act(() => {
      result.current.publishProjectionSurface(
        makeIngestPublication({ instanceKey: "ingest\u001finstance-b" }),
      );
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    act(() => {
      cleanup?.();
      cleanup = result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payloadB);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toEqual(payloadB);
  });

  function PublisherPatternHarness({ config }: { config: SurfaceConfig }) {
    const { publishProjectionSurface, updateProjectionSurfaceConfig } = useAgentInteraction();
    const publication = useMemo<ProjectionSurfacePublication>(
      () => ({ identity: planIdentity, config }),
      [config],
    );
    const publicationInstanceKey = publication.identity.instanceKey;
    const publicationRef = useRef(publication);
    publicationRef.current = publication;
    useEffect(() => {
      return publishProjectionSurface(publicationRef.current);
    }, [publicationInstanceKey, publishProjectionSurface]);
    useEffect(() => {
      updateProjectionSurfaceConfig(publication);
    }, [publication, updateProjectionSurfaceConfig]);
    return null;
  }

  function LeaseProbe() {
    const { active, projectionSurface } = useAgentInteraction();
    return (
      <p data-testid="lease-probe">
        {active ? `${active.kind}:${active.key}` : "none"}|{projectionSurface?.publication.config.label ?? "none"}
      </p>
    );
  }

  it("publisher pattern: a config-only republish preserves the open tool without an intervening unbind", () => {
    const baseConfig: SurfaceConfig = makePlanPublication().config;
    const revisedConfig: SurfaceConfig = { ...baseConfig, label: "Plan (revised)" };
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    const { rerender, getByTestId } = render(
      <AgentInteractionProvider>
        <PublisherPatternHarness config={baseConfig} />
        <LeaseProbe />
        <CaptureApi />
      </AgentInteractionProvider>,
    );
    act(() => {
      hostApi!.openTool("recap");
    });
    expect(getByTestId("lease-probe").textContent).toBe("tool:recap|Plan");

    rerender(
      <AgentInteractionProvider>
        <PublisherPatternHarness config={revisedConfig} />
        <LeaseProbe />
        <CaptureApi />
      </AgentInteractionProvider>,
    );

    expect(getByTestId("lease-probe").textContent).toBe("tool:recap|Plan (revised)");
  });

  it("publisher pattern: an identity change still clears the open projection", () => {
    const baseConfig: SurfaceConfig = makePlanPublication().config;
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    function IdentitySwitchHarness({ config, identity }: { config: SurfaceConfig; identity: ProjectionSurfacePublication["identity"] }) {
      const { publishProjectionSurface } = useAgentInteraction();
      useEffect(() => {
        return publishProjectionSurface({ identity, config });
      }, [identity, config, publishProjectionSurface]);
      return null;
    }

    const { rerender, getByTestId } = render(
      <AgentInteractionProvider>
        <IdentitySwitchHarness config={baseConfig} identity={planIdentity} />
        <LeaseProbe />
        <CaptureApi />
      </AgentInteractionProvider>,
    );
    act(() => {
      hostApi!.openTool("recap");
    });
    expect(getByTestId("lease-probe").textContent).toBe("tool:recap|Plan");

    rerender(
      <AgentInteractionProvider>
        <IdentitySwitchHarness
          config={baseConfig}
          identity={{ surfaceId: "plan", instanceKey: "plan\u001fother-document" }}
        />
        <LeaseProbe />
        <CaptureApi />
      </AgentInteractionProvider>,
    );

    expect(getByTestId("lease-probe").textContent).toBe("none|Plan");
  });
});
