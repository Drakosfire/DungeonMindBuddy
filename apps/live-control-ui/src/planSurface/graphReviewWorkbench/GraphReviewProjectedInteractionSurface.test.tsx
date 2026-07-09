import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphReviewProjectedInteractionSurface } from "./GraphReviewProjectedInteractionSurface";
import type { GraphReviewSelectedNodeViewModel } from "./graphReviewSelectionUtils";

const baseNode: GraphProjectionNodeView = {
  node_id: "alden",
  label: "Alden",
  kind: "character",
  role: "pc",
  aliases: [],
  source_domains: ["live_run"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A cautious scout.",
};

function viewModel(
  overrides: Partial<GraphReviewSelectedNodeViewModel> = {},
): GraphReviewSelectedNodeViewModel {
  return {
    laneRole: "live",
    node: baseNode,
    status: "unknown",
    deltaId: "delta-alden",
    counterpart: null,
    ...overrides,
  };
}

describe("GraphReviewProjectedInteractionSurface", () => {
  it("keeps dialog chrome minimal and shows object identity once on the card", () => {
    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel({
          node: { ...baseNode, label: "The wall", kind: "location", role: "location" },
        })}
        selectedRelationship={null}
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "Selected object: The wall" });
    const chromeHeader = within(dialog).getByText("Selected object").closest("header");
    expect(chromeHeader).toBeTruthy();
    expect(within(chromeHeader!).queryByText("The wall")).not.toBeInTheDocument();
    expect(screen.getAllByText("The wall")).toHaveLength(1);
    expect(screen.getByLabelText("Object type: Location")).toHaveTextContent("Location");
    expect(screen.queryByText("location / location")).not.toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: "Close selected object" }),
    ).toBeInTheDocument();
  });

  it("calls onClose when Escape is pressed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel()}
        selectedRelationship={null}
        onClose={onClose}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
      />,
    );

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not show authoring actions or resolver in review inspect dialog", () => {
    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel()}
        selectedRelationship={null}
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "Selected object: Alden" });
    expect(
      within(dialog).queryByRole("button", { name: "Stage memory assertion" }),
    ).not.toBeInTheDocument();
    expect(
      within(dialog).queryByRole("button", { name: "Use as relationship source" }),
    ).not.toBeInTheDocument();
    expect(
      within(dialog).queryByRole("button", { name: "Stage relationship" }),
    ).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Find existing object")).not.toBeInTheDocument();
  });

  it("keeps details collapsed by default", () => {
    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel()}
        selectedRelationship={null}
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
      />,
    );

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toHaveAttribute("open");
  });
});
