import { describe, expect, it } from "vitest";

import { mediaForOfConksNodeId } from "./ofConksNodeMedia";

describe("ofConksNodeMedia", () => {
  it("associates Morwin with the store/wagon module page", () => {
    const media = mediaForOfConksNodeId("npc:morwin-blackwell");
    expect(media).not.toBeNull();
    expect(media?.kind).toBe("module-page");
    expect(media?.src).toContain("page-09-area-2-3-store-wagon.jpg");
    expect(media?.src.startsWith("/corpus/of-conks-cons-markdown/media/")).toBe(true);
  });

  it("associates grotesque tree threat with Area 5 page", () => {
    expect(mediaForOfConksNodeId("threat:grotesque-tree")?.src).toContain(
      "page-11-area-5-grotesque-tree.jpg",
    );
  });

  it("returns null for unknown nodes", () => {
    expect(mediaForOfConksNodeId("npc:stranger")).toBeNull();
  });
});
