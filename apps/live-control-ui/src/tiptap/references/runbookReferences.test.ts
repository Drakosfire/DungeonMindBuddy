import { describe, expect, it } from "vitest";

import {
  healRunbookReferenceLabel,
  normalizeRunbookReferenceAttrs,
  normalizeSemanticReferenceLabel,
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

describe("normalizeSemanticReferenceLabel", () => {
  it("trims without stripping literal emphasis characters", () => {
    expect(normalizeSemanticReferenceLabel("  **Meat Mind**  ")).toBe("**Meat Mind**");
    expect(normalizeSemanticReferenceLabel("  __Meat Mind__  ")).toBe("__Meat Mind__");
  });
});

describe("normalizeRunbookReferenceAttrs", () => {
  it("preserves parser-derived literal emphasis characters by default", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:authored:d60f9863b0faf7f586d69182a0882f1f",
      label: "**Meat Mind**",
    });
    expect(attrs.label).toBe("**Meat Mind**");
  });

  it("still heals escaped labels when labelSource is legacy", () => {
    const attrs = normalizeRunbookReferenceAttrs(
      {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:authored:d60f9863b0faf7f586d69182a0882f1f",
        label: "\\*\\*Meat Mind\\*\\*",
      },
      { labelSource: "legacy" },
    );
    expect(attrs.label).toBe("Meat Mind");
  });
});
