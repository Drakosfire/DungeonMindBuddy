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

  it("round-trips opaque revision identities including %, path segments, parentheses, and Unicode", () => {
    const opaqueRevisions = [
      "rev%",
      "rev/nested",
      "rev(1)",
      "rev:café-Δ",
      "rev:inner  spaces",
    ];

    for (const revisionId of opaqueRevisions) {
      const attrs = normalizeRunbookReferenceAttrs({
        kind: "ref",
        refType: "graph-node",
        refId: "threat:authored:d16d43d376833e38caf46dd19b1dd17f",
        label: "Mireward Latchling",
        ...COMPLETE_SCOPE,
        graphRevisionId: revisionId,
      });
      const href = runbookReferenceHref(attrs);
      expect(href).toBeTruthy();
      const query = href!.slice(href!.indexOf("?"));
      expect(parseGraphScopeQuery(query)).toEqual({
        ...COMPLETE_SCOPE,
        graphRevisionId: revisionId,
      });
      expect(href).not.toMatch(/revision=[^&]*[()]/);
    }
  });

  it("treats omitted and undefined scope fields as absent legacy, not partial", () => {
    expect(graphScopePresence({})).toBe("none");
    expect(
      graphScopePresence({
        graphWorldId: undefined,
        graphCampaignId: undefined,
        graphScopeMode: undefined,
        graphRevisionId: undefined,
      }),
    ).toBe("none");
  });

  it("preserves internal opaque whitespace while trimming ends only", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:tripod-null-calf",
      label: "Tripod",
      graphWorldId: "  eldyrwild  ",
      graphCampaignId: "longmont-c2",
      graphScopeMode: "campaign",
      graphRevisionId: "  rev:inner  spaces  ",
    });
    expect(attrs.graphWorldId).toBe("eldyrwild");
    expect(attrs.graphRevisionId).toBe("rev:inner  spaces");
  });

  it.each([
    "?world=eldyrwild&campaign=longmont-c2&scope=campaign",
    "?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A1&extra=bad",
    "?world=eldyrwild&world=duplicate&campaign=longmont-c2&scope=campaign&revision=rev%3A1",
    "?world=%ZZ&campaign=longmont-c2&scope=campaign&revision=rev%3A1",
    "?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%",
  ])("rejects invalid scoped query %s", (query) => {
    expect(parseGraphScopeQuery(query)).toBeNull();
  });
});
