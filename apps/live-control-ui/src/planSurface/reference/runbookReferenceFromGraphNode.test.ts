import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import {
  isSupportedRunbookReference,
  runbookReferenceHref,
} from "../../tiptap/references/runbookReferences";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { resolvePlanReferenceFromGraphProjection } from "./graphAwareReferenceResolver";
import { runbookReferenceFromGraphNode } from "./runbookReferenceFromGraphNode";
import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";

function node(
  overrides: Partial<GraphProjectionNodeView> & Pick<GraphProjectionNodeView, "node_id" | "label" | "kind">,
): GraphProjectionNodeView {
  return {
    role: "npc",
    aliases: [],
    source_domains: [],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    ...overrides,
  };
}

const tripodWorldNode: WorldGraphProjectionNodeView = {
  nodeId: "threat:tripod-null-calf",
  label: "Tripod Null-Calf",
  kind: "threat",
  role: "threat",
  aliases: ["Tripod"],
  sourceDomains: ["statblock"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "Mireward north-gate pressure.",
};

const projection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    revisionId: "rev:8356c358675a7eb801101f1a49dcdccc",
    headRevisionId: "rev:8356c358675a7eb801101f1a49dcdccc",
    isHead: true,
    focus: { kind: "session", sessionId: "session-21" },
    admissibility: "gm",
  },
  summary: {
    nodeCount: 1,
    relationshipCount: 0,
    attributeCount: 0,
    evidenceCount: 0,
    sourceArtifactCount: 0,
    projectionTruncated: false,
  },
  nodes: [tripodWorldNode],
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

describe("runbookReferenceFromGraphNode", () => {
  it("emits graph-native refs that preserve exact durable node ids", () => {
    expect(
      runbookReferenceFromGraphNode(
        node({
          node_id: "threat:tripod-null-calf",
          label: "Tripod Null-Calf",
          kind: "threat",
        }),
      ),
    ).toEqual({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
    });
  });

  it("does not sanitize colon-delimited ids or remap kinds onto corpus types", () => {
    const attrs = runbookReferenceFromGraphNode(
      node({ node_id: "npc:glowkindle", label: "Glowkindle", kind: "actor" }),
    );
    expect(attrs).toEqual({
      kind: "ref",
      refType: "graph-node",
      refId: "npc:glowkindle",
      label: "Glowkindle",
    });
    expect(isSupportedRunbookReference(attrs)).toBe(true);
    expect(runbookReferenceHref(attrs)).toBe("#dmb-ref:graph-node:npc:glowkindle");
  });

  it("round-trips a threat chip through save/reload and resolves by durable id", () => {
    const attrs = runbookReferenceFromGraphNode(
      node({
        node_id: "threat:tripod-null-calf",
        label: "Tripod Null-Calf",
        kind: "threat",
      }),
    );

    expect(isSupportedRunbookReference(attrs)).toBe(true);
    const href = runbookReferenceHref(attrs);
    expect(href).toBe("#dmb-ref:graph-node:threat:tripod-null-calf");

    const markdown = `[${attrs.label}](${href})`;
    const imported = markdownToTiptapDoc(markdown);
    const paragraph = (imported.doc.content[0] as { content: Array<{ type: string; attrs?: Record<string, string> }> });
    const chip = paragraph.content.find((entry) => entry.type === "runbookReference");
    expect(chip?.attrs).toMatchObject({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
    });

    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toContain("#dmb-ref:graph-node:threat:tripod-null-calf");

    const reloaded = markdownToTiptapDoc(exported);
    const reloadedParagraph = (reloaded.doc.content[0] as {
      content: Array<{ type: string; attrs?: Record<string, string> }>;
    });
    const reloadedChip = reloadedParagraph.content.find((entry) => entry.type === "runbookReference");
    expect(reloadedChip?.attrs?.refId).toBe("threat:tripod-null-calf");

    const resolution = resolvePlanReferenceFromGraphProjection({
      ref: {
        kind: "ref",
        refType: String(reloadedChip?.attrs?.refType ?? ""),
        refId: String(reloadedChip?.attrs?.refId ?? ""),
        label: String(reloadedChip?.attrs?.label ?? ""),
      },
      projection,
    });

    expect(resolution.kind).toBe("graph-node");
    expect(resolution.graphNodeId).toBe("threat:tripod-null-calf");
    expect(resolution.source).toBe("world-graph");
    expect(resolution.graphObject?.label).toBe("Tripod Null-Calf");
  });
});
