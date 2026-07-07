import { useState } from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getGoldGraphProjection,
  getUnionSupergraphProjection,
} from "../../api/liveApi";
import type {
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphReviewAuthorDraftToolPanel } from "./GraphReviewAuthorDraftToolPanel";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

function AuthorModeProbe() {
  const { authorDraft } = useGraphReviewLiveState();
  return <span data-testid="author-mode">{authorDraft.authorMode}</span>;
}

function AuthorDraftPanelHarness() {
  const [showPanel, setShowPanel] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setShowPanel(false)}>
        Hide author draft panel
      </button>
      {showPanel ? <GraphReviewAuthorDraftToolPanel /> : null}
      <AuthorModeProbe />
    </>
  );
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
  source_spans: [],
  mentions: [],
};

describe("GraphReviewAuthorDraftToolPanel", () => {
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

  it("renders empty state when projection is not ready", () => {
    renderGraphReviewLiveHarness({
      liveRun: null,
      children: <GraphReviewAuthorDraftToolPanel />,
    });

    expect(
      screen.getByText(
        "Select a live run with a projection before authoring draft corrections.",
      ),
    ).toBeInTheDocument();
  });

  it("shows author draft staging controls when projection is ready", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftToolPanel />,
    });

    await waitFor(() =>
      expect(
        screen.getByText("Author Draft text-selection actions"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: "Stage node from selection" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Return to review" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Author Draft lives in the toolbox for now/i),
    ).toBeInTheDocument();
  });

  it("returns to review mode and closes the toolbox via Return to review", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);
    const user = userEvent.setup();

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: (
        <>
          <GraphReviewAuthorDraftToolPanel />
          <AuthorModeProbe />
        </>
      ),
    });

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("author_draft"),
    );

    await user.click(screen.getByRole("button", { name: "Return to review" }));

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("review"),
    );
  });

  it("returns to review mode when the author draft panel unmounts", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);
    const user = userEvent.setup();

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <AuthorDraftPanelHarness />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("author_draft"),
    );

    await user.click(screen.getByRole("button", { name: "Hide author draft panel" }));

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("review"),
    );
  });
});
