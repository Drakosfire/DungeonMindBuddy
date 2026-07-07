import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import type { GraphReviewSelectedNodeViewModel } from "./graphReviewSelectionUtils";

const baseNode: GraphProjectionNodeView = {
  node_id: "the-group",
  label: "The group",
  kind: "group",
  role: "party",
  aliases: ["gang"],
  source_domains: ["authored_overlay"],
  evidence_badges: [
    {
      evidence_ref_id: "ev-1",
      source_artifact_id: "artifact-1",
      source_domain: "authored_overlay",
      evidence_role: "source_span",
      is_focus_session_evidence: true,
      can_open_source: true,
      can_highlight_span: false,
      label: "Session recap",
    },
  ],
  adjacency: [
    {
      edge_id: "edge-1",
      node_id: "glowkindle",
      label: "Glowkindle",
      kind: "npc",
      predicate: "negotiated with",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["authored_overlay"],
      evidence_ref_ids: [],
      session_ids: ["session-2"],
    },
  ],
  anchored_to_focus_session: true,
  summary: "The adventuring collective that cleared the tower basement.",
  authored: true,
  assertion_id: "assert-group-001",
  visibility: "gm_private",
  graph_scope: ["campaign_retrospective"],
  source_anchor_text: "gang",
};

function viewModel(
  overrides: Partial<GraphReviewSelectedNodeViewModel> = {},
  nodeOverrides: Partial<GraphProjectionNodeView> = {},
): GraphReviewSelectedNodeViewModel {
  return {
    laneRole: "live",
    node: { ...baseNode, ...nodeOverrides },
    status: "unknown",
    deltaId: null,
    counterpart: null,
    ...overrides,
  };
}

describe("GraphReviewNodeGameCard", () => {
  it("renders summary before technical details in DOM order", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    const summaryIndex = card.textContent!.indexOf(
      "The adventuring collective that cleared the tower basement.",
    );
    const technicalIndex = card.textContent!.indexOf("Technical details");
    expect(summaryIndex).toBeGreaterThanOrEqual(0);
    expect(technicalIndex).toBeGreaterThan(summaryIndex);
  });

  it("renders relationship section before technical details in DOM order", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    const relationshipIndex = card.textContent!.indexOf(
      "Connected objects / relationships",
    );
    const technicalIndex = card.textContent!.indexOf("Technical details");
    expect(relationshipIndex).toBeGreaterThanOrEqual(0);
    expect(technicalIndex).toBeGreaterThan(relationshipIndex);
  });

  it("does not show assertion ID in the primary visible card flow", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText(/Assertion ID:/i)).not.toBeVisible();
    expect(screen.getByText("assert-group-001")).not.toBeVisible();
    expect(screen.queryByText("Authored overlay")).not.toBeInTheDocument();
  });

  it("shows assertion ID only inside Technical details when expanded", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText("assert-group-001")).not.toBeVisible();

    await user.click(screen.getByText("Technical details"));

    const technicalPanel = screen.getByText("Technical details").closest("details");
    expect(technicalPanel).not.toBeNull();
    expect(within(technicalPanel!).getByText("assert-group-001")).toBeVisible();
  });

  it("renders aliases as game-facing Also known as copy", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText(/Also known as: gang/)).toBeInTheDocument();
    expect(screen.queryByText(/^Aliases:/)).not.toBeInTheDocument();
  });

  it("hides no-comparison review status from primary view when no comparison context exists", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({ status: "unknown", deltaId: null, counterpart: null })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(
      screen.queryByText("No comparison status is available yet."),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Review status" })).not.toBeInTheDocument();
  });

  it("shows review status when comparison context exists", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({ status: "matched", deltaId: "delta-1" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Review status" })).toBeInTheDocument();
    expect(screen.getByText("Matched with the other lane.")).toBeInTheDocument();
  });

  it("keeps evidence/source collapsed by default", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const evidencePanel = screen.getByText("Evidence / Source").closest("details");
    expect(evidencePanel).not.toHaveAttribute("open");
  });

  it("renders friendly authored memory copy for authored overlay nodes", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText(/Authored memory/)).toBeInTheDocument();
    expect(screen.getByText(/This node includes authored memory\./)).toBeInTheDocument();
    expect(screen.queryByText("Authored overlay")).not.toBeInTheDocument();
    expect(screen.getByText(/Grounded from source phrase: “gang”/)).toBeInTheDocument();
  });

  it("renders friendly visibility copy for graph authoring enum values", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { visibility: "player_visible" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const aliasNote = screen.getByLabelText("Aliases and memory");
    expect(within(aliasNote).getByText("Visibility: Player visible")).toBeInTheDocument();
    expect(within(aliasNote).queryByText(/player_visible/i)).not.toBeInTheDocument();
  });

  it("renders table_known visibility as friendly copy in the primary card", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { visibility: "table_known" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const aliasNote = screen.getByLabelText("Aliases and memory");
    expect(within(aliasNote).getByText("Visibility: Table known")).toBeInTheDocument();
    expect(within(aliasNote).queryByText(/table_known/i)).not.toBeInTheDocument();
  });

  it("renders a single object type line when kind and role match", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { kind: "location", role: "location" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    expect(within(card).getByText("location")).toBeInTheDocument();
    expect(within(card).queryByText("location / location")).not.toBeInTheDocument();
  });

  it("renders distinct kind and role when they differ", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { kind: "npc", role: "merchant" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    expect(within(card).getByText("npc / merchant")).toBeInTheDocument();
  });

  it("renders no Actions section when no actions are supplied and no evidence is available", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({ deltaId: null })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.queryByRole("heading", { name: "Actions" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Inspect evidence/source" }),
    ).not.toBeInTheDocument();
  });

  it("renders supplied selected-object actions with accessible button labels", async () => {
    const user = userEvent.setup();
    const onStage = vi.fn();
    const onUseAsSource = vi.fn();

    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
        actions={[
          {
            id: "stage-memory",
            label: "Stage memory assertion",
            onClick: onStage,
          },
          {
            id: "use-as-source",
            label: "Use as relationship source",
            onClick: onUseAsSource,
          },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Actions" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Stage memory assertion" }));
    await user.click(screen.getByRole("button", { name: "Use as relationship source" }));
    expect(onStage).toHaveBeenCalledOnce();
    expect(onUseAsSource).toHaveBeenCalledOnce();
  });

  it("calls the evidence callback from Inspect evidence/source when available", async () => {
    const user = userEvent.setup();
    const onSelectEvidenceDelta = vi.fn();

    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({ deltaId: "delta-1" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={onSelectEvidenceDelta}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Inspect evidence/source" }));
    expect(onSelectEvidenceDelta).toHaveBeenCalledWith("delta-1");
  });

  it("disables Stage relationship when source and target are the same object", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
        relationshipStaging={{
          predicate: "knows",
          onPredicateChange: vi.fn(),
          canStageRelationship: false,
          onStageRelationship: vi.fn(),
          relationshipDraftSourceLabel: "The group",
          sameObjectAsSource: true,
        }}
      />,
    );

    expect(screen.getByRole("button", { name: "Stage relationship" })).toBeDisabled();
    expect(
      screen.getByText(
        /This object is already the relationship source\. Choose a different object as the target\./,
      ),
    ).toBeInTheDocument();
  });

  it("uses inspect evidence/source action copy instead of open evidence/debug", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({ deltaId: "delta-1" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
        onSelectEvidenceDelta={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Inspect evidence/source" })).toBeInTheDocument();
    expect(screen.queryByText("Open evidence/debug")).not.toBeInTheDocument();
  });
});
