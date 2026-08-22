import { describe, expect, it } from "vitest";

import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import { PLAYABLE_ELEMENT_DIAGNOSTIC } from "./playableElementIdentity";
import {
  PLAYABLE_STRUCTURE_DIAGNOSTIC,
  indexPlayableStructure,
  indexPlayableStructureV2,
  type PlayableStructureIndexResult,
  type PlayableStructureIndexV2Result,
} from "./playableStructureIndex";

function heading(
  level: number,
  text: string,
  playable?: { kind: "scene" | "beat" | "choice" | "option"; id: string },
) {
  return {
    type: "heading",
    attrs: playable
      ? { level, playableElementKind: playable.kind, playableElementId: playable.id }
      : { level },
    content: [{ type: "text", text }],
  };
}

function doc(...content: unknown[]) {
  return { type: "doc", content };
}

function expectReady(result: PlayableStructureIndexResult) {
  expect(result.status).toBe("ready");
  if (result.status !== "ready") throw new Error("expected ready index");
  return result.index;
}

function expectBlocked(result: PlayableStructureIndexResult) {
  expect(result.status).toBe("blocked");
  if (result.status !== "blocked") throw new Error("expected blocked index");
  return result.diagnostics;
}

describe("indexPlayableStructure", () => {
  it("indexes one Scene and its Beats by exact IDs, order, and parent", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:arrival" }),
      { type: "paragraph", content: [{ type: "text", text: "Prose." }] },
      heading(3, "Gate opens", { kind: "beat", id: "beat:gate-opens" }),
      heading(3, "Tolls", { kind: "beat", id: "beat:tolls" }),
    )));

    expect(index.sceneOrder).toEqual(["scene:arrival"]);
    expect(index.choices).toEqual([]);
    expect(index.scenes).toEqual([
      { sceneId: "scene:arrival", order: 0, beatOrder: ["beat:gate-opens", "beat:tolls"], choiceOrder: [] },
    ]);
    expect(index.elements).toEqual([
      { kind: "scene", id: "scene:arrival", order: 0 },
      { kind: "beat", id: "beat:gate-opens", order: 1, sceneId: "scene:arrival" },
      { kind: "beat", id: "beat:tolls", order: 2, sceneId: "scene:arrival" },
    ]);
  });

  it("partitions Beats across multiple marked Scenes", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "A1", { kind: "beat", id: "beat:a1" }),
      heading(3, "A2", { kind: "beat", id: "beat:a2" }),
      heading(2, "Harbor", { kind: "scene", id: "scene:b" }),
      heading(3, "B1", { kind: "beat", id: "beat:b1" }),
    )));

    expect(index.sceneOrder).toEqual(["scene:a", "scene:b"]);
    expect(index.scenes).toEqual([
      { sceneId: "scene:a", order: 0, beatOrder: ["beat:a1", "beat:a2"], choiceOrder: [] },
      { sceneId: "scene:b", order: 1, beatOrder: ["beat:b1"], choiceOrder: [] },
    ]);
    expect(index.elements.filter((element) => element.kind === "beat")).toEqual([
      { kind: "beat", id: "beat:a1", order: 1, sceneId: "scene:a" },
      { kind: "beat", id: "beat:a2", order: 2, sceneId: "scene:a" },
      { kind: "beat", id: "beat:b1", order: 4, sceneId: "scene:b" },
    ]);
  });

  it("indexes a real P1A Markdown import with the same IDs and parents", () => {
    const imported = markdownToTiptapDoc([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:a -->",
      "## Scene A",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:a1 -->",
      "### Beat A1",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:a2 -->",
      "### Beat A2",
      "",
      "## Unmarked heading",
      "",
      "<!-- dmb-playable-element:v1 kind=scene id=scene:b -->",
      "## Scene B",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:b1 -->",
      "### Beat B1",
      "",
    ].join("\n"));

    expect(imported.diagnostics).toEqual([]);
    const index = expectReady(indexPlayableStructure(imported.doc));
    expect(index.sceneOrder).toEqual(["scene:a", "scene:b"]);
    expect(index.scenes).toEqual([
      { sceneId: "scene:a", order: 0, beatOrder: ["beat:a1", "beat:a2"], choiceOrder: [] },
      { sceneId: "scene:b", order: 1, beatOrder: ["beat:b1"], choiceOrder: [] },
    ]);
  });

  it("does not rebind identity or parent when heading text is renamed", () => {
    const original = doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "Gate", { kind: "beat", id: "beat:x" }),
    );
    const renamed = doc(
      heading(2, "The docks", { kind: "scene", id: "scene:a" }),
      heading(3, "Harbor gate", { kind: "beat", id: "beat:x" }),
    );

    expect(indexPlayableStructure(renamed)).toEqual(indexPlayableStructure(original));
  });

  it("changes only Beat order when Beats are reordered inside the same Scene", () => {
    const original = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "First", { kind: "beat", id: "beat:x" }),
      heading(3, "Second", { kind: "beat", id: "beat:y" }),
    )));
    const reordered = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "Second", { kind: "beat", id: "beat:y" }),
      heading(3, "First", { kind: "beat", id: "beat:x" }),
    )));

    expect(reordered.sceneOrder).toEqual(original.sceneOrder);
    expect(reordered.scenes[0]?.sceneId).toBe("scene:a");
    expect(reordered.scenes[0]?.beatOrder).toEqual(["beat:y", "beat:x"]);
    expect(reordered.elements.filter((element) => element.kind === "beat")).toEqual([
      { kind: "beat", id: "beat:y", order: 1, sceneId: "scene:a" },
      { kind: "beat", id: "beat:x", order: 2, sceneId: "scene:a" },
    ]);
  });

  it("moves a Beat across a marked Scene boundary while keeping the Beat ID", () => {
    const before = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "Crossing", { kind: "beat", id: "beat:x" }),
      heading(2, "Harbor", { kind: "scene", id: "scene:b" }),
    )));
    const after = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(2, "Harbor", { kind: "scene", id: "scene:b" }),
      heading(3, "Crossing", { kind: "beat", id: "beat:x" }),
    )));

    expect(before.elements).toEqual(expect.arrayContaining([
      { kind: "beat", id: "beat:x", order: 1, sceneId: "scene:a" },
    ]));
    expect(after.elements).toEqual(expect.arrayContaining([
      { kind: "beat", id: "beat:x", order: 2, sceneId: "scene:b" },
    ]));
    expect(after.scenes).toEqual([
      { sceneId: "scene:a", order: 0, beatOrder: [], choiceOrder: [] },
      { sceneId: "scene:b", order: 1, beatOrder: ["beat:x"], choiceOrder: [] },
    ]);
  });

  it("ignores unmarked headings as structure and Scene boundaries", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(2, "Looks like a scene"),
      heading(3, "Looks like a beat"),
      heading(3, "Gate", { kind: "beat", id: "beat:x" }),
      heading(1, "Document title"),
    )));

    expect(index.sceneOrder).toEqual(["scene:a"]);
    expect(index.scenes[0]?.beatOrder).toEqual(["beat:x"]);
    expect(index.elements).toEqual([
      { kind: "scene", id: "scene:a", order: 0 },
      { kind: "beat", id: "beat:x", order: 1, sceneId: "scene:a" },
    ]);
  });

  it("blocks the entire index when a marked Beat precedes any marked Scene", () => {
    const diagnostics = expectBlocked(indexPlayableStructure(doc(
      heading(3, "Too soon", { kind: "beat", id: "beat:x" }),
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
    )));

    expect(diagnostics).toEqual([
      {
        code: "orphan_beat",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanBeat,
        elementId: "beat:x",
      },
    ]);
  });

  it("blocks invalid, duplicate, and nested identity without a partial index", () => {
    const invalid = expectBlocked(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      {
        type: "heading",
        attrs: { playableElementKind: "beat", playableElementId: "beat:x" },
        content: [{ type: "text", text: "Missing level" }],
      },
    )));
    expect(invalid).toEqual([
      {
        code: "invalid_identity",
        message: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch,
        elementId: "beat:x",
      },
    ]);

    const duplicate = expectBlocked(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "First", { kind: "beat", id: "beat:x" }),
      heading(3, "Copy", { kind: "beat", id: "beat:x" }),
    )));
    expect(duplicate).toEqual([
      {
        code: "duplicate_identity",
        message: PLAYABLE_ELEMENT_DIAGNOSTIC.duplicateAttrs,
        elementId: "beat:x",
      },
    ]);

    const nested = expectBlocked(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      {
        type: "callout",
        attrs: { kind: "gm-note" },
        content: [heading(3, "Hidden", { kind: "beat", id: "beat:nested" })],
      },
    )));
    expect(nested).toEqual([
      {
        code: "nested_identity",
        message: PLAYABLE_ELEMENT_DIAGNOSTIC.nested,
        elementId: "beat:nested",
      },
    ]);
  });

  it("returns a ready empty index for unmarked or empty documents", () => {
    expect(indexPlayableStructure(doc())).toEqual({
      status: "ready",
      index: { sceneOrder: [], scenes: [], choices: [], elements: [] },
    });
    expect(indexPlayableStructure(doc(
      heading(1, "Runbook"),
      heading(2, "Ordinary scene-looking heading"),
      { type: "paragraph", content: [{ type: "text", text: "Prose." }] },
    ))).toEqual({
      status: "ready",
      index: { sceneOrder: [], scenes: [], choices: [], elements: [] },
    });
  });

  it("indexes a marked Scene with no Beats", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
    )));
    expect(index.scenes).toEqual([{ sceneId: "scene:a", order: 0, beatOrder: [], choiceOrder: [] }]);
  });

  it("blocks a non-document root", () => {
    expect(expectBlocked(indexPlayableStructure(heading(2, "Arrival", { kind: "scene", id: "scene:a" })))).toEqual([
      { code: "non_doc_root", message: PLAYABLE_STRUCTURE_DIAGNOSTIC.nonDocRoot },
    ]);
  });

  it("returns a deep-equivalent index for the same document twice", () => {
    const document = doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "Gate", { kind: "beat", id: "beat:x" }),
      heading(2, "Harbor", { kind: "scene", id: "scene:b" }),
    );
    expect(indexPlayableStructure(document)).toEqual(indexPlayableStructure(document));
  });

  it("indexes Choice/Option membership under the marked Scene and Choice", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "The Gate", { kind: "scene", id: "scene:gate" }),
      heading(3, "Arrival", { kind: "beat", id: "beat:arrival" }),
      heading(3, "Which route?", { kind: "choice", id: "choice:route" }),
      heading(4, "Burn", { kind: "option", id: "option:fire" }),
      heading(4, "Wait", { kind: "option", id: "option:wait" }),
    )));

    expect(index.sceneOrder).toEqual(["scene:gate"]);
    expect(index.scenes).toEqual([
      {
        sceneId: "scene:gate",
        order: 0,
        beatOrder: ["beat:arrival"],
        choiceOrder: ["choice:route"],
      },
    ]);
    expect(index.choices).toEqual([
      {
        choiceId: "choice:route",
        sceneId: "scene:gate",
        order: 0,
        optionOrder: ["option:fire", "option:wait"],
      },
    ]);
    expect(index.elements).toEqual([
      { kind: "scene", id: "scene:gate", order: 0 },
      { kind: "beat", id: "beat:arrival", order: 1, sceneId: "scene:gate" },
      { kind: "choice", id: "choice:route", order: 2, sceneId: "scene:gate" },
      { kind: "option", id: "option:fire", order: 3, sceneId: "scene:gate", choiceId: "choice:route" },
      { kind: "option", id: "option:wait", order: 4, sceneId: "scene:gate", choiceId: "choice:route" },
    ]);
  });

  it("indexes a Choice with zero Options", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "The Gate", { kind: "scene", id: "scene:gate" }),
      heading(3, "Which route?", { kind: "choice", id: "choice:route" }),
    )));
    expect(index.choices).toEqual([
      { choiceId: "choice:route", sceneId: "scene:gate", order: 0, optionOrder: [] },
    ]);
  });

  it("moves a Choice across a Scene boundary while keeping the Choice ID", () => {
    const after = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(2, "Harbor", { kind: "scene", id: "scene:b" }),
      heading(3, "Which route?", { kind: "choice", id: "choice:x" }),
    )));
    expect(after.choices).toEqual([
      { choiceId: "choice:x", sceneId: "scene:b", order: 0, optionOrder: [] },
    ]);
  });

  it("moves an Option across a Choice boundary while keeping the Option ID", () => {
    const after = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "First", { kind: "choice", id: "choice:a" }),
      heading(3, "Second", { kind: "choice", id: "choice:b" }),
      heading(4, "Crossing", { kind: "option", id: "option:x" }),
    )));
    expect(after.choices).toEqual([
      { choiceId: "choice:a", sceneId: "scene:a", order: 0, optionOrder: [] },
      { choiceId: "choice:b", sceneId: "scene:a", order: 1, optionOrder: ["option:x"] },
    ]);
    expect(after.elements).toEqual(expect.arrayContaining([
      { kind: "option", id: "option:x", order: 3, sceneId: "scene:a", choiceId: "choice:b" },
    ]));
  });

  it("blocks an Option that follows a Beat after a Choice", () => {
    const diagnostics = expectBlocked(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "Which route?", { kind: "choice", id: "choice:route" }),
      heading(4, "Burn", { kind: "option", id: "option:fire" }),
      heading(3, "Aftermath", { kind: "beat", id: "beat:after" }),
      heading(4, "Wait", { kind: "option", id: "option:wait" }),
    )));
    expect(diagnostics).toEqual([
      {
        code: "orphan_option",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanOption,
        elementId: "option:wait",
      },
    ]);
  });

  it("blocks a Choice before any marked Scene", () => {
    const diagnostics = expectBlocked(indexPlayableStructure(doc(
      heading(3, "Too soon", { kind: "choice", id: "choice:x" }),
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
    )));
    expect(diagnostics).toEqual([
      {
        code: "orphan_choice",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanChoice,
        elementId: "choice:x",
      },
    ]);
  });

  it("blocks an Option before any active Choice", () => {
    const diagnostics = expectBlocked(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(4, "Too soon", { kind: "option", id: "option:x" }),
    )));
    expect(diagnostics).toEqual([
      {
        code: "orphan_option",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanOption,
        elementId: "option:x",
      },
    ]);
  });

  it("ignores unmarked H3/H4 between a Choice and its Options", () => {
    const index = expectReady(indexPlayableStructure(doc(
      heading(2, "Arrival", { kind: "scene", id: "scene:a" }),
      heading(3, "Which route?", { kind: "choice", id: "choice:route" }),
      heading(3, "Looks like a choice"),
      heading(4, "Looks like an option"),
      heading(4, "Burn", { kind: "option", id: "option:fire" }),
    )));
    expect(index.choices).toEqual([
      { choiceId: "choice:route", sceneId: "scene:a", order: 0, optionOrder: ["option:fire"] },
    ]);
  });
});
// ---------------------------------------------------------------------------
// Beat-first (v2) structure index
// ---------------------------------------------------------------------------

const V2_REPRESENTATIVE = [
  "# Session 27 North Gate Runbook",
  "",
  "Ordinary prose before any structural directive stays non-semantic.",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
  "## Hold the gate",
  "",
  "Triage at the gate line while the refugee crush builds.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-line -->",
  "### The gate line",
  "",
  "Guards waver while Lysandro works the crowd.",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:who-gets-through scene=scene:gate-line -->",
  "### Who gets through first?",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:cure-line-first activates=beat:panic-breaks -->",
  "- Prioritize the cure line",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:families-first suppresses=beat:meat-flank -->",
  "- Keep families together",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:panic-breaks beat_kind=optional -->",
  "## Panic breaks",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:the-crush -->",
  "### The crush",
  "",
  "The line surges against the wagons.",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:meat-flank beat_kind=interrupt -->",
  "## Meat flank",
  "",
  "The sewer meat creature hits the last wagon.",
  "",
].join("\n");

function expectReadyV2(result: PlayableStructureIndexV2Result) {
  if (result.status !== "ready") {
    throw new Error(`expected ready, got blocked: ${JSON.stringify(result.diagnostics)}`);
  }
  return result.index;
}

function expectBlockedV2(result: PlayableStructureIndexV2Result, code: string) {
  expect(result.status).toBe("blocked");
  if (result.status !== "blocked") throw new Error("expected blocked");
  expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain(code);
}

describe("indexPlayableStructureV2", () => {
  it("indexes a representative C2S27-shaped Beat/Scene/Decision/Option document", () => {
    const imported = markdownToTiptapDoc(V2_REPRESENTATIVE);
    expect(imported.diagnostics).toEqual([]);
    const index = expectReadyV2(indexPlayableStructureV2(imported.doc));

    expect(index.beatOrder).toEqual([
      "beat:hold-the-gate",
      "beat:panic-breaks",
      "beat:meat-flank",
    ]);
    expect(index.beats.map((beat) => [beat.beatId, beat.beatKind])).toEqual([
      ["beat:hold-the-gate", "spine"],
      ["beat:panic-breaks", "optional"],
      ["beat:meat-flank", "interrupt"],
    ]);
    expect(index.beats[0]).toMatchObject({
      beatId: "beat:hold-the-gate",
      sceneOrder: ["scene:gate-line"],
      choiceOrder: ["choice:who-gets-through"],
    });
    expect(index.scenes).toEqual([
      { sceneId: "scene:gate-line", beatId: "beat:hold-the-gate", order: 0 },
      { sceneId: "scene:the-crush", beatId: "beat:panic-breaks", order: 1 },
    ]);
    expect(index.choices).toEqual([
      {
        choiceId: "choice:who-gets-through",
        beatId: "beat:hold-the-gate",
        sceneId: "scene:gate-line",
        order: 0,
        optionOrder: ["option:cure-line-first", "option:families-first"],
      },
    ]);
    expect(index.options).toEqual([
      {
        optionId: "option:cure-line-first",
        choiceId: "choice:who-gets-through",
        order: 0,
        activates: ["beat:panic-breaks"],
        suppresses: [],
      },
      {
        optionId: "option:families-first",
        choiceId: "choice:who-gets-through",
        order: 1,
        activates: [],
        suppresses: ["beat:meat-flank"],
      },
    ]);
    // Flat element projection preserves document order across all four kinds.
    expect(index.elements.map((element) => element.id)).toEqual([
      "beat:hold-the-gate",
      "scene:gate-line",
      "choice:who-gets-through",
      "option:cure-line-first",
      "option:families-first",
      "beat:panic-breaks",
      "scene:the-crush",
      "beat:meat-flank",
    ]);
  });

  it("keeps Scene and Decision as distinguishable Beat-owned H3 siblings", () => {
    const imported = markdownToTiptapDoc(V2_REPRESENTATIVE);
    const headings = (imported.doc.content ?? []).filter(
      (node) => node.type === "heading"
        && (node.attrs as { playableElementKind?: string } | undefined)?.playableElementKind,
    );
    const byId = new Map(
      headings.map((node) => {
        const attrs = node.attrs as {
          playableElementId: string;
          playableElementKind: string;
          level: number;
        };
        return [attrs.playableElementId, attrs];
      }),
    );
    // Both H3, both owned by the same Beat; only the directive kind differs.
    expect(byId.get("scene:gate-line")).toMatchObject({ level: 3, playableElementKind: "scene" });
    expect(byId.get("choice:who-gets-through")).toMatchObject({ level: 3, playableElementKind: "choice" });
    const index = expectReadyV2(indexPlayableStructureV2(imported.doc));
    expect(index.scenes[0]?.beatId).toBe("beat:hold-the-gate");
    expect(index.choices[0]?.beatId).toBe("beat:hold-the-gate");
  });

  it("blocks orphan Scene/Choice/Option containment violations", () => {
    expectBlockedV2(
      indexPlayableStructureV2(markdownToTiptapDoc(
        "<!-- dmb-playable-element:v2 kind=scene id=scene:x -->\n### X\n",
      ).doc),
      "orphan_scene",
    );
    expectBlockedV2(
      indexPlayableStructureV2(markdownToTiptapDoc(
        "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->\n### C\n",
      ).doc),
      "orphan_choice",
    );
    expectBlockedV2(
      indexPlayableStructureV2(markdownToTiptapDoc(
        [
          "<!-- dmb-playable-element:v2 kind=beat id=beat:b -->",
          "## B",
          "<!-- dmb-playable-element:v2 kind=option id=option:o -->",
          "- go",
        ].join("\n"),
      ).doc),
      "orphan_option",
    );
  });

  it("blocks cross-Beat and unknown Scene associations", () => {
    expectBlockedV2(
      indexPlayableStructureV2(markdownToTiptapDoc(
        [
          "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
          "## A",
          "<!-- dmb-playable-element:v2 kind=scene id=scene:s -->",
          "### S",
          "<!-- dmb-playable-element:v2 kind=beat id=beat:b -->",
          "## B",
          "<!-- dmb-playable-element:v2 kind=choice id=choice:c scene=scene:s -->",
          "### C",
        ].join("\n"),
      ).doc),
      "bad_scene_association",
    );
    expectBlockedV2(
      indexPlayableStructureV2(markdownToTiptapDoc(
        [
          "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
          "## A",
          "<!-- dmb-playable-element:v2 kind=choice id=choice:c scene=scene:ghost -->",
          "### C",
        ].join("\n"),
      ).doc),
      "bad_scene_association",
    );
  });

  it("blocks transition edges to unknown targets", () => {
    expectBlockedV2(
      indexPlayableStructureV2(markdownToTiptapDoc(
        [
          "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
          "## A",
          "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->",
          "### C",
          "<!-- dmb-playable-element:v2 kind=option id=option:o activates=beat:ghost -->",
          "- go",
        ].join("\n"),
      ).doc),
      "bad_edge",
    );
  });

  it("blocks duplicate ids across all four kinds", () => {
    // Import-level duplicates are sealed as text with a warning; the index
    // must still defend against duplicates constructed inside the editor.
    const duplicated = markdownToTiptapDoc(
      [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
        "## A",
        "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->",
        "### C",
        "<!-- dmb-playable-element:v2 kind=option id=option:o -->",
        "- one",
        "<!-- dmb-playable-element:v2 kind=option id=option:o -->",
        "- two",
      ].join("\n"),
    );
    expect(duplicated.diagnostics.length).toBeGreaterThan(0);

    const crafted = {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 2, playableElementKind: "beat", playableElementId: "beat:a", playableElementVersion: "v2" },
          content: [{ type: "text", text: "A" }],
        },
        {
          type: "heading",
          attrs: { level: 3, playableElementKind: "choice", playableElementId: "choice:c", playableElementVersion: "v2" },
          content: [{ type: "text", text: "C" }],
        },
        {
          type: "bulletList",
          content: [
            {
              type: "listItem",
              attrs: { playableElementKind: "option", playableElementId: "option:o", playableElementVersion: "v2" },
              content: [{ type: "paragraph", content: [{ type: "text", text: "one" }] }],
            },
          ],
        },
        {
          type: "bulletList",
          content: [
            {
              type: "listItem",
              attrs: { playableElementKind: "option", playableElementId: "option:o", playableElementVersion: "v2" },
              content: [{ type: "paragraph", content: [{ type: "text", text: "two" }] }],
            },
          ],
        },
      ],
    };
    expectBlockedV2(indexPlayableStructureV2(crafted), "duplicate_identity");
  });

  it("ignores ordinary unmarked headings without disturbing v2 structure", () => {
    // D2 ordinary-heading termination: unmarked headings are prose, not
    // structure; they neither join nor break Beat ownership.
    const withOrdinaryHeadings = [
      "<!-- dmb-playable-element:v2 kind=beat id=beat:a beat_kind=spine -->",
      "## Beat A",
      "",
      "### Ordinary H3 note",
      "",
      "GM prose under an unmarked heading.",
      "",
      "<!-- dmb-playable-element:v2 kind=scene id=scene:s -->",
      "### S",
      "",
      "## Ordinary H2 interlude",
      "",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:b beat_kind=optional -->",
      "## Beat B",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(withOrdinaryHeadings);
    expect(imported.diagnostics).toEqual([]);
    const index = expectReadyV2(indexPlayableStructureV2(imported.doc));
    expect(index.beatOrder).toEqual(["beat:a", "beat:b"]);
    expect(index.beats[0]?.sceneOrder).toEqual(["scene:s"]);
    expect(index.beats[1]?.sceneOrder).toEqual([]);
    expect(index.elements.map((element) => element.id)).toEqual([
      "beat:a",
      "scene:s",
      "beat:b",
    ]);
  });

  it("fails closed on mixed v1/v2 documents in both index directions", () => {
    const mixed = [
      "<!-- dmb-playable-element:v1 kind=scene id=scene:s -->",
      "## S",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:b -->",
      "## B",
    ].join("\n");
    const imported = markdownToTiptapDoc(mixed);
    // Import itself fails closed: no identity attaches under mixed versions.
    expect(imported.diagnostics.length).toBeGreaterThan(0);
    expect(JSON.stringify(imported.doc)).not.toContain("playableElementId");

    const v2Only = markdownToTiptapDoc(V2_REPRESENTATIVE);
    expectBlockedV2(
      indexPlayableStructure(v2Only.doc) as never,
      "unsupported_version",
    );
  });
});
