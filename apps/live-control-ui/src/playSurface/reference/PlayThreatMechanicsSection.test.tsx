import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../../api/liveApi";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphReferenceResolution } from "../../graphReference/types";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { PlayThreatMechanicsSection } from "./PlayThreatMechanicsSection";

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
  revisionId: "rev-g1",
};

function resolution(
  kind: string,
  nodeId: string,
  label: string,
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${nodeId}`,
    reference: null,
    graphNodeId: nodeId,
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: nodeId,
      label,
      kind,
      role: kind === "threat" ? "creature" : "ally",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
    }),
    graphScope: scope,
    projectionState: "ready",
    message: "Resolved.",
  };
}

describe("PlayThreatMechanicsSection", () => {
  beforeEach(() => {
    vi.mocked(postThreatQueryHydration).mockReset();
  });

  it("does not hydrate ordinary non-Threat objects", () => {
    render(
      <PlayThreatMechanicsSection
        resolution={resolution("npc", "npc:mira", "Mira")}
      />,
    );
    expect(postThreatQueryHydration).not.toHaveBeenCalled();
    expect(screen.queryByTestId("play-threat-mechanics-section")).not.toBeInTheDocument();
  });

  it("renders exact Threat mechanics from the pinned graph revision", async () => {
    vi.mocked(postThreatQueryHydration).mockResolvedValue({
      schema: "dmb_threat_query_hydration_response_v1",
      worldId: scope.worldId,
      campaignId: scope.campaignId,
      scopeMode: scope.scopeMode,
      revisionId: scope.revisionId,
      queryText: "threat:tripod-null-calf",
      resultLabel: "threat_query_hydration_ok",
      hits: [
        {
          threat: {
            nodeId: "threat:tripod-null-calf",
            label: "Tripod Null-Calf",
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
              threatNodeId: "threat:tripod-null-calf",
              resourceNodeId: revision.statblock_id,
              provider: "dungeonmind",
              statblockId: revision.statblock_id,
              revisionId: revision.revision_id,
              definitionDigest: revision.definition_digest,
              hydrationStatus: "available",
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
    });

    render(
      <PlayThreatMechanicsSection
        resolution={resolution("threat", "threat:tripod-null-calf", "Tripod Null-Calf")}
      />,
    );

    await waitFor(() => {
      expect(document.querySelector("[data-statblock-renderer]")).toBeTruthy();
    });
    expect(postThreatQueryHydration).toHaveBeenCalledWith(
      expect.objectContaining({ revisionPin: "rev-g1", queryText: "threat:tripod-null-calf" }),
    );
    expect(screen.queryByText(/add to combat/i)).not.toBeInTheDocument();
  });

  it("degrades locally when mechanics are unavailable", async () => {
    vi.mocked(postThreatQueryHydration).mockRejectedValue(
      new LiveApiError("mechanics service unavailable", 503),
    );
    render(
      <PlayThreatMechanicsSection
        resolution={resolution("threat", "threat:tripod-null-calf", "Tripod Null-Calf")}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("threat-sheet-load-status")).toHaveAttribute(
        "data-load-status",
        "unavailable",
      );
    });
    expect(screen.getByTestId("play-threat-mechanics-section")).toBeInTheDocument();
    expect(document.querySelector("[data-statblock-renderer]")).toBeNull();
  });
});
