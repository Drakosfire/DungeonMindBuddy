import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  GraphProjectionNodeView,
  WorldGraphProjection,
  WorldGraphProjectionNodeView,
} from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { AgentInteractionProjectionTestHost } from "../projection/projectionTestHost";
import { useProjection } from "../projection/projectionContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import type { SurfaceConfig } from "../types";
import { GraphObjectDogfoodPanel } from "./GraphObjectDogfoodPanel";
import { graphObjectDogfoodStorageKey } from "./graphObjectDogfoodStorage";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    postWorldGraphProjection: vi.fn(),
  };
});

import * as liveApi from "../../api/liveApi";

const thinNode: GraphProjectionNodeView = {
  node_id: "npc-thin",
  label: "Thin NPC",
  kind: "npc",
  role: "npc",
  aliases: [],
  source_domains: [],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: null,
};

const richNode: GraphProjectionNodeView = {
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

function toWorldGraphNode(node: GraphProjectionNodeView): WorldGraphProjectionNodeView {
  return {
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    aliases: node.aliases,
    sourceDomains: node.source_domains,
    evidenceBadges: node.evidence_badges.map((badge) => ({
      evidenceRefId: badge.evidence_ref_id,
      sourceArtifactId: badge.source_artifact_id ?? "",
      sourceDomain: badge.source_domain ?? "recap",
      evidenceRole: "mention",
      isFocusSessionEvidence: true,
      canOpenSource: true,
      canHighlightSpan: true,
      label: badge.label ?? "",
      sessionId: "session-21",
      sourceSpanRefId: null,
    })),
    adjacency: node.adjacency.map((candidate) => ({
      edgeId: candidate.edge_id,
      nodeId: candidate.node_id,
      label: candidate.label,
      kind: candidate.kind,
      predicate: candidate.predicate,
      direction: candidate.direction ?? "outgoing",
      anchoredToFocusSession: candidate.anchored_to_focus_session,
      sourceDomains: candidate.source_domains,
      evidenceRefIds: candidate.evidence_ref_ids,
      sessionIds: candidate.session_ids,
      relatedSummary: candidate.related_summary,
      sourceExcerpt: candidate.source_excerpt,
    })),
    suggestedExpansions: [],
    evidenceRefIds: node.evidence_badges.map((badge) => badge.evidence_ref_id),
    sourceArtifactIds: node.evidence_badges
      .map((badge) => badge.source_artifact_id)
      .filter((value): value is string => Boolean(value)),
    anchoredToFocusSession: node.anchored_to_focus_session,
    summary: node.summary,
  };
}

const projection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    revisionId: "rev-1",
    headRevisionId: "rev-1",
    isHead: true,
    focus: { kind: "session", sessionId: "session-21" },
    admissibility: "gm",
  },
  summary: {
    nodeCount: 3,
    relationshipCount: 0,
    attributeCount: 0,
    evidenceCount: 0,
    sourceArtifactCount: 0,
    projectionTruncated: false,
  },
  nodes: [richNode, thinNode, innNode].map(toWorldGraphNode),
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

function graphResolutionFromNode(node: GraphProjectionNodeView): GraphReferenceResolution {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: referenceFromGraphNode(node),
    graphObject: buildGraphObjectCardFromNodeView(node),
    graphNodeId: node.node_id,
    projectionState: "ready",
    message: `Resolved graph node ${node.label}.`,
  };
}

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    liveSession: 22,
    ingestSession: 21,
    headerLabel: sessionDescriptor.planningDocument.title,
  },
  sessionDescriptor,
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: sessionDescriptor.planningDocument.documentId },
  theme: {},
};

function seedDogfoodList(nodeIds: string[]) {
  localStorage.setItem(
    graphObjectDogfoodStorageKey(sessionDescriptor),
    JSON.stringify({
      schema: "dmb_graph_object_dogfood_v1",
      addedNodeIds: nodeIds,
      viewedNodeIds: [],
      usefulnessByNodeId: {},
      notesByNodeId: {},
    }),
  );
}

function ActiveTitleProbe() {
  const { active, activeGraphReference } = useProjection();
  return (
    <div data-testid="active-probe">
      <span data-testid="active-title">{active?.title ?? ""}</span>
      <span data-testid="active-kind">{activeGraphReference?.kind ?? ""}</span>
      <span data-testid="active-node">{activeGraphReference?.graphNodeId ?? ""}</span>
    </div>
  );
}

function renderPanel() {
  return render(
    <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
      <AgentInteractionProjectionTestHost config={surfaceConfig}>
        <GraphObjectDogfoodPanel sessionDescriptor={sessionDescriptor} />
        <ActiveTitleProbe />
      </AgentInteractionProjectionTestHost>
    </PlanGraphReferenceResolverProvider>,
  );
}

describe("GraphObjectDogfoodPanel", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(liveApi.postWorldGraphProjection).mockReset();
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(projection);
  });

  it("points dogfood toward Edit toolbar search instead of a second browser", async () => {
    renderPanel();

    expect(await screen.findByText(/Edit → World Graph objects/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-dogfood-available")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Search graph")).not.toBeInTheDocument();
    expect(screen.getByText(/No cards on the dogfood list yet/i)).toBeInTheDocument();
  });

  it("adds the currently viewed related card without a duplicate search UI", async () => {
    const user = userEvent.setup();

    function SeedRelatedView({ node }: { node: GraphProjectionNodeView }) {
      const { activeGraphReference, openGraphReference } = useProjection();
      useEffect(() => {
        if (activeGraphReference) return;
        openGraphReference({
          resolution: graphResolutionFromNode(node),
          projectionState: "ready",
        });
      }, [activeGraphReference, node, openGraphReference]);
      return null;
    }

    render(
      <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
        <AgentInteractionProjectionTestHost config={surfaceConfig}>
          <SeedRelatedView node={richNode} />
          <GraphObjectDogfoodPanel sessionDescriptor={sessionDescriptor} />
        </AgentInteractionProjectionTestHost>
      </PlanGraphReferenceResolverProvider>,
    );

    expect(
      await screen.findByText(/Viewing a related card that is not on the dogfood list/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add this card to dogfood list" }));

    const collection = screen.getByTestId("graph-object-dogfood-collection");
    expect(within(collection).getByText("Glowkindle")).toBeInTheDocument();

    const stored = JSON.parse(
      localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor)) ?? "{}",
    );
    expect(stored.addedNodeIds).toEqual(["npc-glowkindle"]);
  });

  it("views a card through the real Plan reference projection path", async () => {
    const user = userEvent.setup();
    seedDogfoodList(["npc-glowkindle"]);
    renderPanel();

    const collection = await screen.findByTestId("graph-object-dogfood-collection");
    await user.click(within(collection).getByRole("button", { name: "View card" }));

    await waitFor(() => {
      expect(screen.getByTestId("active-title")).toHaveTextContent("Glowkindle");
      expect(screen.getByTestId("active-kind")).toHaveTextContent("resolved_graph");
      expect(screen.getByTestId("active-node")).toHaveTextContent("npc-glowkindle");
    });

    const stored = JSON.parse(
      localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor)) ?? "{}",
    );
    expect(stored.viewedNodeIds).toContain("npc-glowkindle");
  });

  it("surfaces thin-card coverage when summary/relationships/evidence are missing", async () => {
    seedDogfoodList(["npc-thin"]);
    renderPanel();

    expect(await screen.findByText(/Thin card/i)).toBeInTheDocument();
    expect(screen.getByText(/Missing: summary/i)).toBeInTheDocument();
  });

  it("removes from dogfood list with local-only copy and no write endpoints", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    seedDogfoodList(["npc-glowkindle"]);
    renderPanel();

    await screen.findByTestId("graph-object-dogfood-collection");
    await user.click(screen.getByRole("button", { name: "Remove from dogfood list" }));

    expect(screen.queryByTestId("graph-object-dogfood-collection")).not.toBeInTheDocument();
    expect(screen.getByText(/No cards on the dogfood list yet/i)).toBeInTheDocument();
    expect(screen.getByText(/Does not delete graph nodes or corpus markdown/i)).toBeInTheDocument();

    const writeCalls = fetchSpy.mock.calls.filter((call) => {
      const init = call[1] as RequestInit | undefined;
      const method = String(init?.method ?? "GET").toUpperCase();
      return method !== "GET" && method !== "HEAD";
    });
    expect(writeCalls).toHaveLength(0);
    fetchSpy.mockRestore();
  });

  it("persists usefulness and notes locally", async () => {
    const user = userEvent.setup();
    seedDogfoodList(["npc-glowkindle"]);
    renderPanel();

    await screen.findByTestId("graph-object-dogfood-collection");
    await user.selectOptions(screen.getByLabelText("Usefulness for Glowkindle"), "useful");
    await user.type(screen.getByLabelText("Notes for Glowkindle"), "Would use at the table.");

    await waitFor(() => {
      const stored = JSON.parse(
        localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor)) ?? "{}",
      );
      expect(stored.usefulnessByNodeId["npc-glowkindle"]).toBe("useful");
      expect(stored.notesByNodeId["npc-glowkindle"]).toContain("Would use at the table.");
    });
  });

  it("clears local dogfood graph state", async () => {
    const user = userEvent.setup();
    seedDogfoodList(["npc-glowkindle"]);
    renderPanel();

    await screen.findByTestId("graph-object-dogfood-collection");
    await user.click(screen.getByRole("button", { name: "Clear graph object dogfood list" }));

    expect(localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor))).toBeNull();
    expect(screen.getByText(/No cards on the dogfood list yet/i)).toBeInTheDocument();
  });
});

describe("GraphObjectDogfoodPanel relationship traversal handoff", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(liveApi.postWorldGraphProjection).mockReset();
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(projection);
  });

  it("does not auto-add a related card opened outside Add", async () => {
    function SeedRelatedView({ node }: { node: GraphProjectionNodeView }) {
      const { activeGraphReference, openGraphReference } = useProjection();
      useEffect(() => {
        if (activeGraphReference) return;
        openGraphReference({
          resolution: graphResolutionFromNode(node),
          projectionState: "ready",
        });
      }, [activeGraphReference, node, openGraphReference]);
      return null;
    }

    render(
      <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
        <AgentInteractionProjectionTestHost config={surfaceConfig}>
          <SeedRelatedView node={innNode} />
          <GraphObjectDogfoodPanel sessionDescriptor={sessionDescriptor} />
        </AgentInteractionProjectionTestHost>
      </PlanGraphReferenceResolverProvider>,
    );

    expect(await screen.findByText(/Viewing a related card that is not on the dogfood list/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-dogfood-collection")).not.toBeInTheDocument();
  });
});
