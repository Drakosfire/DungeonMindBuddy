import { act, render, renderHook, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

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
import { validateProjectionSurfacePublication } from "./projectionSurfacePublication";
import {
  adaptProjectionSurfaceToNeutralBase,
  buildAppChromeCompatibilityFragment,
  ROUTE_COMPATIBILITY_PUBLICATIONS,
} from "./surfaceInteractionCompat";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../surfaceInteraction/projection/projectionCatalog";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { BUILD_REFERENCE_SEARCH_PROJECTION_ID } from "../buildSurface/reference/buildReferenceIds";
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

  it("openTool returns false when the tool is missing after a same-identity publish", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      expect(result.current.openTool("recap")).toBe(true);
    });
    expect(result.current.active?.key).toBe("recap");

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({ tools: [{ id: "statblock", label: "Statblock", size: "wide" as const }] }),
      );
    });

    let opened = true;
    act(() => {
      opened = result.current.openTool("recap");
    });
    expect(opened).toBe(false);
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
      result.current.registerGraphReferenceBinding(makePlanBinding());
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
      result.current.registerGraphReferenceBinding(makePlanBinding());
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
    const staleOpenGraphReference = result.current.openGraphReference;
    const staleExpandContent = result.current.expandContent;
    const staleClose = result.current.close;

    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      staleOpenTool("recap");
      staleOpenGraphReference({
        reference: { refType: "creature", refId: "creature:bubbles", label: "Bubbles" } as never,
        resolution,
        glanceOnly: true,
      });
      openResolution(staleOpenGraphReference);
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
      result.current.openGraphReference({
        reference: { refType: "creature", refId: "creature:bubbles", label: "Bubbles" } as never,
        resolution,
        glanceOnly: true,
      });
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

  it("clears open graph-reference content when a same-identity update disables projections", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.active?.kind).toBe("content");

    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({ context: null, tools: [] }),
      );
    });

    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);
    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
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

  it("clears graph-reference binding and active projection when invalid chrome fragment invalidates effective publication", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();
    expect(result.current.active?.kind).toBe("content");

    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "recap", label: "Duplicate recap", onClick: vi.fn() }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    expect(result.current.surfaceInteractionPublication).toBeNull();
    expect(result.current.graphReferenceBinding).toBeNull();
    expect(result.current.active).toBeNull();

    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    expect(result.current.graphReferenceBinding).toBeNull();

    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    expect(result.current.surfaceInteractionPublication).not.toBeNull();
    expect(result.current.graphReferenceBinding).toBeNull();

    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();
  });

  it("clears diagnostics payload when invalid chrome fragment invalidates effective publication and recovers after valid composition", () => {
    const payload = { selectedDeltaNodeId: "npc-a" } as GraphReviewDiagnosticsProjectionPayload;
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    act(() => {
      result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toEqual(payload);

    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "ingest-recap", label: "Duplicate recap", onClick: vi.fn() }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    expect(result.current.surfaceInteractionPublication).toBeNull();
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    act(() => {
      result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    expect(result.current.surfaceInteractionPublication).not.toBeNull();
    expect(result.current.graphReviewDiagnosticsPayload).toBeNull();

    act(() => {
      result.current.registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
    });
    expect(result.current.graphReviewDiagnosticsPayload).toEqual(payload);
  });

  function makeBuildGraphReferencePublication(): SurfaceInteractionPublication {
    return {
      surfaceId: "build",
      label: "Build",
      identity: buildSurfaceInteractionIdentity({
        surfaceId: "build",
        instanceParts: ["build", "doc-capability-test"],
      }),
      canvas: null,
      agentContext: null,
      tools: [
        {
          id: "build-find-existing-object",
          label: "Find existing object",
          placement: {
            groupId: "build-world-reference",
            groupLabel: "World references",
            groupOrder: 10,
            itemOrder: 0,
          },
          availability: { status: "enabled" },
          activation: {
            kind: "projection",
            projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
          },
        },
      ],
      editCommands: [],
      projections: [
        {
          id: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
          kind: "tool",
          preferredSize: "wide",
          bindingIds: [],
        },
        {
          id: GRAPH_REFERENCE_PROJECTION_ID,
          kind: "content",
          preferredSize: "wide",
          bindingIds: [],
        },
      ],
      projectionBindings: [],
    };
  }

  function makePublicationWithoutGraphReferenceCapability(): SurfaceInteractionPublication {
    return {
      surfaceId: "build",
      label: "Build",
      identity: buildSurfaceInteractionIdentity({
        surfaceId: "build",
        instanceParts: ["build", "no-graph-ref"],
      }),
      canvas: null,
      agentContext: null,
      tools: [],
      editCommands: [],
      projections: [],
      projectionBindings: [],
    };
  }

  it("regression: Plan still registers binding and opens graph reference when binding is present", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();
    expect(result.current.active?.kind).toBe("content");
    expect(result.current.activeGraphReference?.locator).toBe(resolution.locator);
  });

  it("allows graph-reference register and open on Build when publication declares capability and binding is present", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishSurfaceInteractionPublication(makeBuildGraphReferencePublication());
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.graphReferenceBinding).not.toBeNull();
    expect(result.current.active?.kind).toBe("content");
    expect(result.current.activeGraphReference?.locator).toBe(resolution.locator);
  });

  it("rejects graph-reference register and open when publication lacks the content descriptor", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishSurfaceInteractionPublication(makePublicationWithoutGraphReferenceCapability());
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.graphReferenceBinding).toBeNull();
    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
  });

  it("rejects graph-reference register and open on Ingest without capability declaration", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    act(() => {
      result.current.registerGraphReferenceBinding(makePlanBinding());
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.graphReferenceBinding).toBeNull();
    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
  });

  it("rejects openGraphReference when declaration is present but binding is not registered", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      openResolution(result.current.openGraphReference);
    });
    expect(result.current.active).toBeNull();
    expect(result.current.activeGraphReference).toBeNull();
  });
});

describe("AgentInteractionProvider neutral surface interaction lease", () => {
  it("exposes lease-guarded neutral publication for legacy projection binds", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface({
        identity: { surfaceId: "plan", instanceKey: "plan\u001fneutral-test" },
        config: {
          id: "plan",
          label: "Plan",
          context: {
            campaignId: "longmont-c2",
            liveSession: 22,
            ingestSession: 21,
            headerLabel: "Plan",
          },
          tools: [{ id: "recap", label: "Recap", size: "wide" }],
          canvas: { documentId: FIXTURE_DOC_ID },
          theme: {},
        },
      });
    });
    expect(result.current.surfaceInteractionPublication?.surfaceId).toBe("plan");
    expect(result.current.surfaceInteractionPublication?.tools[0]?.id).toBe("recap");
  });

  it("preserves singular token and returns no-op cleanup for same-identity publishProjectionSurface", () => {
    const publication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fsame-id" },
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
      identity: { surfaceId: "build", instanceKey: "build\u001fsame-id-rotate" },
      config: {
        id: "build" as const,
        label: "Build",
        context: null,
        tools: [],
        canvas: { documentId: null },
        theme: {},
      },
    };
    const onClick = vi.fn();
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.publishProjectionSurface(publication);
    });
    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "page-tool", label: "Page tool", onClick }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    const beforePublication = result.current.surfaceInteractionPublication;
    const firstInvoke = beforePublication?.tools.find((tool) => tool.id === "page-tool")?.activation;
    expect(firstInvoke?.kind).toBe("command");
    if (firstInvoke?.kind !== "command") throw new Error("expected command activation");

    let cleanupSameIdentity: (() => void) | undefined;
    act(() => {
      cleanupSameIdentity = result.current.publishProjectionSurface({
        ...publication,
        config: { ...publication.config, label: "Plan revised" },
      });
    });
    expect(result.current.surfaceInteractionPublication?.label).toBe("Plan revised");
    expect(result.current.surfaceInteractionPublication?.identity).toEqual(beforePublication?.identity);

    act(() => {
      void firstInvoke.invoke();
    });
    expect(onClick).toHaveBeenCalledTimes(1);

    act(() => {
      cleanupSameIdentity?.();
    });
    expect(result.current.surfaceInteractionPublication?.label).toBe("Plan revised");

    act(() => {
      result.current.publishProjectionSurface(buildPublication);
    });
    act(() => {
      void firstInvoke.invoke();
    });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("publishSurfaceInteractionPublication always creates a fresh lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const publication = ROUTE_COMPATIBILITY_PUBLICATIONS.index;
    const firstSpy = vi.fn();
    const secondSpy = vi.fn();
    let firstCleanup: (() => void) | undefined;

    act(() => {
      firstCleanup = result.current.publishSurfaceInteractionPublication(publication);
    });
    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "first-action", label: "First", onClick: firstSpy }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    const firstLabel = result.current.surfaceInteractionPublication?.label;
    const firstInvoke = result.current.surfaceInteractionPublication?.tools.find((tool) => tool.id === "first-action")
      ?.activation;
    expect(firstInvoke?.kind).toBe("command");
    if (firstInvoke?.kind !== "command") throw new Error("expected command activation");

    act(() => {
      result.current.publishSurfaceInteractionPublication(publication);
    });
    expect(result.current.surfaceInteractionPublication?.label).toBe(firstLabel);

    act(() => {
      void firstInvoke.invoke();
    });
    expect(firstSpy).not.toHaveBeenCalled();

    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "second-action", label: "Second", onClick: secondSpy }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    const secondInvoke = result.current.surfaceInteractionPublication?.tools.find((tool) => tool.id === "second-action")
      ?.activation;
    expect(secondInvoke?.kind).toBe("command");
    if (secondInvoke?.kind !== "command") throw new Error("expected command activation");
    act(() => {
      void secondInvoke.invoke();
    });
    expect(secondSpy).toHaveBeenCalledTimes(1);

    act(() => {
      firstCleanup?.();
    });
    expect(result.current.surfaceInteractionPublication?.label).toBe(firstLabel);
  });

  it("binds AppChrome compatibility fragments without overwriting Plan legacy lease", () => {
    const planPublication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fchrome-fragment" },
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
      result.current.publishProjectionSurface(planPublication);
    });
    const planIdentity = result.current.surfaceInteractionPublication?.identity;
    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "page-tool", label: "Page tool", onClick: vi.fn() }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    expect(result.current.surfaceInteractionPublication?.identity).toEqual(planIdentity);
    expect(result.current.surfaceInteractionPublication?.tools.some((tool) => tool.id === "page-tool")).toBe(true);
  });

  it("null editCommandTarget withholds Edit commands without invalidating page-action publication", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishSurfaceInteractionPublication(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
    });
    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "inspector", label: "Inspector", onClick: vi.fn() }],
          editorTools: {
            pinnedActions: [{ id: "bold", label: "Bold", onClick: vi.fn() }],
          },
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    expect(result.current.surfaceInteractionPublication).not.toBeNull();
    expect(result.current.surfaceInteractionPublication?.tools.some((tool) => tool.id === "inspector")).toBe(true);
    expect(result.current.surfaceInteractionPublication?.editCommands ?? []).toEqual([]);
  });

  it("executes AppChrome page actions through guarded effective publication", () => {
    const onClick = vi.fn();
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishSurfaceInteractionPublication(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
    });
    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "launch", label: "Launch", onClick }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    const launch = result.current.surfaceInteractionPublication?.tools.find((tool) => tool.id === "launch");
    expect(launch?.activation.kind).toBe("command");
    if (launch?.activation.kind !== "command") throw new Error("expected command activation");
    act(() => {
      void launch.activation.invoke();
    });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("blocks AppChrome page-tool invoke after invalid chrome fragment nullifies effective publication", () => {
    const onClick = vi.fn();
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishSurfaceInteractionPublication(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
    });
    act(() => {
      result.current.publishAppChromeCompatibility(
        buildAppChromeCompatibilityFragment({
          pageActions: [{ id: "page-tool", label: "Page tool", onClick }],
          editorTools: null,
          basePublication: result.current.surfaceInteractionBasePublication,
          editCommandTarget: null,
        }),
      );
    });
    const firstInvoke = result.current.surfaceInteractionPublication?.tools.find((tool) => tool.id === "page-tool")
      ?.activation;
    expect(firstInvoke?.kind).toBe("command");
    if (firstInvoke?.kind !== "command") throw new Error("expected command activation");
    act(() => {
      void firstInvoke.invoke();
    });
    expect(onClick).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.publishAppChromeCompatibility({
        tools: [],
        editCommands: [{
          id: "bold",
          label: "Bold",
          placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
          availability: { status: "enabled" },
          target: { kind: "", id: "" },
          invoke: vi.fn(),
        }],
      });
    });
    expect(result.current.surfaceInteractionPublication).toBeNull();

    act(() => {
      void firstInvoke.invoke();
    });
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("AgentInteractionProvider projection catalog registration", () => {
  const planIdentity = { surfaceId: "plan", instanceKey: "plan\u001fcatalog-test" };
  const planContext = {
    campaignId: "longmont-c2",
    liveSession: 22,
    ingestSession: 21,
    headerLabel: "Plan",
  };

  function makePlanPublication(
    configOverrides: Partial<SurfaceConfig> = {},
  ): ProjectionSurfacePublication {
    return {
      identity: planIdentity,
      config: {
        id: "plan",
        label: "Plan",
        context: planContext,
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
        ...configOverrides,
      },
    };
  }

  const toolActive = {
    kind: "tool" as const,
    key: "recap",
    size: "wide" as const,
    title: "Recap",
  };

  it("returns permanent inert cleanup when registering without an active lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const render = vi.fn(() => "body");
    let cleanup: (() => void) | undefined;
    act(() => {
      cleanup = result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render,
      });
    });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      cleanup?.();
    });
    act(() => {
      result.current.openTool("recap");
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).toBe("unregistered");
    expect(render).not.toHaveBeenCalled();
  });

  it("resolves ready when registration, descriptor, and bindings align", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const render = vi.fn(() => "catalog-body");
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render,
      });
    });
    act(() => {
      result.current.openTool("recap");
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: result.current.active!,
      bindings: { "plan-context": planContext },
    });
    expect(resolution).toEqual({ status: "ready", body: "catalog-body" });
    expect(render).toHaveBeenCalledTimes(1);
  });

  it("fails closed with duplicate_registration for two live entries on the same ID", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const renderA = vi.fn(() => "a");
    const renderB = vi.fn(() => "b");
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render: renderA,
      });
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render: renderB,
      });
    });
    act(() => {
      result.current.openTool("recap");
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: result.current.active!,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).toBe("duplicate_registration");
    expect(renderA).not.toHaveBeenCalled();
    expect(renderB).not.toHaveBeenCalled();
  });

  it("cannot bypass publication descriptor with registration alone", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const render = vi.fn(() => "body");
    act(() => {
      result.current.publishProjectionSurface(
        makePlanPublication({ tools: [{ id: "statblock", label: "Statblock", size: "wide" as const }] }),
      );
    });
    act(() => {
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render,
      });
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).toBe("descriptor_missing");
    expect(render).not.toHaveBeenCalled();
  });

  it("preserves registrations across a same-identity config update", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const render = vi.fn(() => "still-live");
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render,
      });
    });
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication({ label: "Plan (revised)" }));
    });
    act(() => {
      result.current.openTool("recap");
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: result.current.active!,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).toBe("ready");
    expect(render).toHaveBeenCalledTimes(1);
  });

  it("clears catalog entries when the lease identity changes", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const render = vi.fn(() => "body");
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render,
      });
    });
    act(() => {
      result.current.publishProjectionSurface({
        identity: { surfaceId: "ingest", instanceKey: "ingest\u001fcatalog-test" },
        config: {
          id: "ingest",
          label: "Ingest",
          context: planContext,
          tools: [{ id: "ingest-recap", label: "Recap", size: "wide" as const }],
          canvas: { documentId: null },
          theme: {},
        },
      });
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).not.toBe("ready");
    expect(render).not.toHaveBeenCalled();
  });

  it("lets stale cleanup from lease A run as no-op after lease B registers the same ID", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const renderA = vi.fn(() => "a");
    const renderB = vi.fn(() => "b");
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    let cleanupA: (() => void) | undefined;
    act(() => {
      cleanupA = result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render: renderA,
      });
    });
    act(() => {
      result.current.publishProjectionSurface({
        identity: { surfaceId: "plan", instanceKey: "plan\u001fcatalog-instance-b" },
        config: makePlanPublication().config,
      });
    });
    act(() => {
      result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render: renderB,
      });
    });
    act(() => {
      cleanupA?.();
    });
    act(() => {
      result.current.openTool("recap");
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: result.current.active!,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).toBe("ready");
    expect(renderB).toHaveBeenCalledTimes(1);
    expect(renderA).not.toHaveBeenCalled();
  });

  it("makes a stale registrar from lease A permanently inert after lease B binds", () => {
    let renders = 0;
    const { result } = renderHook(
      () => {
        renders += 1;
        return useAgentInteraction();
      },
      { wrapper },
    );
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    const staleRegister = result.current.registerProjectionCatalog;
    act(() => {
      result.current.publishProjectionSurface({
        identity: { surfaceId: "plan", instanceKey: "plan\u001fcatalog-instance-b" },
        config: makePlanPublication().config,
      });
    });
    const rendersBeforeStaleInvoke = renders;
    const render = vi.fn(() => "stale-body");
    let cleanup: (() => void) | undefined;
    act(() => {
      cleanup = staleRegister({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render,
      });
    });
    expect(renders).toBe(rendersBeforeStaleInvoke);
    act(() => {
      cleanup?.();
    });
    expect(renders).toBe(rendersBeforeStaleInvoke);
    act(() => {
      result.current.openTool("recap");
    });
    const resolution = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: result.current.active!,
      bindings: { "plan-context": planContext },
    });
    expect(resolution.status).toBe("unregistered");
    expect(render).not.toHaveBeenCalled();
  });

  it("keeps an open tool mounted across a same-identity preferredSize update", () => {
    const mounts = { count: 0 };
    function StatefulTool() {
      useState(() => {
        mounts.count += 1;
        return true;
      });
      return <div data-testid="stateful-tool">mounted</div>;
    }

    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }
    function CatalogBody() {
      const host = useAgentInteraction();
      if (!host.active) return <div data-testid="idle">idle</div>;
      const resolution = host.resolveProjectionCatalog({
        projectionId: "recap",
        active: host.active,
        bindings: { "plan-context": planContext },
      });
      return (
        <>
          {resolution.status !== "ready" ? (
            <div data-testid="catalog-status">{resolution.status}</div>
          ) : (
            resolution.body
          )}
          <div data-testid="active-size">{host.active.size}</div>
        </>
      );
    }

    render(
      <AgentInteractionProvider>
        <CaptureApi />
        <CatalogBody />
      </AgentInteractionProvider>,
    );

    act(() => {
      hostApi!.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      hostApi!.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render: () => <StatefulTool />,
      });
    });
    act(() => {
      hostApi!.openTool("recap");
    });

    expect(screen.getByTestId("stateful-tool")).toBeInTheDocument();
    expect(mounts.count).toBe(1);

    act(() => {
      hostApi!.updateProjectionSurfaceConfig(
        makePlanPublication({
          tools: [{ id: "recap", label: "Recap", size: "fullscreen" as const }],
        }),
      );
    });

    expect(screen.queryByTestId("catalog-status")).not.toBeInTheDocument();
    expect(screen.getByTestId("active-size")).toHaveTextContent("fullscreen");
    expect(screen.getByTestId("stateful-tool")).toBeInTheDocument();
    expect(mounts.count).toBe(1);
  });

  it("does not rewrite registration kind on same-identity publication updates", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    let cleanup: (() => void) | undefined;

    const validated = validateProjectionSurfacePublication(makePlanPublication());
    const neutralBase = adaptProjectionSurfaceToNeutralBase(validated);

    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      cleanup = result.current.registerProjectionCatalog({
        projectionId: "recap",
        surfaceId: "plan",
        kind: "tool",
        preferredSize: "wide",
        requiredBindingIds: ["plan-context"],
        render: () => "tool-body",
      });
    });

    const flipped: typeof neutralBase = {
      ...neutralBase,
      tools: neutralBase.tools.filter((tool) => tool.id !== "recap"),
      projections: neutralBase.projections.map((descriptor) =>
        descriptor.id === "recap"
          ? { ...descriptor, kind: "content" as const }
          : descriptor,
      ),
    };

    act(() => {
      result.current.updateSurfaceInteractionPublication(flipped);
    });

    // Registration kind must remain tool-owned. A content active must not become
    // ready merely because the publication descriptor kind flipped.
    const after = result.current.resolveProjectionCatalog({
      projectionId: "recap",
      active: {
        kind: "content",
        key: "doc:should-not-render-recap-tool",
        size: "wide",
        title: "Content",
      },
      bindings: { "plan-context": planContext },
    });
    expect(after.status).toBe("kind_mismatch");
    act(() => {
      cleanup?.();
    });
  });

  it("opens tool projections from effective publication without legacy projection surface", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const publication = {
      surfaceId: "native",
      label: "Native",
      identity: buildSurfaceInteractionIdentity({ surfaceId: "native", instanceParts: ["open-tool"] }),
      canvas: null,
      agentContext: null,
      tools: [{
        id: "native-tool",
        label: "Native Tool",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" as const },
        activation: { kind: "projection" as const, projectionId: "native-tool" },
      }],
      editCommands: [],
      projections: [{
        id: "native-tool",
        kind: "tool" as const,
        preferredSize: "wide" as const,
        bindingIds: [],
      }],
      projectionBindings: [],
    };
    act(() => {
      result.current.publishSurfaceInteractionPublication(publication);
    });
    act(() => {
      expect(result.current.activateProjectionTool("native-tool")).toBe(true);
    });
    expect(result.current.active).toEqual({
      kind: "tool",
      key: "native-tool",
      size: "wide",
      title: "Native Tool",
    });
  });

  it("opens a native Projection when tool id differs from activation.projectionId", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const publication = {
      surfaceId: "native",
      label: "Native",
      identity: buildSurfaceInteractionIdentity({
        surfaceId: "native",
        instanceParts: ["divergent-ids"],
      }),
      canvas: null,
      agentContext: null,
      tools: [{
        id: "find-existing",
        label: "Find Existing",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" as const },
        activation: {
          kind: "projection" as const,
          projectionId: "graph-reference-search",
        },
      }],
      editCommands: [],
      projections: [{
        id: "graph-reference-search",
        kind: "tool" as const,
        preferredSize: "wide" as const,
        bindingIds: [],
      }],
      projectionBindings: [],
    };
    act(() => {
      result.current.publishSurfaceInteractionPublication(publication);
    });
    act(() => {
      expect(result.current.activateProjectionTool("find-existing")).toBe(true);
    });
    expect(result.current.active).toEqual({
      kind: "tool",
      key: "graph-reference-search",
      size: "wide",
      title: "Find Existing",
    });
    act(() => {
      expect(result.current.activateProjectionTool("graph-reference-search")).toBe(false);
    });
  });

  it("clears a native Projection on same-identity tool removal and does not resurrect it", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const identity = buildSurfaceInteractionIdentity({
      surfaceId: "native",
      instanceParts: ["no-resurrect"],
    });
    const withTool = {
      surfaceId: "native",
      label: "Native",
      identity,
      canvas: null,
      agentContext: null,
      tools: [{
        id: "find-existing",
        label: "Find Existing",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" as const },
        activation: {
          kind: "projection" as const,
          projectionId: "graph-reference-search",
        },
      }],
      editCommands: [],
      projections: [{
        id: "graph-reference-search",
        kind: "tool" as const,
        preferredSize: "wide" as const,
        bindingIds: [],
      }],
      projectionBindings: [],
    };
    const withoutTool = {
      ...withTool,
      tools: [],
      projections: [],
    };

    act(() => {
      result.current.publishSurfaceInteractionPublication(withTool);
    });
    act(() => {
      expect(result.current.activateProjectionTool("find-existing")).toBe(true);
    });
    expect(result.current.active?.key).toBe("graph-reference-search");

    act(() => {
      result.current.updateSurfaceInteractionPublication(withoutTool);
    });
    expect(result.current.active).toBeNull();

    act(() => {
      result.current.updateSurfaceInteractionPublication(withTool);
    });
    expect(result.current.active).toBeNull();

    act(() => {
      expect(result.current.activateProjectionTool("find-existing")).toBe(true);
    });
    expect(result.current.active?.key).toBe("graph-reference-search");
  });

  it("awaits a registered async activator before reporting success", async () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    let resolveActivator!: (value: boolean) => void;
    const activator = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          resolveActivator = resolve;
        }),
    );
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerProjectionToolActivator(activator);
    });

    let pending!: Promise<boolean>;
    act(() => {
      const opened = result.current.activateProjectionTool("recap");
      expect(opened).toBeInstanceOf(Promise);
      pending = opened as Promise<boolean>;
    });
    expect(activator).toHaveBeenCalledWith("recap");
    expect(result.current.active).toBeNull();

    await act(async () => {
      resolveActivator(true);
      await expect(pending).resolves.toBe(true);
    });
  });

  it("routes activateProjectionTool through a registered activator on the current lease", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const activator = vi.fn();
    act(() => {
      result.current.publishProjectionSurface(makePlanPublication());
    });
    act(() => {
      result.current.registerProjectionToolActivator(activator);
    });
    act(() => {
      expect(result.current.activateProjectionTool("recap")).toBe(true);
    });
    expect(activator).toHaveBeenCalledWith("recap");
  });
});
