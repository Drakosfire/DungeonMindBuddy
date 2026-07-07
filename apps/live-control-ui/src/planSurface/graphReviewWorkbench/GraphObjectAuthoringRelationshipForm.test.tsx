import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  buildGraphObjectAuthoringRelationshipProposal,
  buildManualObjectRef,
  buildObjectRefFromInspectedNode,
  createDefaultGraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import { GraphObjectAuthoringRelationshipForm } from "./GraphObjectAuthoringRelationshipForm";

const sourceRef = buildObjectRefFromInspectedNode({ node_id: "group", label: "the group", kind: "party" });
const targetRef = buildObjectRefFromInspectedNode({ node_id: "glowkindle", label: "Glowkindle", kind: "npc" });

function renderForm(
  overrides: Partial<ReturnType<typeof createDefaultGraphObjectAuthoringRelationshipFormState>> = {},
) {
  const formState = {
    ...createDefaultGraphObjectAuthoringRelationshipFormState(),
    sourceObjectRef: sourceRef,
    targetObjectRef: targetRef,
    relationshipType: "threatens",
    ...overrides,
  };
  const onChange = vi.fn();
  render(
    <GraphObjectAuthoringRelationshipForm
      formState={formState}
      onChange={onChange}
      proposals={[]}
    />,
  );
  return { onChange, formState };
}

describe("GraphObjectAuthoringRelationshipForm", () => {
  it("displays human-facing labels in the relationship type select", () => {
    renderForm();

    const typeSelect = screen.getByLabelText("Relationship type") as HTMLSelectElement;
    const optionLabels = Array.from(typeSelect.options).map((option) => option.textContent);
    expect(optionLabels).toContain("has member");
    expect(optionLabels).toContain("threatens");
    expect(optionLabels).not.toContain("has_member");
  });

  it("does not use same_as in the custom predicate placeholder", () => {
    renderForm({ relationshipType: "" });

    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "__custom__" },
    });

    expect(screen.getByLabelText("Custom relationship type")).toHaveAttribute(
      "placeholder",
      expect.not.stringContaining("same_as"),
    );
  });

  it("renders a campaign-language preview sentence", () => {
    renderForm();

    expect(screen.getByTestId("graph-object-authoring-relationship-preview")).toHaveTextContent(
      "Preview: the group threatens Glowkindle",
    );
  });

  it("shows a hint when source or target is missing", () => {
    render(
      <GraphObjectAuthoringRelationshipForm
        formState={createDefaultGraphObjectAuthoringRelationshipFormState()}
        onChange={vi.fn()}
        proposals={[]}
      />,
    );

    expect(screen.getByTestId("graph-object-authoring-relationship-preview")).toHaveTextContent(
      "Choose two objects to preview the relationship.",
    );
  });

  it("warns when a custom predicate looks identity-like", () => {
    renderForm({ relationshipType: "same_as" });

    expect(screen.getByTestId("graph-object-authoring-identity-predicate-warning")).toHaveTextContent(
      /Link existing/i,
    );
  });

  it("warns and blocks same exact source/target object refs in the surface guard helper", () => {
    renderForm({ targetObjectRef: sourceRef });

    expect(screen.getByTestId("graph-object-authoring-same-object-warning")).toHaveTextContent(
      /Source and target are the same object/i,
    );
  });

  it("allows same label on different existing node IDs", () => {
    const glowkindleCharacter = buildObjectRefFromInspectedNode({
      node_id: "glowkindle-char",
      label: "Glowkindle",
      kind: "npc",
    });
    const glowkindleFaction = buildObjectRefFromInspectedNode({
      node_id: "glowkindle-faction",
      label: "Glowkindle",
      kind: "faction",
    });

    renderForm({
      sourceObjectRef: glowkindleCharacter,
      targetObjectRef: glowkindleFaction,
    });

    expect(screen.queryByTestId("graph-object-authoring-same-object-warning")).not.toBeInTheDocument();
  });
});

describe("buildGraphObjectAuthoringRelationshipProposal with player_visible", () => {
  it("preserves player_visible in the staged payload", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: targetRef,
      relationshipType: "threatens",
      visibility: "player_visible" as const,
    };
    const proposal = buildGraphObjectAuthoringRelationshipProposal(formState, null, "local-rel-player");

    expect(proposal?.visibility.visibility).toBe("player_visible");
  });
});
