import { describe, expect, it } from "vitest";

import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { collectPlayableBodyChips } from "./playableBodyReferences";

const MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold beat_kind=spine -->",
  "## Hold the Breach",
  "",
  "Beat framing with [Mara](#dmb-ref:npc:mara-venn).",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->",
  "### North Gate",
  "",
  "Scene body with [Caelynn](dmb-node:pc_caelynn) and [Mara](#dmb-ref:npc:mara-venn).",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:surviving-brood scene=scene:north-gate -->",
  "### Surviving Brood",
  "",
  "Choice framing.",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:follow-brood activates=scene:tunnel-pursuit -->",
  "- Follow it",
  "",
  "Option body [Glowkindle](dmb-node:npc-glowkindle).",
  "",
].join("\n");

describe("collectPlayableBodyChips", () => {
  it("collects graph and corpus chips from the owning Playable body only", () => {
    const imported = markdownToTiptapDoc(MARKDOWN);
    expect(imported.diagnostics.filter((row) => row.level === "error")).toEqual([]);

    const beat = collectPlayableBodyChips(imported.doc, "beat:hold");
    expect(beat.map((chip) => chip.label)).toEqual(["Mara"]);
    expect(beat[0]?.className).toContain("md-ref-chip-npc");

    const scene = collectPlayableBodyChips(imported.doc, "scene:north-gate");
    expect(scene.map((chip) => chip.label)).toEqual(["Caelynn", "Mara"]);
    expect(scene[0]?.className).toContain("md-ref-chip-graph-node");

    const choice = collectPlayableBodyChips(imported.doc, "choice:surviving-brood");
    expect(choice.map((chip) => chip.label)).toEqual(["Glowkindle"]);

    const option = collectPlayableBodyChips(imported.doc, "option:follow-brood");
    expect(option).toEqual([]);
  });
});
