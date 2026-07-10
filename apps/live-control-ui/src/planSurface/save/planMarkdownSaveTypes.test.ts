import { describe, expect, it } from "vitest";

import { planMarkdownSaveStatusLabel } from "./planMarkdownSaveTypes";

describe("planMarkdownSaveStatusLabel", () => {
  it("labels idle and dirty states", () => {
    expect(planMarkdownSaveStatusLabel({ status: "idle" })).toMatch(/not yet saved/i);
    expect(planMarkdownSaveStatusLabel({ status: "dirty" })).toMatch(/since last Markdown save/i);
  });

  it("labels saving, committed, and error states", () => {
    expect(planMarkdownSaveStatusLabel({ status: "saving" })).toMatch(/Saving to Markdown/i);
    expect(planMarkdownSaveStatusLabel({ status: "committed" })).toMatch(/Saved to Markdown/i);
    expect(planMarkdownSaveStatusLabel({ status: "error", error: "boom" })).toBe("boom");
  });
});
