import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";

describe("GraphReviewWorkbenchHeader", () => {
  it("shows only Load recap when nothing is loaded", () => {
    render(
      <GraphReviewWorkbenchHeader loaded={false} sessionLabel={null} onOpenLoad={vi.fn()} />,
    );

    expect(screen.queryByRole("heading", { name: "Graph Review Workbench" })).not.toBeInTheDocument();
    expect(screen.queryByText("Prose-first review tool")).not.toBeInTheDocument();
    expect(screen.queryByText("No session loaded")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-mode-toggle")).not.toBeInTheDocument();
  });

  it("shows warm-up activity beside Load recap", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded={false}
        sessionLabel={null}
        onOpenLoad={vi.fn()}
        activity={{
          phase: "warming",
          message: "Warming Longmont C2 · Session 23…",
          busy: true,
        }}
      />,
    );

    const activity = screen.getByTestId("graph-review-activity");
    expect(activity).toHaveAttribute("data-phase", "warming");
    expect(activity).toHaveTextContent("Warming Longmont C2 · Session 23…");
    expect(activity).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
  });

  it("keeps session label and loading activity beside Load recap", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 23 · longmont-c2"
        onOpenLoad={vi.fn()}
        activity={{
          phase: "loading-session",
          message: "Loading Longmont C2 · Session 23…",
          busy: true,
        }}
      />,
    );

    expect(screen.getByTestId("graph-review-session-label")).toHaveTextContent(
      "Session 23 · longmont-c2",
    );
    expect(screen.getByTestId("graph-review-activity")).toHaveAttribute(
      "data-phase",
      "loading-session",
    );
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
  });

  it("shows compact session label and Load recap when loaded", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 1 · longmont-c1"
        onOpenLoad={vi.fn()}
      />,
    );

    expect(screen.getByText("Session 1 · longmont-c1")).toBeInTheDocument();
    expect(screen.queryByText(/category_decomposed/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Author graph objects" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-mode-toggle")).not.toBeInTheDocument();
  });

  it("floats a green Memory indicator beside Load recap when in memory", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 1 · longmont-c1"
        onOpenLoad={vi.fn()}
        inMemory
      />,
    );

    expect(screen.getByTestId("graph-review-memory-indicator")).toHaveTextContent("Memory");
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
  });
});
