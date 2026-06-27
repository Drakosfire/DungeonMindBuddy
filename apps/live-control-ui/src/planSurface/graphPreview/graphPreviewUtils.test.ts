import { describe, expect, it } from "vitest";

import { buildHighlightSegments, spanRefLabel } from "./graphPreviewUtils";

describe("graphPreviewUtils", () => {
  it("builds highlight segments from anchor quote matches", () => {
    const paragraph = "Grobnok took the rockie-talkie from Frank.";
    const segments = buildHighlightSegments(paragraph, [
      {
        quote: "Grobnok",
        char_start: 0,
        char_end: 7,
        match_text: "Grobnok",
      },
    ]);
    expect(segments).toEqual([
      { text: "Grobnok", highlighted: true },
      { text: " took the rockie-talkie from Frank.", highlighted: false },
    ]);
  });

  it("returns plain paragraph when no matches", () => {
    const segments = buildHighlightSegments("plain text", []);
    expect(segments).toEqual([{ text: "plain text", highlighted: false }]);
  });

  it("formats span ref ids into human-readable session/paragraph labels", () => {
    expect(spanRefLabel("spref:session-22:p014")).toBe("Session 22 · ¶14");
    expect(spanRefLabel("spref:session-7:p3")).toBe("Session 7 · ¶3");
    expect(spanRefLabel("weird-id")).toBe("weird-id");
    expect(spanRefLabel(null)).toBeNull();
  });
});
