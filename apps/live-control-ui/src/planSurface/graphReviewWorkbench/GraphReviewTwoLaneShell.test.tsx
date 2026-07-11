import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GraphReviewTwoLaneShell } from "./GraphReviewTwoLaneShell";
import type { GraphReviewPrimaryLaneView, GraphReviewReferenceLaneView } from "./graphReviewReferenceLaneUtils";

const primary: GraphReviewPrimaryLaneView = { laneId: "live:1", label: "Run A", runLabel: "Run A", manifestPath: "manifest.json", status: "succeeded", counts: { nodes: 1, edges: 2, evidenceRefs: 3 } };
const reference: GraphReviewReferenceLaneView = { kind: "gold_reference", laneId: "gold:1", label: "Gold Fixture", role: "gold", sourceKind: "gold_fixture", status: "missing_projection", summaryItems: [], warnings: [], note: "Projected source rendering is not implemented for this reference lane yet." };

describe("GraphReviewTwoLaneShell", () => {
  it("renders primary and reference labels plus children", () => {
    render(<GraphReviewTwoLaneShell primaryLane={primary} referenceLane={reference} layoutMode="single" onLayoutModeChange={() => undefined} primary={<div>Primary child</div>} reference={<div>Reference child</div>} />);
    expect(screen.getByText("Run A")).toBeInTheDocument();
    expect(screen.getByText("Gold Fixture")).toBeInTheDocument();
    expect(screen.getByText("Primary child")).toBeInTheDocument();
    expect(screen.getByText("Reference child")).toBeInTheDocument();
  });
  it("sets the layout mode attribute", () => {
    const { container, rerender } = render(<GraphReviewTwoLaneShell primaryLane={primary} referenceLane={reference} layoutMode="single" onLayoutModeChange={() => undefined} primary={<div />} reference={<div />} />);
    expect(container.querySelector(".graph-review-two-lane-body")).toHaveAttribute("data-layout-mode", "single");
    rerender(<GraphReviewTwoLaneShell primaryLane={primary} referenceLane={reference} layoutMode="split" onLayoutModeChange={() => undefined} primary={<div />} reference={<div />} />);
    expect(container.querySelector(".graph-review-two-lane-body")).toHaveAttribute("data-layout-mode", "split");
  });
  it("mode buttons call onLayoutModeChange", () => {
    const onChange = vi.fn();
    render(<GraphReviewTwoLaneShell primaryLane={primary} referenceLane={reference} layoutMode="single" onLayoutModeChange={onChange} primary={<div />} reference={<div />} />);
    fireEvent.click(screen.getByRole("button", { name: "split" }));
    expect(onChange).toHaveBeenCalledWith("split");
  });
});
