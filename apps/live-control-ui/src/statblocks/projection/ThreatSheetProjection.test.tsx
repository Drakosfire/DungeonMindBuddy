import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphReferenceProjectionBinding } from "../../graphReference/types";
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
      expect(screen.getByLabelText("Compact mechanics summary")).toBeInTheDocument();
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

    const projection = screen.getByTestId("threat-sheet-projection");
    expect(projection).toHaveAttribute("data-glance", "true");
    expect(screen.getByRole("heading", { level: 3, name: "Tripod Null-Calf" })).toBeInTheDocument();
    expect(projection).toHaveTextContent("A three-legged aberration.");
    expect(projection).not.toHaveTextContent(/^Threat$/m);
    expect(screen.queryByText("Threat · Creature")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Compact mechanics summary")).toHaveTextContent(/AC|HP|CR|Speed/i);

    const inspect = screen.getByText("Inspect proof and tools").closest("details");
    expect(inspect).toBeInstanceOf(HTMLDetailsElement);
    expect(inspect).not.toHaveAttribute("open");
    expect(inspect).toContainElement(screen.getByTestId("threat-sheet-binding-summary"));
    expect(screen.getByTestId("threat-sheet-binding-summary")).toHaveTextContent("1 available");
    expect(screen.getByTestId("threat-sheet-binding-summary")).toHaveTextContent("disposition");

    // Campaign glance must not lead with ledger disposition / digests outside inspect.
    const visibleCue = projection.textContent ?? "";
    const inspectText = inspect?.textContent ?? "";
    const outsideInspect = visibleCue.replace(inspectText, "");
    expect(outsideInspect).not.toMatch(/disposition/i);
    expect(outsideInspect).not.toMatch(/sha256:/i);
    expect(outsideInspect).not.toMatch(/Mechanics bindings:/i);
  });

  it("keeps multi-binding glance honest without choosing a first winner", async () => {
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
            {
              relationshipEdgeId: "edge-2",
              bindingId: "bind-2",
              bindingRole: "phase",
              threatNodeId: "threat:tripod-null-calf",
              resourceNodeId: "sb_000002",
              provider: "dungeonmind",
              statblockId: "sb_000002",
              revisionId: revision.revision_id,
              definitionDigest: revision.definition_digest,
              hydrationStatus: "available",
              binding: null,
              revision,
              message: null,
            },
          ],
          mechanicsDisposition: "partial",
        },
      ],
      diagnostics: [],
      message: null,
    });

    render(<ThreatSheetProjection resolution={threatResolution()} glanceOnly />);

    await waitFor(() => {
      expect(screen.getByText(/2 exact bindings/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("Compact mechanics summary")).not.toBeInTheDocument();
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

  it("does not commit a stale relationship after the selected Threat changes", async () => {
    const relationship = {
      edgeId: "edge-inn",
      sourceNodeId: "threat:tripod-null-calf",
      targetNodeId: "location-inn",
      predicate: "guards",
      label: "Inn",
      direction: "outgoing" as const,
      sessionIds: [],
      sourceDomains: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
      activeContributionIds: [],
    };
    const responseFor = (
      nodeId: string,
      label: string,
      relationships: typeof relationship[] = [],
    ) => ({
      schema: "dmb_threat_query_hydration_response_v1" as const,
      worldId: scope.worldId,
      campaignId: scope.campaignId,
      scopeMode: scope.scopeMode,
      revisionId: scope.revisionId,
      queryText: nodeId,
      resultLabel: "threat_query_hydration_ok" as const,
      hits: [
        {
          threat: {
            nodeId,
            label,
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
          relationships,
          bindings: [],
          mechanicsDisposition: "no_binding" as const,
        },
      ],
      diagnostics: [],
      message: null,
    });
    let resolveRelationship: ((value: ReturnType<typeof threatResolution>) => void) | undefined;
    const deferredRelationship = new Promise<ReturnType<typeof threatResolution>>((resolve) => {
      resolveRelationship = resolve;
    });
    const openResolvedReference = vi.fn();
    const binding: GraphReferenceProjectionBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(() => deferredRelationship),
      openResolvedReference,
      openTool: vi.fn(),
    };
    vi.mocked(postThreatQueryHydration)
      .mockResolvedValueOnce(responseFor("threat:tripod-null-calf", "Tripod Null-Calf", [relationship]))
      .mockResolvedValueOnce(responseFor("threat:other", "Other Threat"));

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
    const user = userEvent.setup();
    const { rerender } = render(
      <ThreatSheetProjection
        resolution={firstResolution}
        graphReferenceBinding={binding}
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Inn.*guards/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /Inn.*guards/i }));
    rerender(
      <ThreatSheetProjection
        resolution={secondResolution}
        graphReferenceBinding={binding}
      />,
    );
    await waitFor(() => {
      expect(postThreatQueryHydration).toHaveBeenCalledTimes(2);
    });

    await act(async () => {
      resolveRelationship?.(threatResolution());
      await deferredRelationship;
    });
    expect(openResolvedReference).not.toHaveBeenCalled();
  });

  it("does not call openResolvedReference after unmount when deferred relationship resolves", async () => {
    const relationship = {
      edgeId: "edge-inn",
      sourceNodeId: "threat:tripod-null-calf",
      targetNodeId: "location-inn",
      predicate: "guards",
      label: "Inn",
      direction: "outgoing" as const,
      sessionIds: [],
      sourceDomains: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
      activeContributionIds: [],
    };
    let resolveRelationship: ((value: ReturnType<typeof threatResolution>) => void) | undefined;
    const deferredRelationship = new Promise<ReturnType<typeof threatResolution>>((resolve) => {
      resolveRelationship = resolve;
    });
    const openResolvedReference = vi.fn();
    const binding: GraphReferenceProjectionBinding = {
      resolverState: "ready",
      resolveRelationship: vi.fn(() => deferredRelationship),
      openResolvedReference,
      openTool: vi.fn(),
    };
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
          relationships: [relationship],
          bindings: [],
          mechanicsDisposition: "no_binding",
        },
      ],
      diagnostics: [],
      message: null,
    });

    const user = userEvent.setup();
    const { unmount } = render(
      <ThreatSheetProjection
        resolution={threatResolution()}
        graphReferenceBinding={binding}
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Inn.*guards/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /Inn.*guards/i }));
    unmount();

    await act(async () => {
      resolveRelationship?.(threatResolution());
      await deferredRelationship;
    });
    expect(openResolvedReference).not.toHaveBeenCalled();
  });

  it("renders campaign full statblock chrome when expanded", async () => {
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

    render(<ThreatSheetProjection resolution={threatResolution()} glanceOnly={false} />);

    await waitFor(() => {
      expect(document.querySelector("[data-statblock-renderer]")).toHaveAttribute(
        "data-chrome",
        "campaign",
      );
    });
    expect(screen.getByTestId("threat-sheet-projection")).toHaveAttribute("data-glance", "false");
    expect(screen.getByText("Threat · full statblock")).toBeInTheDocument();
    const renderer = document.querySelector("[data-statblock-renderer]");
    expect(renderer?.textContent).not.toMatch(/Revision\s+rev_/i);
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
