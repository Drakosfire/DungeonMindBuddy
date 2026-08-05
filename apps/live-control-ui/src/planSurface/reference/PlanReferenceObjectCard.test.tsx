import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { ReactElement } from "react";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import type { PlanReferenceProjectionBinding } from "../projection/projectionBindings";
import { AgentInteractionProjectionTestHost } from "../projection/projectionTestHost";
import { useProjection } from "../projection/projectionContext";
import type { SurfaceConfig } from "../types";
import { PlanReferenceObjectCard } from "./PlanReferenceObjectCard";
import { PlanReferenceProjectionBinding as PlanReferenceProjectionBindingMount } from "./PlanReferenceProjectionBinding";
import { PlanGraphReferenceResolverProvider } from "./usePlanGraphReferenceResolver";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    postWorldGraphProjection: vi.fn(),
  };
});

import * as liveApi from "../../api/liveApi";
import { FIXTURE_DOC_ID } from "../config/planSessionDescriptor";

const innNode: GraphProjectionNodeView = {
  node_id: "location-inn",
  label: "Inn",
  kind: "location",
  role: "location",
  aliases: ["The Inn"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "Meeting place.",
};

const glowkindleNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  source_domains: ["recap"],
  evidence_badges: [
    {
      evidence_ref_id: "ev-1",
      label: "Session recap mention",
      source_domain: "recap",
      source_artifact_id: "artifact-1",
    },
  ],
  adjacency: [
    {
      edge_id: "edge-1",
      node_id: "location-inn",
      label: "Inn",
      kind: "location",
      predicate: "met at",
      direction: "outgoing",
      related_summary: "Trades herbs.",
      evidence_ref_ids: [],
      source_domains: ["recap"],
      anchored_to_focus_session: true,
      session_ids: ["session-21"],
      source_excerpt: "Glowkindle waved from the inn.",
      source_excerpt_is_full_paragraph: false,
    },
  ],
  anchored_to_focus_session: true,
  summary: "A friendly merchant.",
  source_anchor_text: "Glowkindle waved from the inn.",
};

const lysandraA: GraphProjectionNodeView = {
  ...glowkindleNode,
  node_id: "npc-lysandra-a",
  label: "Lysandra Ironveil",
  aliases: ["Lysandra"],
  adjacency: [],
};

const lysandraB: GraphProjectionNodeView = {
  ...glowkindleNode,
  node_id: "npc-lysandra-b",
  label: "Lysandra of the Gate",
  aliases: ["Lysandra"],
  adjacency: [],
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-21",
  node_views: {
    "npc-glowkindle": glowkindleNode,
    "location-inn": innNode,
    "npc-lysandra-a": lysandraA,
    "npc-lysandra-b": lysandraB,
  },
  focus: {
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  mentions: [],
};

const sessionDescriptor = {
  surfaceId: "plan" as const,
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown" as const,
  planningDocument: {
    documentId: FIXTURE_DOC_ID,
    title: "C2 Session 23 Prep",
    targetRelpath: "corpus/example.md",
    storageKey: "dmb.workspaceDocument.FIXTURE_DOC_ID",
    status: "active", contentStatus: "draft", revision: 1, kind: "plan", campaignId: "longmont-c2", targetSession: 23 as const,
  },
};

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Longmont C2",
    ingestSession: 21,
    liveSession: 22,
  },
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: FIXTURE_DOC_ID },
  theme: {},
  sessionDescriptor,
};

function resolvedGraphFromNode(
  node: GraphProjectionNodeView,
  overrides: Partial<Extract<GraphReferenceResolution, { kind: "resolved_graph" }>> = {},
): GraphReferenceResolution {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: referenceFromGraphNode(node),
    graphObject: buildGraphObjectCardFromNodeView(node),
    graphNodeId: node.node_id,
    projectionState: "ready",
    ...overrides,
  };
}

function renderBare(ui: ReactElement) {
  return render(ui);
}

function PlanReferenceProjectionHarness({
  initialResolution,
}: {
  initialResolution: GraphReferenceResolution;
}) {
  const {
    activeGraphReference,
    graphReferenceProjectionState,
    openGraphReference,
    graphReferenceBinding,
  } = useProjection();

  // Seed only once the surface lease is live: a callback captured before
  // publication is a permanent no-op, so retry until the seed lands.
  useEffect(() => {
    if (activeGraphReference) return;
    openGraphReference({
      resolution: initialResolution,
      projectionState: initialResolution.projectionState ?? "ready",
    });
  }, [activeGraphReference, initialResolution, openGraphReference]);

  if (!activeGraphReference) {
    return <p>Seeding projection…</p>;
  }

  return (
    <PlanReferenceObjectCard
      resolution={activeGraphReference}
      sessionDescriptor={sessionDescriptor}
      projectionState={graphReferenceProjectionState}
      graphReferenceBinding={graphReferenceBinding}
      glanceOnly={false}
    />
  );
}

function renderHarness(initialResolution: GraphReferenceResolution) {
  return render(
    <AgentInteractionProjectionTestHost config={surfaceConfig}>
      <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
        <PlanReferenceProjectionBindingMount />
        <PlanReferenceProjectionHarness initialResolution={initialResolution} />
      </PlanGraphReferenceResolverProvider>
    </AgentInteractionProjectionTestHost>,
  );
}

function renderWithLiveBinding(card: ReactElement) {
  function BoundCard() {
    const { graphReferenceBinding } = useProjection();
    const props = card.props as React.ComponentProps<typeof PlanReferenceObjectCard>;
    return (
      <PlanReferenceObjectCard
        {...props}
        graphReferenceBinding={graphReferenceBinding}
        glanceOnly={false}
      />
    );
  }

  return render(
    <AgentInteractionProjectionTestHost config={surfaceConfig}>
      <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
        <PlanReferenceProjectionBindingMount />
        <BoundCard />
      </PlanGraphReferenceResolverProvider>
    </AgentInteractionProjectionTestHost>,
  );
}

function mockBinding(
  overrides: Partial<PlanReferenceProjectionBinding> = {},
): PlanReferenceProjectionBinding {
  return {
    resolverState: "ready",
    resolveRelationship: vi.fn(),
    openResolvedReference: vi.fn(),
    openTool: vi.fn(),
    ...overrides,
  };
}

describe("PlanReferenceObjectCard", () => {
  beforeEach(() => {
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild", campaignId: "longmont-c2", scopeMode: "campaign", revisionId: "rev-1", headRevisionId: "rev-1",
        isHead: true, focus: { kind: "session", sessionId: "session-21" }, admissibility: "gm",
      },
      summary: { nodeCount: 2, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
      nodes: [
        {
          nodeId: "npc-glowkindle", label: "Glowkindle", kind: "npc", role: "merchant", aliases: ["Glow"],
          sourceDomains: ["recap"], summary: "A friendly merchant.", anchoredToFocusSession: true,
          evidenceBadges: [], adjacency: [], suggestedExpansions: [], evidenceRefIds: [], sourceArtifactIds: [],
        },
        {
          nodeId: "location-inn", label: "Inn", kind: "location", role: "location", aliases: ["The Inn"],
          sourceDomains: ["recap"], summary: "Meeting place.", anchoredToFocusSession: true,
          evidenceBadges: [], adjacency: [], suggestedExpansions: [], evidenceRefIds: [], sourceArtifactIds: [],
        },
        {
          nodeId: "npc-lysandra-a", label: "Lysandra Ironveil", kind: "npc", role: "npc", aliases: ["Lysandra"],
          sourceDomains: ["recap"], summary: "First Lysandra.", anchoredToFocusSession: true,
          evidenceBadges: [], adjacency: [], suggestedExpansions: [], evidenceRefIds: [], sourceArtifactIds: [],
        },
        {
          nodeId: "npc-lysandra-b", label: "Lysandra of the Gate", kind: "npc", role: "npc", aliases: ["Lysandra"],
          sourceDomains: ["recap"], summary: "Second Lysandra.", anchoredToFocusSession: true,
          evidenceBadges: [], adjacency: [], suggestedExpansions: [], evidenceRefIds: [], sourceArtifactIds: [],
        },
      ],
      relationships: [], attributes: [], evidence: [], sourceArtifacts: [], diagnostics: [],
    });
  });

  it("renders GraphObjectCard for graph-node hits", async () => {
    const resolution = resolvedGraphFromNode(glowkindleNode);

    const user = userEvent.setup();
    renderBare(<PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />);

    const card = screen.getByLabelText(/Glowkindle graph object/i);
    expect(card).toHaveClass("graph-object-card");
    expect(within(card).getByRole("heading", { level: 4 })).toHaveTextContent("Glowkindle");
    expect(within(card).getByText(/Also known as: Glow/)).toBeInTheDocument();
    expect(within(card).getByText("A friendly merchant.")).toBeInTheDocument();
    expect(within(card).getByRole("heading", { name: "Related objects" })).toBeInTheDocument();

    expect(within(card).queryByRole("heading", { name: "Actions" })).not.toBeInTheDocument();
    expect(within(card).getByText("Memory tools")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Review memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );
    expect(within(card).getByRole("button", { name: /Inspect source\/evidence/i })).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Open statblock tool/i })).not.toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Open roll table tool/i })).not.toBeInTheDocument();

    await user.click(within(card).getByText("Details"));
    expect(within(card).getByText(/1 evidence badge/)).toBeInTheDocument();
    expect(within(card).queryByText(/Node ID:/)).not.toBeInTheDocument();
    expect(within(card).queryByText("npc-glowkindle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("plan-reference-fallback-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("plan-reference-unresolved-card")).not.toBeInTheDocument();
  });

  it("opens Details when Inspect source/evidence is clicked", async () => {
    const resolution = resolvedGraphFromNode(glowkindleNode);

    const user = userEvent.setup();
    renderBare(<PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />);

    const card = screen.getByLabelText(/Glowkindle graph object/i);
    const details = within(card).getByText("Details").closest("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");

    await user.click(within(card).getByRole("button", { name: /Inspect source\/evidence/i }));
    expect(details).toHaveAttribute("open");
  });

  it("renders Open statblock tool for grounded statblock graph nodes when projection can open tools", async () => {
    const resolution = resolvedGraphFromNode({
      ...glowkindleNode,
      node_id: "statblock-tripod",
      label: "Tripod Null-Calf",
      kind: "statblock",
      role: "statblock",
    });

    const user = userEvent.setup();
    const openTool = vi.fn();
    renderBare(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
        graphReferenceBinding={mockBinding({ openTool })}
      />,
    );

    const card = screen.getByLabelText(/Tripod Null-Calf graph object/i);
    expect(within(card).getByRole("button", { name: "Open statblock tool" })).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Open roll table tool/i })).not.toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Review memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );

    await user.click(within(card).getByRole("button", { name: "Open statblock tool" }));
    expect(openTool).toHaveBeenCalledWith("statblock");
  });

  it("omits Open statblock tool when projection context is unavailable", () => {
    const resolution = resolvedGraphFromNode({
      ...glowkindleNode,
      node_id: "statblock-tripod",
      label: "Tripod Null-Calf",
      kind: "statblock",
      role: "statblock",
    });

    renderBare(<PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />);

    expect(screen.queryByRole("button", { name: "Open statblock tool" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Review memory in \/ingest/i })).toBeInTheDocument();
  });

  it("opens related graph node by targetId and updates the projection rail", async () => {
    const user = userEvent.setup();
    const initialResolution = resolvedGraphFromNode(glowkindleNode);

    renderHarness(initialResolution);

    await waitFor(() => {
      expect(screen.getByLabelText(/Glowkindle graph object/i)).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /Open related object .*Inn/i }),
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/Inn graph object/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/Glowkindle graph object/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/selected object/i)).not.toBeInTheDocument();
  });

  it("does not commit a stale relationship after the selected object changes", async () => {
    let resolveRelationship: ((value: GraphReferenceResolution) => void) | undefined;
    const deferredRelationship = new Promise<GraphReferenceResolution>((resolve) => {
      resolveRelationship = resolve;
    });
    const openResolvedReference = vi.fn();
    const binding = mockBinding({
      resolveRelationship: vi.fn(() => deferredRelationship),
      openResolvedReference,
    });
    const firstResolution = resolvedGraphFromNode(glowkindleNode);
    const secondResolution = resolvedGraphFromNode(innNode);
    const user = userEvent.setup();
    const { rerender } = render(
      <PlanReferenceObjectCard
        resolution={firstResolution}
        sessionDescriptor={sessionDescriptor}
        graphReferenceBinding={binding}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Open related object .*Inn/i }));
    rerender(
      <PlanReferenceObjectCard
        resolution={secondResolution}
        sessionDescriptor={sessionDescriptor}
        graphReferenceBinding={binding}
      />,
    );

    await act(async () => {
      resolveRelationship?.(secondResolution);
      await deferredRelationship;
    });
    expect(openResolvedReference).not.toHaveBeenCalled();
  });

  it("does not call openResolvedReference after unmount when deferred relationship resolves", async () => {
    let resolveRelationship: ((value: GraphReferenceResolution) => void) | undefined;
    const deferredRelationship = new Promise<GraphReferenceResolution>((resolve) => {
      resolveRelationship = resolve;
    });
    const openResolvedReference = vi.fn();
    const binding = mockBinding({
      resolveRelationship: vi.fn(() => deferredRelationship),
      openResolvedReference,
    });
    const resolution = resolvedGraphFromNode(glowkindleNode);
    const user = userEvent.setup();
    const { unmount } = render(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
        graphReferenceBinding={binding}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Open related object .*Inn/i }));
    unmount();

    await act(async () => {
      resolveRelationship?.(resolvedGraphFromNode(innNode));
      await deferredRelationship;
    });
    expect(openResolvedReference).not.toHaveBeenCalled();
  });

  it("disables related-object buttons while the card-local graph projection is loading", async () => {
    vi.mocked(liveApi.postWorldGraphProjection).mockImplementation(
      () => new Promise(() => undefined),
    );

    const resolution = resolvedGraphFromNode(glowkindleNode);

    renderWithLiveBinding(
      <PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />,
    );

    const related = await screen.findByRole("button", { name: /Open related object .*Inn/i });
    expect(related).toBeDisabled();
  });

  it("shows ambiguous unresolved card for related-object label collisions", async () => {
    const user = userEvent.setup();
    const nodeWithAmbiguousRelation: GraphProjectionNodeView = {
      ...glowkindleNode,
      adjacency: [
        {
          edge_id: "edge-lysandra",
          node_id: "",
          label: "Lysandra",
          kind: "npc",
          predicate: "knows",
          direction: "outgoing",
          related_summary: null,
          evidence_ref_ids: [],
          source_domains: [],
          anchored_to_focus_session: true,
          session_ids: [],
        },
      ],
    };

    const initialResolution = resolvedGraphFromNode(nodeWithAmbiguousRelation);

    renderHarness(initialResolution);

    await waitFor(() => {
      expect(screen.getByLabelText(/Glowkindle graph object/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Open related object .*Lysandra/i }));

    await waitFor(() => {
      expect(screen.getByTestId("plan-reference-unresolved-card")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /Fix memory in \/ingest/i })).toBeInTheDocument();
    const technical = screen.getByText("Matching graph node ids").closest("details");
    expect(technical).not.toBeNull();
    expect(within(technical!).getByText("npc-lysandra-a")).toBeInTheDocument();
    expect(within(technical!).getByText("npc-lysandra-b")).toBeInTheDocument();
  });

  it("shows unresolved miss card when related target is missing", async () => {
    const user = userEvent.setup();
    const nodeWithMissingRelation: GraphProjectionNodeView = {
      ...glowkindleNode,
      adjacency: [
        {
          edge_id: "edge-missing",
          node_id: "location-missing",
          label: "Missing Gate",
          kind: "location",
          predicate: "near",
          direction: "outgoing",
          related_summary: null,
          evidence_ref_ids: [],
          source_domains: [],
          anchored_to_focus_session: true,
          session_ids: [],
        },
      ],
    };

    const initialResolution = resolvedGraphFromNode(nodeWithMissingRelation);

    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ locations: [] }),
    } as Response);

    renderHarness(initialResolution);

    await waitFor(() => {
      expect(screen.getByLabelText(/Glowkindle graph object/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Open related object .*Missing Gate/i }));

    await waitFor(() => {
      expect(screen.getByTestId("plan-reference-unresolved-card")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /Fix memory in \/ingest/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Glowkindle graph object/i)).not.toBeInTheDocument();
  });

  it("navigates the clicked label-only relationship when multiple empty targetIds share a card", async () => {
    const user = userEvent.setup();
    const nodeWithMultipleLabelOnly: GraphProjectionNodeView = {
      ...glowkindleNode,
      adjacency: [
        {
          edge_id: "edge-lysandra",
          node_id: "",
          label: "Lysandra",
          kind: "npc",
          predicate: "knows",
          direction: "outgoing",
          related_summary: null,
          evidence_ref_ids: [],
          source_domains: [],
          anchored_to_focus_session: true,
          session_ids: [],
        },
        {
          edge_id: "edge-inn",
          node_id: "",
          label: "Inn",
          kind: "location",
          predicate: "met at",
          direction: "outgoing",
          related_summary: null,
          evidence_ref_ids: [],
          source_domains: [],
          anchored_to_focus_session: true,
          session_ids: [],
        },
      ],
    };

    const initialResolution = resolvedGraphFromNode(nodeWithMultipleLabelOnly);

    renderHarness(initialResolution);

    await waitFor(() => {
      expect(screen.getByLabelText(/Glowkindle graph object/i)).toBeInTheDocument();
    });

    // First empty-targetId row is ambiguous Lysandra. Clicking Inn must not first-win that row.
    await user.click(screen.getByRole("button", { name: /Open related object .*Inn/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Inn graph object/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("plan-reference-unresolved-card")).not.toBeInTheDocument();
  });

  it("renders unresolved state for ambiguous graph matches", () => {
    const resolution: GraphReferenceResolution = {
      kind: "unresolved",
      locator: "#dmb-ref:npc:lysandra",
      reference: {
        kind: "ref",
        refType: "npc",
        refId: "lysandra",
        label: "Lysandra Ironveil",
      },
      matchingGraphNodeIds: ["npc-lysandra-a", "npc-lysandra-b"],
      message:
        "Could not uniquely resolve this object from graph memory. Use /ingest to review aliases or identity. Open /ingest to fix memory.",
      projectionState: "ready",
    };

    renderBare(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
      />,
    );

    expect(screen.getByTestId("plan-reference-unresolved-card")).toBeInTheDocument();
    expect(screen.getByText(/Could not uniquely resolve this object from graph memory/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Fix memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );
    expect(screen.queryByLabelText(/graph object/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/selected object/i)).not.toBeInTheDocument();
  });

  it("renders corpus fallback as fallback, not authoritative graph memory", () => {
    const resolution: GraphReferenceResolution = {
      kind: "resolved_corpus_fallback",
      locator: "#dmb-ref:location:north-reach-gate",
      reference: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      fallback: {
        status: "resolved",
        ref: {
          kind: "ref",
          refType: "location",
          refId: "north-reach-gate",
          label: "North Reach Gate",
        },
        source: "location-index",
        item: {
          title: "North Reach Gate",
          settlement: "Mireward Reach",
          corpus_display_path: "corpus/locations/north_reach_gate.md",
        },
        sourcePath: "corpus/locations/north_reach_gate.md",
        message: "Resolved from live location index.",
      },
      projectionState: "ready",
    };

    renderBare(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
      />,
    );

    expect(screen.getByTestId("plan-reference-fallback-banner")).toHaveTextContent(
      /Graph memory did not resolve this yet/i,
    );
    expect(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).toBeInTheDocument();
    expect(within(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).getByText(
      "Location reference resolved from corpus index.",
    )).toBeInTheDocument();
    expect(
      within(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).getByRole("link", {
        name: /Review memory in \/ingest/i,
      }),
    ).toHaveAttribute("href", "/ingest?campaign=longmont-c2&session=session-21");
    expect(
      within(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).getByText(
        "Freshness: Corpus index fallback",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/selected object/i)).not.toBeInTheDocument();
  });

  it("shows projection-unavailable note on unresolved cards", () => {
    const resolution: GraphReferenceResolution = {
      kind: "unresolved",
      locator: "#dmb-ref:npc:missing",
      reference: {
        kind: "ref",
        refType: "npc",
        refId: "missing",
        label: "Missing NPC",
      },
      message: "Could not resolve this reference from graph memory or corpus indexes. Open /ingest to fix memory.",
      projectionState: "unavailable",
    };

    renderBare(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
        projectionState="unavailable"
      />,
    );

    expect(screen.getByText(/World Graph projection is unavailable/i)).toBeInTheDocument();
  });

  it("PR380B: delegates graph-native rendering to GraphObjectProjectionCard", () => {
    expect(
      existsSync(
        path.join(
          path.dirname(fileURLToPath(import.meta.url)),
          "../../graphObjectCard/GraphObjectProjectionCard.tsx",
        ),
      ),
    ).toBe(true);
  });
});
