import { describe, expect, it } from "vitest";

import {
  buildPlayPanelEmbedSrc,
  playPanelFromPath,
  playPanelHref,
} from "./playPanels";

describe("playPanels", () => {
  it("maps Play and legacy paths onto panels", () => {
    expect(playPanelFromPath("/play")).toBe("combat");
    expect(playPanelFromPath("/play/combat")).toBe("combat");
    expect(playPanelFromPath("/play/roll")).toBe("roll");
    expect(playPanelFromPath("/play/items")).toBe("items");
    expect(playPanelFromPath("/play/statblocks")).toBe("statblocks");
    expect(playPanelFromPath("/combat")).toBe("combat");
    expect(playPanelFromPath("/roll/")).toBe("roll");
    expect(playPanelFromPath("/plan")).toBeNull();
  });

  it("builds play hrefs and prep embed src", () => {
    expect(playPanelHref("statblocks")).toBe("/play/statblocks");
    expect(buildPlayPanelEmbedSrc("combat", "?campaigns=of-conks-cons", ["of-conks-cons"])).toBe(
      "/prep/combat?campaigns=of-conks-cons&embed=1",
    );
  });
});
