import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ExistingObjectResolverPanel,
  buildQueryOnlySelectedNode,
  buildResolverSelectedNode,
  QUERY_SEARCH_NODE_ID,
} from "./ExistingObjectResolverPanel";
import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
} from "../../api/types";
import { resolveGraphReviewExistingObjectCandidates } from "../../api/liveApi";
import type { SearchMergeStageInput } from "./graphExistingObjectIdentityWorkbench";

vi.mock("../../api/liveApi", () => ({
  resolveGraphReviewExistingObjectCandidates: vi.fn(),
}));

const node: GraphProjectionNodeView = {
  node_id: "node_tripod",
  label: "Tripod Null-Calf",
  kind: "threat",
  role: "siege scout",
  aliases: [],
  source_domains: ["live_projection"],
  evidence_badges: [
    {
      evidence_ref_id: "ev-1",
      source_artifact_id: "a",
      source_domain: "recap",
      evidence_role: "mention",
      is_focus_session_evidence: true,
      can_open_source: true,
      can_highlight_span: true,
    },
  ],
  adjacency: [
    {
      edge_id: "e1",
      node_id: "north_gate",
      label: "North Gate",
      kind: "location",
      predicate: "threatens",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["live_projection"],
      evidence_ref_ids: [],
    },
  ],
  anchored_to_focus_session: true,
  summary: "Siege scout and gate-pressure monster.",
};

function renderPanel(overrides: { linkSourceNode?: GraphProjectionNodeView | null } = {}) {
  return render(
    <ExistingObjectResolverPanel
      campaignId="longmont-c1"
      sessionId="session-1"
      laneRole="live"
      linkSourceNode={overrides.linkSourceNode ?? null}
      projectionGraphId="graph-1"
      liveRunManifestPath="runs/manifest.json"
    />,
  );
}

function renderPanelWithLinkSource() {
  return render(
    <ExistingObjectResolverPanel
      campaignId="longmont-c1"
      sessionId="session-1"
      laneRole="live"
      linkSourceNode={node}
      projectionGraphId="graph-1"
      liveRunManifestPath="runs/manifest.json"
    />,
  );
}

function typeSearchQuery(value: string) {
  fireEvent.change(screen.getByPlaceholderText(/PC, party, location/i), {
    target: { value },
  });
}

describe("ExistingObjectResolverPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("builds selected node context with adjacency, evidence, and lane-safe fields", () => {
    expect(buildResolverSelectedNode(node)).toMatchObject({
      node_id: "node_tripod",
      adjacent_labels: ["North Gate"],
      evidence_ref_ids: ["ev-1"],
      source_domains: ["live_projection"],
    });
  });

  it("builds query-only selected node context for text search without a pill", () => {
    expect(buildQueryOnlySelectedNode("Caelynn")).toMatchObject({
      node_id: "__graph_review_query_search__",
      label: "Caelynn",
    });
  });

  it("supports text search without a selected recap pill", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: "__graph_review_query_search__",
      selected_label: "Caelynn",
      candidates: [],
      warnings: [],
    });
    render(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="live"
        projectionGraphId="graph-1"
        liveRunManifestPath="runs/manifest.json"
      />,
    );
    fireEvent.change(screen.getByPlaceholderText(/PC, party, location/i), {
      target: { value: "Caelynn" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    await waitFor(() =>
      expect(resolveGraphReviewExistingObjectCandidates).toHaveBeenCalled(),
    );
    expect(
      vi.mocked(resolveGraphReviewExistingObjectCandidates).mock.calls[0][0],
    ).toMatchObject({
      query: "Caelynn",
      selected_node: {
        node_id: "__graph_review_query_search__",
        label: "Caelynn",
      },
    });
  });

  it("uses query-only context for search regardless of link source", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: "__graph_review_query_search__",
      selected_label: "Lysandro",
      candidates: [],
      warnings: [],
    });
    renderPanelWithLinkSource();
    fireEvent.change(screen.getByPlaceholderText(/PC, party, location/i), {
      target: { value: "Lysandro" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(
      screen.getByText("Searching campaign graph scopes…"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(resolveGraphReviewExistingObjectCandidates).toHaveBeenCalled(),
    );
    expect(
      vi.mocked(resolveGraphReviewExistingObjectCandidates).mock.calls[0][0],
    ).toMatchObject({
      lane_role: "live",
      query: "Lysandro",
      selected_node: {
        node_id: "__graph_review_query_search__",
        label: "Lysandro",
      },
    });
  });

  it("preserves gold lane context without sending a live manifest path", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: "node_tripod",
      selected_label: "Tripod Null-Calf",
      candidates: [],
      warnings: [],
    });
    render(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="gold"
        projectionGraphId="gold-graph"
        liveRunManifestPath={null}
      />,
    );
    expect(
      screen.getByText(/Search across current recap, authored memory/i),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText(/PC, party, location/i), {
      target: { value: "Tripod Null-Calf" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    await waitFor(() =>
      expect(resolveGraphReviewExistingObjectCandidates).toHaveBeenCalled(),
    );
    expect(
      vi.mocked(resolveGraphReviewExistingObjectCandidates).mock.calls[0][0],
    ).toMatchObject({
      lane_role: "gold",
      projection_graph_id: "gold-graph",
      live_run_manifest_path: null,
    });
  });

  it("renders candidate cards with stage link intent when callback is provided", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: "node_tripod",
      selected_label: "Tripod Null-Calf",
      warnings: [],
      candidates: [
        {
          candidate_id: "gold-tripod",
          label: "Tripod Null-Calf",
          kind: "Threat",
          role: "Siege scout",
          confidence: "high",
          score: 0.92,
          reason: "exact label match, same kind",
          source: "gold_fixture",
          suggested_action: "link_existing_later",
          existing_object_ref: {
            source: "gold_fixture",
            object_id: "gold-tripod",
          },
          matched_features: ["exact label match", "same kind"],
          graph_scope: "current_recap_projection",
          source_label: "Current recap",
        },
      ],
    });
    const { container } = renderPanel();
    typeSearchQuery("Tripod Null-Calf");
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(
      await screen.findByText("Likely existing objects"),
    ).toBeInTheDocument();
    const card = screen
      .getByRole("heading", { name: /Tripod Null-Calf/i, level: 6 })
      .closest("article");
    expect(card).toBeTruthy();
    expect(
      within(card!).getByText(/High confidence · 0.92/i),
    ).toBeInTheDocument();
    expect(
      within(card!).getAllByText(/exact label match/i).length,
    ).toBeGreaterThan(0);
    expect(within(card!).getByText("gold-tripod")).toBeInTheDocument();
    expect(within(card!).getByText(/gold-tripod · Current recap/i)).toBeInTheDocument();
    expect(
      within(card!).getAllByText(/exact label match, same kind/i).length,
    ).toBeGreaterThan(0);
    expect(within(card!).getByText(/Link existing later/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Review candidate" }),
    ).not.toBeInTheDocument();
    expect(container).not.toHaveTextContent(/Save|Link now|Merge/);
  });

  it("shows Stage link intent only when local authoring callback is provided", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: "node_tripod",
      selected_label: "Tripod Null-Calf",
      warnings: [],
      candidates: [
        {
          candidate_id: "gold-tripod",
          label: "Tripod Null-Calf",
          kind: "Threat",
          role: "Siege scout",
          confidence: "high",
          score: 0.92,
          reason: "exact label match",
          source: "gold_fixture",
          suggested_action: "link_existing_later",
          existing_object_ref: {
            source: "gold_fixture",
            object_id: "gold-tripod",
          },
          matched_features: [],
          graph_scope: "current_recap_projection",
          source_label: "Current recap",
        },
      ],
    });
    const onStageLinkIntent = vi.fn();
    const onStageLinkIntentComplete = vi.fn();
    const { rerender } = render(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="live"
        projectionGraphId="graph-1"
        liveRunManifestPath="runs/manifest.json"
      />,
    );
    typeSearchQuery("Tripod Null-Calf");
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(
      await screen.findByText("Likely existing objects"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stage link intent" }),
    ).not.toBeInTheDocument();

    rerender(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="live"
        linkSourceNode={node}
        projectionGraphId="graph-1"
        liveRunManifestPath="runs/manifest.json"
        onStageLinkIntent={onStageLinkIntent}
        onStageLinkIntentComplete={onStageLinkIntentComplete}
      />,
    );
    typeSearchQuery("Tripod Null-Calf");
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    const stageButton = await screen.findByRole("button", {
      name: "Stage link intent",
    });
    fireEvent.click(stageButton);
    expect(onStageLinkIntent).toHaveBeenCalledWith(
      expect.objectContaining({ candidate_id: "gold-tripod" }),
    );
    expect(onStageLinkIntentComplete).toHaveBeenCalled();
    expect(
      screen.getByText(/Link intent staged locally/i),
    ).toBeInTheDocument();
  });

  it("renders empty and error states", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValueOnce(
      {
        schema: "dmb_graph_review_existing_object_resolver_response_v1",
        campaign_id: "longmont-c1",
        session_id: "session-1",
        selected_node_id: "node_tripod",
        selected_label: "Tripod Null-Calf",
        candidates: [],
        warnings: [],
      },
    );
    const { rerender } = renderPanel();
    typeSearchQuery("Tripod Null-Calf");
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(
      await screen.findByText(/No likely existing objects found/i),
    ).toBeInTheDocument();
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockRejectedValueOnce(
      new Error("boom"),
    );
    rerender(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="live"
      />,
    );
    typeSearchQuery("Tripod Null-Calf");
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });

  const lysandraCandidates: GraphReviewExistingObjectCandidate[] = [
    {
      candidate_id: "node:lysandra",
      label: "Lysandra",
      kind: "npc",
      role: "captain",
      confidence: "high",
      score: 0.91,
      reason: "label match in recap",
      source: "live_projection",
      suggested_action: "manual_review_needed",
      matched_features: ["label"],
      graph_scope: "current_recap_projection",
      source_label: "Current recap",
      aliases: ["Lysandra"],
    },
    {
      candidate_id: "party:captain_lysandra_ironveil",
      label: "Captain Lysandra Ironveil",
      kind: "character",
      role: "companion",
      confidence: "high",
      score: 0.95,
      reason: "alias match in party registry",
      source: "union_supergraph",
      suggested_action: "link_existing_later",
      matched_features: ["alias", "label"],
      graph_scope: "party_pc",
      source_label: "Party / PCs",
      aliases: ["Lysandra", "Captain Ironveil"],
    },
  ];

  async function renderLysandraSearch(
    overrides: {
      onStageSearchMerge?: (input: SearchMergeStageInput) => boolean;
      onStageSearchMergeComplete?: () => void;
    } = {},
  ) {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: QUERY_SEARCH_NODE_ID,
      selected_label: "Lysandra",
      warnings: [],
      candidates: lysandraCandidates,
    });
    render(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="live"
        projectionGraphId="graph-1"
        liveRunManifestPath="runs/manifest.json"
        onStageSearchMerge={overrides.onStageSearchMerge ?? vi.fn(() => true)}
        onStageSearchMergeComplete={overrides.onStageSearchMergeComplete}
      />,
    );
    typeSearchQuery("Lysandra");
    fireEvent.click(screen.getByRole("button", { name: "Find existing object" }));
    await screen.findByText("Likely existing objects");
  }

  it("renders candidate ids and identity actions without a recap pill", async () => {
    await renderLysandraSearch();
    expect(screen.getByText("node:lysandra")).toBeInTheDocument();
    expect(screen.getByText("party:captain_lysandra_ironveil")).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: "Set as canonical" }),
    ).toHaveLength(2);
    expect(
      screen.getAllByRole("button", { name: "Select as duplicate" }),
    ).toHaveLength(2);
  });

  it("stages merge proposal through overlay search merge callback", async () => {
    const onStageSearchMerge = vi.fn(() => true);
    const onStageSearchMergeComplete = vi.fn();
    await renderLysandraSearch({ onStageSearchMerge, onStageSearchMergeComplete });

    fireEvent.click(
      screen.getAllByRole("button", { name: "Set as canonical" })[1],
    );
    fireEvent.click(
      screen.getAllByRole("button", { name: "Select as duplicate" })[0],
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Stage merge into canonical" }),
    );

    expect(onStageSearchMerge).toHaveBeenCalledWith(
      expect.objectContaining({
        mergeReason:
          "Search result identity merge: node:lysandra → party:captain_lysandra_ironveil",
        survivorObjectRef: expect.objectContaining({
          nodeId: "party:captain_lysandra_ironveil",
        }),
        mergedObjectRefs: [
          expect.objectContaining({ nodeId: "node:lysandra" }),
        ],
      }),
    );
    expect(onStageSearchMergeComplete).toHaveBeenCalled();
    expect(
      screen.getByText(/Identity merge staged in authored overlay/i),
    ).toBeInTheDocument();
  });

  it("prevents canonical candidate from also being duplicate", async () => {
    await renderLysandraSearch();
    const canonicalButtons = screen.getAllByRole("button", {
      name: "Set as canonical",
    });
    fireEvent.click(canonicalButtons[1]);
    expect(
      screen.getAllByRole("button", { name: "Clear canonical" }),
    ).toHaveLength(1);
    const duplicateButtons = screen.getAllByRole("button", {
      name: "Select as duplicate",
    });
    expect(duplicateButtons[0]).not.toBeDisabled();
    expect(duplicateButtons[1]).toBeDisabled();
  });

  it("shows compare panel when one canonical and one duplicate are selected", async () => {
    await renderLysandraSearch();
    fireEvent.click(
      screen.getAllByRole("button", { name: "Set as canonical" })[1],
    );
    fireEvent.click(
      screen.getAllByRole("button", { name: "Select as duplicate" })[0],
    );
    expect(screen.getByText("Compare selected identity")).toBeInTheDocument();
    expect(screen.getByText("Canonical / survivor")).toBeInTheDocument();
    expect(screen.getByText("Duplicate / merge away")).toBeInTheDocument();
  });

  it("reports duplicate staged merge pair without creating another proposal", async () => {
    const onStageSearchMerge = vi.fn(() => false);
    await renderLysandraSearch({ onStageSearchMerge });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Set as canonical" })[1],
    );
    fireEvent.click(
      screen.getAllByRole("button", { name: "Select as duplicate" })[0],
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Stage merge into canonical" }),
    );
    expect(onStageSearchMerge).toHaveBeenCalledTimes(1);
    expect(
      screen.getByText(/already staged in the authored overlay tray/i),
    ).toBeInTheDocument();
  });
});
