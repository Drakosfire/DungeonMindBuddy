import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../../api/liveApi";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphReferenceProjectionBinding } from "../../graphReference/types";
import type { GraphReferenceResolution } from "../../graphReference/types";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { PlayGraphObjectSheet } from "./PlayGraphObjectSheet";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    postThreatQueryHydration: vi.fn(),
  };
});

import { postThreatQueryHydration } from "../../api/liveApi";

const revision = revisionFixture as StatblockRevisionResourceV1;
const scopeG1 = {
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  scopeMode: "world" as const,
  revisionId: "rev-g1",
};

function graphResolution(input: {
  nodeId: string;
  label: string;
  kind: string;
  role?: string;
  graphScope?: typeof scopeG1;
  relationships?: GraphReferenceResolution extends { kind: "resolved_graph" }
    ? Extract<GraphReferenceResolution, { kind: "resolved_graph" }>["graphObject"]["relationships"]
    : never;
}): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  const graphObject = buildGraphObjectCardFromNodeView({
    node_id: input.nodeId,
    label: input.label,
    kind: input.kind,
    role: input.role ?? (input.kind === "threat" ? "creature" : "place"),
    aliases: [],
    source_domains: input.kind === "threat" ? ["recap"] : [],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    summary: `${input.label} summary.`,
  });
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${input.nodeId}`,
    reference: null,
    graphNodeId: input.nodeId,
    graphObject: {
      ...graphObject,
      relationships: input.relationships ?? graphObject.relationships,
      details: {
        ...graphObject.details,
        sourceDomains: input.kind === "threat" ? ["recap"] : [],
        evidenceCount: input.kind === "threat" ? 1 : 0,
        sourceAnchorText: input.kind === "threat" ? "the tripod calf" : null,
      },
    },
    graphScope: input.graphScope ?? scopeG1,
    projectionState: "ready",
    message: "Resolved.",
  };
}

function hydrationOk(nodeId: string) {
  return {
    schema: "dmb_threat_query_hydration_response_v1" as const,
    worldId: scopeG1.worldId,
    campaignId: scopeG1.campaignId,
    scopeMode: scopeG1.scopeMode,
    revisionId: scopeG1.revisionId,
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

describe("PlayGraphObjectSheet", () => {
  beforeEach(() => {
    vi.mocked(postThreatQueryHydration).mockReset();
  });

  it("does not request mechanics for an ordinary non-Threat object", () => {
    render(
      <PlayGraphObjectSheet
        resolution={graphResolution({ nodeId: "npc:mira", label: "Mira", kind: "npc" })}
      />,
    );
    expect(postThreatQueryHydration).not.toHaveBeenCalled();
    expect(screen.getByTestId("play-graph-object-sheet-world")).toHaveTextContent("Mira");
    expect(screen.queryByTestId("play-threat-mechanics-section")).not.toBeInTheDocument();
  });

  it("keeps World, Source, and Runbook context while mechanics load and when they fail", async () => {
    vi.mocked(postThreatQueryHydration).mockRejectedValue(
      new LiveApiError("mechanics service unavailable", 503),
    );
    render(
      <PlayGraphObjectSheet
        resolution={graphResolution({
          nodeId: "threat:tripod-null-calf",
          label: "Tripod Null-Calf",
          kind: "threat",
        })}
        occurrences={[
          {
            graphNodeId: "threat:tripod-null-calf",
            sourceNodeType: "graphNodeReference",
            sceneId: "scene-1",
            beatId: "beat-1",
          },
          {
            graphNodeId: "threat:tripod-null-calf",
            sourceNodeType: "runbookReference",
            sceneId: "scene-1",
            choiceId: "choice-1",
          },
        ]}
      />,
    );

    expect(screen.getByTestId("play-graph-object-sheet-world")).toHaveTextContent("Tripod Null-Calf");
    expect(screen.getByTestId("play-graph-object-sheet-source")).toHaveTextContent("the tripod calf");
    expect(screen.getByTestId("play-graph-object-sheet-runbook")).toHaveTextContent("Beat beat-1");
    const choiceOccurrence = screen.getAllByTestId("play-graph-object-occurrence")[1];
    expect(choiceOccurrence).toHaveAttribute("data-beat-id", "");
    expect(choiceOccurrence).toHaveAttribute("data-choice-id", "choice-1");

    await waitFor(() => {
      expect(screen.getByTestId("threat-sheet-load-status")).toHaveAttribute(
        "data-load-status",
        "unavailable",
      );
    });
    expect(screen.getByTestId("play-graph-object-sheet-world")).toBeInTheDocument();
    expect(screen.getByTestId("play-graph-object-sheet-runbook")).toBeInTheDocument();
  });

  it("passes originating G1 scope when drilling a relationship", async () => {
    vi.mocked(postThreatQueryHydration).mockResolvedValue(
      hydrationOk("threat:tripod-null-calf"),
    );
    const nextResolution = graphResolution({
      nodeId: "threat:other",
      label: "Other Threat",
      kind: "threat",
    });
    const binding: GraphReferenceProjectionBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn().mockResolvedValue(nextResolution),
      openResolvedReference: vi.fn(),
      openTool: vi.fn(),
    };
    const first = graphResolution({
      nodeId: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      relationships: [
        {
          id: "edge-inn",
          label: "Inn",
          predicate: "guards",
          direction: "outgoing",
          targetId: "location-inn",
        },
      ],
    });

    const user = userEvent.setup();
    render(<PlayGraphObjectSheet resolution={first} graphReferenceBinding={binding} />);
    await user.click(screen.getByRole("button", { name: /Inn.*guards/i }));

    await waitFor(() => {
      expect(binding.resolveRelationship).toHaveBeenCalledWith(
        expect.objectContaining({ id: "edge-inn" }),
        scopeG1,
      );
    });
    expect(binding.openResolvedReference).toHaveBeenCalled();
    expect(binding.openTool).not.toHaveBeenCalled();
  });

  it("does not paint a stale relationship resolution after the selected object changes", async () => {
    vi.mocked(postThreatQueryHydration)
      .mockResolvedValueOnce(hydrationOk("threat:tripod-null-calf"))
      .mockResolvedValueOnce(hydrationOk("threat:other"));
    let resolveRelationship: ((value: ReturnType<typeof graphResolution>) => void) | undefined;
    const deferred = new Promise<ReturnType<typeof graphResolution>>((resolve) => {
      resolveRelationship = resolve;
    });
    const openResolvedReference = vi.fn();
    const binding: GraphReferenceProjectionBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(() => deferred),
      openResolvedReference,
      openTool: vi.fn(),
    };
    const first = graphResolution({
      nodeId: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      relationships: [
        {
          id: "edge-inn",
          label: "Inn",
          predicate: "guards",
          direction: "outgoing",
          targetId: "location-inn",
        },
      ],
    });
    const second = graphResolution({
      nodeId: "threat:other",
      label: "Other Threat",
      kind: "threat",
    });

    const user = userEvent.setup();
    const { rerender } = render(
      <PlayGraphObjectSheet resolution={first} graphReferenceBinding={binding} />,
    );
    await user.click(screen.getByRole("button", { name: /Inn.*guards/i }));
    rerender(<PlayGraphObjectSheet resolution={second} graphReferenceBinding={binding} />);

    await act(async () => {
      resolveRelationship?.(first);
      await deferred;
    });
    expect(openResolvedReference).not.toHaveBeenCalled();
  });

  it("does not paint a stale relationship resolution after campaignId or scopeMode changes", async () => {
    vi.mocked(postThreatQueryHydration)
      .mockResolvedValueOnce(hydrationOk("threat:tripod-null-calf"))
      .mockResolvedValueOnce(hydrationOk("threat:tripod-null-calf"));
    let resolveRelationship: ((value: ReturnType<typeof graphResolution>) => void) | undefined;
    const deferred = new Promise<ReturnType<typeof graphResolution>>((resolve) => {
      resolveRelationship = resolve;
    });
    const openResolvedReference = vi.fn();
    const binding: GraphReferenceProjectionBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(() => deferred),
      openResolvedReference,
      openTool: vi.fn(),
    };
    const first = graphResolution({
      nodeId: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      relationships: [
        {
          id: "edge-inn",
          label: "Inn",
          predicate: "guards",
          direction: "outgoing",
          targetId: "location-inn",
        },
      ],
    });
    const sameNodeDifferentCampaign = graphResolution({
      nodeId: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      graphScope: {
        ...scopeG1,
        campaignId: "longmont-c1",
        scopeMode: "campaign",
      },
    });

    const user = userEvent.setup();
    const { rerender } = render(
      <PlayGraphObjectSheet resolution={first} graphReferenceBinding={binding} />,
    );
    await user.click(screen.getByRole("button", { name: /Inn.*guards/i }));
    rerender(
      <PlayGraphObjectSheet
        resolution={sameNodeDifferentCampaign}
        graphReferenceBinding={binding}
      />,
    );

    await act(async () => {
      resolveRelationship?.(first);
      await deferred;
    });
    expect(openResolvedReference).not.toHaveBeenCalled();
  });

  it("does not expose Combat or Plan session actions while inspecting a Threat", async () => {
    vi.mocked(postThreatQueryHydration).mockResolvedValue(
      hydrationOk("threat:tripod-null-calf"),
    );
    render(
      <PlayGraphObjectSheet
        resolution={graphResolution({
          nodeId: "threat:tripod-null-calf",
          label: "Tripod Null-Calf",
          kind: "threat",
        })}
      />,
    );
    await waitFor(() => {
      expect(document.querySelector("[data-statblock-renderer]")).toBeTruthy();
    });
    expect(screen.queryByText(/add to combat/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/open ingest/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("play-graph-object-sheet")).toHaveAttribute(
      "data-revision-id",
      "rev-g1",
    );
  });
});
