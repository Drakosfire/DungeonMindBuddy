import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import type { GraphReviewSelectedNodeViewModel } from "./graphReviewSelectionUtils";

vi.mock("../../sourceNavigation/sourceNavigation", async () => {
  const actual = await vi.importActual<typeof import("../../sourceNavigation/sourceNavigation")>(
    "../../sourceNavigation/sourceNavigation",
  );
  return {
    ...actual,
    resolveAndNavigateToBuildSource: vi.fn(),
  };
});

import { resolveAndNavigateToBuildSource } from "../../sourceNavigation/sourceNavigation";

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
      source_domain: "worldbuilding",
      evidence_role: "source_span",
      is_focus_session_evidence: true,
      can_open_source: true,
      can_highlight_span: false,
      label: "Session recap",
      source_span_ref_id: "span-group-1",
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
  beforeEach(() => {
    vi.mocked(resolveAndNavigateToBuildSource).mockReset();
  });

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

  it("renders summary before relationships and details in DOM order", () => {
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
    const detailsIndex = card.textContent!.indexOf("Details");
    expect(summaryIndex).toBeGreaterThanOrEqual(0);
    expect(relationshipIndex).toBeGreaterThan(summaryIndex);
    expect(detailsIndex).toBeGreaterThan(relationshipIndex);
  });

  it("renders relationship section before details in DOM order", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    const relationshipIndex = card.textContent!.indexOf("Related objects");
    const detailsIndex = card.textContent!.indexOf("Details");
    expect(relationshipIndex).toBeGreaterThanOrEqual(0);
    expect(detailsIndex).toBeGreaterThan(relationshipIndex);
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

  it("shows assertion ID only inside Details when expanded", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.getByText("assert-group-001")).not.toBeVisible();

    await user.click(screen.getByText("Details"));

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText("assert-group-001")).toBeVisible();
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
    expect(screen.queryByText("Review status")).not.toBeInTheDocument();
  });

  it("shows review status inside Details when comparison context exists", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({ status: "matched", deltaId: "delta-1" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(screen.queryByText("Matched with the other lane.")).not.toBeVisible();

    await user.click(screen.getByText("Details"));
    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText("Review status")).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("Matched with the other lane.")).toBeVisible();
  });

  it("keeps details collapsed by default", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toHaveAttribute("open");
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

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toHaveAttribute("open");
    expect(screen.queryByText(/This node includes authored memory\./)).not.toBeVisible();

    await user.click(screen.getByText("Details"));

    expect(within(detailsPanel!).getByText(/Authored memory/)).toBeVisible();
    expect(within(detailsPanel!).getByText(/This node includes authored memory\./)).toBeVisible();
    expect(within(detailsPanel!).getByText(/Grounded from source phrase: “gang”/)).toBeVisible();
    expect(screen.queryByText("Authored overlay")).not.toBeInTheDocument();
  });

  it("renders friendly visibility copy inside details", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { visibility: "player_visible" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    await user.click(screen.getByText("Details"));
    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText("Visibility: Player visible")).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("player_visible")).toBeInTheDocument();
  });

  it("renders table_known visibility as friendly copy inside details", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { visibility: "table_known" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    await user.click(screen.getByText("Details"));
    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText("Visibility: Table known")).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("table_known")).toBeInTheDocument();
  });

  it("renders a single object type badge when kind and role match", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { kind: "location", role: "location" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    expect(within(card).getByLabelText("Object type: Location")).toHaveTextContent("Location");
    expect(within(card).queryByText("location / location")).not.toBeInTheDocument();
  });

  it("renders distinct kind badge and role subtitle when they differ", () => {
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel({}, { kind: "npc", role: "merchant" })}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    expect(within(card).getByLabelText("Object type: Npc")).toHaveTextContent("Npc");
    expect(within(card).getByText("Merchant")).toBeInTheDocument();
    expect(within(card).queryByText("npc / merchant")).not.toBeInTheDocument();
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

  it("resolves Read source from the custom details panel", async () => {
    vi.mocked(resolveAndNavigateToBuildSource).mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    const card = screen.getByLabelText(/the group game card/i);
    await user.click(within(card).getByText("Details"));
    await user.click(within(card).getByRole("button", { name: "Read source" }));

    expect(resolveAndNavigateToBuildSource).toHaveBeenCalledWith(
      expect.objectContaining({
        sourceArtifactId: "artifact-1",
        sourceSpanRefId: "span-group-1",
        navigate: expect.any(Function),
      }),
    );
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

  it("shows merged identity note inside Details for durable survivor nodes", async () => {
    const user = userEvent.setup();
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

    expect(screen.queryByRole("heading", { name: "Merged identity" })).not.toBeVisible();

    await user.click(screen.getByText("Details"));

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    const mergedIdentity = within(detailsPanel!).getByLabelText("Merged identity");
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

  it("keeps raw merge provenance ids inside details only", async () => {
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

    await user.click(screen.getByText("Details"));

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText("redirect:lysandra")).toBeVisible();
    expect(within(detailsPanel!).getByText("assert-merge-lysandra")).toBeVisible();
    expect(within(detailsPanel!).getByText("node:lysandra")).toBeVisible();
    expect(within(detailsPanel!).getByText("merge_record:lysandra")).toBeVisible();
  });

  it("keeps connection count fallback inside Details only", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel(
          {},
          {
            summary: null,
            kind: "character",
            adjacency: baseNode.adjacency,
          },
        )}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(
      screen.queryByText(/connected campaign relationship/i),
    ).not.toBeVisible();

    await user.click(screen.getByText("Details"));

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(
      within(detailsPanel!).getByText(
        /This character has 1 connected campaign relationship in this session\./,
      ),
    ).toBeVisible();
  });

  it("does not duplicate connection count in Details when a primary summary exists", async () => {
    const user = userEvent.setup();
    render(
      <GraphReviewNodeGameCard
        viewModel={viewModel()}
        selectedEdgeId={null}
        onSelectRelationship={vi.fn()}
      />,
    );

    expect(
      screen.getByText("The adventuring collective that cleared the tower basement."),
    ).toBeInTheDocument();

    await user.click(screen.getByText("Details"));

    const detailsPanel = screen.getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(
      within(detailsPanel!).queryByText(/connected campaign relationship/i),
    ).not.toBeInTheDocument();
  });

  it("renders relationships before details in DOM order for merged nodes", () => {
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
    const detailsIndex = card.textContent!.indexOf("Details");
    expect(relationshipIndex).toBeGreaterThanOrEqual(0);
    expect(detailsIndex).toBeGreaterThan(relationshipIndex);
    expect(card.textContent!.indexOf("Merged identity")).toBeGreaterThan(detailsIndex);
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
