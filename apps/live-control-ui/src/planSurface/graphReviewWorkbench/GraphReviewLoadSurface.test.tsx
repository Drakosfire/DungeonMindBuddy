import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";

const sessionWithRun = {
  session_id: "session-23",
  session_number: 23,
  campaign_id: "longmont-c2",
  gold_fixture_id: "gold-23",
  gold_manifest_path: "m23",
  gold_graph_path: "g23",
  gold_counts: { nodes: 2, edges: 1, evidence_refs: 1, beats: 0 },
  available_runs: [
    {
      manifest_path: "artifacts/run-a/manifest.json",
      run_dir: "artifacts/run-a",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      status: "preview_union_store_ready",
      updated_at: null,
      created_at: null,
      preview_union_store_path: "artifacts/run-a/preview-union.json",
      preview_union_store_valid: true,
      node_count: 2,
      edge_count: 1,
      evidence_ref_count: 1,
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
    },
  ],
};

describe("GraphReviewLoadSurface", () => {
  it("renders picker, lane summary, and actions when open", () => {
    render(
      <GraphReviewLoadSurface
        open
        sessions={[sessionWithRun]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftManifestPath="artifacts/run-a/manifest.json"
        draftSession={sessionWithRun}
        draftLiveRun={sessionWithRun.available_runs[0]}
        onClose={vi.fn()}
        onLoad={vi.fn()}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onManifestSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("dialog", { name: "Choose session and live run" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Gold \(expected\):/)).toBeInTheDocument();
    expect(screen.getByText(/Live \(ingested\):/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load" })).toBeEnabled();
  });

  it("calls onLoad when Load is clicked", () => {
    const onLoad = vi.fn();
    render(
      <GraphReviewLoadSurface
        open
        sessions={[sessionWithRun]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftManifestPath="artifacts/run-a/manifest.json"
        draftSession={sessionWithRun}
        draftLiveRun={sessionWithRun.available_runs[0]}
        onClose={vi.fn()}
        onLoad={onLoad}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onManifestSelect={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    expect(onLoad).toHaveBeenCalledTimes(1);
  });

  it("does not render when closed", () => {
    render(
      <GraphReviewLoadSurface
        open={false}
        sessions={[sessionWithRun]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftManifestPath="artifacts/run-a/manifest.json"
        draftSession={sessionWithRun}
        draftLiveRun={sessionWithRun.available_runs[0]}
        onClose={vi.fn()}
        onLoad={vi.fn()}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onManifestSelect={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("dialog", { name: "Choose session and live run" }),
    ).not.toBeInTheDocument();
  });
});
