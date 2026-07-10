import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { LiveApiError } from "../../api/liveApi";
import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
import { resetReferenceIndexCache } from "./referenceResolver";
import { usePlanGraphReferenceResolver, resolvePlanReferenceWithFallback } from "./usePlanGraphReferenceResolver";

const glowkindleNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A friendly merchant.",
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-21",
  node_views: {
    "npc-glowkindle": glowkindleNode,
  },
  focus: {
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  mentions: [],
};

const sessionDescriptor = {
  surfaceId: "plan" as const,
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown" as const,
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "C2 Session 23 Prep",
    targetRelpath: "corpus/example.md",
    storageKey: "storage-key",
    status: "local_draft" as const,
  },
};

describe("usePlanGraphReferenceResolver", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    resetReferenceIndexCache();
  });

  it("loads projection and resolves graph-node hits", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockResolvedValue(projection);
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ npcs: [] }),
    } as Response);

    const { result } = renderHook(() => usePlanGraphReferenceResolver(sessionDescriptor));

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));

    const resolution = await result.current.resolvePlanReference({
      kind: "ref",
      refType: "npc",
      refId: "glowkindle",
      label: "Glow",
    });

    expect(resolution.kind).toBe("graph-node");
    expect(resolution.graphNodeId).toBe("npc-glowkindle");
    expect(resolution.graphProjectionState).toBe("ready");
  });

  it("marks projection unavailable without crashing resolution", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockRejectedValue(
      new LiveApiError("missing projection", 404),
    );
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        locations: [{
          index_id: "north-reach-gate",
          title: "North Reach Gate",
        }],
      }),
    } as Response);

    const { result } = renderHook(() => usePlanGraphReferenceResolver(sessionDescriptor));

    await waitFor(() => expect(result.current.projectionState).toBe("unavailable"));

    const resolution = await result.current.resolvePlanReference({
      kind: "ref",
      refType: "location",
      refId: "north-reach-gate",
      label: "North Reach Gate",
    });

    expect(resolution.kind).toBe("corpus-index");
    expect(resolution.graphProjectionState).toBe("unavailable");
  });
});

describe("resolvePlanReferenceWithFallback", () => {
  beforeEach(() => {
    resetReferenceIndexCache();
  });

  it("returns ambiguous unresolved when duplicate aliases match", async () => {
    const ambiguousProjection: UnionSupergraphProjectionResponse = {
      ...projection,
      node_views: {
        "npc-lysandra-a": {
          ...glowkindleNode,
          node_id: "npc-lysandra-a",
          label: "Lysandra Ironveil",
          aliases: ["Lysandra"],
        },
        "npc-lysandra-b": {
          ...glowkindleNode,
          node_id: "npc-lysandra-b",
          label: "Lysandra of the Gate",
          aliases: ["Lysandra"],
        },
      },
    };

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "npc",
        refId: "lysandra",
        label: "Lysandra",
      },
      {
        projection: ambiguousProjection,
        projectionState: "ready",
        fetchImpl: async () =>
          ({
            ok: true,
            json: async () => ({ npcs: [] }),
          }) as Response,
      },
    );

    expect(resolution.kind).toBe("unresolved");
    expect(resolution.ambiguousNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
  });
});
