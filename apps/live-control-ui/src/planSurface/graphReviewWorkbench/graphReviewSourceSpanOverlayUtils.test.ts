import { describe, expect, it } from "vitest";

import type { RecapProjectionSourceSpan } from "../../api/types";
import type { GraphReviewContextualDelta, GraphReviewDeltaStatus } from "./graphReviewDeltaTypes";
import { buildSourceSpanDeltaIndex, statusLabelForSourceSpan } from "./graphReviewSourceSpanOverlayUtils";

function span(overrides: Partial<RecapProjectionSourceSpan>): RecapProjectionSourceSpan {
  return { span_id: "span-1", kind: "paragraph", ordinal: null, text_excerpt: null, line_start: null, line_end: null, ...overrides };
}

function delta(overrides: Partial<GraphReviewContextualDelta> = {}): GraphReviewContextualDelta {
  const status = overrides.status ?? "matched";
  return {
    deltaId: overrides.deltaId ?? `${status}:node:live-node-1`,
    objectKind: overrides.objectKind ?? "node",
    status,
    laneObjectRefs: overrides.laneObjectRefs ?? [
      { laneId: "live", laneRole: "live", objectKind: "node", objectId: "live-node-1", label: "Live Node" },
    ],
    label: overrides.label ?? "Live Node",
    summary: overrides.summary ?? `${status} node`,
    comparatorReason: overrides.comparatorReason ?? null,
    sourceSpanRefIds: overrides.sourceSpanRefIds ?? ["span-1"],
    primarySourceSpanRefId: overrides.primarySourceSpanRefId ?? "span-1",
    evidenceRefIds: overrides.evidenceRefIds ?? [],
    confidence: overrides.confidence ?? "high",
    metadata: overrides.metadata,
  };
}

function statusDelta(status: GraphReviewDeltaStatus, spanId = "span-1", deltaId = status) {
  return delta({ status, sourceSpanRefIds: [spanId], deltaId });
}

describe("buildSourceSpanDeltaIndex", () => {
  it("creates unclassified presentations and initialized counts for empty deltas", () => {
    const index = buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "span-1" })], deltas: [] });
    expect(index.spansById["span-1"].status).toBe("unclassified");
    expect(index.countsByStatus).toEqual({ matched: 0, live_only: 0, comparator_uncertain: 0, mixed: 0, unclassified: 1 });
  });

  it("maps matched, live-only, and uncertain deltas to source-span statuses", () => {
    expect(buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "span-1" })], deltas: [statusDelta("matched")] }).spansById["span-1"].status).toBe("matched");
    expect(buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "span-1" })], deltas: [statusDelta("live_only")] }).spansById["span-1"].status).toBe("live_only");
    expect(buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "span-1" })], deltas: [statusDelta("comparator_uncertain")] }).spansById["span-1"].status).toBe("comparator_uncertain");
  });

  it("marks matched plus live-only as mixed unless uncertain is present", () => {
    const mixed = buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "span-1" })], deltas: [statusDelta("matched", "span-1", "a"), statusDelta("live_only", "span-1", "b")] });
    expect(mixed.spansById["span-1"].status).toBe("mixed");

    const uncertain = buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "span-1" })], deltas: [...mixed.spansById["span-1"].deltas, statusDelta("comparator_uncertain", "span-1", "c")] });
    expect(uncertain.spansById["span-1"].status).toBe("comparator_uncertain");
    expect(uncertain.spansById["span-1"].primaryDelta?.deltaId).toBe("c");
  });

  it("does not attach deltas without known explicit source span refs", () => {
    const index = buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "known" })], deltas: [delta({ sourceSpanRefIds: [] }), delta({ sourceSpanRefIds: ["unknown"] })] });
    expect(index.spansById.known.deltas).toEqual([]);
    expect(index.spansById.known.status).toBe("unclassified");
    expect(index.spansById.unknown).toBeUndefined();
  });

  it("derives live node ids only from live node refs and merges evidence/reasons uniquely", () => {
    const index = buildSourceSpanDeltaIndex({
      sourceSpans: [span({ span_id: "span-1" })],
      deltas: [
        delta({
          evidenceRefIds: ["ev-2", "ev-1", "ev-1"],
          comparatorReason: "reason-b",
          laneObjectRefs: [
            { laneId: "live", laneRole: "live", objectKind: "node", objectId: "node-b" },
            { laneId: "live", laneRole: "live", objectKind: "edge", objectId: "edge-1" },
            { laneId: "gold", laneRole: "gold", objectKind: "node", objectId: "gold-node" },
          ],
        }),
        delta({ deltaId: "second", evidenceRefIds: ["ev-3", "ev-2"], comparatorReason: "reason-a", laneObjectRefs: [{ laneId: "live", laneRole: "live", objectKind: "node", objectId: "node-a" }] }),
      ],
    });
    expect(index.spansById["span-1"].liveNodeIds).toEqual(["node-a", "node-b"]);
    expect(index.spansById["span-1"].evidenceRefIds).toEqual(["ev-1", "ev-2", "ev-3"]);
    expect(index.spansById["span-1"].comparatorReasons).toEqual(["reason-a", "reason-b"]);
  });

  it("orders spans by ordinal then id", () => {
    const index = buildSourceSpanDeltaIndex({ sourceSpans: [span({ span_id: "b", ordinal: 2 }), span({ span_id: "c", ordinal: 1 }), span({ span_id: "a", ordinal: 2 })], deltas: [] });
    expect(index.orderedSpans.map((item) => item.sourceSpanRefId)).toEqual(["c", "a", "b"]);
  });
});

describe("statusLabelForSourceSpan", () => {
  it("returns labels", () => {
    expect(statusLabelForSourceSpan("matched")).toBe("Matched");
    expect(statusLabelForSourceSpan("live_only")).toBe("Live-only");
    expect(statusLabelForSourceSpan("comparator_uncertain")).toBe("Uncertain");
    expect(statusLabelForSourceSpan("mixed")).toBe("Mixed");
    expect(statusLabelForSourceSpan("unclassified")).toBe("Unclassified");
  });
});
