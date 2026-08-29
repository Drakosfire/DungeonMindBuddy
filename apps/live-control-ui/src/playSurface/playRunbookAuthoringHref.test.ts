import { describe, expect, it } from "vitest";

import {
  playRunbookAuthoringCampaignMismatch,
  playRunbookAuthoringHref,
} from "./playRunbookAuthoringHref";

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

describe("playRunbookAuthoringCampaignMismatch", () => {
  it("does not block when Play has no product campaign", () => {
    expect(playRunbookAuthoringCampaignMismatch(null, "longmont-c1")).toBeNull();
    expect(playRunbookAuthoringCampaignMismatch("  ", "longmont-c1")).toBeNull();
  });

  it("does not block when the Runbook campaign matches Play", () => {
    expect(playRunbookAuthoringCampaignMismatch("longmont-c2", "longmont-c2")).toBeNull();
  });

  it("names a known campaign mismatch", () => {
    const reason = playRunbookAuthoringCampaignMismatch("longmont-c2", "longmont-c1");
    expect(reason).toContain("longmont-c1");
    expect(reason).toContain("longmont-c2");
  });
});
