import { describe, expect, it } from "vitest";

import { planMarkdownSaveStatusLabel } from "./planMarkdownSaveTypes";

describe("planMarkdownSaveStatusLabel", () => {
  it("labels idle and dirty states", () => {
    expect(planMarkdownSaveStatusLabel({ status: "idle" })).toMatch(/not yet saved/i);
    expect(planMarkdownSaveStatusLabel({ status: "dirty" })).toMatch(/since last Markdown save/i);
  });

  it("labels committed and error states", () => {
    expect(planMarkdownSaveStatusLabel({ status: "committed" })).toMatch(/Saved to Markdown/i);
    expect(planMarkdownSaveStatusLabel({ status: "error", error: "boom" })).toBe("boom");
  });

  it("shows stale-preview error on dirty state when present", () => {
    expect(
      planMarkdownSaveStatusLabel({
        status: "dirty",
        error: "Editor changed after preview. Preview the save again before committing.",
      }),
    ).toMatch(/Preview the save again/i);
  });
});
