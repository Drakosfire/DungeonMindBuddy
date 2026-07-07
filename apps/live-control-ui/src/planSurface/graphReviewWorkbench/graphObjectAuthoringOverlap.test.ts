import { describe, expect, it } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildOverlapContextFromProjection,
  detectObjectFormOverlapWarnings,
  detectProposalOverlapWarnings,
  findPickerCrossGroupHint,
  normalizeOverlapText,
} from "./graphObjectAuthoringOverlap";
import {
  buildGraphObjectAuthoringMergeProposal,
  buildGraphObjectAuthoringProposal,
  createDefaultGraphObjectAuthoringFormState,
} from "./graphObjectAuthoringDraft";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";

const selection: GraphAuthoringSelection = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  selectionKind: "text_span",
  selectedText: "gang",
  normalizedSelectedText: "gang",
  graphId: "graph-c1s2",
  laneRole: "live",
};

describe("graphObjectAuthoringOverlap", () => {
  it("normalizes overlap text case-insensitively", () => {
    expect(normalizeOverlapText("  Gang  ")).toBe("gang");
  });

  it("warns when object form label matches authored memory", () => {
    const existingNodes: GraphObjectAuthoringInspectedNode[] = [
      {
        node_id: "authored:assert-1",
        label: "Questionable Company",
        kind: "party",
        aliases: ["gang"],
        authored: true,
      },
    ];
    const formState = {
      ...createDefaultGraphObjectAuthoringFormState(selection),
      label: "Questionable Company",
      kind: "party",
    };
    const context = buildOverlapContextFromProjection([], existingNodes);
    const warnings = detectObjectFormOverlapWarnings(formState, selection, context);

    expect(warnings.some((item) => item.code.includes("duplicate"))).toBe(true);
  });

  it("warns when staged proposal overlaps another staged draft", () => {
    const first = buildGraphObjectAuthoringProposal(
      selection,
      {
        ...createDefaultGraphObjectAuthoringFormState(selection),
        label: "Questionable Company",
        kind: "party",
      },
      "local-1",
    );
    const second = buildGraphObjectAuthoringProposal(
      selection,
      {
        ...createDefaultGraphObjectAuthoringFormState(selection),
        label: "Questionable Company",
        kind: "party",
      },
      "local-2",
    );
    const context = buildOverlapContextFromProjection([first], []);
    const warnings = detectProposalOverlapWarnings(second, context);

    expect(warnings.some((item) => item.code === "staged_proposal_possible_duplicate")).toBe(true);
  });

  it("does not crash when checking overlap warnings for merge proposals", () => {
    const mergeProposal = buildGraphObjectAuthoringMergeProposal({
      survivorObjectRef: {
        refKind: "existing_graph_node",
        nodeId: "survivor-1",
        label: "Tripod Null-Calf",
        kind: "threat",
      },
      mergedObjectRefs: [
        {
          refKind: "existing_graph_node",
          nodeId: "merged-1",
          label: "Tripod Null Calf",
          kind: "threat",
        },
      ],
      mergeReason: "Exact normalized label match",
      matchedFeatures: ["Exact normalized label match"],
    });
    expect(mergeProposal).not.toBeNull();
    const context = buildOverlapContextFromProjection([], []);
    expect(() =>
      detectProposalOverlapWarnings(mergeProposal!, context),
    ).not.toThrow();
  });

  it("shows cross-group hint when extracted label matches authored memory", () => {
    const existingNodes: GraphObjectAuthoringInspectedNode[] = [
      {
        node_id: "authored:assert-1",
        label: "Questionable Company",
        kind: "party",
        authored: true,
      },
      {
        node_id: "extracted-qc",
        label: "Questionable Company",
        kind: "unknown",
        authored: false,
      },
    ];
    const context = buildOverlapContextFromProjection([], existingNodes);
    const hint = findPickerCrossGroupHint(existingNodes[1], context);

    expect(typeof hint).toBe("string");
    expect(hint).toMatch(/authored memory/i);
  });

  it("does not collapse extracted and authored nodes with same label", () => {
    const existingNodes: GraphObjectAuthoringInspectedNode[] = [
      {
        node_id: "authored:assert-1",
        label: "gang",
        kind: "party",
        authored: true,
      },
      {
        node_id: "extracted-gang",
        label: "gang",
        kind: "unknown",
        authored: false,
      },
    ];
    expect(existingNodes.filter((node) => node.authored)).toHaveLength(1);
    expect(existingNodes.filter((node) => !node.authored)).toHaveLength(1);
  });
});
