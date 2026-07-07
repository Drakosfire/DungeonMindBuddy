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
        authorMode="review"
        relationshipDraftSource={null}
        relationshipPredicate="knows"
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
        onStageNodeAssertion={vi.fn()}
        onUseAsRelationshipSource={vi.fn()}
        onRelationshipPredicateChange={vi.fn()}
        onStageRelationship={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "Selected object: The wall" });
    const chromeHeader = within(dialog).getByText("Selected object").closest("header");
    expect(chromeHeader).toBeTruthy();
    expect(within(chromeHeader!).queryByText("The wall")).not.toBeInTheDocument();
    expect(screen.getAllByText("The wall")).toHaveLength(1);
    expect(screen.getAllByText("Live Run · read-only")).toHaveLength(1);
    expect(screen.getAllByText("location")).toHaveLength(1);
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
        authorMode="review"
        relationshipDraftSource={null}
        relationshipPredicate="knows"
        onClose={onClose}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
        onStageNodeAssertion={vi.fn()}
        onUseAsRelationshipSource={vi.fn()}
        onRelationshipPredicateChange={vi.fn()}
        onStageRelationship={vi.fn()}
      />,
    );

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not expose gold-fixture staging copy in author draft mode", () => {
    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel()}
        selectedRelationship={null}
        authorMode="author_draft"
        relationshipDraftSource={null}
        relationshipPredicate="knows"
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
        onStageNodeAssertion={vi.fn()}
        onUseAsRelationshipSource={vi.fn()}
        onRelationshipPredicateChange={vi.fn()}
        onStageRelationship={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "Selected object: Alden" });
    expect(
      within(dialog).getByRole("button", { name: "Stage memory assertion" }),
    ).toBeInTheDocument();
    expect(within(dialog).queryByText(/possible gold node/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/nominate gold/i)).not.toBeInTheDocument();
  });

  it("renders stage and relationship actions inside the card before the resolver", () => {
    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel()}
        selectedRelationship={null}
        authorMode="author_draft"
        relationshipDraftSource={{ laneRole: "live", nodeId: "alden" }}
        relationshipDraftSourceLabel="Alden"
        relationshipPredicate="knows"
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
        onStageNodeAssertion={vi.fn()}
        onUseAsRelationshipSource={vi.fn()}
        onRelationshipPredicateChange={vi.fn()}
        onStageRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/alden game card/i);
    expect(within(card).getByRole("heading", { name: "Actions" })).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Stage memory assertion" }),
    ).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Use as relationship source" }),
    ).toBeInTheDocument();
    expect(
      within(card).getByRole("button", { name: "Inspect evidence/source" }),
    ).toBeInTheDocument();

    const cardIndex = document.body.textContent!.indexOf("Stage memory assertion");
    const resolverIndex = document.body.textContent!.indexOf("Find existing object");
    expect(cardIndex).toBeGreaterThanOrEqual(0);
    expect(resolverIndex).toBeGreaterThan(cardIndex);
  });

  it("keeps technical details collapsed by default in author draft mode", () => {
    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel()}
        selectedRelationship={null}
        authorMode="author_draft"
        relationshipDraftSource={null}
        relationshipPredicate="knows"
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
        onStageNodeAssertion={vi.fn()}
        onUseAsRelationshipSource={vi.fn()}
        onRelationshipPredicateChange={vi.fn()}
        onStageRelationship={vi.fn()}
      />,
    );

    const evidencePanel = screen.getByText("Evidence / Source").closest("details");
    const technicalPanel = screen.getByText("Technical details").closest("details");
    expect(evidencePanel).not.toHaveAttribute("open");
    expect(technicalPanel).not.toHaveAttribute("open");
  });

  it("wires stage relationship when a different object is the source", async () => {
    const user = userEvent.setup();
    const onStageRelationship = vi.fn();

    render(
      <GraphReviewProjectedInteractionSurface
        open
        selectedNode={viewModel({ node: { ...baseNode, node_id: "bera", label: "Bera" } })}
        selectedRelationship={null}
        authorMode="author_draft"
        relationshipDraftSource={{ laneRole: "live", nodeId: "alden" }}
        relationshipDraftSourceLabel="Alden"
        relationshipPredicate="knows"
        onClose={vi.fn()}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
        onStageNodeAssertion={vi.fn()}
        onUseAsRelationshipSource={vi.fn()}
        onRelationshipPredicateChange={vi.fn()}
        onStageRelationship={onStageRelationship}
      />,
    );

    const stageButton = screen.getByRole("button", { name: "Stage relationship" });
    expect(stageButton).toBeEnabled();
    await user.click(stageButton);
    expect(onStageRelationship).toHaveBeenCalledOnce();
  });
});
