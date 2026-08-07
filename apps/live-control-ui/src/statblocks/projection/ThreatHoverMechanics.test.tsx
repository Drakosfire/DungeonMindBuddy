import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import * as liveApi from "../../api/liveApi";
import type { ExactGraphReferenceScope } from "../../graphReference/types";
import {
  resetThreatHoverHydrationCacheForTests,
  useThreatHoverMechanics,
} from "./ThreatHoverMechanics";

const revision = revisionFixture as StatblockRevisionResourceV1;

const scope: ExactGraphReferenceScope = {
  worldId: "eldyrwild",
  campaignId: "longmont-c1",
  scopeMode: "campaign",
  revisionId: "rev-1",
};

const okResponse = {
  schema: "dmb_threat_query_hydration_response_v1" as const,
  worldId: scope.worldId,
  campaignId: scope.campaignId,
  scopeMode: scope.scopeMode,
  revisionId: scope.revisionId,
  queryText: "threat-1",
  resultLabel: "threat_query_hydration_ok" as const,
  hits: [
    {
      threat: {
        nodeId: "threat-1",
        label: "Threat One",
        kind: "threat",
        role: "creature",
        aliases: [],
        sourceDomains: [],
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [],
        anchoredToFocusSession: true,
        summary: null,
      },
      matchReasons: ["exact_node_id"],
      relationships: [],
      bindings: [
        {
          relationshipEdgeId: "edge-1",
          bindingId: "bind-1",
          bindingRole: "primary",
          threatNodeId: "threat-1",
          resourceNodeId: "sb_000001",
          provider: "dungeonmind",
          statblockId: "sb_000001",
          revisionId: revision.revision_id,
          definitionDigest: revision.definition_digest,
          hydrationStatus: "available" as const,
          binding: null,
          revision,
          message: null,
        },
      ],
      mechanicsDisposition: "hydrated",
    },
  ],
  diagnostics: [],
  message: null,
};

describe("useThreatHoverMechanics", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    resetThreatHoverHydrationCacheForTests();
  });

  it("reuses cached hydration for the same exact tuple across leave/re-enter", async () => {
    const postSpy = vi.spyOn(liveApi, "postThreatQueryHydration").mockResolvedValue(okResponse as never);

    const { result, rerender } = renderHook(
      ({ enabled }) => useThreatHoverMechanics(enabled, "threat-1", scope),
      { initialProps: { enabled: true } },
    );

    await waitFor(() => expect(result.current.loadStatus).toBe("ready"));
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(result.current.compactBinding?.bindingId).toBe("bind-1");

    rerender({ enabled: false });
    expect(result.current.loadStatus).toBe("idle");

    rerender({ enabled: true });
    await waitFor(() => expect(result.current.loadStatus).toBe("ready"));
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(result.current.compactBinding?.bindingId).toBe("bind-1");
  });

  it("coalesces concurrent hydrations for the same exact tuple", async () => {
    let resolveHydration!: (value: typeof okResponse) => void;
    const deferred = new Promise<typeof okResponse>((resolve) => {
      resolveHydration = resolve;
    });
    const postSpy = vi.spyOn(liveApi, "postThreatQueryHydration").mockReturnValue(deferred as never);

    const first = renderHook(() => useThreatHoverMechanics(true, "threat-1", scope));
    const second = renderHook(() => useThreatHoverMechanics(true, "threat-1", scope));

    expect(postSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveHydration(okResponse);
    });

    await waitFor(() => expect(first.result.current.loadStatus).toBe("ready"));
    await waitFor(() => expect(second.result.current.loadStatus).toBe("ready"));
    expect(postSpy).toHaveBeenCalledTimes(1);
  });

  it("posts again when the exact Threat tuple changes", async () => {
    const postSpy = vi.spyOn(liveApi, "postThreatQueryHydration").mockResolvedValue(okResponse as never);

    const { rerender } = renderHook(
      ({ threatNodeId }) => useThreatHoverMechanics(true, threatNodeId, scope),
      { initialProps: { threatNodeId: "threat-1" } },
    );

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));
    rerender({ threatNodeId: "threat-2" });
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2));
  });
});
