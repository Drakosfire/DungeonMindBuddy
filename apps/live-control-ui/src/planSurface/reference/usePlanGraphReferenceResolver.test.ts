import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { LiveApiError } from "../../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { resetReferenceIndexCache } from "./referenceResolver";
import {
  PlanGraphReferenceResolverProvider,
  usePlanGraphReferenceResolver,
  resolvePlanReferenceWithFallback,
  isCorpusFallbackAllowed,
} from "./usePlanGraphReferenceResolver";

const glowkindleNode: WorldGraphProjectionNodeView = {
  nodeId: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "A friendly merchant.",
};

const projection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: "eldyrwild", campaignId: "longmont-c2", revisionId: "rev-1", headRevisionId: "rev-1",
    isHead: true, focus: { kind: "session", sessionId: "session-21" }, admissibility: "gm",
  },
  summary: { nodeCount: 1, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
  nodes: [glowkindleNode],
  relationships: [], attributes: [], evidence: [], sourceArtifacts: [], diagnostics: [],
};

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

function resolverWrapper({ children }: { children: ReactNode }) {
  return createElement(
    PlanGraphReferenceResolverProvider,
    { sessionDescriptor },
    children,
  );
}

describe("usePlanGraphReferenceResolver", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    resetReferenceIndexCache();
  });

  it("loads projection and resolves graph-node hits without corpus-index fetch", async () => {
    const projectionSpy = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(projection);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ npcs: [] }),
    } as Response);

    const { result } = renderHook(() => usePlanGraphReferenceResolver(), { wrapper: resolverWrapper });

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
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(projectionSpy).toHaveBeenCalledWith({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "world",
      focus: {
        kind: "session",
        sessionId: "session-21",
        campaignId: "longmont-c2",
      },
      admissibility: "gm",
    });
  });

  it("resolves relationship targetId through resolvePlanRelationship", async () => {
    const innNode: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "location-inn",
      label: "Inn",
      kind: "location",
      role: "location",
      aliases: [],
    };
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...projection,
      nodes: [glowkindleNode, innNode],
    });

    const { result } = renderHook(() => usePlanGraphReferenceResolver(), { wrapper: resolverWrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("ready"));

    const resolution = await result.current.resolvePlanRelationship({
      id: "edge-1",
      label: "Inn",
      targetId: "location-inn",
      targetKind: "location",
      predicate: "met at",
    });

    expect(resolution.kind).toBe("graph-node");
    expect(resolution.locator).toBe("dmb-node:location-inn");
    expect(resolution.graphNodeId).toBe("location-inn");
  });

  it("marks projection unavailable without crashing resolution", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(
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

    const { result } = renderHook(() => usePlanGraphReferenceResolver(), { wrapper: resolverWrapper });

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

  it("maps projection integrity errors to error state without corpus fallback", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(
      new LiveApiError("Projection integrity check failed.", 409, {
        code: "projection_integrity_error",
      }),
    );
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        locations: [{
          index_id: "north-reach-gate",
          title: "North Reach Gate",
        }],
      }),
    } as Response);

    const { result } = renderHook(() => usePlanGraphReferenceResolver(), { wrapper: resolverWrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("error"));

    const resolution = await result.current.resolvePlanReference({
      kind: "ref",
      refType: "location",
      refId: "north-reach-gate",
      label: "North Reach Gate",
    });

    expect(resolution.kind).toBe("error");
    expect(resolution.graphProjectionState).toBe("error");
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe("resolvePlanReferenceWithFallback", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    resetReferenceIndexCache();
  });

  it("does not fetch corpus index when graph projection resolves a unique node", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("corpus index should not be fetched for graph hits");
    });

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "npc",
        refId: "glowkindle",
        label: "Glow",
      },
      {
        projection,
        projectionState: "ready",
        fetchImpl,
      },
    );

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(resolution.kind).toBe("graph-node");
    expect(resolution.graphNodeId).toBe("npc-glowkindle");
  });

  it("does not fetch corpus index when graph projection match is ambiguous", async () => {
    const ambiguousProjection: WorldGraphProjection = {
      ...projection,
      nodes: [
        {
          ...glowkindleNode,
          nodeId: "npc-lysandra-a",
          label: "Lysandra Ironveil",
          aliases: ["Lysandra"],
        },
        {
          ...glowkindleNode,
          nodeId: "npc-lysandra-b",
          label: "Lysandra of the Gate",
          aliases: ["Lysandra"],
        },
      ],
    };

    const fetchImpl = vi.fn(async () => {
      throw new Error("corpus index should not be fetched for ambiguous graph matches");
    });

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
        fetchImpl,
      },
    );

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(resolution.kind).toBe("unresolved");
    expect(resolution.ambiguousNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
  });

  it("fetches corpus index only after a graph miss", async () => {
    const fetchImpl = vi.fn(async () =>
      ({
        ok: true,
        json: async () => ({
          npcs: [{
            index_id: "missing-slug",
            title: "Glowkindle",
          }],
        }),
      }) as Response);

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "npc",
        refId: "missing-slug",
        label: "Not In Graph",
      },
      {
        projection,
        projectionState: "ready",
        fetchImpl,
      },
    );

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(resolution.kind).toBe("corpus-index");
  });

  it("does not fetch corpus index when projection state is error", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("corpus index should not be fetched when World Graph failed");
    });

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "npc",
        refId: "glowkindle",
        label: "Glow",
      },
      {
        projection: null,
        projectionState: "error",
        fetchImpl,
      },
    );

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(resolution.kind).toBe("error");
    expect(resolution.source).toBe("error");
    expect(resolution.graphProjectionState).toBe("error");
  });

  it("does not resolve against stale projection while loading", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("corpus index should not be fetched while projection is loading");
    });

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "npc",
        refId: "glowkindle",
        label: "Glow",
      },
      {
        projection: null,
        projectionState: "loading",
        fetchImpl,
      },
    );

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(resolution.kind).toBe("unresolved");
    expect(resolution.graphProjectionState).toBe("loading");
  });

  it("allows corpus fallback when projection is unavailable", async () => {
    const fetchImpl = vi.fn(async () =>
      ({
        ok: true,
        json: async () => ({
          locations: [{
            index_id: "north-reach-gate",
            title: "North Reach Gate",
          }],
        }),
      }) as Response);

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      {
        projection: null,
        projectionState: "unavailable",
        fetchImpl,
      },
    );

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(resolution.kind).toBe("corpus-index");
    expect(resolution.graphProjectionState).toBe("unavailable");
    expect(isCorpusFallbackAllowed("unavailable")).toBe(true);
    expect(isCorpusFallbackAllowed("error")).toBe(false);
    expect(isCorpusFallbackAllowed("loading")).toBe(false);
  });

  it("does not rebind a missing graph-node id when another node shares the label", async () => {
    const twinProjection: WorldGraphProjection = {
      ...projection,
      nodes: [
        {
          ...glowkindleNode,
          nodeId: "threat:other-beast",
          label: "Tripod Null-Calf",
          aliases: ["Tripod Null-Calf"],
          kind: "threat",
        },
      ],
    };
    const fetchImpl = vi.fn(async () => {
      throw new Error("corpus index must not be queried for graph-native refs");
    });

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      {
        projection: twinProjection,
        projectionState: "ready",
        fetchImpl,
      },
    );

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(resolution.kind).toBe("unresolved");
    expect(resolution.graphNodeId).toBeNull();
    expect(resolution.graphObject).toBeNull();
    expect(resolution.message).toMatch(/not found/i);
    expect(resolution.message).not.toMatch(/invalid reference locator/i);
  });

  it("reports World Graph unavailable for colon graph-node chips without corpus or invalid-locator errors", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("corpus index must not be queried for graph-native refs");
    });

    const resolution = await resolvePlanReferenceWithFallback(
      {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      {
        projection: null,
        projectionState: "unavailable",
        fetchImpl,
      },
    );

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(resolution.kind).toBe("unresolved");
    expect(resolution.graphProjectionState).toBe("unavailable");
    expect(resolution.message).toMatch(/world graph is unavailable/i);
    expect(resolution.message).not.toMatch(/invalid reference locator/i);
  });
});
