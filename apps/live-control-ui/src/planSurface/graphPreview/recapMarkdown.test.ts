import { describe, expect, it } from "vitest";

import { parseRecapInlineSegments, splitRecapBlocks } from "./recapMarkdown";

describe("recapMarkdown", () => {
  it("parses dmb-node links into node segments", () => {
    expect(parseRecapInlineSegments("They met [Lysandro](dmb-node:npc_lysandro).")).toEqual([
      { type: "text", text: "They met " },
      {
        type: "node",
        text: "Lysandro",
        href: "dmb-node:npc_lysandro",
        objectId: "npc_lysandro",
      },
      { type: "text", text: "." },
    ]);
  });

  it("leaves normal markdown links as text", () => {
    expect(parseRecapInlineSegments("[plain](https://example.test)")).toEqual([
      { type: "text", text: "[plain](https://example.test)" },
    ]);
  });

  it("splits normalized recap lines into readable blocks", () => {
    expect(splitRecapBlocks("First paragraph.\n\nSecond paragraph.\n")).toEqual([
      "First paragraph.",
      "Second paragraph.",
    ]);
  });
});
