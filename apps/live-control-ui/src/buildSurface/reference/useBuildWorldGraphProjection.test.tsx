import { createElement, type ReactNode } from "react";
import { WorldGraphLensProjectionProvider, useOptionalWorldGraphLensProjection, useOptionalWorldGraphLensInformationChannel, useWorldGraphLensProjectionDemand } from "../../graphLens/useWorldGraphLensProjection";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as selectedWorld from "../../selectedWorld/SelectedWorldContext";
import type { ManagedWorldGraphProjectionResponse } from "../../api/types";
import * as liveApi from "../../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import type { WorldGraphLensProjectionValue } from "../../graphLens/useWorldGraphLensProjection";
import {
  mapWorldGraphLensObservation,
  worldGraphLensInformationDescriptor,
} from "../../graphLens/worldGraphLensSurfaceInformation";
import { createSurfaceInformationChannel } from "../../surfaceInformation";
import { worldGraphProjectionRequestKey } from "../../worldGraph/worldGraphProjectionRequestKey";
import {
  observedIsHead,
  observedRevisionId,
  searchItemsFromWorldGraphState,
} from "./buildWorldGraphSurfaceInformation";
import { resolveBuildGraphLens, type BuildGraphLensResolution } from "./resolveBuildGraphLens";
import {
  useBuildWorldGraphProjection,
  type UseBuildWorldGraphInformationResult,
} from "./useBuildWorldGraphProjection";

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

function headRequest(campaignId = "longmont-c1") {
  return {
    schema: "dmb_world_graph_projection_request_v1" as const,
    worldId: "eldyrwild",
    campaignId,
    scopeMode: "campaign" as const,
    focus: { kind: "none" as const, sessionId: null },
    admissibility: "gm" as const,
    revisionPin: null,
  };
}

function headProjection(revisionId = "rev-head", campaignId = "longmont-c1"): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId,
      revisionId,
      headRevisionId: revisionId,
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
    },
    summary: {
      nodeCount: 1,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [glowkindleNode],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

function emptyProjection(revisionId = "rev-head"): WorldGraphProjection {
  return {
    ...headProjection(revisionId),
    summary: {
      ...headProjection(revisionId).summary,
      nodeCount: 0,
    },
    nodes: [],
  };
}

function readyLens(
  overrides: Partial<Extract<BuildGraphLensResolution, { status: "ready" }>> = {},
): BuildGraphLensResolution {
  return {
    status: "ready",
    documentId: "doc-1",
    documentCampaignId: "longmont-c1",
    campaignId: "longmont-c1",
    worldId: "eldyrwild",
    availableCampaignIds: ["longmont-c1"],
    revision: { kind: "head" },
    scopeMode: "campaign",
    focus: { kind: "none", sessionId: null },
    ...overrides,
  };
}

function snapshotOf(result: UseBuildWorldGraphInformationResult) {
  return result.channel?.getSnapshot() ?? null;
}

function statusOf(result: UseBuildWorldGraphInformationResult) {
  return snapshotOf(result)?.state.status ?? null;
}

function reasonOf(result: UseBuildWorldGraphInformationResult) {
  const state = snapshotOf(result)?.state;
  if (!state || !("reason" in state)) return null;
  return state.reason;
}

function itemsOf(result: UseBuildWorldGraphInformationResult) {
  const state = snapshotOf(result)?.state;
  return state ? searchItemsFromWorldGraphState(state) : [];
}

function revisionOf(result: UseBuildWorldGraphInformationResult) {
  const state = snapshotOf(result)?.state;
  return state ? observedRevisionId(state) : null;
}

function isHeadOf(result: UseBuildWorldGraphInformationResult) {
  const state = snapshotOf(result)?.state;
  return state ? observedIsHead(state, result.revisionMode) : false;
}

function commitSharedChannel(
  request: ReturnType<typeof headRequest>,
  response: WorldGraphProjection,
) {
  const channel = createSurfaceInformationChannel(worldGraphLensInformationDescriptor(request));
  const ticket = channel.beginObservation();
  if (!ticket) {
    throw new Error("expected shared-channel observation ticket");
  }
  channel.commit(ticket, mapWorldGraphLensObservation({ request, response }));
  return channel;
}

describe("useBuildWorldGraphProjection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("skips API for selection_required and owns no channel", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    const lens = resolveBuildGraphLens({
      documentId: "doc-world",
      documentCampaignId: "eldyrwild",
      requestedCampaignId: null,
      requestedRevisionId: null,
    });
    expect(lens.status).toBe("selection_required");

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-world", campaignId: "eldyrwild" },
      }),
    );

    expect(result.current.source).toBe("none");
    expect(result.current.channel).toBeNull();
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("skips API for invalid lens and owns no channel", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    const lens = resolveBuildGraphLens({
      documentId: "doc-1",
      documentCampaignId: "longmont-c1",
      requestedCampaignId: "longmont-c2",
      requestedRevisionId: null,
    });
    expect(lens.status).toBe("invalid");

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    expect(result.current.source).toBe("none");
    expect(result.current.channel).toBeNull();
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("requests head projection with revisionPin null and commits READY", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      headProjection(),
    );
    const lens = readyLens();

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(result.current.source).toBe("secondary");
    expect(result.current.channel?.descriptor.providerId).toBe("build_world_graph_projection");
    expect(result.current.channel?.descriptor.authority).toBe("dungeonmind");
    expect(postSpy).toHaveBeenCalledWith({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign",
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      revisionPin: null,
    });
    expect(result.current.revisionMode).toBe("head");
    expect(result.current.requestedRevisionId).toBeNull();
    expect(revisionOf(result.current)).toBe("rev-head");
    expect(isHeadOf(result.current)).toBe(true);
    expect(itemsOf(result.current)).toHaveLength(1);
    expect(itemsOf(result.current)[0]?.nodeId).toBe("npc-glowkindle");
    expect(itemsOf(result.current)[0]?.scopeLabel).toBe("World");
  });

  it("labels campaign-scoped nodes with their own campaign_scope, not the projection anchor", async () => {
    const c2Node: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "npc-c2",
      label: "C2 NPC",
      campaignScope: "longmont-c2",
    };
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...headProjection(),
      snapshot: {
        ...headProjection().snapshot,
        campaignId: "longmont-c2",
        scopeMode: "world",
      },
      nodes: [c2Node, glowkindleNode],
      summary: {
        ...headProjection().summary,
        nodeCount: 2,
      },
    });
    const lens = readyLens({
      campaignId: "longmont-c2",
      scopeMode: "world",
    });

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(itemsOf(result.current).map((item) => [item.nodeId, item.scopeLabel])).toEqual([
      ["npc-c2", "longmont-c2"],
      ["npc-glowkindle", "World"],
    ]);
  });

  it("requests pinned projection with exact revision id", async () => {
    const pinnedRevision = "rev:abc";
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      headProjection(pinnedRevision),
    );
    const lens = readyLens({
      revision: { kind: "pinned", revisionId: pinnedRevision },
    });

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(postSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        campaignId: "longmont-c1",
        revisionPin: pinnedRevision,
      }),
    );
    expect(result.current.revisionMode).toBe("pinned");
    expect(result.current.requestedRevisionId).toBe(pinnedRevision);
    expect(revisionOf(result.current)).toBe(pinnedRevision);
    expect(isHeadOf(result.current)).toBe(false);
  });

  it("commits EMPTY for a verified zero-node response", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(emptyProjection());
    const lens = readyLens();
    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("empty"));
    expect(result.current.source).toBe("secondary");
    expect(revisionOf(result.current)).toBe("rev-head");
    expect(itemsOf(result.current)).toEqual([]);
  });

  it("commits UNAVAILABLE when the secondary read fails", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(new Error("authority down"));
    const lens = readyLens();
    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("unavailable"));
    expect(reasonOf(result.current)).toMatch(/authority down/);
    expect(itemsOf(result.current)).toEqual([]);
  });

  it("fails closed on pinned revision mismatch without head retry", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      headProjection("rev-other"),
    );
    const lens = readyLens({
      revision: { kind: "pinned", revisionId: "rev-requested" },
    });

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("integrity_error"));
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(reasonOf(result.current)).toMatch(
      /Pinned revision rev-requested does not match loaded revision rev-other/,
    );
    expect(revisionOf(result.current)).toBeNull();
    expect(itemsOf(result.current)).toEqual([]);
  });

  it("ignores late responses after a newer request starts", async () => {
    let resolveFirst!: (value: WorldGraphProjection) => void;
    const firstDeferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveFirst = resolve;
    });
    const postSpy = vi
      .spyOn(liveApi, "postWorldGraphProjection")
      .mockImplementationOnce(() => firstDeferred)
      .mockResolvedValueOnce({
        ...headProjection("rev-second", "longmont-c2"),
      });

    const initialLens = readyLens({ campaignId: "longmont-c1" });
    const { result, rerender } = renderHook(
      ({ lens }) =>
        useBuildWorldGraphProjection({
          lens,
          documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
        }),
      { initialProps: { lens: initialLens } },
    );

    await waitFor(() => expect(result.current.source).toBe("secondary"));
    await waitFor(() => expect(statusOf(result.current)).toBe("loading"));
    const firstChannel = result.current.channel;

    rerender({
      lens: readyLens({ campaignId: "longmont-c2", documentCampaignId: "longmont-c2" }),
    });

    expect(result.current.channel).not.toBe(firstChannel);
    expect(itemsOf(result.current)).toEqual([]);

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(revisionOf(result.current)).toBe("rev-second");
    const secondChannel = result.current.channel;

    await act(async () => {
      resolveFirst(headProjection("rev-stale"));
    });

    expect(result.current.channel).toBe(secondChannel);
    expect(revisionOf(result.current)).toBe("rev-second");
    expect(statusOf(result.current)).toBe("ready");
    expect(postSpy).toHaveBeenCalledTimes(2);
  });

  it("drops the previous secondary channel synchronously when the lens changes", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection")
      .mockResolvedValueOnce(headProjection("rev-c1"))
      .mockResolvedValueOnce(headProjection("rev-c2", "longmont-c2"));

    const { result, rerender } = renderHook(
      ({ lens }) =>
        useBuildWorldGraphProjection({
          lens,
          documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
        }),
      { initialProps: { lens: readyLens({ campaignId: "longmont-c1" }) } },
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(itemsOf(result.current)).toHaveLength(1);
    const firstChannel = result.current.channel;

    rerender({
      lens: readyLens({ campaignId: "longmont-c2", documentCampaignId: "longmont-c2" }),
    });

    expect(result.current.source).toBe("secondary");
    expect(result.current.channel).not.toBe(firstChannel);
    expect(itemsOf(result.current)).toEqual([]);
    expect(revisionOf(result.current)).toBeNull();

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(revisionOf(result.current)).toBe("rev-c2");
  });

  it("fails closed when a head response is not actually head", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...headProjection("rev-not-head"),
      snapshot: {
        ...headProjection("rev-not-head").snapshot,
        isHead: false,
        headRevisionId: "rev-real-head",
      },
    });
    const lens = readyLens();

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("integrity_error"));
    expect(reasonOf(result.current)).toMatch(/Requested current head but projection reports non-head/);
    expect(isHeadOf(result.current)).toBe(false);
  });

  it("fails closed when response campaign does not match the requested lens", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...headProjection(),
      snapshot: {
        ...headProjection().snapshot,
        campaignId: "longmont-c2",
      },
    });
    const lens = readyLens();

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("integrity_error"));
    expect(reasonOf(result.current)).toMatch(/does not match requested campaign/);
    expect(itemsOf(result.current)).toEqual([]);
  });

  it("fails closed when response world does not match the requested lens", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...headProjection(),
      snapshot: {
        ...headProjection().snapshot,
        worldId: "other-world",
      },
    });
    const lens = readyLens();

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("integrity_error"));
    expect(reasonOf(result.current)).toMatch(/does not match requested world/);
    expect(itemsOf(result.current)).toEqual([]);
  });

  it("fails closed when response scopeMode does not match the request", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...headProjection(),
      snapshot: {
        ...headProjection().snapshot,
        scopeMode: "world",
      },
    });
    const lens = readyLens();

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("integrity_error"));
    expect(reasonOf(result.current)).toMatch(/scopeMode/);
  });

  it("fails closed when response focus includes a campaign the request omitted", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      ...headProjection(),
      snapshot: {
        ...headProjection().snapshot,
        focus: { kind: "none", sessionId: null, campaignId: "longmont-c1" },
      },
    });
    const lens = readyLens();

    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("integrity_error"));
    expect(reasonOf(result.current)).toMatch(/focus does not match/);
  });

  it("ignores completion after unmount", async () => {
    let resolveProjection!: (value: WorldGraphProjection) => void;
    const deferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveProjection = resolve;
    });
    vi.spyOn(liveApi, "postWorldGraphProjection").mockReturnValue(deferred);

    const lens = readyLens();
    const { result, unmount } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
      }),
    );

    await waitFor(() => expect(result.current.source).toBe("secondary"));
    unmount();

    await act(async () => {
      resolveProjection(headProjection("rev-after-unmount"));
    });
  });

  it("distinguishes current-head mode from a pinned revision whose opaque id is head", async () => {
    const postSpy = vi
      .spyOn(liveApi, "postWorldGraphProjection")
      .mockResolvedValueOnce(headProjection("rev-current-head"))
      .mockResolvedValueOnce({
        ...headProjection("head"),
        snapshot: {
          ...headProjection("head").snapshot,
          revisionId: "head",
          headRevisionId: "rev-current-head",
          isHead: false,
        },
      });

    const headLens = readyLens({ revision: { kind: "head" } });
    const { result, rerender } = renderHook(
      ({ lens }) =>
        useBuildWorldGraphProjection({
          lens,
          documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
        }),
      { initialProps: { lens: headLens } },
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(result.current.revisionMode).toBe("head");
    expect(revisionOf(result.current)).toBe("rev-current-head");
    expect(itemsOf(result.current)).toHaveLength(1);
    const headLoadKey = result.current.loadKey;
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ revisionPin: null }),
    );

    const pinnedHeadLens = readyLens({
      revision: { kind: "pinned", revisionId: "head" },
    });
    rerender({ lens: pinnedHeadLens });

    expect(result.current.source).toBe("secondary");
    expect(itemsOf(result.current)).toEqual([]);
    expect(revisionOf(result.current)).toBeNull();
    expect(result.current.loadKey).not.toBe(headLoadKey);
    expect(result.current.revisionMode).toBe("pinned");
    expect(result.current.requestedRevisionId).toBe("head");

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(postSpy).toHaveBeenCalledTimes(2);
    expect(postSpy.mock.calls[1]?.[0]).toEqual(
      expect.objectContaining({ revisionPin: "head" }),
    );
    expect(revisionOf(result.current)).toBe("head");
    expect(isHeadOf(result.current)).toBe(false);
    expect(result.current.revisionMode).toBe("pinned");
  });
});

describe("useBuildWorldGraphProjection shared exact-match reuse", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function sharedValue(
    overrides: Partial<WorldGraphLensProjectionValue> = {},
  ): WorldGraphLensProjectionValue {
    const request = headRequest();
    return {
      request,
      requestKey: `native:${worldGraphProjectionRequestKey(request)}`,
      managedBinding:null,
      projection: headProjection(),
      projectionState: "ready",
      projectionError: null,
      nodeCount: 1,
      lastProjectionLoadMs: 1,
      lastProjectionLoadOutcome: "ready",
      ...overrides,
    };
  }

  it("reuses the shared channel when exact request keys match (zero Build POSTs)", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    const request = headRequest();
    const shared = sharedValue({ request, requestKey: `native:${worldGraphProjectionRequestKey(request)}` });
    const sharedChannel = commitSharedChannel(request, headProjection());

    const lens = readyLens();
    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
        sharedProjection: shared,
        sharedChannel,
      }),
    );

    expect(result.current.source).toBe("shared");
    expect(result.current.channel).toBe(sharedChannel);
    expect(statusOf(result.current)).toBe("ready");
    expect(revisionOf(result.current)).toBe("rev-head");
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("waits during shared replacement without issuing a secondary POST", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    const matchingRequest = headRequest("longmont-c1");
    const shared = sharedValue({
      request: matchingRequest,
      requestKey: `native:${worldGraphProjectionRequestKey(matchingRequest)}`,
    });
    const staleRequest = headRequest("longmont-c2");
    const staleChannel = createSurfaceInformationChannel(
      worldGraphLensInformationDescriptor(staleRequest),
    );

    const lens = readyLens();
    const { result, rerender } = renderHook(
      ({ sharedChannel }) =>
        useBuildWorldGraphProjection({
          lens,
          documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
          sharedProjection: shared,
          sharedChannel,
        }),
      { initialProps: { sharedChannel: staleChannel } },
    );

    expect(result.current.source).toBe("shared_pending");
    expect(result.current.channel).toBeNull();
    expect(postSpy).not.toHaveBeenCalled();

    const matchingChannel = commitSharedChannel(matchingRequest, headProjection());
    rerender({ sharedChannel: matchingChannel });

    expect(result.current.source).toBe("shared");
    expect(result.current.channel).toBe(matchingChannel);
    expect(statusOf(result.current)).toBe("ready");
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("secondary-loads when Build pins a revision that shared head cannot satisfy", async () => {
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      headProjection("rev-pinned"),
    );
    const request = headRequest();
    const shared = sharedValue({ request, requestKey: `native:${worldGraphProjectionRequestKey(request)}` });
    const sharedChannel = commitSharedChannel(request, headProjection());

    const lens = readyLens({ revision: { kind: "pinned", revisionId: "rev-pinned" } });
    const { result } = renderHook(() =>
      useBuildWorldGraphProjection({
        lens,
        documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
        sharedProjection: shared,
        sharedChannel,
      }),
    );

    await waitFor(() => expect(statusOf(result.current)).toBe("ready"));
    expect(result.current.source).toBe("secondary");
    expect(result.current.channel).not.toBe(sharedChannel);
    expect(result.current.channel?.descriptor.providerId).toBe("build_world_graph_projection");
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ revisionPin: "rev-pinned" }),
    );
    expect(revisionOf(result.current)).toBe("rev-pinned");
  });
});


describe("managed Build discovery", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(selectedWorld, "useSelectedWorld").mockReturnValue({kind:"managed",worldId:"new-world",name:"New World",documentId:null});
  });
  const lens = () => readyLens({worldId:"new-world",documentCampaignId:"new-world",campaignId:"",scopeMode:"world"});
  const request = () => ({...headRequest(""),worldId:"new-world",scopeMode:"world" as const});
  const response = (revision="rev-head"): ManagedWorldGraphProjectionResponse => ({
    schema:"dmb_managed_world_graph_projection_v1",managedWorldId:"new-world",nativeWorldId:"world:opaque",bindingVersion:1,
    projection:{...headProjection(revision,""),snapshot:{...headProjection(revision,"").snapshot,worldId:"world:opaque",scopeMode:"world"}},
  });
  const identity = {documentId:"doc-1",campaignId:"new-world"};
  function shared(): WorldGraphLensProjectionValue {
    return {request:request(),requestKey:`managed:${worldGraphProjectionRequestKey(request())}`,projection:response().projection,
      projectionState:"ready",projectionError:null,nodeCount:1,lastProjectionLoadMs:1,lastProjectionLoadOutcome:"ready"};
  }
  function channel() {
    const value=createSurfaceInformationChannel<WorldGraphProjection>(worldGraphLensInformationDescriptor(request(),"managed"));
    value.commit(value.beginObservation()!,mapWorldGraphLensObservation({request:request(),managedResponse:response()}));return value;
  }
  it("composes with the actual shared provider and issues only one managed read",async()=>{
    const native=vi.spyOn(liveApi,"postWorldGraphProjection");const managed=vi.spyOn(liveApi,"postManagedWorldGraphProjection").mockResolvedValue(response());
    const wrapper=({children}:{children:ReactNode})=>createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:"",children});
    const {result}=renderHook(()=>{
      useWorldGraphLensProjectionDemand(true);
      return useBuildWorldGraphProjection({lens:lens(),documentIdentity:identity,sharedProjection:useOptionalWorldGraphLensProjection(),sharedChannel:useOptionalWorldGraphLensInformationChannel()});
    },{wrapper});
    await waitFor(()=>expect(statusOf(result.current)).toBe("ready"));expect(result.current.source).toBe("shared");
    expect(itemsOf(result.current)).toHaveLength(1);expect(managed).toHaveBeenCalledTimes(1);expect(native).not.toHaveBeenCalled();
  });
  it("reuses managed bytes without duplicate reads",()=>{
    const native=vi.spyOn(liveApi,"postWorldGraphProjection");const managed=vi.spyOn(liveApi,"postManagedWorldGraphProjection");const retained=channel();
    const {result}=renderHook(()=>useBuildWorldGraphProjection({lens:lens(),documentIdentity:identity,sharedProjection:shared(),sharedChannel:retained}));
    expect(result.current.source).toBe("shared");expect(result.current.channel).toBe(retained);expect(statusOf(result.current)).toBe("ready");
    expect(native).not.toHaveBeenCalled();expect(managed).not.toHaveBeenCalled();
  });
  it("waits for the managed channel and refuses a native channel with the same request",()=>{
    const native=vi.spyOn(liveApi,"postWorldGraphProjection");const managed=vi.spyOn(liveApi,"postManagedWorldGraphProjection");
    const foreign=createSurfaceInformationChannel<WorldGraphProjection>(worldGraphLensInformationDescriptor(request()));
    const {result,rerender}=renderHook(({current})=>useBuildWorldGraphProjection({lens:lens(),documentIdentity:identity,sharedProjection:shared(),sharedChannel:current}),{initialProps:{current:foreign}});
    expect(result.current.source).toBe("shared_pending");expect(result.current.channel).toBeNull();
    const retained=channel();rerender({current:retained});expect(result.current.channel).toBe(retained);
    expect(native).not.toHaveBeenCalled();expect(managed).not.toHaveBeenCalled();
  });
  it("reads a distinct managed pin through the managed route",async()=>{
    const native=vi.spyOn(liveApi,"postWorldGraphProjection");const managed=vi.spyOn(liveApi,"postManagedWorldGraphProjection").mockResolvedValue(response("rev-pin"));
    const retained=channel();const {result}=renderHook(()=>useBuildWorldGraphProjection({lens:{...lens(),revision:{kind:"pinned",revisionId:"rev-pin"}},documentIdentity:identity,sharedProjection:shared(),sharedChannel:retained}));
    await waitFor(()=>expect(statusOf(result.current)).toBe("ready"));expect(revisionOf(result.current)).toBe("rev-pin");expect(managed).toHaveBeenCalledTimes(1);
    expect(managed).toHaveBeenCalledWith({schema:"dmb_managed_world_graph_projection_request_v1",managedWorldId:"new-world",revisionPin:"rev-pin",queryText:null});expect(native).not.toHaveBeenCalled();
  });
  it("rejects foreign envelope bytes without a native fallback",async()=>{
    const native=vi.spyOn(liveApi,"postWorldGraphProjection");vi.spyOn(liveApi,"postManagedWorldGraphProjection").mockResolvedValue({...response(),managedWorldId:"foreign"});
    const {result}=renderHook(()=>useBuildWorldGraphProjection({lens:lens(),documentIdentity:identity}));
    await waitFor(()=>expect(statusOf(result.current)).toBe("integrity_error"));expect(itemsOf(result.current)).toEqual([]);expect(native).not.toHaveBeenCalled();
  });
  it.each(["loading", "error"] as const)("does not reinterpret a %s managed selection as native",async(kind)=>{
    const native=vi.spyOn(liveApi,"postWorldGraphProjection");const managed=vi.spyOn(liveApi,"postManagedWorldGraphProjection");
    vi.mocked(selectedWorld.useSelectedWorld).mockReturnValue(kind === "loading" ? {kind,requestedWorldId:"new-world"} : {kind,message:"unavailable"});
    const {result}=renderHook(()=>useBuildWorldGraphProjection({lens:lens(),documentIdentity:identity,sharedProjection:shared(),sharedChannel:channel()}));
    expect(result.current.request).toBeNull();expect(result.current.channel).toBeNull();expect(native).not.toHaveBeenCalled();expect(managed).not.toHaveBeenCalled();
  });
  it("discards pending results on a managed owner switch",async()=>{
    let resolve!: (value:ManagedWorldGraphProjectionResponse)=>void;
    vi.spyOn(liveApi,"postManagedWorldGraphProjection").mockReturnValue(new Promise(r=>{resolve=r;}));const native=vi.spyOn(liveApi,"postWorldGraphProjection");
    const {result,rerender}=renderHook(()=>useBuildWorldGraphProjection({lens:lens(),documentIdentity:identity}));
    await waitFor(()=>expect(resolve).toBeDefined());
    vi.mocked(selectedWorld.useSelectedWorld).mockReturnValue({kind:"managed",worldId:"other",name:"Other",documentId:null});rerender();
    await act(async()=>resolve(response()));expect(result.current.channel).toBeNull();expect(itemsOf(result.current)).toEqual([]);expect(native).not.toHaveBeenCalled();
  });
});
