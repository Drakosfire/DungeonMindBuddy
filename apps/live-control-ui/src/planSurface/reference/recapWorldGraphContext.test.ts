import { buildRecapWorldGraphContext } from "./recapWorldGraphContext";

describe("buildRecapWorldGraphContext", () => {
  it("builds a session-focused world-scope context for known campaigns", () => {
    expect(buildRecapWorldGraphContext("longmont-c2", "session-24")).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "world",
      focus: {
        kind: "session",
        sessionId: "session-24",
        focusCampaignId: "longmont-c2",
      },
    });
  });

  it("returns null for unknown campaigns or empty sessions", () => {
    expect(buildRecapWorldGraphContext("unknown-campaign", "session-1")).toBeNull();
    expect(buildRecapWorldGraphContext("longmont-c2", "  ")).toBeNull();
  });
});
