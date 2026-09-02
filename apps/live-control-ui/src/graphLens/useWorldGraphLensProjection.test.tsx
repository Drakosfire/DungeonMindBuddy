import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi, type ReactNode } from "vitest";
import { createElement } from "react";

import * as liveApi from "../api/liveApi";
import type { WorldGraphProjection } from "../api/types";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
  useOptionalWorldGraphLensInformationChannel,
  useWorldGraphLens,
  useWorldGraphLensProjection,
} from "./index";

function headProjection(
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
  projectionOverrides: Partial<WorldGraphProjection> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev-head",
      headRevisionId: "rev-head",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
      ...snapshotOverrides,
    },
    summary: {
      nodeCount: 0,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
    ...projectionOverrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  return createElement(
    WorldGraphLensProvider,
    { planCampaignId: "longmont-c2" },
    createElement(
      WorldGraphLensProjectionProvider,
      { defaultCampaignId: "longmont-c2" },
      children,
    ),
  );
}

describe("WorldGraphLensProjectionProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/plan");
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue({
      schema: "dmb_ingestion_source_bundle_v1",
      campaigns: {},
    } as never);
  });

  it("marks verified head responses ready", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(headProjection());

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-head");
    expect(result.current.projectionError).toBeNull();
  });

  it("fails closed when response identity does not match the request", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      headProjection({ campaignId: "longmont-c1" }),
    );

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("error"));
    expect(result.current.projection).toBeNull();
    expect(result.current.projectionError).toMatch(/campaign longmont-c1 does not match requested campaign longmont-c2/);
  });

  it("fails closed when head claim is inconsistent", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      headProjection({ isHead: true, revisionId: "rev-a", headRevisionId: "rev-b" }),
    );

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("error"));
    expect(result.current.projection).toBeNull();
    expect(result.current.projectionError).toMatch(/head claim is inconsistent/);
  });

  it("exposes exact request identity for consumers", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(headProjection());

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.request).toEqual(
      expect.objectContaining({
        campaignId: "longmont-c2",
        scopeMode: "campaign",
        admissibility: "gm",
      }),
    );
    expect(result.current.requestKey).toEqual(expect.any(String));
  });

  it("clears ready bytes synchronously when revision refresh generation changes", async () => {
    let resolveSecond!: (value: WorldGraphProjection) => void;
    const secondDeferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveSecond = resolve;
    });
    vi.spyOn(liveApi, "postWorldGraphProjection")
      .mockResolvedValueOnce(headProjection({ revisionId: "rev-1", headRevisionId: "rev-1" }))
      .mockReturnValueOnce(secondDeferred);

    let refreshToken = "r0";
    const { result, rerender } = renderHook(() => useWorldGraphLensProjection(), {
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(
          WorldGraphLensProvider,
          { planCampaignId: "longmont-c2" },
          createElement(
            WorldGraphLensProjectionProvider,
            {
              defaultCampaignId: "longmont-c2",
              revisionRefreshToken: refreshToken,
            },
            children,
          ),
        ),
    });

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-1");
    const requestKey = result.current.requestKey;

    refreshToken = "r1";
    rerender();
    // Same request key, new refresh generation → fail-closed loading with null bytes.
    expect(result.current.requestKey).toBe(requestKey);
    expect(result.current.projectionState).toBe("loading");
    expect(result.current.projection).toBeNull();

    await act(async () => {
      resolveSecond(headProjection({ revisionId: "rev-2", headRevisionId: "rev-2" }));
    });
    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-2");
  });

  const glowkindle = {
    nodeId: "npc:glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: ["Glow"],
    sourceDomains: ["recap"],
    evidenceBadges: [],
    adjacency: [],
    suggestedExpansions: [],
    anchoredToFocusSession: true,
    summary: "A friendly merchant.",
    campaignScope: "longmont-c2",
    evidenceRefIds: [],
    sourceArtifactIds: [],
  };

  function useProjectionAndChannel() {
    const lens = useWorldGraphLens();
    return {
      projection: useWorldGraphLensProjection(),
      channel: useOptionalWorldGraphLensInformationChannel(),
      setSelectedCampaignIds: lens.setSelectedCampaignIds,
    };
  }

  it("publishes one Surface Information channel per exact request and disposes it on replacement", async () => {
    const spy = vi.spyOn(liveApi, "postWorldGraphProjection").mockImplementation(async (request) =>
      headProjection({
        campaignId: request.campaignId,
        worldId: "eldyrwild",
        revisionId: `rev-${request.campaignId}`,
        headRevisionId: `rev-${request.campaignId}`,
      }),
    );

    const { result } = renderHook(() => useProjectionAndChannel(), { wrapper });

    await waitFor(() => expect(result.current.channel).not.toBeNull());
    const first = result.current.channel!;
    expect(first.descriptor.authority).toBe("dungeonmind");
    expect(first.descriptor.providerId).toBe("world_graph_lens_projection");
    expect(first.descriptor.subject).toEqual({ kind: "world", id: "eldyrwild" });
    expect(first.descriptor.scope).toEqual(
      expect.arrayContaining([
        { kind: "campaign", id: "longmont-c2" },
        { kind: "scope_mode", id: "campaign" },
        { kind: "admissibility", id: "gm" },
      ]),
    );
    expect(JSON.stringify(first.descriptor)).not.toMatch(/rev-/);
    await waitFor(() => {
      const status = first.getSnapshot().state.status;
      expect(status === "empty" || status === "ready").toBe(true);
    });
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0]?.[0].campaignId).toBe("longmont-c2");

    const staleTicket = first.beginObservation({ publishLoading: false });
    act(() => {
      result.current.setSelectedCampaignIds(["longmont-c1"]);
    });
    await waitFor(() => expect(result.current.channel).not.toBe(first));
    expect(result.current.channel).not.toBeNull();
    expect(result.current.channel!.descriptor.scope).toEqual(
      expect.arrayContaining([{ kind: "campaign", id: "longmont-c1" }]),
    );
    await waitFor(() => {
      const status = result.current.channel?.getSnapshot().state.status;
      expect(status === "empty" || status === "ready").toBe(true);
    });
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[1]?.[0].campaignId).toBe("longmont-c1");
    expect(
      first.commit(staleTicket!, {
        status: "ready",
        value: headProjection({}, { nodes: [glowkindle] }),
        revision: { kind: "exact", value: "rev-late" },
        provenance: [],
        inspectionTargets: [],
        diagnostics: [],
      }),
    ).toBe(false);
  });

  it("does not fetch World Graph on a disposed channel during descriptor replacement", async () => {
    let resolveFirst!: (value: WorldGraphProjection) => void;
    const firstDeferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveFirst = resolve;
    });
    const spy = vi.spyOn(liveApi, "postWorldGraphProjection")
      .mockReturnValueOnce(firstDeferred)
      .mockImplementation(async (request) =>
        headProjection({
          campaignId: request.campaignId,
          worldId: "eldyrwild",
          revisionId: `rev-${request.campaignId}`,
          headRevisionId: `rev-${request.campaignId}`,
        }),
      );

    const { result } = renderHook(() => useProjectionAndChannel(), { wrapper });
    await waitFor(() => expect(result.current.channel).not.toBeNull());
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0]?.[0].campaignId).toBe("longmont-c2");
    const first = result.current.channel!;

    act(() => {
      result.current.setSelectedCampaignIds(["longmont-c1"]);
    });
    await waitFor(() => expect(result.current.channel).not.toBe(first));
    await waitFor(() => {
      const status = result.current.channel?.getSnapshot().state.status;
      expect(status === "empty" || status === "ready").toBe(true);
    });
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[1]?.[0].campaignId).toBe("longmont-c1");

    await act(async () => {
      resolveFirst(
        headProjection({
          campaignId: "longmont-c2",
          revisionId: "rev-late-c2",
          headRevisionId: "rev-late-c2",
        }),
      );
    });
    expect(spy).toHaveBeenCalledTimes(2);
    const live = result.current.channel!.getSnapshot();
    expect(live.state.status === "empty" || live.state.status === "ready").toBe(true);
    if (live.state.status === "empty" || live.state.status === "ready") {
      expect(live.state.revision).toEqual({ kind: "exact", value: "rev-longmont-c1" });
    }
  });

  it("rejects a late same-scope response on the Surface Information channel", async () => {
    let resolveA!: (value: WorldGraphProjection) => void;
    let resolveB!: (value: WorldGraphProjection) => void;
    const deferredA = new Promise<WorldGraphProjection>((resolve) => {
      resolveA = resolve;
    });
    const deferredB = new Promise<WorldGraphProjection>((resolve) => {
      resolveB = resolve;
    });
    vi.spyOn(liveApi, "postWorldGraphProjection")
      .mockReturnValueOnce(deferredA)
      .mockReturnValueOnce(deferredB);

    let refreshToken = "r0";
    const { result, rerender } = renderHook(() => useProjectionAndChannel(), {
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(
          WorldGraphLensProvider,
          { planCampaignId: "longmont-c2" },
          createElement(
            WorldGraphLensProjectionProvider,
            {
              defaultCampaignId: "longmont-c2",
              revisionRefreshToken: refreshToken,
            },
            children,
          ),
        ),
    });

    await waitFor(() => expect(result.current.channel).not.toBeNull());
    const channel = result.current.channel!;
    const descriptor = channel.descriptor;

    refreshToken = "r1";
    rerender();
    expect(result.current.channel).toBe(channel);

    await act(async () => {
      const campaignId = result.current.projection.request?.campaignId ?? "longmont-c2";
      resolveB(
        headProjection(
          { campaignId, revisionId: "rev-B", headRevisionId: "rev-B" },
          { nodes: [glowkindle] },
        ),
      );
    });
    await waitFor(() => expect(channel.getSnapshot().state.status).toBe("ready"));
    const accepted = channel.getSnapshot();
    if (accepted.state.status === "ready") {
      expect(accepted.state.revision).toEqual({ kind: "exact", value: "rev-B" });
    }

    await act(async () => {
      const campaignId = result.current.projection.request?.campaignId ?? "longmont-c2";
      resolveA(
        headProjection(
          { campaignId, revisionId: "rev-A", headRevisionId: "rev-A" },
          { nodes: [glowkindle] },
        ),
      );
    });
    expect(result.current.channel).toBe(channel);
    expect(channel.descriptor).toBe(descriptor);
    expect(channel.getSnapshot()).toBe(accepted);
    expect(channel.getSnapshot().generation).toBe(accepted.generation);
  });

  it("treats an equivalent verified refresh as a new observation generation", async () => {
    const payload = headProjection(
      { revisionId: "rev-same", headRevisionId: "rev-same" },
      { nodes: [glowkindle] },
    );
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(payload);

    let refreshToken = "r0";
    const { result, rerender } = renderHook(() => useProjectionAndChannel(), {
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(
          WorldGraphLensProvider,
          { planCampaignId: "longmont-c2" },
          createElement(
            WorldGraphLensProjectionProvider,
            {
              defaultCampaignId: "longmont-c2",
              revisionRefreshToken: refreshToken,
            },
            children,
          ),
        ),
    });

    await waitFor(() => expect(result.current.channel?.getSnapshot().state.status).toBe("ready"));
    const channel = result.current.channel!;
    const first = channel.getSnapshot();
    refreshToken = "r1";
    rerender();
    await waitFor(() => expect(channel.getSnapshot().generation).toBeGreaterThan(first.generation));
    expect(result.current.channel).toBe(channel);
  });

  it("does not introduce a second World Graph request path", async () => {
    const spy = vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(headProjection());
    const { result } = renderHook(() => useProjectionAndChannel(), { wrapper });
    await waitFor(() => expect(result.current.projection.projectionState).toBe("ready"));
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
