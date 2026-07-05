import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getGoldGraphProjection,
  getUnionSupergraphProjection,
  resolveGraphReviewExistingObjectCandidates,
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
    resolveGraphReviewExistingObjectCandidates: vi.fn(),
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

const projectionWithMention: UnionSupergraphProjectionResponse = {
  ...projection,
  markdown: "The party met Alden at the gate.",
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
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockReset();
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockReset();
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
    expect(screen.queryByText("Selected live lane")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Source projection" }),
    ).not.toBeInTheDocument();
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

    render(
      <GraphReviewLiveProjectionPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        liveRun={baseRun}
      />,
    );

    await screen.findAllByRole("button", { name: /Alden/ });
    fireEvent.click(screen.getAllByRole("button", { name: /Alden/ }).at(-1)!);

    const dialog = screen.getByRole("dialog", { name: "Alden" });
    expect(dialog).toHaveTextContent("Selected object");
    expect(dialog).toHaveTextContent("Live Run · read-only");
    expect(dialog).toHaveTextContent(
      "Alden guards the western gate and knows the patrol routes.",
    );
    expect(dialog).toHaveTextContent("No link or merge is written here.");
    expect(
      screen.queryByRole("button", { name: "Highlight counterpart" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Statblock unavailable" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Encounter note unavailable" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Selected graph object"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stage node assertion" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Close selected object" }),
    );
    expect(
      screen.queryByRole("dialog", { name: "Alden" }),
    ).not.toBeInTheDocument();
  });

  it("shows Author Draft selected-object actions and relationship staging flow", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue({
      ...projectionWithMention,
      markdown: "Alden watched Bera.",
      node_views: {
        ...projectionWithMention.node_views,
        bera: {
          ...projectionWithMention.node_views.alden,
          node_id: "bera",
          label: "Bera",
          role: "scout",
          summary: "Bera scouts the old road.",
        },
      },
      mentions: [
        {
          mention_id: "m-alden",
          node_id: "alden",
          label: "Alden",
          start_offset: 0,
          end_offset: 5,
          anchor_status: "anchored",
        },
        {
          mention_id: "m-bera",
          node_id: "bera",
          label: "Bera",
          start_offset: 14,
          end_offset: 18,
          anchor_status: "anchored",
        },
      ],
    });

    render(
      <GraphReviewLiveProjectionPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        liveRun={baseRun}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Author Draft" }));
    await screen.findAllByRole("button", { name: /Alden/ });
    fireEvent.click(screen.getAllByRole("button", { name: /Alden/ }).at(-1)!);
    expect(screen.getByRole("dialog", { name: "Alden" })).toHaveTextContent(
      "Draft only. Staging is local; no gold fixture, graph state, or corpus file has changed.",
    );
    expect(
      screen.getByRole("button", { name: "Stage as possible gold node" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Relationship type")).toBeInTheDocument();
    expect(
      screen.getByText(/Nothing is written until Prepare and Commit/),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Use as relationship source" }),
    );

    fireEvent.click(screen.getAllByRole("button", { name: /Bera/ }).at(-1)!);
    expect(screen.getByRole("dialog", { name: "Bera" })).toHaveTextContent(
      "Relationship source: live:alden",
    );
    expect(
      screen.getByRole("button", { name: "Stage relationship" }),
    ).toBeEnabled();
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
