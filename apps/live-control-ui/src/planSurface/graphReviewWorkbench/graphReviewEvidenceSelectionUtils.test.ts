import { describe, expect, it } from "vitest";

import type { GraphReviewContextualDelta } from "./graphReviewDeltaTypes";
import { buildEvidenceSelectionForDelta, evidenceApiObjectKind } from "./graphReviewEvidenceSelectionUtils";

function delta(overrides: Partial<GraphReviewContextualDelta> = {}): GraphReviewContextualDelta {
  return {
    deltaId: "delta-1",
    objectKind: "node",
    status: "matched",
    laneObjectRefs: [],
    label: "Lysandra",
    summary: "Matched node.",
    sourceSpanRefIds: [],
    evidenceRefIds: [],
    ...overrides,
  };
}

describe("buildEvidenceSelectionForDelta", () => {
  it("returns no_object_ref for a null delta", () => {
    expect(buildEvidenceSelectionForDelta(null).status).toBe("no_object_ref");
  });

  it("prefers the gold ref for matched deltas", () => {
    const selection = buildEvidenceSelectionForDelta(delta({
      laneObjectRefs: [
        { laneId: "gold", laneRole: "gold", objectKind: "node", objectId: "gold-node" },
        { laneId: "live", laneRole: "live", objectKind: "node", objectId: "live-node" },
      ],
    }));
    expect(selection.status).toBe("queryable");
    expect(selection.queryObjectKind).toBe("nodes");
    expect(selection.queryObjectId).toBe("gold-node");
    expect(selection.preferredRef?.laneRole).toBe("gold");
  });

  it("makes gold-only deltas queryable", () => {
    const selection = buildEvidenceSelectionForDelta(delta({
      status: "gold_only",
      laneObjectRefs: [{ laneId: "gold", laneRole: "gold", objectKind: "edge", objectId: "gold-edge" }],
    }));
    expect(selection.status).toBe("queryable");
    expect(selection.queryObjectKind).toBe("edges");
  });

  it("does not query live-only deltas without a gold ref", () => {
    const selection = buildEvidenceSelectionForDelta(delta({
      status: "live_only",
      laneObjectRefs: [{ laneId: "live", laneRole: "live", objectKind: "node", objectId: "live-node" }],
    }));
    expect(selection.status).toBe("live_only_no_gold");
    expect(selection.queryObjectId).toBeUndefined();
  });

  it("returns no_object_ref for comparator-uncertain deltas with no refs", () => {
    const selection = buildEvidenceSelectionForDelta(delta({ status: "comparator_uncertain", comparatorReason: "Missing pair." }));
    expect(selection.status).toBe("no_object_ref");
    expect(selection.reason).toBe("Missing pair.");
  });

  it("queries comparator-uncertain deltas when a gold ref exists", () => {
    const selection = buildEvidenceSelectionForDelta(delta({
      status: "comparator_uncertain",
      laneObjectRefs: [{ laneId: "gold", laneRole: "gold", objectKind: "beat", objectId: "gold-beat" }],
    }));
    expect(selection.status).toBe("queryable");
    expect(selection.queryObjectKind).toBe("beats");
  });

  it("maps local object kinds to evidence API section kinds", () => {
    expect(evidenceApiObjectKind("node")).toBe("nodes");
    expect(evidenceApiObjectKind("edge")).toBe("edges");
    expect(evidenceApiObjectKind("beat")).toBe("beats");
    expect(evidenceApiObjectKind("write")).toBe("proposed_writes");
    expect(evidenceApiObjectKind("ignored_item")).toBe("ignored_items");
    expect(evidenceApiObjectKind("deferred_item")).toBe("deferred_items");
  });

  it("returns unsupported_object_kind for unsupported gold refs", () => {
    const selection = buildEvidenceSelectionForDelta(delta({
      laneObjectRefs: [{ laneId: "gold", laneRole: "gold", objectKind: "mention", objectId: "gold-mention" }],
    }));
    expect(selection.status).toBe("unsupported_object_kind");
  });
});
