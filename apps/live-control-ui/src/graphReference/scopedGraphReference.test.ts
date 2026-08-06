import { describe, expect, it } from "vitest";

import {
  exactScopeFromReferenceAttrs,
  exactScopesEqual,
  graphScopePresence,
  referenceAttrsWithExactScope,
} from "./scopedGraphReference";

const EXACT_SCOPE = {
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  scopeMode: "campaign" as const,
  revisionId: "rev:3413bf6f5044cf2680233f5e37c90dcf",
};

describe("scopedGraphReference", () => {
  it("maps complete attrs to exact scope", () => {
    const attrs = referenceAttrsWithExactScope(
      {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:authored:d16d43d376833e38caf46dd19b1dd17f",
        label: "Mireward Latchling",
      },
      EXACT_SCOPE,
    );

    expect(exactScopeFromReferenceAttrs(attrs)).toEqual(EXACT_SCOPE);
    expect(graphScopePresence(attrs)).toBe("complete");
  });

  it("returns null exact scope for partial attrs without downgrading presence", () => {
    const attrs = referenceAttrsWithExactScope(
      {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null Calf",
      },
      EXACT_SCOPE,
    );

    const partial = {
      ...attrs,
      graphCampaignId: null,
    };

    expect(exactScopeFromReferenceAttrs(partial)).toBeNull();
    expect(graphScopePresence(partial)).toBe("partial");
  });

  it("compares exact scopes by value", () => {
    expect(exactScopesEqual(EXACT_SCOPE, { ...EXACT_SCOPE })).toBe(true);
    expect(exactScopesEqual(EXACT_SCOPE, { ...EXACT_SCOPE, revisionId: "rev:other" })).toBe(false);
  });
});
