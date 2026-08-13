import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { ResolvedGraphObjectProjection } from "./ResolvedGraphObjectProjection";
import type { GraphReferenceResolution } from "./types";

vi.mock("../statblocks/projection/ThreatSheetProjection", () => ({
  ThreatSheetProjection: () => <div data-testid="threat-sheet-stub" />,
}));

function resolvedNpc(nodeId: string, label: string): Extract<
  GraphReferenceResolution,
  { kind: "resolved_graph" }
> {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${nodeId}`,
    reference: null,
    graphNodeId: nodeId,
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: nodeId,
      label,
      kind: "npc",
      role: "npc",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: null,
    }),
    graphScope: {
      worldId: "of-conks-cons",
      campaignId: "of-conks-cons",
      revisionId: "rev-1",
      scopeMode: "exact",
    },
    projectionState: "ready",
    message: null,
  };
}

describe("ResolvedGraphObjectProjection play fork", () => {
  it("renders Play Object Sheet for Morwin", () => {
    render(
      <ResolvedGraphObjectProjection resolution={resolvedNpc("npc:morwin-blackwell", "Morwin")} />,
    );
    expect(screen.getByTestId("play-object-sheet")).toBeInTheDocument();
    expect(screen.queryByTestId("threat-sheet-stub")).not.toBeInTheDocument();
  });

  it("keeps GraphObjectCard for non-bridged NPCs", () => {
    render(
      <ResolvedGraphObjectProjection
        resolution={resolvedNpc("npc:stranger", "Stranger")}
        aria-label="Stranger graph object"
      />,
    );
    expect(screen.queryByTestId("play-object-sheet")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Stranger graph object")).toBeInTheDocument();
  });
});
