import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY,
  GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS,
  createDefaultGraphObjectAuthoringFormState,
  createDefaultGraphObjectAuthoringLinkExistingFormState,
  createDefaultGraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import { GraphObjectAuthoringVisibilitySection } from "./GraphObjectAuthoringVisibilitySection";

describe("GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS", () => {
  it("includes separate Table known and Player visible options", () => {
    const labels = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.map((option) => option.label);
    expect(labels).toContain("Table known");
    expect(labels).toContain("Player visible");
    expect(labels).not.toContain("Table known / player visible");
  });

  it("keeps gm_private as the default visibility", () => {
    expect(GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY).toBe("gm_private");
    expect(createDefaultGraphObjectAuthoringFormState(null).visibility).toBe("gm_private");
    expect(createDefaultGraphObjectAuthoringLinkExistingFormState().visibility).toBe("gm_private");
    expect(createDefaultGraphObjectAuthoringRelationshipFormState().visibility).toBe("gm_private");
  });

  it("includes notes for every visibility option", () => {
    for (const option of GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS) {
      expect(option.note?.trim()).toBeTruthy();
    }
  });
});

describe("GraphObjectAuthoringVisibilitySection", () => {
  it("shows the selected visibility note for player visible", () => {
    render(
      <GraphObjectAuthoringVisibilitySection
        visibility="player_visible"
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Visibility")).toHaveValue("player_visible");
    expect(screen.getByText(/Safe to show in future player-facing views/i)).toBeInTheDocument();
  });

  it("can select player_visible from the dropdown", () => {
    const onChange = vi.fn();
    render(
      <GraphObjectAuthoringVisibilitySection
        visibility="gm_private"
        onChange={onChange}
      />,
    );

    fireEvent.change(screen.getByLabelText("Visibility"), {
      target: { value: "player_visible" },
    });
    expect(onChange).toHaveBeenCalledWith("player_visible");
  });
});
