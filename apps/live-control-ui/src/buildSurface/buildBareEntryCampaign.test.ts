import { beforeEach, describe, expect, it } from "vitest";

import {
  BUILD_LAST_CAMPAIGN_STORAGE_KEY,
  bareBuildAutoCreateKey,
  resolveBareBuildCampaignId,
  resolveSuggestedBuildCreateCampaignId,
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

  it("fails closed on unknown route campaign (does not fall through to last)", () => {
    writeBuildLastCampaignId("longmont-c2");
    expect(resolveBareBuildCampaignId({ search: "?campaign=eldyrwild" })).toBeNull();
    expect(resolveBareBuildCampaignId({ search: "?campaign=typo" })).toBeNull();
  });

  it("fails closed on blank route campaign (does not fall through to last)", () => {
    expect(resolveBareBuildCampaignId({ search: "?campaign=" })).toBeNull();
    expect(resolveBareBuildCampaignId({ search: "?campaign=%20" })).toBeNull();
    writeBuildLastCampaignId("longmont-c1");
    expect(resolveBareBuildCampaignId({ search: "?campaign=" })).toBeNull();
    expect(resolveBareBuildCampaignId({ search: "?campaign=%20" })).toBeNull();
  });

  it("suggests only known create campaigns and honors campaign= fail-closed", () => {
    writeBuildLastCampaignId("longmont-c2");
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "eldyrwild",
        search: "",
      }),
    ).toBe("longmont-c2");
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "eldyrwild",
        search: "?campaign=",
      }),
    ).toBeNull();
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "eldyrwild",
        search: "?campaign=typo",
      }),
    ).toBeNull();
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "longmont-c1",
        search: "?campaign=",
      }),
    ).toBe("longmont-c1");
  });

  it("uses shared-lens campaigns when Build campaign param is absent", () => {
    writeBuildLastCampaignId("longmont-c1");
    expect(resolveBareBuildCampaignId({ search: "?campaigns=longmont-c2" })).toBe("longmont-c2");
    expect(
      resolveBareBuildCampaignId({ search: "?campaigns=longmont-c1,longmont-c2" }),
    ).toBe("longmont-c1");
  });

  it("prefers explicit Build campaign over shared-lens campaigns", () => {
    expect(
      resolveBareBuildCampaignId({ search: "?campaign=longmont-c2&campaigns=longmont-c1" }),
    ).toBe("longmont-c2");
  });

  it("keys auto-create latch by campaign identity", () => {
    expect(bareBuildAutoCreateKey("longmont-c1")).not.toBe(bareBuildAutoCreateKey("longmont-c2"));
  });
});
