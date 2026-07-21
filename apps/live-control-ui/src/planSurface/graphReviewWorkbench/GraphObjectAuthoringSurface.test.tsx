import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../api/liveApi", () => ({
  prepareGraphObjectAuthoringWrite: vi.fn(),
  commitGraphObjectAuthoringWrite: vi.fn(),
  resolveGraphReviewExistingObjectCandidates: vi.fn().mockResolvedValue({
    schema: "dmb_graph_review_existing_object_resolver_response_v1",
    campaign_id: "longmont-c1",
    session_id: "session-2",
    selected_node_id: "selection:gang",
    selected_label: "gang",
    candidates: [],
    warnings: [],
    diagnostics: [],
    scopes_searched: [],
  }),
}));

import { prepareGraphObjectAuthoringWrite, commitGraphObjectAuthoringWrite } from "../../api/liveApi";
import { buildManualGraphAuthoringSelection, type GraphAuthoringSelection } from "./graphAuthoringSelection";
import { GraphObjectAuthoringSurface } from "./GraphObjectAuthoringSurface";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { useGraphObjectAuthoringDraft } from "./useGraphObjectAuthoringDraft";

const selection: GraphAuthoringSelection = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  selectionKind: "text_span",
  selectedText: "gang",
  normalizedSelectedText: "gang",
  graphId: "graph-c1s2",
  laneRole: "live",
};

const defaultExistingNodes: GraphObjectAuthoringInspectedNode[] = [
  { node_id: "bonogo", label: "Bonogo", kind: "pc", role: "rogue" },
];

function Harness({
  initialSelection,
  existingNodes = defaultExistingNodes,
  withPrepareCommit = false,
  focusPanel,
  pendingSelection = null,
  enableBindExisting = false,
}: {
  initialSelection?: GraphAuthoringSelection;
  existingNodes?: GraphObjectAuthoringInspectedNode[];
  withPrepareCommit?: boolean;
  focusPanel?: import("./GraphObjectAuthoringSurface").GraphObjectAuthoringFocusPanel;
  pendingSelection?: GraphAuthoringSelection | null;
  enableBindExisting?: boolean;
}) {
  const draft = useGraphObjectAuthoringDraft();
  const [bindCompleteCount, setBindCompleteCount] = useState(0);

  return (
    <div>
      <button type="button" onClick={() => draft.openWithSelection(initialSelection ?? selection)}>
        Open with selection
      </button>
      <span data-testid="bind-complete-count">{bindCompleteCount}</span>
      <GraphObjectAuthoringSurface
        focusPanel={focusPanel}
        selectedSource={draft.selectedSource}
        formState={draft.formState}
        proposals={draft.proposals}
        onFormFieldChange={draft.updateFormField}
        onStageProposal={draft.stageProposal}
        onRemoveProposal={draft.removeProposal}
        onStartManualDraft={() =>
          draft.openWithSelection(
            buildManualGraphAuthoringSelection({
              campaignId: "longmont-c1",
              sessionId: "session-2",
            }),
          )
        }
        pendingSelection={pendingSelection}
        onUseSelectedText={(nextSelection) => draft.openWithSelection(nextSelection)}
        onStageLinkExisting={
          enableBindExisting
            ? (candidate) => {
                const selected = draft.selectedSource;
                if (!selected) return false;
                return draft.stageLinkExistingFromResolver({
                  selection: selected,
                  candidate,
                });
              }
            : undefined
        }
        onStageLinkExistingComplete={
          enableBindExisting
            ? () => {
                setBindCompleteCount((count) => count + 1);
                draft.dismissSelection();
              }
            : undefined
        }
        relationshipFormState={draft.relationshipFormState}
        onRelationshipFieldChange={draft.updateRelationshipField}
        onStageRelationshipProposal={draft.stageRelationshipProposal}
        campaignId={withPrepareCommit || enableBindExisting ? "longmont-c1" : undefined}
        sessionId={withPrepareCommit || enableBindExisting ? "session-2" : undefined}
        onCommittedProposals={
          withPrepareCommit ? draft.clearCommittedProposals : undefined
        }
        existingNodes={existingNodes}
      />
    </div>
  );
}

describe("GraphObjectAuthoringSurface", () => {
  it("shows an empty hint before any selection has been opened", () => {
    render(<Harness />);
    expect(
      screen.getByText(/Highlight source text in the recap/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/No staged memory yet/i)).toBeInTheDocument();
  });

  it("lets the user start and stage a manual object draft without a recap selection", () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("graph-object-authoring-start-manual-draft-button"));

    expect(screen.getByText("New object")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
  });

  it("shows a call-to-action to use highlighted recap text inside the New object pane", () => {
    render(<Harness pendingSelection={selection} />);

    expect(screen.getByTestId("graph-object-authoring-pending-selection")).toBeInTheDocument();
    expect(screen.getByText("“gang”")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-object-authoring-use-selected-text-button"));

    expect(screen.getByLabelText("Label")).toHaveValue("gang");
    expect(
      screen.queryByTestId("graph-object-authoring-pending-selection"),
    ).not.toBeInTheDocument();
  });

  it("offers Add as alias matches after using highlighted text", async () => {
    const { resolveGraphReviewExistingObjectCandidates } = await import("../../api/liveApi");
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValueOnce({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c1",
      session_id: "session-2",
      selected_node_id: "selection:bubbles",
      selected_label: "bubbles",
      candidates: [
        {
          candidate_id: "npc:bubbles_the_float_goat",
          label: "Bubbles the Float Goat",
          kind: "npc",
          role: "npc",
          confidence: "high",
          score: 0.95,
          reason: "Alias match: bubbles",
          source: "union_supergraph",
          suggested_action: "link_existing_later",
          existing_object_ref: {
            source: "party_pc",
            object_id: "npc:bubbles_the_float_goat",
            source_label: "Party / PCs",
          },
          matched_features: ["Alias match: bubbles"],
          graph_scope: "party_pc",
          source_label: "Party / PCs",
          aliases: ["Bubbles"],
          authored: false,
        },
      ],
      warnings: [],
      diagnostics: [],
      scopes_searched: ["party_pc"],
    });

    const bubblesSelection: GraphAuthoringSelection = {
      ...selection,
      selectedText: "bubbles",
      normalizedSelectedText: "bubbles",
    };

    render(
      <Harness
        pendingSelection={bubblesSelection}
        enableBindExisting
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-use-selected-text-button"));

    expect(
      await screen.findByTestId("graph-object-authoring-bind-existing"),
    ).toBeInTheDocument();
    const bindList = await screen.findByTestId("graph-object-authoring-bind-existing-list");
    expect(within(bindList).getByText(/Bubbles the Float Goat/i)).toBeInTheDocument();

    fireEvent.click(
      within(bindList).getByTestId("graph-object-authoring-bind-as-alias-button"),
    );

    await waitFor(() => {
      expect(screen.getByTestId("bind-complete-count")).toHaveTextContent("1");
    });
    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveTextContent("Bubbles the Float Goat");
    expect(staged).toHaveTextContent("bubbles");
    expect(staged).toHaveTextContent("Alias text: bubbles");
  });

  it("does not show the pending-selection call-to-action once its text is already loaded", () => {
    render(<Harness initialSelection={selection} pendingSelection={selection} />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));

    expect(
      screen.queryByTestId("graph-object-authoring-pending-selection"),
    ).not.toBeInTheDocument();
  });

  it("disables staging a manual draft until a label is entered", () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("graph-object-authoring-start-manual-draft-button"));

    expect(screen.getByTestId("graph-object-authoring-stage-button")).toBeDisabled();
  });

  it("shows creating state and error feedback from quick commit", () => {
    render(
      <GraphObjectAuthoringSurface
        focusPanel="create_new"
        selectedSource={selection}
        formState={{
          label: "Questionable Company",
          kind: "party",
          role: "",
          aliasesText: "",
          summary: "",
          operatorNote: "",
          visibility: "gm_private",
        }}
        proposals={[]}
        onFormFieldChange={() => {}}
        onStageProposal={() => {}}
        onRemoveProposal={() => {}}
        creatingObject
        createObjectError="Commit did not complete."
      />,
    );

    expect(screen.getByTestId("graph-object-authoring-stage-button")).toBeDisabled();
    expect(screen.getByTestId("graph-object-authoring-stage-button")).toHaveTextContent(
      "Creating…",
    );
    expect(screen.getByText("Bind highlighted text or create a node")).toBeInTheDocument();
    expect(
      screen.getByText(/Prefer adding an alias to an existing node/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Commit did not complete.");
  });

  it("seeds the label field from the selected text once opened", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));

    expect(screen.getByLabelText("Label")).toHaveValue("gang");
    expect(screen.getByLabelText("Visibility")).toHaveValue("gm_private");
  });

  it("preserves the selected text as an alias when the label is changed", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));

    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "party" } });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
    expect(stagedProposal).toHaveTextContent("Aliases: gang");
    expect(stagedProposal).toHaveTextContent("party");
  });

  it("lets the user change visibility away from the GM-private default", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));

    fireEvent.change(screen.getByLabelText("Visibility"), {
      target: { value: "table_known" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("Table known");
  });

  it("lets the user stage an object draft with player_visible visibility", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));

    fireEvent.change(screen.getByLabelText("Visibility"), {
      target: { value: "player_visible" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("Player visible");
    expect(stagedProposal).not.toHaveTextContent("player_visible");
  });

  it("shows no-write copy on the staging tray once a proposal is staged", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    expect(
      screen.getByText(/These drafts are local until you prepare and commit them/i),
    ).toBeInTheDocument();
  });

  it("closes the open draft form after staging and allows removing the staged proposal", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    expect(screen.queryByLabelText("Label")).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-staged-proposal")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(
      screen.queryByTestId("graph-object-authoring-staged-proposal"),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/No staged memory yet/i)).toBeInTheDocument();
  });

  it("disables staging when the label is blank", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "   " } });

    expect(screen.getByTestId("graph-object-authoring-stage-button")).toBeDisabled();
  });

  it("stages a relationship proposal between the inspected node and a manual ref without requiring a selection", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "has_member" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    const manualInputs = screen.getAllByPlaceholderText("Type a label for an object not staged yet");
    fireEvent.change(manualInputs[manualInputs.length - 1], {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveAttribute("data-proposal-kind", "relationship");
    expect(stagedProposal).toHaveTextContent("Bonogo");
    expect(stagedProposal).toHaveTextContent("has member Questionable Company");
    expect(
      screen.getByText(/These drafts are local until you prepare and commit them/i),
    ).toBeInTheDocument();
  });

  it("lists every quick relationship predicate in the type select", () => {
    render(<Harness />);

    const typeSelect = screen.getByLabelText("Relationship type") as HTMLSelectElement;
    const optionValues = Array.from(typeSelect.options).map((option) => option.value);
    const optionLabels = Array.from(typeSelect.options).map((option) => option.textContent);
    expect(optionValues).toEqual([
      "has_member",
      "member_of",
      "located_in",
      "controls",
      "allied_with",
      "opposes",
      "owns",
      "created_by",
      "travels_with",
      "protects",
      "threatens",
      "related_to",
      "__custom__",
    ]);
    expect(optionLabels).toContain("has member");
    expect(optionLabels).toContain("threatens");
  });

  it("stages a custom relationship predicate when Custom is selected", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "__custom__" },
    });
    fireEvent.change(screen.getByLabelText("Custom relationship type"), {
      target: { value: "owes_debt_to" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    const manualInputs = screen.getAllByPlaceholderText("Type a label for an object not staged yet");
    fireEvent.change(manualInputs[manualInputs.length - 1], {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    expect(screen.getByTestId("graph-object-authoring-staged-proposal")).toHaveTextContent(
      "Bonogo owes debt to Questionable Company",
    );
  });

  it("shows identity guidance for custom same_as predicates without blocking staging", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "__custom__" },
    });
    fireEvent.change(screen.getByLabelText("Custom relationship type"), {
      target: { value: "same_as" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    const manualInputs = screen.getAllByPlaceholderText("Type a label for an object not staged yet");
    fireEvent.change(manualInputs[manualInputs.length - 1], {
      target: { value: "Questionable Company" },
    });

    expect(screen.getByTestId("graph-object-authoring-identity-predicate-warning")).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeEnabled();
  });

  it("disables relationship staging when source and target are the exact same object", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), {
      target: { value: "existing_node:bonogo" },
    });

    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeDisabled();
    expect(screen.getByTestId("graph-object-authoring-same-object-warning")).toBeInTheDocument();
  });

  it("allows relationship staging when two nodes share a label but have different IDs", () => {
    render(
      <Harness
        existingNodes={[
          { node_id: "glowkindle-char", label: "Glowkindle", kind: "npc" },
          { node_id: "glowkindle-faction", label: "Glowkindle", kind: "faction" },
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:glowkindle-char" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), {
      target: { value: "existing_node:glowkindle-faction" },
    });

    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeEnabled();
    expect(screen.queryByTestId("graph-object-authoring-same-object-warning")).not.toBeInTheDocument();
  });

  it("lets relationship drafts use player_visible visibility", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    fireEvent.change(screen.getAllByPlaceholderText("Type a label for an object not staged yet")[0], {
      target: { value: "Questionable Company" },
    });
    fireEvent.change(screen.getByLabelText("Relationship visibility"), {
      target: { value: "player_visible" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    expect(screen.getByTestId("graph-object-authoring-staged-proposal")).toHaveTextContent(
      "Player visible",
    );
  });

  it("disables relationship staging until both object refs are chosen", () => {
    render(<Harness />);
    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeDisabled();
  });

  it("keeps relationship staging disabled when a manual ref is selected but the label is blank", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "has_member" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });

    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeDisabled();

    const manualInputs = screen.getAllByPlaceholderText("Type a label for an object not staged yet");
    fireEvent.change(manualInputs[manualInputs.length - 1], { target: { value: "   " } });
    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeDisabled();
  });

  it("clears the manual object input after staging so stale text does not leak into the next proposal", () => {
    render(<Harness />);

    fireEvent.change(screen.getByLabelText("Source object"), { target: { value: "manual" } });
    fireEvent.change(screen.getByPlaceholderText("Type a label for an object not staged yet"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "has_member" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), {
      target: { value: "existing_node:bonogo" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    // The relationship section stays mounted after staging. Re-selecting manual
    // entry for a fresh proposal must not resurrect the previous typed label.
    fireEvent.change(screen.getByLabelText("Source object"), { target: { value: "manual" } });
    expect(screen.getByPlaceholderText("Type a label for an object not staged yet")).toHaveValue("");
    expect(screen.getByTestId("graph-object-authoring-stage-relationship-button")).toBeDisabled();
  });

  it("offers every existing graph object as a target, not just a single last-inspected node", () => {
    render(
      <Harness
        existingNodes={[
          { node_id: "alden", label: "Alden", kind: "npc", role: "gate warden" },
          { node_id: "bonogo", label: "Bonogo", kind: "pc", role: "rogue" },
          { node_id: "grishna", label: "Grishna", kind: "npc", role: "innkeeper" },
        ]}
      />,
    );

    const sourcePicker = screen.getByLabelText("Source object") as HTMLSelectElement;
    const existingGroup = within(sourcePicker).getByRole("group", { name: "Current recap" });
    const options = within(existingGroup).getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "Alden · npc",
      "Bonogo · pc",
      "Grishna · npc",
    ]);
  });

  it("deduplicates existing graph object candidates by node id", () => {
    render(
      <Harness
        existingNodes={[
          { node_id: "alden", label: "Alden", kind: "npc" },
          { node_id: "alden", label: "Alden", kind: "npc" },
        ]}
      />,
    );

    const sourcePicker = screen.getByLabelText("Source object") as HTMLSelectElement;
    const existingGroup = within(sourcePicker).getByRole("group", { name: "Current recap" });
    expect(within(existingGroup).getAllByRole("option")).toHaveLength(1);
  });

  it("keeps existing object proposal staging working alongside the new proposal kinds", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveAttribute("data-proposal-kind", "object");
  });

  it("shows overlap warning when staging duplicates authored memory label", () => {
    render(
      <Harness
        existingNodes={[
          {
            node_id: "authored:assert-qc",
            label: "Questionable Company",
            kind: "party",
            aliases: ["gang"],
            authored: true,
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "party" } });

    expect(screen.getByTestId("graph-object-authoring-overlap-warnings")).toBeInTheDocument();
  });

  it("groups authored and extracted nodes separately in the picker", () => {
    render(
      <Harness
        existingNodes={[
          {
            node_id: "authored:assert-qc",
            label: "Questionable Company",
            kind: "party",
            aliases: ["gang"],
            authored: true,
          },
          { node_id: "gang-node", label: "gang", kind: "unknown", authored: false },
        ]}
      />,
    );

    const sourcePicker = screen.getByLabelText("Source object") as HTMLSelectElement;
    expect(within(sourcePicker).getByRole("group", { name: "Authored memory" })).toBeInTheDocument();
    expect(within(sourcePicker).getByRole("group", { name: "Current recap" })).toBeInTheDocument();
  });

  it("does not show prepare button until proposals exist and prepare/commit wiring is enabled", () => {
    render(<Harness withPrepareCommit />);
    expect(screen.queryByTestId("graph-object-authoring-prepare-button")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    expect(screen.getByTestId("graph-object-authoring-prepare-button")).toBeEnabled();
  });

  it("clears committed proposals from sessionStorage after successful commit", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      prepared: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      current_overlay_token: "a",
      proposed_assertions_digest: "b",
      confirm_token: "c",
      assertion_count: 1,
      event_count: 2,
      assertions_preview: [],
      overlay_summary: {
        existing_assertion_count: 0,
        proposed_assertion_count: 1,
        total_assertion_count: 1,
        object_count: 1,
        link_existing_count: 0,
        relationship_count: 0,
      },
      diagnostics: [],
      no_mutation_guarantees: ["Prepare wrote nothing."],
    });
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue({
      committed: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      backup_path: null,
      assertion_count: 1,
      event_count: 2,
      new_overlay_token: "new-token",
      diagnostics: [],
      no_mutation_guarantees: ["Committed authored graph memory."],
    });

    function CommitHarness() {
      const draft = useGraphObjectAuthoringDraft({
        campaignId: "longmont-c1",
        sessionId: "session-2",
      });
      return (
        <div>
          <button type="button" onClick={() => draft.openWithSelection(selection)}>
            Open with selection
          </button>
          <GraphObjectAuthoringSurface
            selectedSource={draft.selectedSource}
            formState={draft.formState}
            proposals={draft.proposals}
            onFormFieldChange={draft.updateFormField}
            onStageProposal={draft.stageProposal}
            onRemoveProposal={draft.removeProposal}
            campaignId="longmont-c1"
            sessionId="session-2"
            onCommittedProposals={draft.clearCommittedProposals}
          />
        </div>
      );
    }

    render(<CommitHarness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));
    expect(
      sessionStorage.getItem("graph-object-authoring-staged:longmont-c1:session-2"),
    ).toBeTruthy();

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-commit-button"));

    await waitFor(() => {
      expect(
        sessionStorage.getItem("graph-object-authoring-staged:longmont-c1:session-2"),
      ).toBeNull();
    });
  });

  it("calls prepare API when prepare write is clicked", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      prepared: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      current_overlay_token: "a",
      proposed_assertions_digest: "b",
      confirm_token: "c",
      assertion_count: 1,
      event_count: 2,
      assertions_preview: [],
      overlay_summary: {
        existing_assertion_count: 0,
        proposed_assertion_count: 1,
        total_assertion_count: 1,
        object_count: 1,
        link_existing_count: 0,
        relationship_count: 0,
      },
      diagnostics: [],
      no_mutation_guarantees: ["Prepare wrote nothing."],
    });

    render(<Harness withPrepareCommit />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));
    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));

    await waitFor(() => {
      expect(prepareGraphObjectAuthoringWrite).toHaveBeenCalled();
    });
    expect(screen.getByText(/Safe write preview generated/i)).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-write-safety-details")).not.toHaveAttribute("open");
  });

  it("uses one staged-memory header on the stage and commit tab", () => {
    render(<Harness withPrepareCommit focusPanel="stage_overlay" />);

    expect(screen.getAllByText("Review staged memory")).toHaveLength(1);
    expect(
      screen.getByText(/Stage a draft from New object, Existing object, Merge candidates, or Relationships/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Create an object, link, relationship, or merge draft above/i),
    ).not.toBeInTheDocument();
  });

  it("groups staged memory review before technical write details", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      prepared: true,
      campaign_id: "longmont-c1",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      current_overlay_token: "a",
      proposed_assertions_digest: "b",
      confirm_token: "c",
      assertion_count: 1,
      event_count: 2,
      assertions_preview: [],
      overlay_summary: {
        existing_assertion_count: 0,
        proposed_assertion_count: 1,
        total_assertion_count: 1,
        object_count: 1,
        link_existing_count: 0,
        relationship_count: 0,
      },
      diagnostics: [],
      no_mutation_guarantees: ["Prepare wrote nothing."],
    });

    render(<Harness withPrepareCommit />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));
    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-prepare-preview")).toBeInTheDocument();
    });

    const surfaceText = screen.getByTestId("graph-object-authoring-surface").textContent ?? "";
    const reviewIndex = surfaceText.indexOf("Review staged memory");
    const technicalIndex = surfaceText.indexOf("Technical write details");
    expect(reviewIndex).toBeGreaterThanOrEqual(0);
    expect(technicalIndex).toBeGreaterThan(reviewIndex);
    expect(screen.getByTestId("graph-object-authoring-technical-write-details")).not.toHaveAttribute("open");
  });

  it("hides selected source technical metadata until Source details is expanded", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));

    expect(screen.getByText("“gang”")).toBeInTheDocument();
    const sourceDetails = screen.getByTestId("graph-object-authoring-source-details");
    expect(sourceDetails).not.toHaveAttribute("open");

    await user.click(screen.getByText("Source details"));
    expect(sourceDetails).toHaveAttribute("open");
    expect(within(sourceDetails).getByText("graph-c1s2")).toBeInTheDocument();
  });
});
