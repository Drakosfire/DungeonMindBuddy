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
  buildResolverSelectedNode,
} from "./ExistingObjectResolverPanel";
import type { GraphProjectionNodeView } from "../../api/types";
import { resolveGraphReviewExistingObjectCandidates } from "../../api/liveApi";

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

function renderPanel() {
  return render(
    <ExistingObjectResolverPanel
      campaignId="longmont-c1"
      sessionId="session-1"
      laneRole="live"
      selectedNode={node}
      projectionGraphId="graph-1"
      liveRunManifestPath="runs/manifest.json"
    />,
  );
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

  it("calls the resolver with lane role and selected node context", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      selected_node_id: "node_tripod",
      selected_label: "Tripod Null-Calf",
      candidates: [],
      warnings: [],
    });
    renderPanel();
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(
      screen.getByText("Checking same-session graph sources…"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(resolveGraphReviewExistingObjectCandidates).toHaveBeenCalled(),
    );
    expect(
      vi.mocked(resolveGraphReviewExistingObjectCandidates).mock.calls[0][0],
    ).toMatchObject({
      lane_role: "live",
      selected_node: {
        label: "Tripod Null-Calf",
        adjacent_labels: ["North Gate"],
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
        selectedNode={node}
        projectionGraphId="gold-graph"
        liveRunManifestPath={null}
      />,
    );
    expect(
      screen.getByText(/same-session gold\/live graph sources/i),
    ).toBeInTheDocument();
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

  it("renders candidate cards and local review-only selection without write actions", async () => {
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
        },
      ],
    });
    const { container } = renderPanel();
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(
      await screen.findByText("Likely existing objects"),
    ).toBeInTheDocument();
    const card = screen
      .getByRole("heading", { name: "Tripod Null-Calf" })
      .closest("article");
    expect(card).toBeTruthy();
    expect(
      within(card!).getByText(/High confidence · 0.92/i),
    ).toBeInTheDocument();
    expect(
      within(card!).getAllByText(/exact label match/i).length,
    ).toBeGreaterThan(0);
    expect(within(card!).getByText(/gold fixture/i)).toBeInTheDocument();
    expect(within(card!).getByText(/Link existing later/i)).toBeInTheDocument();
    fireEvent.click(
      within(card!).getByRole("button", { name: "Review candidate" }),
    );
    expect(
      screen.getByText(
        "Selected suggestion for review only. No link has been written.",
      ),
    ).toBeInTheDocument();
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
        },
      ],
    });
    const onStageLinkIntent = vi.fn();
    const { rerender } = render(
      <ExistingObjectResolverPanel
        campaignId="longmont-c1"
        sessionId="session-1"
        laneRole="live"
        selectedNode={node}
        projectionGraphId="graph-1"
        liveRunManifestPath="runs/manifest.json"
      />,
    );
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
        selectedNode={node}
        projectionGraphId="graph-1"
        liveRunManifestPath="runs/manifest.json"
        onStageLinkIntent={onStageLinkIntent}
      />,
    );
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
    expect(
      screen.getByText("Draft only — no link will be written."),
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
        selectedNode={{ ...node, node_id: "node_2" }}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Find existing object" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});
