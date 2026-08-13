import { describe, expect, it } from "vitest";

import {
  OF_CONKS_HEMPHOLM_SPINE,
  beatById,
  visibleScenesForBranch,
} from "./ofConksHempholmBeats";

describe("ofConksHempholmBeats", () => {
  it("includes Maglubiyet, firefighting, and Marrow chamber beats", () => {
    expect(beatById(OF_CONKS_HEMPHOLM_SPINE, "saladin-wagon")?.beat.chips?.some(
      (c) => c.nodeId === "item:maglubiyets-statue",
    )).toBe(true);
    expect(beatById(OF_CONKS_HEMPHOLM_SPINE, "firefighting")?.beat.rulesNow?.some(
      (line) => /DC 12/i.test(line),
    )).toBe(true);
    expect(beatById(OF_CONKS_HEMPHOLM_SPINE, "marrow-fight")?.scene.readAloud).toMatch(/helix/i);
  });

  it("hides aftermath scenes until branch chosen, then shows one", () => {
    const none = visibleScenesForBranch(OF_CONKS_HEMPHOLM_SPINE, { aftermath: null });
    expect(none.some((s) => s.id.startsWith("aftermath-"))).toBe(false);

    const celeb = visibleScenesForBranch(OF_CONKS_HEMPHOLM_SPINE, {
      aftermath: "celebration",
    });
    expect(celeb.map((s) => s.id)).toContain("aftermath-celebration");
    expect(celeb.map((s) => s.id)).not.toContain("aftermath-fire");
    expect(celeb.map((s) => s.id)).toContain("caretakers");
  });
});
