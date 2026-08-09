import { describe, expect, it } from "vitest";

import {
  healRunbookReferenceLabel,
  normalizeRunbookReferenceAttrs,
} from "./runbookReferences";

describe("healRunbookReferenceLabel", () => {
  it("unescapes markdown emphasis wrappers into a plain chip label", () => {
    expect(healRunbookReferenceLabel("\\*\\*Meat Mind\\*\\*")).toBe("Meat Mind");
  });

  it("collapses runaway backslash doubling from save/load cycles", () => {
    const runaway = "\\\\\\\\\\\\*\\\\\\\\\\\\*Meat Mind\\\\\\\\\\\\*\\\\\\\\\\\\*";
    expect(healRunbookReferenceLabel(runaway)).toBe("Meat Mind");
  });
});

describe("normalizeRunbookReferenceAttrs", () => {
  it("heals escaped graph-node labels used as chip text", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:authored:d60f9863b0faf7f586d69182a0882f1f",
      label: "\\*\\*Meat Mind\\*\\*",
    });
    expect(attrs.label).toBe("Meat Mind");
  });
});
