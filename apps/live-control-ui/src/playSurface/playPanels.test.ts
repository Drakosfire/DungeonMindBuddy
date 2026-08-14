import { describe, expect, it } from "vitest";

import {
  buildPlayPanelEmbedSrc,
  isPrepPlayPanel,
  playBeatsFocusFromSearch,
  playBeatsFocusHref,
  playPanelFromPath,
  playPanelHref,
} from "./playPanels";

describe("playPanels", () => {
  it("maps Play and legacy paths onto panels", () => {
    expect(playPanelFromPath("/play")).toBe("beats");
    expect(playPanelFromPath("/play/beats")).toBe("beats");
    expect(playPanelFromPath("/play/combat")).toBe("combat");
    expect(playPanelFromPath("/play/roll")).toBe("roll");
    expect(playPanelFromPath("/play/items")).toBe("items");
    expect(playPanelFromPath("/play/statblocks")).toBe("statblocks");
    expect(playPanelFromPath("/combat")).toBe("combat");
    expect(playPanelFromPath("/roll/")).toBe("roll");
    expect(playPanelFromPath("/plan")).toBeNull();
  });

  it("builds play hrefs and prep embed src", () => {
    expect(playPanelHref("beats")).toBe("/play/beats");
    expect(playPanelHref("statblocks")).toBe("/play/statblocks");
    expect(isPrepPlayPanel("beats")).toBe(false);
    expect(isPrepPlayPanel("combat")).toBe(true);
    expect(buildPlayPanelEmbedSrc("beats", "?campaigns=of-conks-cons", ["of-conks-cons"])).toBeNull();
    expect(buildPlayPanelEmbedSrc("combat", "?campaigns=of-conks-cons", ["of-conks-cons"])).toBe(
      "/prep/combat?campaigns=of-conks-cons&embed=1",
    );
  });

  it("builds Beats focus hrefs and parses beat/node from search", () => {
    expect(playBeatsFocusHref({
      beatId: "shacks-arrival",
      nodeId: "location:the-shacks",
      search: "?",
    })).toBe(
      "/play/beats?beat=shacks-arrival&node=location%3Athe-shacks",
    );
    expect(
      playBeatsFocusHref({
        beatId: "shacks-arrival",
        nodeId: "location:the-shacks",
        search: "?campaigns=of-conks-cons",
      }),
    ).toBe(
      "/play/beats?campaigns=of-conks-cons&beat=shacks-arrival&node=location%3Athe-shacks",
    );
    expect(
      playBeatsFocusFromSearch("?campaigns=of-conks-cons&beat=shacks-arrival&node=location:the-shacks"),
    ).toEqual({
      beatId: "shacks-arrival",
      nodeId: "location:the-shacks",
    });
  });
});
