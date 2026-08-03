import { describe, expect, it } from "vitest";

import {
  sameStringSetMembership,
  stabilizeStringSetMembership,
} from "./projectionCatalogMembership";

describe("projectionCatalogMembership", () => {
  it("treats equal Sets as the same membership regardless of insertion order", () => {
    expect(sameStringSetMembership(new Set(["a", "b"]), new Set(["b", "a"]))).toBe(true);
    expect(sameStringSetMembership(new Set(["a"]), new Set(["a", "b"]))).toBe(false);
  });

  it("does not collapse delimiter-containing IDs into multi-ID membership", () => {
    const composed = new Set(["a\0b"]);
    const splitPair = new Set(["a", "b"]);
    expect(sameStringSetMembership(composed, splitPair)).toBe(false);

    const stable = stabilizeStringSetMembership(new Set(), ["a\0b"]);
    expect(stable.has("a\0b")).toBe(true);
    expect(stable.has("a")).toBe(false);
    expect(stable.has("b")).toBe(false);
    expect(stabilizeStringSetMembership(stable, ["a\0b"])).toBe(stable);
    expect(stabilizeStringSetMembership(stable, ["a", "b"])).not.toBe(stable);
  });
});
