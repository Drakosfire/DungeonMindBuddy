import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
} from "../../graphReference/projectionBindings";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { BuildReferenceObjectProjection } from "./BuildReferenceObjectProjection";

const glowkindleNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A friendly merchant.",
};

function resolvedGraphResolution(
  node: GraphProjectionNodeView,
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: referenceFromGraphNode(node),
    graphNodeId: node.node_id,
    graphObject: buildGraphObjectCardFromNodeView(node),
    projectionState: "ready",
    message: `Resolved graph node ${node.label}.`,
  };
}

function renderWithResolution(resolution: GraphReferenceResolution) {
  return render(
    <BuildReferenceObjectProjection
      bindings={{
        [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: resolution,
      }}
    />,
  );
}

describe("BuildReferenceObjectProjection", () => {
  it("renders resolved_graph through GraphObjectProjectionCard", () => {
    renderWithResolution(resolvedGraphResolution(glowkindleNode));

    expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
    expect(screen.getByText("Glowkindle")).toBeInTheDocument();
  });

  it("shows ambiguous candidate ids without auto-select", () => {
    renderWithResolution({
      kind: "ambiguous",
      locator: "Lysandra",
      reference: null,
      matchingGraphNodeIds: ["npc-lysandra-a", "npc-lysandra-b"],
      projectionState: "ready",
      message: "Could not uniquely resolve this object from graph memory.",
    });

    const list = screen.getByTestId("build-reference-ambiguous-ids");
    expect(list).toHaveTextContent("npc-lysandra-a");
    expect(list).toHaveTextContent("npc-lysandra-b");
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
  });

  it("fail-closes resolved_corpus_fallback", () => {
    renderWithResolution({
      kind: "resolved_corpus_fallback",
      locator: "npc:old-index",
      reference: {
        kind: "ref",
        refType: "npc",
        refId: "npc-old",
        label: "Old Index NPC",
      },
      fallback: {
        status: "resolved",
        ref: {
          kind: "ref",
          refType: "npc",
          refId: "npc-old",
          label: "Old Index NPC",
        },
        message: "Corpus index found a match.",
      },
      projectionState: "ready",
      message: "Corpus index found a match.",
    });

    expect(screen.getByTestId("build-reference-corpus-fallback-blocked")).toBeInTheDocument();
    expect(screen.getByText(/World Graph inspection only/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
  });

  it("wires relationship navigation through graph reference binding", async () => {
    const openResolvedReference = vi.fn();
    const resolveRelationship = vi.fn(async () => resolvedGraphResolution(glowkindleNode));

    render(
      <BuildReferenceObjectProjection
        bindings={{
          [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: resolvedGraphResolution(glowkindleNode),
          [GRAPH_REFERENCE_BINDING_ID]: {
            resolverState: "ready",
            resolveRelationship,
            openResolvedReference,
            openTool: vi.fn(),
          },
        }}
      />,
    );

    expect(screen.getByTestId("graph-object-projection-card")).toBeInTheDocument();
  });
});
