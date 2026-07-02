import { describe, expect, it } from "vitest";

import type { GraphReviewContextualDelta, GraphReviewDeltaStatus } from "./graphReviewDeltaTypes";
import { buildLiveNodeDeltaPresentationIndex, statusLabelForPill } from "./graphReviewPillOverlayUtils";

function delta(overrides: Partial<GraphReviewContextualDelta> = {}): GraphReviewContextualDelta {
  const status = overrides.status ?? "matched";
  return {
    deltaId: overrides.deltaId ?? `${status}:node:live:node:live-node-1`,
    objectKind: overrides.objectKind ?? "node",
    status,
    laneObjectRefs: overrides.laneObjectRefs ?? [
      { laneId: "live-lane", laneRole: "live", objectKind: "node", objectId: "live-node-1", label: "Live Node", matchScore: 0.9 },
    ],
    label: overrides.label ?? "Live Node",
    summary: overrides.summary ?? `${status} node`,
    comparatorReason: overrides.comparatorReason ?? null,
    sourceSpanRefIds: overrides.sourceSpanRefIds ?? [],
    primarySourceSpanRefId: overrides.primarySourceSpanRefId ?? null,
    evidenceRefIds: overrides.evidenceRefIds ?? [],
    confidence: overrides.confidence ?? "high",
    metadata: overrides.metadata,
  };
}

function nodeDelta(status: GraphReviewDeltaStatus, nodeId: string, deltaId = `${status}:${nodeId}`) {
  return delta({
    deltaId,
    status,
    laneObjectRefs: [
      { laneId: "live-lane", laneRole: "live", objectKind: "node", objectId: nodeId, label: nodeId, matchScore: 0.75 },
    ],
    label: nodeId,
  });
}

describe("buildLiveNodeDeltaPresentationIndex", () => {
  it("maps matched live node deltas to node ids", () => {
    const index = buildLiveNodeDeltaPresentationIndex([nodeDelta("matched", "live-node-1")]);
    expect(index["live-node-1"].status).toBe("matched");
  });

  it("maps live-only live node deltas to node ids", () => {
    const index = buildLiveNodeDeltaPresentationIndex([nodeDelta("live_only", "live-node-2")]);
    expect(index["live-node-2"].status).toBe("live_only");
  });

  it("maps comparator-uncertain deltas when they include a live node ref", () => {
    const index = buildLiveNodeDeltaPresentationIndex([nodeDelta("comparator_uncertain", "live-node-3")]);
    expect(index["live-node-3"].status).toBe("comparator_uncertain");
  });

  it("does not map gold-only deltas onto live pills", () => {
    const index = buildLiveNodeDeltaPresentationIndex([
      delta({
        deltaId: "gold-only",
        status: "gold_only",
        laneObjectRefs: [{ laneId: "gold-lane", laneRole: "gold", objectKind: "node", objectId: "gold-node-1" }],
      }),
    ]);
    expect(index).toEqual({});
  });

  it("does not infer edge deltas onto endpoint nodes", () => {
    const index = buildLiveNodeDeltaPresentationIndex([
      delta({
        deltaId: "live-edge",
        objectKind: "edge",
        status: "live_only",
        laneObjectRefs: [{ laneId: "live-lane", laneRole: "live", objectKind: "edge", objectId: "edge-1" }],
      }),
    ]);
    expect(index).toEqual({});
  });

  it("chooses primary status by comparator_uncertain, live_only, matched, unclassified priority", () => {
    const index = buildLiveNodeDeltaPresentationIndex([
      nodeDelta("matched", "live-node-1", "c-matched"),
      nodeDelta("changed_label", "live-node-1", "b-unclassified"),
      nodeDelta("live_only", "live-node-1", "a-live-only"),
      nodeDelta("comparator_uncertain", "live-node-1", "d-uncertain"),
    ]);
    expect(index["live-node-1"].status).toBe("comparator_uncertain");
    expect(index["live-node-1"].primaryDelta?.deltaId).toBe("d-uncertain");
  });

  it("merges source span refs and evidence refs uniquely", () => {
    const index = buildLiveNodeDeltaPresentationIndex([
      delta({ deltaId: "a", sourceSpanRefIds: ["span-2", "span-1"], evidenceRefIds: ["ev-2", "ev-1"] }),
      delta({ deltaId: "b", sourceSpanRefIds: ["span-1", "span-3"], evidenceRefIds: ["ev-1", "ev-3"] }),
    ]);
    expect(index["live-node-1"].sourceSpanRefIds).toEqual(["span-1", "span-2", "span-3"]);
    expect(index["live-node-1"].evidenceRefIds).toEqual(["ev-1", "ev-2", "ev-3"]);
  });

  it("returns deterministic keys and delta ordering", () => {
    const index = buildLiveNodeDeltaPresentationIndex([
      nodeDelta("matched", "node-b", "delta-b2"),
      nodeDelta("matched", "node-a", "delta-a"),
      nodeDelta("live_only", "node-b", "delta-b1"),
    ]);
    expect(Object.keys(index)).toEqual(["node-a", "node-b"]);
    expect(index["node-b"].deltas.map((item) => item.deltaId)).toEqual(["delta-b1", "delta-b2"]);
  });
});

describe("statusLabelForPill", () => {
  it("returns display labels", () => {
    expect(statusLabelForPill("matched")).toBe("Matched");
    expect(statusLabelForPill("live_only")).toBe("Live-only");
    expect(statusLabelForPill("comparator_uncertain")).toBe("Uncertain");
    expect(statusLabelForPill("unclassified")).toBe("Unclassified");
  });
});
