import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";
import { GraphObjectProjectionCard, resolveExactProjectedNode } from "./GraphObjectProjectionCard";

describe("GraphObjectProjectionCard", () => {
  const nodeView = adaptWorldGraphNodeView(session23WorldGraphRecapFixture.nodeViews.pc_caelynn);
  const nodeViews = {
    pc_caelynn: nodeView,
    loc_mirathorn: adaptWorldGraphNodeView(session23WorldGraphRecapFixture.nodeViews.loc_mirathorn),
  };

  it("renders exact node card content from nodeView", () => {
    render(<GraphObjectProjectionCard nodeView={nodeView} />);
    expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    expect(screen.getByText("Caelynn")).toBeInTheDocument();
  });

  it("emits exact relationship target ids", () => {
    const onSelect = vi.fn();
    render(<GraphObjectProjectionCard nodeView={nodeView} onSelectRelationshipTarget={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /Mirathorn/i }));
    expect(onSelect).toHaveBeenCalledWith("loc_mirathorn");
  });

  it("resolveExactProjectedNode performs exact map lookup only", () => {
    expect(resolveExactProjectedNode(nodeViews, "loc_mirathorn")?.node_id).toBe("loc_mirathorn");
    expect(resolveExactProjectedNode(nodeViews, "missing-node")).toBeNull();
  });
});
