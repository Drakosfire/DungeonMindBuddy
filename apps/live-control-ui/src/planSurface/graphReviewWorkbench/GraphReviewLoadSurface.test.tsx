import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ExtractionRunRecord } from "../../api/types";
import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";
import { toCatalogRun } from "./graphReviewWorkbenchUtils";

function canonicalRun(overrides: Partial<ExtractionRunRecord> = {}): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: "er_run_a",
    source_artifact_id: "sa_1",
    source_domain: "recap",
    status: "reviewable",
    campaign_id: "longmont-c2",
    session_id: "session-23",
    ...overrides,
  };
}

const catalogRun = toCatalogRun(
  canonicalRun(),
  "artifacts/run-a/manifest.json",
);

const sessionWithRun = {
  campaignId: "longmont-c2",
  sessionId: "session-23",
  sessionNumber: 23,
  hasGold: true,
  hasReviewableRun: true,
  goldFixtureId: "gold-23",
  goldManifestPath: "m23",
  goldGraphPath: "g23",
  goldCounts: { nodes: 2, edges: 1, evidence_refs: 1, beats: 0 },
  availableRuns: [catalogRun],
};

describe("GraphReviewLoadSurface", () => {
  it("renders picker, lane summary, and actions when open", () => {
    render(
      <GraphReviewLoadSurface
        open
        sessions={[sessionWithRun]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftRunId="er_run_a"
        draftSession={sessionWithRun}
        draftLiveRun={catalogRun}
        onClose={vi.fn()}
        onLoad={vi.fn()}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onRunSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("dialog", { name: "Choose campaign, session, and run" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Gold \(expected\):/)).toBeInTheDocument();
    expect(screen.getByText(/Live \(canonical\):/)).toBeInTheDocument();
    expect(screen.getByText(/Compatibility locator:/)).toBeInTheDocument();
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
        draftRunId="er_run_a"
        draftSession={sessionWithRun}
        draftLiveRun={catalogRun}
        onClose={vi.fn()}
        onLoad={onLoad}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onRunSelect={vi.fn()}
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
        draftRunId="er_run_a"
        draftSession={sessionWithRun}
        draftLiveRun={catalogRun}
        onClose={vi.fn()}
        onLoad={vi.fn()}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onRunSelect={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("dialog", { name: "Choose session and live run" }),
    ).not.toBeInTheDocument();
  });
});
