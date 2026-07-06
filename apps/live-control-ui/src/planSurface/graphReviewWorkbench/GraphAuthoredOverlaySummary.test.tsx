import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GraphAuthoredOverlaySummary } from "./GraphAuthoredOverlaySummary";

describe("GraphAuthoredOverlaySummary", () => {
  it("renders quiet missing overlay copy", () => {
    render(
      <GraphAuthoredOverlaySummary
        summary={{
          loaded: false,
          assertion_count: 0,
          projected_node_count: 0,
          projected_relationship_count: 0,
          diagnostics: [
            {
              code: "authored_overlay_missing",
              message: "No authored overlay file committed for this campaign yet.",
              severity: "info",
            },
          ],
        }}
      />,
    );
    expect(
      screen.getByText("No authored overlay committed for this session yet."),
    ).toBeInTheDocument();
  });

  it("renders loaded overlay counts", () => {
    render(
      <GraphAuthoredOverlaySummary
        summary={{
          loaded: true,
          assertion_count: 3,
          projected_node_count: 2,
          projected_relationship_count: 1,
          diagnostics: [],
        }}
      />,
    );
    expect(
      screen.getByText("Authored overlay loaded: 3 assertions · 2 object · 1 relationship"),
    ).toBeInTheDocument();
  });
});
