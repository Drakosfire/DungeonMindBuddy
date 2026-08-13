import { describe, expect, it } from "vitest";

import { mediaForOfConksNodeId } from "./ofConksNodeMedia";

describe("ofConksNodeMedia", () => {
  it("associates Morwin with the Hempholm village map", () => {
    const media = mediaForOfConksNodeId("npc:morwin-blackwell");
    expect(media).not.toBeNull();
    expect(media?.kind).toBe("map");
    expect(media?.src).toContain("map-hempholm.jpg");
    expect(media?.src.startsWith("/corpus/of-conks-cons-markdown/media/")).toBe(true);
  });

  it("associates grotesque tree threat with the Area 5 harvest plate", () => {
    expect(mediaForOfConksNodeId("threat:grotesque-tree")?.src).toContain(
      "art-area-5-harvest.jpg",
    );
  });

  it("associates Greenfields region nodes with the regional map", () => {
    expect(mediaForOfConksNodeId("item:the-conk")?.src).toContain("map-greenfields.jpg");
  });

  it("returns null for unknown nodes", () => {
    expect(mediaForOfConksNodeId("npc:stranger")).toBeNull();
  });
});
