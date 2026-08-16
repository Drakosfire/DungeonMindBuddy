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
