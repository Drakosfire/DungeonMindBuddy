import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GraphReviewDiagnosticsToolPanel } from "./GraphReviewDiagnosticsToolPanel";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";

describe("GraphReviewDiagnosticsToolPanel", () => {
  it("renders empty state when projection is not ready", () => {
    renderGraphReviewLiveHarness({
      liveRun: null,
      children: <GraphReviewDiagnosticsToolPanel />,
    });

    expect(
      screen.getByText(
        "Select a live run with a projection to inspect diagnostics.",
      ),
    ).toBeInTheDocument();
  });
});
