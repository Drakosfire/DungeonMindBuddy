import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
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
}: {
  initialSelection?: GraphAuthoringSelection;
  existingNodes?: GraphObjectAuthoringInspectedNode[];
}) {
  const draft = useGraphObjectAuthoringDraft();

  return (
    <div>
      <button type="button" onClick={() => draft.openWithSelection(initialSelection ?? selection)}>
        Open with selection
      </button>
      <GraphObjectAuthoringSurface
        selectedSource={draft.selectedSource}
        formState={draft.formState}
        proposals={draft.proposals}
        onFormFieldChange={draft.updateFormField}
        onStageProposal={draft.stageProposal}
        onRemoveProposal={draft.removeProposal}
        linkExistingFormState={draft.linkExistingFormState}
        onLinkExistingFieldChange={draft.updateLinkExistingField}
        onStageLinkExistingProposal={draft.stageLinkExistingProposal}
        relationshipFormState={draft.relationshipFormState}
        onRelationshipFieldChange={draft.updateRelationshipField}
        onStageRelationshipProposal={draft.stageRelationshipProposal}
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
    expect(screen.getByText("No object drafts staged yet.")).toBeInTheDocument();
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
    expect(stagedProposal).toHaveTextContent("Table known / player visible");
  });

  it("shows no-write copy on the staging tray once a proposal is staged", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    expect(screen.getByText("Staged locally. No graph write has happened.")).toBeInTheDocument();
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
    expect(screen.getByText("No object drafts staged yet.")).toBeInTheDocument();
  });

  it("disables staging when the label is blank", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "   " } });

    expect(screen.getByTestId("graph-object-authoring-stage-button")).toBeDisabled();
  });

  it("stages a link-existing proposal from selected text via the Link existing tab", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-mode-link-existing"));

    fireEvent.change(screen.getByLabelText("Existing object"), {
      target: { value: "manual" },
    });
    fireEvent.change(screen.getByPlaceholderText("Type a label for an object not staged yet"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-link-existing-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveAttribute("data-proposal-kind", "link_existing");
    expect(stagedProposal).toHaveTextContent("Link existing");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
    expect(stagedProposal).toHaveTextContent("gang");
    expect(screen.getByText("Staged locally. No graph write has happened.")).toBeInTheDocument();
  });

  it("disables link-existing staging until an existing object ref is chosen", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-mode-link-existing"));

    expect(screen.getByTestId("graph-object-authoring-stage-link-existing-button")).toBeDisabled();
  });

  it("keeps link-existing staging disabled when manual entry is selected but the label is blank", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-mode-link-existing"));

    fireEvent.change(screen.getByLabelText("Existing object"), {
      target: { value: "manual" },
    });

    expect(screen.getByTestId("graph-object-authoring-stage-link-existing-button")).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText("Type a label for an object not staged yet"), {
      target: { value: "   " },
    });
    expect(screen.getByTestId("graph-object-authoring-stage-link-existing-button")).toBeDisabled();
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
    expect(stagedProposal).toHaveTextContent("has_member");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
    expect(screen.getByText("Staged locally. No graph write has happened.")).toBeInTheDocument();
  });

  it("lists every quick relationship predicate in the type select", () => {
    render(<Harness />);

    const typeSelect = screen.getByLabelText("Relationship type") as HTMLSelectElement;
    const optionValues = Array.from(typeSelect.options).map((option) => option.value);
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
      target: { value: "same_as" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    const manualInputs = screen.getAllByPlaceholderText("Type a label for an object not staged yet");
    fireEvent.change(manualInputs[manualInputs.length - 1], {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    expect(screen.getByTestId("graph-object-authoring-staged-proposal")).toHaveTextContent("same_as");
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
    const existingGroup = within(sourcePicker).getByRole("group", { name: "Existing graph objects" });
    const options = within(existingGroup).getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "Alden (npc)",
      "Bonogo (pc)",
      "Grishna (npc)",
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
    const existingGroup = within(sourcePicker).getByRole("group", { name: "Existing graph objects" });
    expect(within(existingGroup).getAllByRole("option")).toHaveLength(1);
  });

  it("keeps existing object proposal staging working alongside the new proposal kinds", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Open with selection" }));
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveAttribute("data-proposal-kind", "object");
  });
});
