import { describe, expect, it } from "vitest";

import {
  effectiveFocusValidationStatus,
  planGraphLensValidationKey,
} from "./WorldGraphLensContext";
import type { PlanGraphLens } from "./sessionCampaignContext";

describe("planGraphLensValidationKey", () => {
  it("binds selected campaigns and focus together", () => {
    const lens: PlanGraphLens = {
      selectedCampaignIds: ["longmont-c1", "longmont-c2"],
      focus: { campaignId: "longmont-c2", sessionNumber: 40 },
    };
    expect(planGraphLensValidationKey(lens)).toBe(
      "longmont-c1,longmont-c2::longmont-c2:40",
    );
  });

  it("changes when campaign selection changes with the same focus", () => {
    const withC2: PlanGraphLens = {
      selectedCampaignIds: ["longmont-c2"],
      focus: { campaignId: "longmont-c2", sessionNumber: 40 },
    };
    const withUnion: PlanGraphLens = {
      selectedCampaignIds: ["longmont-c1", "longmont-c2"],
      focus: { campaignId: "longmont-c2", sessionNumber: 40 },
    };
    expect(planGraphLensValidationKey(withC2)).not.toBe(
      planGraphLensValidationKey(withUnion),
    );
  });
});

describe("effectiveFocusValidationStatus", () => {
  it("returns stored status when bound to the current lens key", () => {
    expect(
      effectiveFocusValidationStatus(
        { status: "valid", boundKey: "longmont-c2::longmont-c2:40" },
        "longmont-c2::longmont-c2:40",
        true,
      ),
    ).toBe("valid");
  });

  it("treats a stale valid override as pending after the lens key changes", () => {
    expect(
      effectiveFocusValidationStatus(
        { status: "valid", boundKey: "longmont-c2::longmont-c2:40" },
        "longmont-c1,longmont-c2::longmont-c2:40",
        true,
      ),
    ).toBe("pending");
  });

  it("treats a stale binding as none when focus was cleared", () => {
    expect(
      effectiveFocusValidationStatus(
        { status: "valid", boundKey: "longmont-c2::longmont-c2:40" },
        "longmont-c2::",
        false,
      ),
    ).toBe("none");
  });
});
