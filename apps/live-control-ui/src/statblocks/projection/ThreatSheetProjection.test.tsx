import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphReferenceResolution } from "../../graphReference/types";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { ThreatSheetProjection } from "./ThreatSheetProjection";

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

function threatResolution(): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: "dmb-node:threat:tripod-null-calf",
    reference: null,
    graphNodeId: "threat:tripod-null-calf",
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      role: "creature",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: "A three-legged aberration.",
    }),
    graphScope: scope,
    projectionState: "ready",
    message: "Resolved graph node Tripod Null-Calf.",
  };
}

describe("ThreatSheetProjection", () => {
  beforeEach(() => {
    vi.mocked(postThreatQueryHydration).mockReset();
  });

  it("loads exact mechanics for the selected Threat tuple", async () => {
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
            summary: "A three-legged aberration.",
          },
          matchReasons: ["exact_node_id"],
          relationships: [],
          bindings: [
            {
              relationshipEdgeId: "edge-1",
              bindingId: "bind-1",
              bindingRole: "primary",
              threatNodeId: "threat:tripod-null-calf",
              resourceNodeId: "sb_000001",
              provider: "dungeonmind",
              statblockId: "sb_000001",
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

    render(<ThreatSheetProjection resolution={threatResolution()} glanceOnly />);

    await waitFor(() => {
      expect(screen.getByTestId("threat-sheet-binding-summary")).toHaveTextContent("1 available");
    });

    expect(postThreatQueryHydration).toHaveBeenCalledWith({
      schema: "dmb_threat_query_hydration_request_v1",
      worldId: scope.worldId,
      campaignId: scope.campaignId,
      scopeMode: scope.scopeMode,
      revisionPin: scope.revisionId,
      queryText: "threat:tripod-null-calf",
      focusNodeIds: ["threat:tripod-null-calf"],
      maxHits: 64,
      includeMechanics: true,
    });
    expect(screen.getByLabelText("Compact mechanics summary")).toBeInTheDocument();
  });

  it("does not commit a stale response after the selection tuple changes", async () => {
    let resolveFirst: ((value: unknown) => void) | undefined;
    const first = new Promise((resolve) => {
      resolveFirst = resolve;
    });

    vi.mocked(postThreatQueryHydration)
      .mockImplementationOnce(() => first as never)
      .mockResolvedValueOnce({
        schema: "dmb_threat_query_hydration_response_v1",
        worldId: scope.worldId,
        campaignId: scope.campaignId,
        scopeMode: scope.scopeMode,
        revisionId: scope.revisionId,
        queryText: "threat:other",
        resultLabel: "threat_query_hydration_ok",
        hits: [
          {
            threat: {
              nodeId: "threat:other",
              label: "Other Threat",
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
            bindings: [],
            mechanicsDisposition: "no_binding",
          },
        ],
        diagnostics: [],
        message: null,
      });

    const firstResolution = threatResolution();
    const secondResolution = {
      ...firstResolution,
      graphNodeId: "threat:other",
      graphObject: {
        ...firstResolution.graphObject,
        id: "threat:other",
        label: "Other Threat",
      },
    };

    const { rerender } = render(<ThreatSheetProjection resolution={firstResolution} glanceOnly />);
    rerender(<ThreatSheetProjection resolution={secondResolution} glanceOnly />);

    await waitFor(() => {
      expect(postThreatQueryHydration).toHaveBeenCalledTimes(2);
    });

    resolveFirst?.({
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
          bindings: [],
          mechanicsDisposition: "no_binding",
        },
      ],
      diagnostics: [],
      message: null,
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 3, name: "Other Threat" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { level: 3, name: "Tripod Null-Calf" })).not.toBeInTheDocument();
  });

  it("fails closed when exact graph scope is missing", () => {
    render(
      <ThreatSheetProjection
        resolution={{
          ...threatResolution(),
          graphScope: null,
        }}
        glanceOnly
      />,
    );

    expect(screen.getByTestId("threat-sheet-load-status")).toHaveAttribute(
      "data-load-status",
      "integrity_failure",
    );
    expect(postThreatQueryHydration).not.toHaveBeenCalled();
  });
});
