import { describe, expect, it } from "vitest";

import {
  deriveApiLens,
  formatPlanGraphLensSummary,
  requestedCampaignFromLocation,
  requestedCampaignsFromLocation,
  requestedDocumentIdFromLocation,
  requestedLensFocusFromLocation,
  requestedSessionNumberFromLocation,
  resolvePlanGraphLens,
  syncPlanGraphLensUrl,
  type PlanGraphLens,
} from "./sessionCampaignContext";

describe("sessionCampaignContext", () => {
  it("parses campaign and session query params", () => {
    expect(requestedCampaignFromLocation("?campaign=longmont-c2")).toBe("longmont-c2");
    expect(requestedSessionNumberFromLocation("?session=24")).toBe(24);
    expect(requestedSessionNumberFromLocation("?session=session-24")).toBe(24);
  });

  it("parses opaque documentId query param", () => {
    expect(requestedDocumentIdFromLocation("?documentId=11111111-1111-4111-8111-111111111111"))
      .toBe("11111111-1111-4111-8111-111111111111");
    expect(requestedDocumentIdFromLocation("?session=24")).toBeNull();
  });

  it("parses multi campaigns and qualified lens focus", () => {
    expect(requestedCampaignsFromLocation("?campaigns=longmont-c1,longmont-c2")).toEqual([
      "longmont-c1",
      "longmont-c2",
    ]);
    expect(requestedLensFocusFromLocation("?session=longmont-c1:3")).toEqual({
      campaignId: "longmont-c1",
      sessionNumber: 3,
    });
    expect(requestedLensFocusFromLocation("?session=c2:24")).toEqual({
      campaignId: "longmont-c2",
      sessionNumber: 24,
    });
    expect(requestedLensFocusFromLocation("?session=24", "longmont-c2")).toEqual({
      campaignId: "longmont-c2",
      sessionNumber: 24,
    });
  });

  it("defaults lens to active plan campaign when URL is empty", () => {
    expect(resolvePlanGraphLens("longmont-c2", "")).toEqual({
      selectedCampaignIds: ["longmont-c2"],
      focus: null,
    });
    expect(resolvePlanGraphLens("longmont-c1", "")).toEqual({
      selectedCampaignIds: ["longmont-c1"],
      focus: null,
    });
  });

  it("maps legacy campaign+scopeMode into selected set", () => {
    expect(resolvePlanGraphLens("longmont-c2", "?campaign=longmont-c1&scopeMode=campaign")).toEqual({
      selectedCampaignIds: ["longmont-c1"],
      focus: null,
    });
    expect(resolvePlanGraphLens("longmont-c2", "?campaign=longmont-c1&scopeMode=world").selectedCampaignIds)
      .toEqual(["longmont-c1", "longmont-c2"]);
  });

  it("treats bare ?campaign= as world union on Plan and single campaign on Build", () => {
    expect(
      resolvePlanGraphLens("longmont-c2", "?campaign=longmont-c1", { surfacePath: "/plan" })
        .selectedCampaignIds,
    ).toEqual(["longmont-c1", "longmont-c2"]);
    expect(
      resolvePlanGraphLens("longmont-c2", "?campaign=longmont-c1", { surfacePath: "/build" })
        .selectedCampaignIds,
    ).toEqual(["longmont-c1"]);
  });

  it("deriveApiLens maps one/both/empty", () => {
    expect(deriveApiLens({ selectedCampaignIds: [], focus: null }, "longmont-c2")).toBeNull();
    expect(deriveApiLens({ selectedCampaignIds: ["longmont-c1"], focus: null }, "longmont-c2")).toEqual({
      campaignId: "longmont-c1",
      scopeMode: "campaign",
      focus: null,
    });
    expect(
      deriveApiLens(
        { selectedCampaignIds: ["longmont-c1", "longmont-c2"], focus: null },
        "longmont-c2",
      ),
    ).toEqual({
      campaignId: "longmont-c2",
      scopeMode: "world",
      focus: null,
    });
    const withFocus: PlanGraphLens = {
      selectedCampaignIds: ["longmont-c1", "longmont-c2"],
      focus: { campaignId: "longmont-c1", sessionNumber: 3 },
    };
    expect(deriveApiLens(withFocus, "longmont-c2")?.focus).toEqual({
      campaignId: "longmont-c1",
      sessionNumber: 3,
    });
  });

  it("formats lens summary for union and single", () => {
    expect(
      formatPlanGraphLensSummary(
        { selectedCampaignIds: ["longmont-c1", "longmont-c2"], focus: null },
        "longmont-c2",
      ),
    ).toBe("Union · C1+C2 · no session focus");
    expect(
      formatPlanGraphLensSummary(
        {
          selectedCampaignIds: ["longmont-c2"],
          focus: { campaignId: "longmont-c2", sessionNumber: 23 },
        },
        "longmont-c2",
      ),
    ).toBe("C2 only · C2 · Session 23");
  });

  it("preserves /build path and documentId when syncing lens URL", () => {
    window.history.replaceState(
      {},
      "",
      "/build?documentId=11111111-1111-4111-8111-111111111111&campaign=longmont-c2",
    );
    syncPlanGraphLensUrl({
      selectedCampaignIds: ["longmont-c2"],
      focus: null,
    });
    expect(window.location.pathname).toBe("/build");
    expect(window.location.search).toContain("documentId=11111111-1111-4111-8111-111111111111");
    expect(window.location.search).toContain("campaign=longmont-c2");
    expect(window.location.search).toContain("campaigns=longmont-c2");
  });
});
