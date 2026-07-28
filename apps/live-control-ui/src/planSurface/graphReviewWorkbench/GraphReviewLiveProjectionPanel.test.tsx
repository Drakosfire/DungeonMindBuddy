import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getGoldGraphProjection,
  getUnionSupergraphProjection,
  postWorldGraphProjection,
  resolveGraphReviewExistingObjectCandidates,
} from "../../api/liveApi";
import type {
  ExtractPromoteConfirmReceipt,
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
  WorldGraphProjection,
} from "../../api/types";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { catalogRunBindingKey } from "./graphReviewCommittedAuthority";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>(
      "../../api/liveApi",
    );
  return {
    ...actual,
    getGoldGraphProjection: vi.fn(),
    getUnionSupergraphProjection: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    resolveGraphReviewExistingObjectCandidates: vi.fn(),
  };
});

const baseRun: GraphIngestRunSummary = {
  manifest_path: "artifacts/run-a/manifest.json",
  run_dir: "artifacts/run-a",
  campaign_id: "longmont-c2",
  session_id: "session-23",
  status: "succeeded",
  updated_at: null,
  created_at: null,
  preview_union_store_path: "artifacts/run-a/preview-union.json",
  preview_union_store_valid: true,
  node_count: 2,
  edge_count: 1,
  evidence_ref_count: 3,
  next_actions: [],
  run_id: "run-a",
  run_label: "Run A",
  generated_at: null,
  model_id: null,
  model_provider: null,
  extraction_profile: "baseline",
  extraction_mode: null,
  vocabulary_mode: "node",
  runner_options_summary: {},
  diagnostics_summary: {},
  preview_union_available: true,
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-23",
  graph_id: "graph-a",
  markdown: "# Projected recap",
  focus: {
    focus_session_id: "session-23",
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  node_views: {},
  source_spans: [
    {
      span_id: "p2",
      kind: "paragraph",
      ordinal: 2,
      text_excerpt: "Second",
      line_start: null,
      line_end: null,
    },
  ],
  mentions: [],
};

const projectionWithMention: UnionSupergraphProjectionResponse = {
  ...projection,
  markdown: "The party met [Alden](dmb-node:alden) at the gate.",
  node_views: {
    alden: {
      node_id: "alden",
      label: "Alden",
      kind: "npc",
      role: "gate warden",
      summary: "Alden guards the western gate and knows the patrol routes.",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
    },
  },
  mentions: [
    {
      mention_id: "mention-alden",
      node_id: "alden",
      label: "Alden",
      start_offset: 14,
      end_offset: 19,
      anchor_status: "anchored",
    },
  ],
};

describe("GraphReviewLiveProjectionPanel", () => {
  beforeEach(() => {
    sessionStorage.removeItem("graph-object-authoring-staged:longmont-c2:session-23");
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockReset();
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockReset();
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      selected_node_id: "",
      selected_label: "",
      candidates: [],
      warnings: [],
    });
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projection,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });
  });

  it("renders an empty state when no live run is selected", () => {
    renderGraphReviewLiveHarness({
      liveRun: null,
      children: <GraphReviewLiveProjectionPanel />,
    });

    expect(
      screen.getByText(
        "Select a live graph-ingest run to render its source projection.",
      ),
    ).toBeInTheDocument();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("renders unavailable metadata and does not call the projection API", () => {
    renderGraphReviewLiveHarness({
      liveRun: {
        ...baseRun,
        preview_union_available: false,
        next_actions: ["Generate preview union"],
      },
      children: <GraphReviewLiveProjectionPanel />,
    });

    expect(
      screen.getByText(
        "Selected live run does not have a preview-union projection available yet.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Generate preview union")).toBeInTheDocument();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("loads the selected run projection by manifest and preview-union paths", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue({
      ...projection,
      authored_overlay: {
        loaded: true,
        assertion_count: 2,
        projected_node_count: 0,
        projected_link_existing_count: 1,
        projected_relationship_count: 1,
        diagnostics: [],
      },
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).toHaveBeenCalledWith({
      campaignId: "longmont-c2",
      sessionId: "session-23",
      graphRunManifestPath: "artifacts/run-a/manifest.json",
      previewUnionStorePath: "artifacts/run-a/preview-union.json",
    });
    expect(getUnionSupergraphProjection).not.toHaveBeenCalledWith(
      expect.objectContaining({ useLatestGraphIngest: true }),
    );
    expect(screen.getByLabelText("Live run prose")).toBeInTheDocument();
    expect(screen.queryByText("Live Run · read-only")).not.toBeInTheDocument();
    expect(screen.queryByText("Selected live lane")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Source projection" }),
    ).not.toBeInTheDocument();
  });

  it("renders a single live lane without fetching gold projection when hasGold is false", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: false,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(getGoldGraphProjection).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Ingested recap projection")).toBeInTheDocument();
    expect(screen.queryByText(/Loading gold fixture projection/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Live run prose")).toBeInTheDocument();
  });

  it("opens and closes one projected interaction surface from a graph mention", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(
      projectionWithMention,
    );
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projectionWithMention,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    const liveReader = screen.getByTestId("graph-projection-reader");
    const liveAldenPill = await waitFor(() => {
      const pill = within(liveReader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(liveAldenPill);

    const dialog = screen.getByRole("dialog", { name: "Selected object: Alden" });
    expect(dialog).toHaveTextContent("Selected object");
    expect(dialog).toHaveTextContent("Live Run · read-only");
    expect(dialog).toHaveTextContent(
      "Alden guards the western gate and knows the patrol routes.",
    );
    expect(
      screen.queryByRole("button", { name: "Highlight counterpart" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stage node assertion" }),
    ).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Find existing object")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Close selected object" }),
    );
    expect(
      screen.queryByRole("dialog", { name: "Selected object: Alden" }),
    ).not.toBeInTheDocument();
  });

  it("renders gold and live projection lanes side by side in the two-lane layout", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projection,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-projection-layout")).toBeInTheDocument(),
    );

    const layout = screen.getByTestId("graph-review-projection-layout");
    expect(layout).toHaveClass("graph-review-real-two-lane-projections");
    expect(within(layout).getByLabelText("Gold fixture prose")).toBeInTheDocument();
    expect(within(layout).getByLabelText("Live run prose")).toBeInTheDocument();
    expect(layout.querySelectorAll(".graph-review-projection-lane")).toHaveLength(2);
  });

  it("preserves gold-vs-live compare decorations on the live lane when authoring mode is off", async () => {
    const goldNodeViews = {
      "gold:alden": {
        node_id: "gold:alden",
        label: "Alden",
        kind: "npc" as const,
        role: "gate warden",
        summary: null,
        aliases: [],
        source_domains: [],
        evidence_badges: [],
        adjacency: [],
      },
    };
    const liveNodeViews = {
      "live:alden": {
        ...goldNodeViews["gold:alden"],
        node_id: "live:alden",
      },
    };
    const goldProjectionPayload: UnionSupergraphProjectionResponse = {
      ...projection,
      markdown: "The party met [Alden](dmb-node:gold:alden) at the gate.",
      node_views: goldNodeViews,
      mentions: [],
    };
    const liveProjectionPayload: UnionSupergraphProjectionResponse = {
      ...projection,
      markdown: "The party met [Alden](dmb-node:live:alden) at the gate.",
      node_views: liveNodeViews,
      mentions: [],
    };

    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(liveProjectionPayload);
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...goldProjectionPayload,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    const liveReader = screen.getByLabelText("Live run prose");
    expect(liveReader).toHaveAttribute("data-lane-role", "live");
    const livePill = await waitFor(() => {
      const pill = within(liveReader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    expect(livePill).toHaveAttribute("data-delta-status");
    expect(
      liveReader.querySelector(".union-supergraph-tiptap-reader"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-action")).not.toBeInTheDocument();
  });

  it("does not render diagnostic panels on the main surface", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("heading", { name: "Gold-vs-live smoke alarms" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Author Draft text-selection actions"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-surface")).not.toBeInTheDocument();
    expect(document.querySelector(".union-supergraph-tiptap-reader")).not.toBeInTheDocument();
  });

  it("renders a friendly error for failed projection loading", async () => {
    vi.mocked(getUnionSupergraphProjection).mockRejectedValue(
      new Error("Projection fixture missing"),
    );

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Projection fixture missing",
      ),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Selected run: Run A");
  });

  it("switches from candidate projection to committed panel after receipt adoption", async () => {
    const candidateProjection: UnionSupergraphProjectionResponse = {
      ...projection,
      node_views: {
        "object-1": {
          node_id: "object-1",
          label: "Candidate Hesta",
          kind: "npc",
          role: "character",
          summary: "candidate",
          evidence_ref_ids: [],
          edge_ids: [],
          beat_ids: [],
          source_span_ids: [],
        },
      },
    };
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(candidateProjection);

    const committed: WorldGraphProjection = {
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-23", campaignId: "longmont-c2" },
        admissibility: "gm",
      },
      summary: {
        nodeCount: 1,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [
        {
          nodeId: "object-1",
          label: "Hesta Ironroot",
          kind: "npc",
          role: "character",
          aliases: [],
          sourceDomains: [],
          anchoredToFocusSession: true,
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
        },
      ],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    };
    vi.mocked(postWorldGraphProjection).mockResolvedValue(committed);

    const receipt: ExtractPromoteConfirmReceipt = {
      schema: "dmb_extract_promote_confirm_v2",
      outcome: "committed",
      worldId: "eldyrwild",
      proposalId: "prop-1",
      proposalDigest: "digest-a",
      parentRevisionId: "rev:parent",
      committedRevisionId: "rev:committed",
      headAdvanced: true,
      selectedAssertionIds: ["a-1"],
      acceptedAssertionIds: ["a-1"],
      affectedObjectIds: ["object-1"],
      appliedAssertionCount: 1,
      auditStatus: "ok",
      warnings: [],
    };

    function AdoptAndShow() {
      const { adoptCommittedReceipt } = useGraphReviewLiveState();
      return (
        <>
          <button
            type="button"
            data-testid="adopt-receipt"
            onClick={() => {
              void adoptCommittedReceipt(receipt);
            }}
          >
            Adopt
          </button>
          <GraphReviewLiveProjectionPanel />
        </>
      );
    }

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      sessionId: "session-23",
      committedBinding: {
        kind: "catalog_run",
        key: catalogRunBindingKey({
          runId: "run-a",
          campaignId: "longmont-c2",
          sessionId: "session-23",
        }),
        runId: "run-a",
        campaignId: "longmont-c2",
        sessionId: "session-23",
      },
      children: <AdoptAndShow />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-projection-layout")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("adopt-receipt"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-committed-projection-panel")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
    expect(screen.queryByText("Candidate Hesta")).toBeNull();
    expect(screen.queryByTestId("graph-review-projection-layout")).toBeNull();
  });
});
