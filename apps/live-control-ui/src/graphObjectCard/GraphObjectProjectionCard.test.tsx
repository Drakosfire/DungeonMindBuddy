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
    expect(screen.queryByRole("button", { name: /Close Caelynn/i })).not.toBeInTheDocument();
  });

  it("places campaign-memory dismiss on the card identity row", () => {
    const onDismiss = vi.fn();
    render(
      <GraphObjectProjectionCard
        mode="campaign-memory"
        nodeView={nodeView}
        onDismiss={onDismiss}
        dismissLabel="Close Caelynn"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Close Caelynn" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("emits exact relationship target ids", () => {
    const onSelect = vi.fn();
    render(<GraphObjectProjectionCard nodeView={nodeView} onSelectRelationshipTarget={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /Mirathorn/i }));
    expect(onSelect).toHaveBeenCalledWith("loc_mirathorn");
  });

  it("emits the full clicked relationship for Plan-style navigation", () => {
    const onSelectRelationship = vi.fn();
    const model = {
      id: "npc-glowkindle",
      label: "Glowkindle",
      typeBadgeLabel: "NPC",
      relationships: [
        { id: "edge-lysandra", label: "Lysandra", predicate: "knows", targetId: "" },
        { id: "edge-inn", label: "Inn", predicate: "met at", targetId: "" },
      ],
    };
    render(
      <GraphObjectProjectionCard model={model} onSelectRelationship={onSelectRelationship} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Open related object .*Inn/i }));
    expect(onSelectRelationship).toHaveBeenCalledWith(
      expect.objectContaining({ id: "edge-inn", label: "Inn", targetId: "" }),
    );
  });

  it("resolveExactProjectedNode performs exact map lookup only", () => {
    expect(resolveExactProjectedNode(nodeViews, "loc_mirathorn")?.node_id).toBe("loc_mirathorn");
    expect(resolveExactProjectedNode(nodeViews, "missing-node")).toBeNull();
  });
});
