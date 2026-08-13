import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  PlayObjectSheetProjection,
  shouldRenderPlayObjectSheet,
} from "./PlayObjectSheetProjection";
import type { GraphReferenceResolution } from "./types";

function morwinResolution(): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: "dmb-node:npc:morwin-blackwell",
    reference: null,
    graphNodeId: "npc:morwin-blackwell",
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: "npc:morwin-blackwell",
      label: "Morwin Blackwell",
      kind: "npc",
      role: "npc",
      aliases: ["Morwin"],
      source_domains: ["worldbuilding"],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: null,
    }),
    graphScope: null,
    projectionState: "ready",
    message: null,
  };
}

describe("PlayObjectSheetProjection", () => {
  it("renders Morwin play sections and Saladin connected chip", () => {
    const resolution = morwinResolution();
    const onSelect = vi.fn();
    render(
      <PlayObjectSheetProjection
        resolution={resolution}
        model={resolution.graphObject}
        onSelectRelationship={onSelect}
      />,
    );

    expect(screen.getByTestId("play-object-sheet")).toBeInTheDocument();
    expect(screen.getByText(/At the table/i)).toBeInTheDocument();
    expect(screen.getByText(/eyes and ears/i)).toBeInTheDocument();
    expect(screen.getByText(/Attitude/i)).toBeInTheDocument();
    expect(screen.getByText(/Offers & hooks/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open Saladin/i })).toBeInTheDocument();
    expect(screen.getByTestId("play-object-sheet-media")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Map of Hempholm/i })).toHaveAttribute(
      "src",
      expect.stringContaining("map-hempholm.jpg"),
    );
  });

  it("shouldRenderPlayObjectSheet is true only for bridged nodes", () => {
    expect(shouldRenderPlayObjectSheet(morwinResolution())).toBe(true);
    const other = {
      ...morwinResolution(),
      graphNodeId: "npc:stranger",
      locator: "dmb-node:npc:stranger",
    };
    expect(shouldRenderPlayObjectSheet(other)).toBe(false);
  });
});
