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
  ExtractionRunRecord,
  UnionSupergraphProjectionResponse,
  WorldGraphProjection,
} from "../../api/types";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { catalogRunBindingKey } from "./graphReviewCommittedAuthority";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";
import { toCatalogRun, type GraphReviewCatalogRun } from "./graphReviewWorkbenchUtils";

function canonicalRun(overrides: Partial<ExtractionRunRecord> = {}): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: "run-a",
    source_artifact_id: "sa_1",
    source_domain: "recap",
    status: "reviewable",
    campaign_id: "longmont-c2",
    session_id: "session-23",
    ...overrides,
  };
}

function catalogRun(
  overrides: Partial<ExtractionRunRecord> = {},
  compatibilityManifestPath: string | null = "artifacts/run-a/manifest.json",
): GraphReviewCatalogRun {
  return toCatalogRun(canonicalRun(overrides), compatibilityManifestPath);
}

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

const baseRun = catalogRun();

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

  it("marks preview-unavailable runs retired without calling the Union API", async () => {
    renderGraphReviewLiveHarness({
      liveRun: {
        ...baseRun,
        next_actions: ["Generate preview union"],
      },
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(
        screen.getByTestId("graph-review-union-preview-retired"),
      ).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("marks store-preview retired and does not call the Union projection API", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(
        screen.getByTestId("graph-review-union-preview-retired"),
      ).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
    expect(
      screen.getByText(/UnionSupergraph store preview for this live\/candidate lane is retired/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("graph-projection-reader")).not.toBeInTheDocument();
  });

  it("never calls getUnionSupergraphProjection for preview-ready live runs", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: false,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(
        screen.getByTestId("graph-review-union-preview-retired"),
      ).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
    expect(getGoldGraphProjection).not.toHaveBeenCalled();
    expect(screen.queryByTestId("graph-projection-reader")).not.toBeInTheDocument();
  });

  it("still loads gold fixture metadata requests only when hasGold, without Union store preview", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(
        screen.getByTestId("graph-review-union-preview-retired"),
      ).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
    // Gold fetch remains for other surfaces; live store-preview lane stays retired.
    await waitFor(() => expect(getGoldGraphProjection).toHaveBeenCalled());
    expect(screen.queryByTestId("graph-review-projection-layout")).not.toBeInTheDocument();
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
      expect(screen.getByTestId("graph-review-union-preview-retired")).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("adopt-receipt"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-committed-projection-panel")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
    expect(screen.queryByText("Candidate Hesta")).toBeNull();
    expect(screen.queryByTestId("graph-review-projection-layout")).toBeNull();
  });
});
