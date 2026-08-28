import { describe, expect, it } from "vitest";

import { playRunbookAuthoringHref } from "./playRunbookAuthoringHref";

const DOC_A = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const DOC_B = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

describe("playRunbookAuthoringHref", () => {
  it("names the exact Runbook WorkObject UUID", () => {
    expect(playRunbookAuthoringHref(DOC_A)).toBe(`/plan?documentId=${DOC_A}`);
  });

  it("preserves unrelated query params and does not infer identity from them", () => {
    const href = playRunbookAuthoringHref(DOC_B, `?run=${DOC_A}&campaigns=longmont-c2`);
    const params = new URL(href, "http://local.test").searchParams;
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("run")).toBe(DOC_A);
    expect(params.get("campaigns")).toBe("longmont-c2");
  });
});
