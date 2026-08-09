import { describe, expect, it } from "vitest";

import { readOpenNodeFromSearch, stripOpenNodeFromLocation } from "./planOpenNodeDeepLink";

describe("planOpenNodeDeepLink", () => {
  it("reads openNode from Plan search", () => {
    expect(
      readOpenNodeFromSearch(
        "?campaign=longmont-c2&openNode=threat%3Aauthored%3Ad60f9863b0faf7f586d69182a0882f1f",
      ),
    ).toBe("threat:authored:d60f9863b0faf7f586d69182a0882f1f");
    expect(readOpenNodeFromSearch("?campaign=longmont-c2")).toBeNull();
    expect(readOpenNodeFromSearch("")).toBeNull();
  });

  it("strips openNode while preserving sibling params", () => {
    expect(
      stripOpenNodeFromLocation(
        "/plan",
        "?campaign=longmont-c2&openNode=threat:authored:abc&session=26",
      ),
    ).toBe("/plan?campaign=longmont-c2&session=26");
  });
});
