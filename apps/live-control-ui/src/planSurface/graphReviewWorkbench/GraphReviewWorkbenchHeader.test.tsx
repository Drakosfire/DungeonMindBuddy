import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";

describe("GraphReviewWorkbenchHeader", () => {
  it("shows empty-state copy and Load recap button when nothing is loaded", () => {
    render(
      <GraphReviewWorkbenchHeader loaded={false} sessionLabel={null} onOpenLoad={vi.fn()} />,
    );

    expect(screen.getByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    expect(screen.getByText("Prose-first review tool")).toBeInTheDocument();
    expect(screen.getByText("No session loaded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-mode-toggle")).not.toBeInTheDocument();
  });

  it("shows compact session label, Load recap, and author button when loaded", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 1 · longmont-c1"
        onOpenLoad={vi.fn()}
        graphAuthoringEnabled={false}
        onGraphAuthoringToggle={vi.fn()}
      />,
    );

    expect(screen.getByText("Session 1 · longmont-c1")).toBeInTheDocument();
    expect(screen.queryByText(/category_decomposed/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Author graph objects" })).toBeInTheDocument();
  });

  it("shows active authoring copy when graph authoring is enabled", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 1 · longmont-c1"
        onOpenLoad={vi.fn()}
        graphAuthoringEnabled
        onGraphAuthoringToggle={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Authoring memory…" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
