import { beforeEach, describe, expect, it } from "vitest";

import {
  BUILD_KNOWN_CAMPAIGN_IDS,
  BUILD_LAST_CAMPAIGN_STORAGE_KEY,
  bareBuildAutoCreateKey,
  resolveBareBuildCampaignId,
  resolveBuildCreateCampaignChoices,
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

  it("derives create choices from known entry defaults plus admissible Build scope", () => {
    expect(resolveBuildCreateCampaignChoices({ documents: null })).toEqual([
      ...BUILD_KNOWN_CAMPAIGN_IDS,
    ]);
    expect(
      resolveBuildCreateCampaignChoices({
        documents: [{ campaign_id: "eldyrwild" }, { campaign_id: "longmont-c1" }],
        activeCampaignId: "shadow-campaign",
      }),
    ).toEqual(["longmont-c1", "longmont-c2", "eldyrwild", "shadow-campaign"]);
  });

  it("suggests creatable active campaigns and honors campaign= fail-closed", () => {
    writeBuildLastCampaignId("longmont-c2");
    const withEldyrwild = resolveBuildCreateCampaignChoices({
      documents: [{ campaign_id: "eldyrwild" }],
    });
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "eldyrwild",
        search: "",
        creatableCampaignIds: withEldyrwild,
      }),
    ).toBe("eldyrwild");
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: null,
        search: "?campaign=",
        creatableCampaignIds: withEldyrwild,
      }),
    ).toBeNull();
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: null,
        search: "?campaign=typo",
        creatableCampaignIds: withEldyrwild,
      }),
    ).toBeNull();
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "longmont-c1",
        search: "?campaign=",
        creatableCampaignIds: withEldyrwild,
      }),
    ).toBe("longmont-c1");
    expect(
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: "foreign-only",
        search: "",
        creatableCampaignIds: [...BUILD_KNOWN_CAMPAIGN_IDS],
      }),
    ).toBe("longmont-c2");
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
