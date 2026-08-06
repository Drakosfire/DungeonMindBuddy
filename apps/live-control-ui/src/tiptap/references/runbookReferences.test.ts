import { describe, expect, it } from "vitest";

import {
  graphScopePresence,
  isSupportedRunbookReference,
  normalizeRunbookReferenceAttrs,
  parseGraphScopeQuery,
  runbookReferenceHref,
} from "./runbookReferences";

const NULL_SCOPE = {
  graphWorldId: null,
  graphCampaignId: null,
  graphScopeMode: null,
  graphRevisionId: null,
} as const;

const COMPLETE_SCOPE = {
  graphWorldId: "eldyrwild",
  graphCampaignId: "longmont-c2",
  graphScopeMode: "campaign" as const,
  graphRevisionId: "rev:3413bf6f5044cf2680233f5e37c90dcf",
};

describe("runbookReferences", () => {
  it("normalizes legacy graph-node attrs with null scope fields", () => {
    expect(
      normalizeRunbookReferenceAttrs({
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null Calf",
      }),
    ).toEqual({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:tripod-null-calf",
      label: "Tripod Null Calf",
      ...NULL_SCOPE,
    });
  });

  it("supports legacy graph-node refs without query", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:tripod-null-calf",
      label: "Tripod Null Calf",
    });

    expect(isSupportedRunbookReference(attrs)).toBe(true);
    expect(runbookReferenceHref(attrs)).toBe("#dmb-ref:graph-node:threat:tripod-null-calf");
  });

  it("builds canonical scoped href with ordered query keys", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:authored:d16d43d376833e38caf46dd19b1dd17f",
      label: "Mireward Latchling",
      ...COMPLETE_SCOPE,
    });

    expect(isSupportedRunbookReference(attrs)).toBe(true);
    expect(runbookReferenceHref(attrs)).toBe(
      "#dmb-ref:graph-node:threat:authored:d16d43d376833e38caf46dd19b1dd17f?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A3413bf6f5044cf2680233f5e37c90dcf",
    );
  });

  it("rejects partial scope attrs", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:tripod-null-calf",
      label: "Tripod Null Calf",
      graphWorldId: "eldyrwild",
    });

    expect(graphScopePresence(attrs)).toBe("partial");
    expect(isSupportedRunbookReference(attrs)).toBe(false);
    expect(runbookReferenceHref(attrs)).toBeNull();
  });

  it("rejects non-graph refs with scope fields", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "npc",
      refId: "lysandro-ironveil",
      label: "Lysandro Ironveil",
      ...COMPLETE_SCOPE,
    });

    expect(isSupportedRunbookReference(attrs)).toBe(false);
    expect(runbookReferenceHref(attrs)).toBeNull();
  });

  it("parses complete scoped query and preserves opaque revision colons", () => {
    expect(
      parseGraphScopeQuery(
        "?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A3413bf6f5044cf2680233f5e37c90dcf",
      ),
    ).toEqual(COMPLETE_SCOPE);
  });

  it.each([
    "?world=eldyrwild&campaign=longmont-c2&scope=campaign",
    "?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A1&extra=bad",
    "?world=eldyrwild&world=duplicate&campaign=longmont-c2&scope=campaign&revision=rev%3A1",
    "?world=%ZZ&campaign=longmont-c2&scope=campaign&revision=rev%3A1",
  ])("rejects invalid scoped query %s", (query) => {
    expect(parseGraphScopeQuery(query)).toBeNull();
  });
});
