import { describe, expect, it } from "vitest";

import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import { PLAYABLE_ELEMENT_DIAGNOSTIC, PlayableIdentitySerializationError } from "./playableElementIdentity";
import { indexPlayableStructure } from "./playableStructureIndex";

const sceneBeatOnly = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
  "## Arrival",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:gate-opens -->",
  "### Gate opens",
  "",
].join("\n");

const choiceMarkdown = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
  "## The Gate",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->",
  "### Arrival",
  "",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
  "### Which route do they take?",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
  "#### Burn through the growth",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
  "#### Wait and watch",
  "",
].join("\n");

describe("P1C Choice/Option identity", () => {
  it("admits exact Choice H3 and Option H4 attrs from Markdown", () => {
    const imported = markdownToTiptapDoc(choiceMarkdown);
    expect(imported.diagnostics).toEqual([]);
    expect(imported.doc.content).toEqual(expect.arrayContaining([
      {
        type: "heading",
        attrs: { level: 3, playableElementKind: "choice", playableElementId: "choice:route" },
        content: [{ type: "text", text: "Which route do they take?" }],
      },
      {
        type: "heading",
        attrs: { level: 4, playableElementKind: "option", playableElementId: "option:fire" },
        content: [{ type: "text", text: "Burn through the growth" }],
      },
      {
        type: "heading",
        attrs: { level: 4, playableElementKind: "option", playableElementId: "option:wait" },
        content: [{ type: "text", text: "Wait and watch" }],
      },
    ]));
  });

  it("keeps existing Scene/Beat marker bytes and parents unchanged", () => {
    const imported = markdownToTiptapDoc(sceneBeatOnly);
    expect(imported.diagnostics).toEqual([]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toBe(sceneBeatOnly);
    const index = indexPlayableStructure(imported.doc);
    expect(index).toEqual({
      status: "ready",
      index: {
        sceneOrder: ["scene:arrival"],
        scenes: [{
          sceneId: "scene:arrival",
          order: 0,
          beatOrder: ["beat:gate-opens"],
          choiceOrder: [],
        }],
        choices: [],
        elements: [
          { kind: "scene", id: "scene:arrival", order: 0 },
          { kind: "beat", id: "beat:gate-opens", order: 1, sceneId: "scene:arrival" },
        ],
      },
    });
  });

  it("round-trips Choice/Option IDs through serialize and re-import after rename", () => {
    const imported = markdownToTiptapDoc(choiceMarkdown);
    const renamed = {
      ...imported.doc,
      content: (imported.doc.content ?? []).map((node) => {
        if (node.type !== "heading") return node;
        const id = (node.attrs as { playableElementId?: string } | undefined)?.playableElementId;
        if (id === "choice:route") {
          return { ...node, content: [{ type: "text", text: "Pick a path" }] };
        }
        if (id === "option:fire") {
          return { ...node, content: [{ type: "text", text: "Burn it" }] };
        }
        return node;
      }),
    };
    const exported = tiptapJsonToSemanticMarkdown(renamed);
    expect(exported).toContain("<!-- dmb-playable-element:v1 kind=choice id=choice:route -->");
    expect(exported).toContain("### Pick a path");
    expect(exported).toContain("<!-- dmb-playable-element:v1 kind=option id=option:fire -->");
    expect(exported).toContain("#### Burn it");
    expect(exported).toContain("<!-- dmb-playable-element:v1 kind=option id=option:wait -->");
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    const index = indexPlayableStructure(reimported.doc);
    expect(index.status).toBe("ready");
    if (index.status !== "ready") throw new Error("expected ready");
    expect(index.index.choices).toEqual([
      { choiceId: "choice:route", sceneId: "scene:gate", order: 0, optionOrder: ["option:fire", "option:wait"] },
    ]);
  });

  it("fails closed on Choice/Option kind/level mismatch", () => {
    const choiceOnH2 = markdownToTiptapDoc(
      "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->\n## Not a choice heading\n",
    );
    expect(choiceOnH2.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch }),
    ]));
    expect(JSON.stringify(choiceOnH2.doc)).not.toContain("playableElementId");

    const optionOnH3 = markdownToTiptapDoc(
      "<!-- dmb-playable-element:v1 kind=option id=option:fire -->\n### Not an option heading\n",
    );
    expect(optionOnH3.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch }),
    ]));
    expect(JSON.stringify(optionOnH3.doc)).not.toContain("playableElementId");
  });

  it("fails closed on duplicate Choice IDs without attaching identity", () => {
    const imported = markdownToTiptapDoc([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
      "## The Gate",
      "",
      "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
      "### First",
      "",
      "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
      "### Second",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.duplicate }),
    ]));
    const playableIds = (imported.doc.content ?? [])
      .map((node) => (node.attrs as { playableElementId?: string } | undefined)?.playableElementId)
      .filter((id): id is string => typeof id === "string");
    expect(playableIds).toEqual(["scene:gate"]);
  });

  it("throws when serializing nested Choice identity inside a callout", () => {
    expect(() => tiptapJsonToSemanticMarkdown({
      type: "doc",
      content: [{
        type: "callout",
        attrs: { kind: "gm-note" },
        content: [{
          type: "heading",
          attrs: { level: 3, playableElementKind: "choice", playableElementId: "choice:route" },
          content: [{ type: "text", text: "Hidden" }],
        }],
      }],
    })).toThrow(PlayableIdentitySerializationError);
  });

  it("does not treat Decision/Consequence as Choice structure", () => {
    const imported = markdownToTiptapDoc([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
      "## The Gate",
      "",
      "> [!DECISION-CONSEQUENCE]",
      ">",
      "> ### Decision",
      "> Ask at the gate.",
      ">",
      "> ### Consequence",
      "> The watch notices.",
      "",
    ].join("\n"));
    expect(JSON.stringify(imported.doc)).toContain("decisionConsequence");
    const index = indexPlayableStructure(imported.doc);
    expect(index).toMatchObject({
      status: "ready",
      index: {
        sceneOrder: ["scene:gate"],
        choices: [],
      },
    });
  });
});
// ---------------------------------------------------------------------------
// Beat-first (v2) grammar round trips
// ---------------------------------------------------------------------------

const v2BeatSceneChoice = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
  "## Hold the gate",
  "",
  "Triage at the gate line.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-line -->",
  "### The gate line",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:who-gets-through scene=scene:gate-line -->",
  "### Who gets through first?",
  "",
].join("\n");

const v2WithOptions = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
  "## Hold the gate",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:who-gets-through -->",
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
  "<!-- dmb-playable-element:v2 kind=beat id=beat:meat-flank beat_kind=interrupt -->",
  "## Meat flank",
  "",
].join("\n");

describe("v2 Beat-first grammar", () => {
  it("imports versioned Beat/Scene/Decision attrs and Option list items", () => {
    const imported = markdownToTiptapDoc(v2WithOptions);
    expect(imported.diagnostics).toEqual([]);
    const json = JSON.stringify(imported.doc);
    expect(json).toContain('"playableElementVersion":"v2"');
    expect(json).toContain('"playableBeatKind":"spine"');

    const headings = (imported.doc.content ?? []).filter((node) => node.type === "heading");
    const beat = headings.find(
      (node) => (node.attrs as { playableElementId?: string }).playableElementId === "beat:hold-the-gate",
    );
    expect(beat?.attrs).toMatchObject({
      level: 2,
      playableElementKind: "beat",
      playableElementVersion: "v2",
      playableBeatKind: "spine",
    });
    const choice = headings.find(
      (node) => (node.attrs as { playableElementId?: string }).playableElementId === "choice:who-gets-through",
    );
    expect(choice?.attrs).toMatchObject({ level: 3, playableElementKind: "choice" });

    const listItems: unknown[] = [];
    for (const node of imported.doc.content ?? []) {
      if (node.type !== "bulletList") continue;
      for (const item of (node as { content?: unknown[] }).content ?? []) {
        listItems.push(item);
      }
    }
    const option = listItems.find(
      (item) => ((item as { attrs?: { playableElementId?: string } }).attrs?.playableElementId)
        === "option:cure-line-first",
    ) as { attrs?: Record<string, unknown> } | undefined;
    expect(option?.attrs).toMatchObject({
      playableElementKind: "option",
      playableElementVersion: "v2",
      playableActivates: ["beat:panic-breaks"],
    });
  });

  it("round-trips v2 Beat/Scene/Decision headings with beat_kind and scene association", () => {
    const imported = markdownToTiptapDoc(v2BeatSceneChoice);
    expect(imported.diagnostics).toEqual([]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toBe(v2BeatSceneChoice);
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
  });

  it("keeps v2 identity stable through heading rename", () => {
    const imported = markdownToTiptapDoc(v2BeatSceneChoice);
    const renamed = {
      ...imported.doc,
      content: (imported.doc.content ?? []).map((node) => {
        if (node.type !== "heading") return node;
        const id = (node.attrs as { playableElementId?: string } | undefined)?.playableElementId;
        if (id === "beat:hold-the-gate") {
          return { ...node, content: [{ type: "text", text: "Hold the gate renamed" }] };
        }
        return node;
      }),
    };
    const exported = tiptapJsonToSemanticMarkdown(renamed);
    expect(exported).toContain(
      "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
    );
    expect(exported).toContain("## Hold the gate renamed");
  });

  it("round-trips v2 Options as marked list items with activates/suppresses edges", () => {
    const imported = markdownToTiptapDoc(v2WithOptions);
    expect(imported.diagnostics).toEqual([]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toContain(
      "<!-- dmb-playable-element:v2 kind=option id=option:cure-line-first activates=beat:panic-breaks -->",
    );
    expect(exported).toContain(
      "<!-- dmb-playable-element:v2 kind=option id=option:families-first suppresses=beat:meat-flank -->",
    );
    expect(exported).toContain("- Prioritize the cure line");
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    const json = JSON.stringify(reimported.doc);
    expect(json).toContain("option:cure-line-first");
    expect(json).toContain("option:families-first");
  });

  it("fails closed on mixed v1/v2 structural directives", () => {
    const mixed = [
      "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
      "## Arrival",
      "",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:gate beat_kind=spine -->",
      "## Gate",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(mixed);
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.mixedVersions }),
    ]));
    expect(JSON.stringify(imported.doc)).not.toContain("playableElementId");
  });

  it("keeps v2 markers inside fenced code literal", () => {
    const fenced = [
      "<!-- dmb-playable-element:v2 kind=beat id=beat:real -->",
      "## Real",
      "",
      "~~~",
      "<!-- dmb-playable-element:v2 kind=scene id=scene:fake -->",
      "### Fake",
      "~~~",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(fenced);
    // The pre-existing fence warning is unrelated to playable admission; the
    // v2 requirement is that the fenced marker stays literal and non-semantic.
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: expect.stringContaining("Fenced code") }),
    ]));
    expect(imported.diagnostics).toHaveLength(1);
    const json = JSON.stringify(imported.doc);
    expect(json).toContain("beat:real");
    // The fenced marker survives as literal code text but attaches no identity.
    expect(json).toContain("scene:fake");
    expect(json).not.toContain('"playableElementKind":"scene"');
  });

  it("fails closed on malformed v2 markers and wrong levels", () => {
    const wrongLevel = markdownToTiptapDoc(
      "<!-- dmb-playable-element:v2 kind=beat id=beat:x -->\n### Not H2\n",
    );
    expect(wrongLevel.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.levelMismatch }),
    ]));

    const badBeatKind = markdownToTiptapDoc(
      "<!-- dmb-playable-element:v2 kind=beat id=beat:x beat_kind=weird -->\n## X\n",
    );
    expect(badBeatKind.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.malformed }),
    ]));

    const optionBeforeHeading = markdownToTiptapDoc(
      [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:b -->",
        "## B",
        "<!-- dmb-playable-element:v2 kind=option id=option:o -->",
        "### Not a list item",
      ].join("\n"),
    );
    expect(optionBeforeHeading.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ message: PLAYABLE_ELEMENT_DIAGNOSTIC.orphanOption }),
    ]));
  });
});
