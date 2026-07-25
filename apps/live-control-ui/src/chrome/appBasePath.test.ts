import { describe, expect, it } from "vitest";

import { appHref, isBuddyPath, stripAppBasePath } from "./appBasePath";

describe("appBasePath", () => {
  it("prefixes app routes with the Vite base", () => {
    expect(appHref("/")).toMatch(/\/dungeonbuddy\/?$/);
    expect(appHref("/plan")).toBe("/dungeonbuddy/plan");
    expect(appHref("/ingest?session=session-23")).toBe("/dungeonbuddy/ingest?session=session-23");
    expect(appHref("/plan?tool=recap#top")).toBe("/dungeonbuddy/plan?tool=recap#top");
  });

  it("strips the Buddy base for route matching", () => {
    expect(stripAppBasePath("/dungeonbuddy")).toBe("/");
    expect(stripAppBasePath("/dungeonbuddy/")).toBe("/");
    expect(stripAppBasePath("/dungeonbuddy/plan")).toBe("/plan");
    expect(stripAppBasePath("/dungeonbuddy/ingest")).toBe("/ingest");
  });

  it("recognizes Buddy mount paths", () => {
    expect(isBuddyPath("/dungeonbuddy")).toBe(true);
    expect(isBuddyPath("/dungeonbuddy/plan")).toBe(true);
    expect(isBuddyPath("/")).toBe(false);
    expect(isBuddyPath("/ruleslawyer")).toBe(false);
  });
});
