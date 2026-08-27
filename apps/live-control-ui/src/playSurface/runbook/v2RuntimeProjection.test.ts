import { describe, expect, it } from "vitest";

import {
  deriveAuthoredRelevance,
  deriveV2OpeningBeatIdFromMarkdown,
  playRunProgressIsEmpty,
} from "./v2RuntimeProjection";

const ORDER_MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:z-opening beat_kind=spine -->",
  "## Opening",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:a-later beat_kind=spine -->",
  "## Later",
  "",
].join("\n");

describe("v2RuntimeProjection", () => {
  it("derives the opening Beat from document bytes, not id order", () => {
    expect(deriveV2OpeningBeatIdFromMarkdown(ORDER_MARKDOWN)).toBe("beat:z-opening");
  });

  it("returns null for zero-Beat markdown", () => {
    expect(deriveV2OpeningBeatIdFromMarkdown("# Empty\n")).toBeNull();
  });

  it("treats empty progress as the pre-READY seedable state", () => {
    expect(playRunProgressIsEmpty({
      current_beat_id: null,
      current_scene_id: null,
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    })).toBe(true);
    expect(playRunProgressIsEmpty({
      current_beat_id: "beat:one",
      current_scene_id: null,
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    })).toBe(false);
  });

  it("does not persist relevance as a progress field", () => {
    const relevance = deriveAuthoredRelevance(
      [{ option_id: "option:x1", effect: "activate", target_kind: "beat", target_id: "beat:two" }],
      { "choice:x": "option:x1" },
      ["beat:two"],
    );
    expect(relevance).toEqual({ "beat:two": "emphasized" });
    expect(Object.keys(relevance)).not.toContain("relevance");
  });

  it("ignores fenced Beat markers when deriving the opening Beat", () => {
    const fenced = [
      "```",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:fenced-first beat_kind=spine -->",
      "## Fenced",
      "```",
      "",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:z-opening beat_kind=spine -->",
      "## Opening",
      "",
    ].join("\n");
    expect(deriveV2OpeningBeatIdFromMarkdown(fenced)).toBe("beat:z-opening");
  });
});
