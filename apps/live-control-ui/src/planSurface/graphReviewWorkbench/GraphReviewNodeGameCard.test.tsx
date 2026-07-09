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
  const innRelationship = {
    edge_id: "edge-inn",
    node_id: "location_inn",
    label: "Inn (Mireward Reach)",
    kind: "location",
    predicate: "related",
    direction: "outgoing",
    anchored_to_focus_session: true,
    source_domains: ["recap"],
    evidence_ref_ids: ["ev-inn"],
    related_summary: "The party's meeting place with the town leader.",
    source_excerpt: "They all head to the Inn to speak with the town leader.",
  };

  it("shows related object name with meta line and expands detail inline on click", async () => {
    const user = userEvent.setup();
    const onSelectRelationship = vi.fn();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { adjacency: [innRelationship] })}
        selectedEdgeId={null}
        onSelectRelationship={onSelectRelationship}
      />,
    );

    expect(screen.getByText("Inn (Mireward Reach)")).toBeInTheDocument();
    expect(
      screen.getByText(/connected · location · The party's meeting place/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Source excerpt")).not.toBeInTheDocument();

    const row = screen.getByRole("button", { name: /Inn \(Mireward Reach\)/i });
    expect(row).toHaveAttribute("aria-expanded", "false");

    await user.click(row);
    expect(onSelectRelationship).toHaveBeenCalledWith(innRelationship);
  });

  it("expands inline relationship detail directly under the clicked row when selected", async () => {
    const user = userEvent.setup();
    const onClearRelationship = vi.fn();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { adjacency: [innRelationship] })}
        selectedEdgeId="edge-inn"
        onSelectRelationship={vi.fn()}
        onClearRelationship={onClearRelationship}
      />,
    );

    const row = screen.getByRole("button", { name: /Inn \(Mireward Reach\)/i });
    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Source excerpt")).toBeInTheDocument();
    expect(
      screen.getByText("They all head to the Inn to speak with the town leader."),
    ).toBeInTheDocument();

    const rowItem = row.closest("li");
    expect(rowItem?.textContent).toContain("Source excerpt");

    await user.click(row);
    expect(onClearRelationship).toHaveBeenCalledOnce();
  });

  it("highlights the verbatim fragments within a resolved source paragraph", () => {
    const fullParagraphRelationship = {
      ...innRelationship,
      source_excerpt:
        "They all head to the Inn where they can clearly hear lots of voices before they even open the doors.",
      source_excerpt_is_full_paragraph: true,
      source_excerpt_highlight_spans: [{ start: 0, end: 20 }],
    };
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { adjacency: [fullParagraphRelationship] })}
        selectedEdgeId="edge-inn"
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText(/Source paragraph \(highlighted excerpt below\)/i)).toBeInTheDocument();
    const mark = screen.getByText("They all head to the");
    expect(mark.tagName).toBe("MARK");
    expect(screen.getByText(/where they can clearly hear/)).toBeInTheDocument();
  });

  it("groups relationships sharing the same highlighted source phrase into one row", () => {
    const sharedExcerpt =
      "Bonogo and Karsemine slipped past the guards while the others caused a distraction.";
    const bonogoRelationship = {
      edge_id: "edge-bonogo",
      node_id: "pc_bonogo",
      label: "Bonogo",
      kind: "pc",
      predicate: "present_at",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["recap"],
      evidence_ref_ids: ["ev-bonogo"],
      related_summary: "A rogue skilled at moving unseen.",
      source_excerpt: sharedExcerpt,
      source_excerpt_is_full_paragraph: true,
      source_excerpt_highlight_spans: [{ start: 0, end: 24 }],
    };
    const karsemineRelationship = {
      ...bonogoRelationship,
      edge_id: "edge-karsemine",
      node_id: "pc_karsemine",
      label: "Karsemine",
      related_summary: "A ranger watching the party's back.",
      evidence_ref_ids: ["ev-karsemine"],
    };

    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { adjacency: [bonogoRelationship, karsemineRelationship] })}
        selectedEdgeId="edge-bonogo"
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText("Bonogo & Karsemine")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Bonogo$/ })).not.toBeInTheDocument();

    const row = screen.getByRole("button", { name: /Bonogo & Karsemine/i });
    expect(row).toHaveAttribute("aria-expanded", "true");

    expect(screen.getByText(/About Bonogo:/)).toBeInTheDocument();
    expect(screen.getByText(/About Karsemine:/)).toBeInTheDocument();
    const excerptHeader = screen.getByText(/Source paragraph \(shared by these linked objects/i);
    const excerptBlock = excerptHeader.closest("blockquote");
    expect(excerptBlock?.textContent).toContain(sharedExcerpt);
  });

  it("renders relationships before summary and technical details in DOM order", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    const relationshipIndex = card.textContent!.indexOf("Related objects");
    const summaryIndex = card.textContent!.indexOf(
      "The adventuring collective that cleared the tower basement.",
    );
    const technicalIndex = card.textContent!.indexOf("Technical details");
    expect(relationshipIndex).toBeGreaterThanOrEqual(0);
    expect(summaryIndex).toBeGreaterThan(relationshipIndex);
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
    const relationshipIndex = card.textContent!.indexOf("Related objects");
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

  it("keeps authored memory metadata collapsed by default", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const memoryPanel = screen.getByText("Memory & visibility").closest("details");
    expect(memoryPanel).not.toHaveAttribute("open");
    expect(screen.queryByText(/This node includes authored memory\./)).not.toBeVisible();

    await user.click(screen.getByText("Memory & visibility"));

    expect(within(memoryPanel!).getByText(/Authored memory/)).toBeVisible();
    expect(within(memoryPanel!).getByText(/This node includes authored memory\./)).toBeVisible();
    expect(within(memoryPanel!).getByText(/Grounded from source phrase: “gang”/)).toBeVisible();
    expect(screen.queryByText("Authored overlay")).not.toBeInTheDocument();
  });

  it("renders friendly visibility copy inside memory details", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { visibility: "player_visible" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    await user.click(screen.getByText("Memory & visibility"));
    const memoryPanel = screen.getByText("Memory & visibility").closest("details");
    expect(memoryPanel).not.toBeNull();
    expect(within(memoryPanel!).getByText("Visibility: Player visible")).toBeInTheDocument();
    expect(within(memoryPanel!).queryByText(/player_visible/i)).not.toBeInTheDocument();
  });

  it("renders table_known visibility as friendly copy inside memory details", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { visibility: "table_known" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    await user.click(screen.getByText("Memory & visibility"));
    const memoryPanel = screen.getByText("Memory & visibility").closest("details");
    expect(memoryPanel).not.toBeNull();
    expect(within(memoryPanel!).getByText("Visibility: Table known")).toBeInTheDocument();
    expect(within(memoryPanel!).queryByText(/table_known/i)).not.toBeInTheDocument();
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

  it("shows merged identity note for durable survivor nodes", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel(
          {},
          {
            node_id: "party:captain_lysandra_ironveil",
            label: "Captain Lysandra Ironveil",
            kind: "companion",
            role: "companion",
            aliases: ["Captain Lysandra Ironveil", "Lysandra"],
            source_domains: ["recap"],
            merged_away_ids: ["node:lysandra"],
            merge_assertion_ids: ["assert-merge-lysandra"],
            identity_redirect_ids: ["redirect:lysandra"],
            identity_merge_record_ids: ["merge_record:lysandra"],
            adjacency: [
              {
                edge_id: "edge:lysandra:mireward",
                node_id: "location_mireward",
                label: "Mireward",
                kind: "location",
                predicate: "travels_to",
                direction: "outgoing",
                anchored_to_focus_session: true,
                source_domains: ["recap"],
                evidence_ref_ids: [],
                session_ids: ["session-23"],
              },
            ],
            evidence_badges: [
              {
                evidence_ref_id: "evidence:session-23:lysandra:recap-mention",
                source_artifact_id: "artifact:session-23-recap",
                source_domain: "recap",
                evidence_role: "mention",
                is_focus_session_evidence: true,
                can_open_source: true,
                can_highlight_span: true,
                label: "Session recap mention",
              },
              {
                evidence_ref_id: "evidence:session-23:lysandra:mireward-command",
                source_artifact_id: "artifact:session-23-recap",
                source_domain: "recap",
                evidence_role: "command",
                is_focus_session_evidence: true,
                can_open_source: true,
                can_highlight_span: true,
                label: "Mireward command",
              },
            ],
          },
        )}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const mergedIdentity = screen.getByLabelText("Merged identity");
    expect(within(mergedIdentity).getByRole("heading", { name: "Merged identity" })).toBeInTheDocument();
    expect(within(mergedIdentity).getByText(/Folded in 1 prior identity: Lysandra\./)).toBeInTheDocument();
    expect(
      within(mergedIdentity).getByText(/Evidence and relationships from the duplicate are now shown here\./),
    ).toBeInTheDocument();
    expect(within(mergedIdentity).queryByText(/Includes .* evidence badge/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mireward/i })).toBeInTheDocument();
    expect(screen.queryByText("0.92")).not.toBeInTheDocument();
    expect(screen.queryByText("evidence:session-23:lysandra:recap-mention")).not.toBeInTheDocument();
  });

  it("does not show merged identity note for normal nodes", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.queryByLabelText("Merged identity")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Merged identity" })).not.toBeInTheDocument();
  });

  it("keeps raw merge provenance ids inside technical details only", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel(
          {},
          {
            merged_away_ids: ["node:lysandra"],
            merge_assertion_ids: ["assert-merge-lysandra"],
            identity_redirect_ids: ["redirect:lysandra"],
            identity_merge_record_ids: ["merge_record:lysandra"],
          },
        )}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.queryByText("redirect:lysandra")).not.toBeVisible();
    expect(screen.queryByText("assert-merge-lysandra")).not.toBeVisible();

    await user.click(screen.getByText("Technical details"));

    const technicalPanel = screen.getByText("Technical details").closest("details");
    expect(technicalPanel).not.toBeNull();
    expect(within(technicalPanel!).getByText("redirect:lysandra")).toBeVisible();
    expect(within(technicalPanel!).getByText("assert-merge-lysandra")).toBeVisible();
    expect(within(technicalPanel!).getByText("node:lysandra")).toBeVisible();
    expect(within(technicalPanel!).getByText("merge_record:lysandra")).toBeVisible();
  });

  it("renders relationships before merged identity in DOM order", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel(
          {},
          {
            merged_away_ids: ["node:lysandra"],
            adjacency: baseNode.adjacency,
          },
        )}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    const relationshipIndex = card.textContent!.indexOf("Related objects");
    const mergedIdentityIndex = card.textContent!.indexOf("Merged identity");
    expect(relationshipIndex).toBeGreaterThanOrEqual(0);
    expect(mergedIdentityIndex).toBeGreaterThan(relationshipIndex);
  });

  it("hides placeholder ingest summaries from the primary card", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel(
          {},
          {
            summary: "Deterministic party context anchor",
            adjacency: [],
            aliases: ["Lysandra"],
          },
        )}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(
      screen.queryByText("Deterministic party context anchor"),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Also known as: Lysandra/)).toBeInTheDocument();
  });
});
