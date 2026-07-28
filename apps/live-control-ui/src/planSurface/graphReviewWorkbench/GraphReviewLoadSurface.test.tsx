import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";
import type { GraphReviewCatalogSession } from "./graphReviewWorkbenchUtils";

const browseSession: GraphReviewCatalogSession = {
  campaignId: "longmont-c2",
  sessionId: "session-23",
  sessionNumber: 23,
  hasGold: false,
  hasReviewableRun: true,
  browseable: true,
  recapAvailable: true,
  contributionCount: 2,
  headRevisionId: "rev:test",
  goldFixtureId: null,
  goldManifestPath: null,
  goldGraphPath: null,
  goldCounts: {},
  availableRuns: [],
};

describe("GraphReviewLoadSurface", () => {
  it("renders picker, lane summary, and actions when open", () => {
    render(
      <GraphReviewLoadSurface
        open
        sessions={[browseSession]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftManifestPath={null}
        draftSession={browseSession}
        draftLiveRun={null}
        onClose={vi.fn()}
        onLoad={vi.fn()}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onManifestSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("dialog", {
        name: "Choose campaign and World Graph session",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/World Graph:/)).toBeInTheDocument();
    expect(screen.getByText(/2 contributions · recap available/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load" })).toBeEnabled();
  });

  it("calls onLoad when Load is clicked", () => {
    const onLoad = vi.fn();
    render(
      <GraphReviewLoadSurface
        open
        sessions={[browseSession]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftManifestPath={null}
        draftSession={browseSession}
        draftLiveRun={null}
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
        sessions={[browseSession]}
        draftCampaignId="longmont-c2"
        draftSessionId="session-23"
        draftManifestPath={null}
        draftSession={browseSession}
        draftLiveRun={null}
        onClose={vi.fn()}
        onLoad={vi.fn()}
        onCampaignSelect={vi.fn()}
        onSessionSelect={vi.fn()}
        onManifestSelect={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("dialog", {
        name: "Choose campaign and World Graph session",
      }),
    ).not.toBeInTheDocument();
  });
});
