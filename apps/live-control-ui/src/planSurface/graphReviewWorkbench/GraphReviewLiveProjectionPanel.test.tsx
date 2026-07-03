import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getGoldGraphProjection,
  getUnionSupergraphProjection,
} from "../../api/liveApi";
import type {
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>(
      "../../api/liveApi",
    );
  return {
    ...actual,
    getGoldGraphProjection: vi.fn(),
    getUnionSupergraphProjection: vi.fn(),
  };
});

vi.mock("../graphProjectionReader/GraphProjectionReader", () => ({
  GraphProjectionReader: ({
    title,
    subtitle,
    markdown,
  }: {
    title: string;
    subtitle: string;
    markdown: string;
  }) => (
    <div data-testid="graph-projection-reader">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      <article>{markdown}</article>
    </div>
  ),
}));

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

describe("GraphReviewLiveProjectionPanel", () => {
  beforeEach(() => {
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projection,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });
  });

  it("renders an empty state when no live run is selected", () => {
    render(
      <GraphReviewLiveProjectionPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        liveRun={null}
      />,
    );

    expect(
      screen.getByText(
        "Select a live graph-ingest run to render its source projection.",
      ),
    ).toBeInTheDocument();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("renders unavailable metadata and does not call the projection API", () => {
    render(
      <GraphReviewLiveProjectionPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        liveRun={{
          ...baseRun,
          preview_union_available: false,
          next_actions: ["Generate preview union"],
        }}
      />,
    );

    expect(
      screen.getByText(
        "Selected live run does not have a preview-union projection available yet.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Generate preview union")).toBeInTheDocument();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("loads the selected run projection by manifest and preview-union paths", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    render(
      <GraphReviewLiveProjectionPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        liveRun={baseRun}
      />,
    );

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
    expect(screen.getAllByText("Live Run · read-only").length).toBeGreaterThan(
      0,
    );
  });

  it("renders a friendly error for failed projection loading", async () => {
    vi.mocked(getUnionSupergraphProjection).mockRejectedValue(
      new Error("Projection fixture missing"),
    );

    render(
      <GraphReviewLiveProjectionPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        liveRun={baseRun}
      />,
    );

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Projection fixture missing",
      ),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Selected run: Run A");
  });
});
