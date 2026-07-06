import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import { GraphObjectAuthoringSurface } from "./GraphObjectAuthoringSurface";
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

function Harness({ initialSelection }: { initialSelection?: GraphAuthoringSelection }) {
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
});
