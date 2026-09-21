import { describe, expect, it } from "vitest";

import {
  fuzzySearchScore,
  rankGraphObjectAuthoringSearchItems,
  type GraphObjectAuthoringSearchItem,
} from "./graphObjectAuthoringSearch";

const items: GraphObjectAuthoringSearchItem[] = [
  {
    key: "questionable-company",
    label: "Questionable Company",
    group: "Party / PCs",
    meta: "Party / PCs · party",
    searchText: "Questionable Company questionable company",
  },
  {
    key: "quiet-company",
    label: "Quiet Company",
    group: "Current recap",
    meta: "Current recap · party",
    searchText: "Quiet Company",
  },
];

describe("graphObjectAuthoringSearch", () => {
  it("scores exact, substring, and subsequence matches while rejecting misses", () => {
    expect(fuzzySearchScore("questionable company", "Questionable Company")).toBeGreaterThan(
      fuzzySearchScore("questionable", "Questionable Company")!,
    );
    expect(fuzzySearchScore("q company", "Questionable Company")).not.toBeNull();
    expect(fuzzySearchScore("zzzz", "Questionable Company")).toBeNull();
  });

  it("ranks a useful fuzzy match ahead of a weaker match", () => {
    expect(rankGraphObjectAuthoringSearchItems(items, "questionable company").map(({ item }) => item.key)).toEqual([
      "questionable-company",
    ]);
  });
});
