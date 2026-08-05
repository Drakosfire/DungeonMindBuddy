import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import { resolveBuildGraphLens, type BuildGraphLensResolution } from "./resolveBuildGraphLens";
import { useBuildWorldGraphProjection } from "./useBuildWorldGraphProjection";

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

function headProjection(revisionId = "rev-head"): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
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
    ...overrides,
  };
}

describe("useBuildWorldGraphProjection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("skips API for selection_required and marks projection unavailable", async () => {
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

    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    expect(postSpy).not.toHaveBeenCalled();
    expect(result.current.projection).toBeNull();
    expect(result.current.items).toEqual([]);
    expect(result.current.error).toMatch(/requires an explicit campaign selection/i);
  });

  it("skips API for invalid lens and surfaces lens.reason as error", async () => {
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(postSpy).not.toHaveBeenCalled();
    expect(result.current.error).toBe(
      "Campaign-scoped document (longmont-c1) does not admit campaign lens longmont-c2.",
    );
    expect(result.current.projection).toBeNull();
    expect(result.current.items).toEqual([]);
  });

  it("requests head projection with revisionPin null", async () => {
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

    await waitFor(() => expect(result.current.state).toBe("ready"));
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
    expect(result.current.loadedRevisionId).toBe("rev-head");
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0]?.nodeId).toBe("npc-glowkindle");
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

    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(postSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        campaignId: "longmont-c1",
        revisionPin: pinnedRevision,
      }),
    );
    expect(result.current.revisionMode).toBe("pinned");
    expect(result.current.requestedRevisionId).toBe(pinnedRevision);
    expect(result.current.loadedRevisionId).toBe(pinnedRevision);
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(result.current.error).toMatch(/Pinned revision rev-requested does not match loaded revision rev-other/);
    expect(result.current.projection).toBeNull();
    expect(result.current.loadedRevisionId).toBeNull();
    expect(result.current.items).toEqual([]);
  });

  it("ignores late responses after a newer generation starts", async () => {
    let resolveFirst!: (value: WorldGraphProjection) => void;
    const firstDeferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveFirst = resolve;
    });
    const postSpy = vi
      .spyOn(liveApi, "postWorldGraphProjection")
      .mockImplementationOnce(() => firstDeferred)
      .mockResolvedValueOnce({
        ...headProjection("rev-second"),
        snapshot: {
          ...headProjection("rev-second").snapshot,
          campaignId: "longmont-c2",
        },
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

    await waitFor(() => expect(result.current.state).toBe("loading"));
    const firstGeneration = result.current.generation;

    rerender({
      lens: readyLens({ campaignId: "longmont-c2", documentCampaignId: "longmont-c2" }),
    });

    // Transition render must not publish lens A results under lens B.
    expect(result.current.state).toBe("loading");
    expect(result.current.items).toEqual([]);
    expect(result.current.projection).toBeNull();

    await waitFor(() => expect(result.current.generation).toBeGreaterThan(firstGeneration));
    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.loadedRevisionId).toBe("rev-second");

    await act(async () => {
      resolveFirst(headProjection("rev-stale"));
    });

    expect(result.current.loadedRevisionId).toBe("rev-second");
    expect(result.current.state).toBe("ready");
    expect(postSpy).toHaveBeenCalledTimes(2);
  });

  it("clears ready results synchronously when the lens changes after a successful load", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection")
      .mockResolvedValueOnce(headProjection("rev-c1"))
      .mockResolvedValueOnce({
        ...headProjection("rev-c2"),
        snapshot: {
          ...headProjection("rev-c2").snapshot,
          campaignId: "longmont-c2",
        },
      });

    const { result, rerender } = renderHook(
      ({ lens }) =>
        useBuildWorldGraphProjection({
          lens,
          documentIdentity: { documentId: "doc-1", campaignId: "longmont-c1" },
        }),
      { initialProps: { lens: readyLens({ campaignId: "longmont-c1" }) } },
    );

    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.items).toHaveLength(1);

    rerender({
      lens: readyLens({ campaignId: "longmont-c2", documentCampaignId: "longmont-c2" }),
    });

    expect(result.current.state).toBe("loading");
    expect(result.current.projection).toBeNull();
    expect(result.current.items).toEqual([]);
    expect(result.current.loadedRevisionId).toBeNull();

    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.loadedRevisionId).toBe("rev-c2");
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(result.current.error).toMatch(/Requested current head but projection reports non-head/);
    expect(result.current.projection).toBeNull();
    expect(result.current.loadedIsHead).toBe(false);
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(result.current.error).toMatch(/does not match requested campaign/);
    expect(result.current.items).toEqual([]);
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(result.current.error).toMatch(/does not match requested world/);
    expect(result.current.items).toEqual([]);
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(result.current.error).toMatch(/scopeMode/);
    expect(result.current.projection).toBeNull();
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

    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(result.current.error).toMatch(/focus does not match/);
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

    await waitFor(() => expect(result.current.state).toBe("loading"));
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

    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.revisionMode).toBe("head");
    expect(result.current.loadedRevisionId).toBe("rev-current-head");
    expect(result.current.items).toHaveLength(1);
    const headLoadKey = result.current.loadKey;
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ revisionPin: null }),
    );

    const pinnedHeadLens = readyLens({
      revision: { kind: "pinned", revisionId: "head" },
    });
    rerender({ lens: pinnedHeadLens });

    // Immediate transition: no prior head results under the pinned lens.
    expect(result.current.state).toBe("loading");
    expect(result.current.projection).toBeNull();
    expect(result.current.items).toEqual([]);
    expect(result.current.loadedRevisionId).toBeNull();
    expect(result.current.loadKey).not.toBe(headLoadKey);
    expect(result.current.revisionMode).toBe("pinned");
    expect(result.current.requestedRevisionId).toBe("head");

    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(postSpy).toHaveBeenCalledTimes(2);
    expect(postSpy.mock.calls[1]?.[0]).toEqual(
      expect.objectContaining({ revisionPin: "head" }),
    );
    expect(result.current.loadedRevisionId).toBe("head");
    expect(result.current.loadedIsHead).toBe(false);
    expect(result.current.revisionMode).toBe("pinned");
  });
});
