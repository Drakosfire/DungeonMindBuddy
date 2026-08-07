import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi, type ReactNode } from "vitest";
import { createElement } from "react";

import * as liveApi from "../api/liveApi";
import type { WorldGraphProjection } from "../api/types";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
  useWorldGraphLensProjection,
} from "./index";

function headProjection(overrides: Partial<WorldGraphProjection["snapshot"]> = {}): WorldGraphProjection {
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
      ...overrides,
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
});
