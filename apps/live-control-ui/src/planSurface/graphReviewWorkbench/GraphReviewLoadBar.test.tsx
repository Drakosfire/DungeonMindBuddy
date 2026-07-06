import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewLoadBar } from "./GraphReviewLoadBar";

describe("GraphReviewLoadBar", () => {
  it("shows empty-state copy and Load session button when nothing is loaded", () => {
    render(<GraphReviewLoadBar loaded={false} summaryLabel={null} onOpenLoad={vi.fn()} />);

    expect(
      screen.getByText("Load an ingested session to review extracted objects in recap prose."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load session" })).toBeInTheDocument();
  });

  it("shows applied summary and Change button when loaded", () => {
    render(
      <GraphReviewLoadBar
        loaded
        summaryLabel="Session 23 · Run A"
        onOpenLoad={vi.fn()}
      />,
    );

    expect(screen.getByText("Session 23 · Run A")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change" })).toBeInTheDocument();
  });
});
