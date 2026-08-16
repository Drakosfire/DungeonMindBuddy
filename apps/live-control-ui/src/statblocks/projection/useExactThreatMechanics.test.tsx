import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../../api/liveApi";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphReferenceResolution } from "../../graphReference/types";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { useExactThreatMechanics } from "./useExactThreatMechanics";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    postThreatQueryHydration: vi.fn(),
  };
});

import { postThreatQueryHydration } from "../../api/liveApi";

const revision = revisionFixture as StatblockRevisionResourceV1;

const scope = {
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  scopeMode: "world" as const,
  revisionId: "rev-1",
};

function threatResolution(
  nodeId = "threat:tripod-null-calf",
  label = "Tripod Null-Calf",
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${nodeId}`,
    reference: null,
    graphNodeId: nodeId,
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: nodeId,
      label,
      kind: "threat",
      role: "creature",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
    }),
    graphScope: scope,
    projectionState: "ready",
    message: "Resolved graph node.",
  };
}

function okResponse(nodeId: string, revisionId = scope.revisionId) {
  return {
    schema: "dmb_threat_query_hydration_response_v1" as const,
    worldId: scope.worldId,
    campaignId: scope.campaignId,
    scopeMode: scope.scopeMode,
    revisionId,
    queryText: nodeId,
    resultLabel: "threat_query_hydration_ok" as const,
    hits: [
      {
        threat: {
          nodeId,
          label: nodeId,
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
        },
        matchReasons: ["exact_node_id"],
        relationships: [],
        bindings: [
          {
            relationshipEdgeId: "edge-1",
            bindingId: "bind-1",
            bindingRole: "primary",
            threatNodeId: nodeId,
            resourceNodeId: revision.statblock_id,
            provider: "dungeonmind",
            statblockId: revision.statblock_id,
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
}

function Probe({
  resolution,
  enabled = true,
}: {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
  enabled?: boolean;
}) {
  const state = useExactThreatMechanics(resolution, { enabled });
  return (
    <div>
      <span data-testid="load-status">{state.loadStatus}</span>
      <span data-testid="threat-id">{state.selectionTuple?.threatNodeId ?? ""}</span>
      <span data-testid="revision-id">{state.selectionTuple?.revisionId ?? ""}</span>
      <span data-testid="hit-id">{state.hit?.threat.nodeId ?? ""}</span>
      <span data-testid="message">{state.message ?? ""}</span>
    </div>
  );
}

describe("useExactThreatMechanics", () => {
  beforeEach(() => {
    vi.mocked(postThreatQueryHydration).mockReset();
  });

  it("requests the exact graph scope and Threat node from the resolution", async () => {
    vi.mocked(postThreatQueryHydration).mockResolvedValue(okResponse("threat:tripod-null-calf"));
    render(<Probe resolution={threatResolution()} />);

    await waitFor(() => {
      expect(screen.getByTestId("load-status")).toHaveTextContent("ready");
    });
    expect(postThreatQueryHydration).toHaveBeenCalledWith(
      expect.objectContaining({
        worldId: scope.worldId,
        campaignId: scope.campaignId,
        scopeMode: scope.scopeMode,
        revisionPin: scope.revisionId,
        queryText: "threat:tripod-null-calf",
        focusNodeIds: ["threat:tripod-null-calf"],
        includeMechanics: true,
      }),
    );
    expect(screen.getByTestId("hit-id")).toHaveTextContent("threat:tripod-null-calf");
  });

  it("does not hydrate when disabled", () => {
    render(<Probe resolution={threatResolution()} enabled={false} />);
    expect(postThreatQueryHydration).not.toHaveBeenCalled();
    expect(screen.getByTestId("load-status")).toHaveTextContent("ready");
    expect(screen.getByTestId("hit-id")).toHaveTextContent("");
  });

  it("fails closed when response graph revision disagrees with the request", async () => {
    vi.mocked(postThreatQueryHydration).mockResolvedValue(
      okResponse("threat:tripod-null-calf", "rev-2"),
    );
    render(<Probe resolution={threatResolution()} />);

    await waitFor(() => {
      expect(screen.getByTestId("load-status")).toHaveTextContent("integrity_failure");
    });
    expect(screen.getByTestId("hit-id")).toHaveTextContent("");
  });

  it("drops a stale X completion after the selection changes to Y", async () => {
    let resolveFirst: ((value: ReturnType<typeof okResponse>) => void) | undefined;
    const first = new Promise<ReturnType<typeof okResponse>>((resolve) => {
      resolveFirst = resolve;
    });
    vi.mocked(postThreatQueryHydration)
      .mockImplementationOnce(() => first as never)
      .mockResolvedValueOnce(okResponse("threat:other"));

    const { rerender } = render(<Probe resolution={threatResolution()} />);
    rerender(<Probe resolution={threatResolution("threat:other", "Other Threat")} />);

    await waitFor(() => {
      expect(postThreatQueryHydration).toHaveBeenCalledTimes(2);
    });
    resolveFirst?.(okResponse("threat:tripod-null-calf"));

    await waitFor(() => {
      expect(screen.getByTestId("hit-id")).toHaveTextContent("threat:other");
    });
    expect(screen.queryByTestId("hit-id")).not.toHaveTextContent("threat:tripod-null-calf");
  });

  it("maps 503 transport failure to unavailable without admitting a hit", async () => {
    vi.mocked(postThreatQueryHydration).mockRejectedValue(
      new LiveApiError("mechanics service unavailable", 503),
    );
    render(<Probe resolution={threatResolution()} />);

    await waitFor(() => {
      expect(screen.getByTestId("load-status")).toHaveTextContent("unavailable");
    });
    expect(screen.getByTestId("hit-id")).toHaveTextContent("");
    expect(screen.getByTestId("message")).toHaveTextContent("mechanics service unavailable");
  });
});
