import { describe, expect, it } from "vitest";

import { hasOfConksPlayObjectBody } from "../../graphReference/ofConksPlayObjectBridge";
import {
  OF_CONKS_HEMPHOLM_SPINE,
  beatById,
  visibleScenesForBranch,
} from "./ofConksHempholmBeats";
import {
  OF_CONKS_HEMPHOLM_PDF_HOMES,
  OF_CONKS_HEMPHOLM_PDF_OMITTED,
} from "./ofConksHempholmPdfHomes";

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

  it("gives every spine beat an atTable run body", () => {
    for (const scene of OF_CONKS_HEMPHOLM_SPINE.scenes) {
      for (const beat of scene.beats) {
        if (beat.kind !== "spine") continue;
        expect(beat.atTable?.trim().length, beat.id).toBeGreaterThan(20);
      }
    }
  });

  it("homes tree-tactics GM note with precious-metal leaves as a callout, not boxed text", () => {
    const beat = beatById(OF_CONKS_HEMPHOLM_SPINE, "tree-tactics")?.beat;
    expect(beat?.gmNote).toMatch(/precious-metal leaves/i);
    expect(beat?.gmNote).toMatch(/Passive Perception 15/i);
    expect(beat?.readAlouds?.some((ra) => /metal leaves/i.test(ra.text))).toBe(false);
    expect(beat?.rulesNow?.some((line) => /metal leaves/i.test(line))).toBe(true);
  });

  it("homes Jove plea multi labeled read-alouds from the PDF", () => {
    const beat = beatById(OF_CONKS_HEMPHOLM_SPINE, "jove-plea")?.beat;
    expect(beat?.readAlouds?.length).toBeGreaterThanOrEqual(3);
    expect(beat?.readAlouds?.some((ra) => ra.label === "Mark Jove" && /bewitched/i.test(ra.text))).toBe(
      true,
    );
    expect(beat?.readAlouds?.some((ra) => ra.label === "Torbin Jove" && /'tato/i.test(ra.text))).toBe(
      true,
    );
  });
});

describe("ofConksHempholmPdfHomes", () => {
  it("maps every inventoried PDF adventure heading to a reachable home", () => {
    expect(OF_CONKS_HEMPHOLM_PDF_OMITTED).toEqual(
      expect.arrayContaining(["Credits & Afterword", "Table of Contents"]),
    );

    for (const entry of OF_CONKS_HEMPHOLM_PDF_HOMES) {
      if (entry.homeKind === "beat") {
        expect(beatById(OF_CONKS_HEMPHOLM_SPINE, entry.homeId), entry.pdfHeading).not.toBeNull();
        continue;
      }
      if (entry.homeKind === "scene") {
        expect(
          OF_CONKS_HEMPHOLM_SPINE.scenes.some((s) => s.id === entry.homeId),
          entry.pdfHeading,
        ).toBe(true);
        continue;
      }
      if (entry.homeKind === "sheet") {
        if (entry.homeId.startsWith("threat:")) {
          // Threat sheets are ThreatSheetProjection / Combat — not Play Object Bridge.
          expect(entry.homeId.startsWith("threat:")).toBe(true);
          continue;
        }
        expect(hasOfConksPlayObjectBody(entry.homeId), entry.pdfHeading).toBe(true);
        continue;
      }
      if (entry.homeKind === "panel") {
        expect(["combat", "roll", "items", "statblocks"]).toContain(entry.homeId);
        continue;
      }
      if (entry.homeKind === "build") {
        expect(entry.homeId).toMatch(/Of Conks/i);
        continue;
      }
      throw new Error(`Unknown homeKind for ${entry.pdfHeading}`);
    }
  });

  it("keeps Shacks door-dump and hill bird RA on their beats", () => {
    const shacks = beatById(OF_CONKS_HEMPHOLM_SPINE, "shacks-arrival")?.beat;
    expect(shacks?.readAlouds?.[0]?.text).toMatch(/donkey/i);
    const hill = beatById(OF_CONKS_HEMPHOLM_SPINE, "hook-hill")?.beat;
    expect(hill?.readAlouds?.[0]?.text).toMatch(/minced meat/i);
  });
});
