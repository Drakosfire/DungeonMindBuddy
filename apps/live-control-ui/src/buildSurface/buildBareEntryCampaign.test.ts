import { beforeEach, describe, expect, it } from "vitest";

import {
  BUILD_LAST_CAMPAIGN_STORAGE_KEY,
  bareBuildAutoCreateKey,
  resolveBareBuildCampaignId,
  writeBuildLastCampaignId,
} from "./buildBareEntryCampaign";

describe("buildBareEntryCampaign", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("prefers route campaign over last-campaign memory", () => {
    writeBuildLastCampaignId("longmont-c2");
    expect(resolveBareBuildCampaignId({ search: "?campaign=longmont-c1" })).toBe("longmont-c1");
  });

  it("uses last Build campaign when route has none", () => {
    writeBuildLastCampaignId("longmont-c1");
    expect(resolveBareBuildCampaignId({ search: "" })).toBe("longmont-c1");
  });

  it("returns null when no campaign context exists", () => {
    expect(resolveBareBuildCampaignId({ search: "" })).toBeNull();
    expect(localStorage.getItem(BUILD_LAST_CAMPAIGN_STORAGE_KEY)).toBeNull();
  });

  it("keys auto-create latch by campaign identity", () => {
    expect(bareBuildAutoCreateKey("longmont-c1")).not.toBe(bareBuildAutoCreateKey("longmont-c2"));
  });
});
