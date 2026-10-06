import { Editor } from "@tiptap/core";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import bodyCodecFixture from "../../../../../tests/fixtures/plan_playable_body_codec_v1.json";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { playableBodyProtectedStructureMatches, resolvePlayableBodyTarget, type PlayableBodyTarget } from "./planPlayableBodyTarget";

const editors: Editor[] = [];
const vectors = bodyCodecFixture.vectors as Array<{
  name: string;
  draft_markdown: string;
  target: PlayableBodyTarget;
  expected: { available: boolean; body_markdown?: string; body_sha256?: string };
}>;

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

afterEach(() => {
  for (const editor of editors.splice(0)) editor.destroy();
});

describe("shared Playable body codec vectors", () => {
  for (const vector of vectors) {
    it(vector.name, async () => {
      const imported = markdownToTiptapDoc(vector.draft_markdown);
      const editor = new Editor({
        extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
        content: imported.doc,
      });
      editors.push(editor);

      if (!vector.expected.available) {
        const warnings = imported.diagnostics.filter((item) => item.level === "warning");
        if (warnings.length) {
          if (vector.name.endsWith("_ordinary_https_unsupported")) {
            expect(warnings.some((item) => item.message.includes("Ordinary Markdown links"))).toBe(true);
          }
          return;
        }
        await expect(resolvePlayableBodyTarget(editor, vector.target)).rejects.toThrow();
        return;
      }

      expect(imported.diagnostics.filter((item) => item.level === "warning")).toEqual([]);
      const resolved = await resolvePlayableBodyTarget(editor, vector.target);
      expect(resolved.targetBodyMarkdown).toBe(vector.expected.body_markdown);
      expect(resolved.targetBodySha256).toBe(vector.expected.body_sha256);
    });
  }
});

it("allows schema-empty headings and list attrs to normalize across protected Markdown reload", async () => {
  const markdown = [
    "- An earlier ordinary list item.",
    "",
    "# ",
    "",
    "<!-- dmb-playable-element:v2 kind=beat id=beat:smoke beat_kind=spine -->",
    "## Smoke",
    "",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:smoke -->",
    "### Quiet scene",
    "",
    "The original body with [the guide](dmb-node:node:guide).",
    "",
    "<!-- dmb-playable-element:v2 kind=choice id=choice:smoke scene=scene:smoke -->",
    "### Choose",
    "",
    "<!-- dmb-playable-element:v2 kind=option id=option:smoke -->",
    "- Continue.",
    "",
    "- A later ordinary list item.",
    "",
  ].join("\n");
  const imported = markdownToTiptapDoc(markdown);
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: imported.doc });
  editors.push(editor);
  const target = await resolvePlayableBodyTarget(editor, { kind: "scene", id: "scene:smoke" });
  const before = editor.getJSON();
  const reloaded = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(before)).doc;

  expect(before.content?.[0]).toMatchObject({ type: "bulletList" });
  const earlierListItem = before.content?.[0]?.content?.[0];
  expect(earlierListItem?.attrs).toMatchObject({
    playableActivates: null,
    playableElementId: null,
    playableElementKind: null,
    playableElementVersion: null,
    playableSuppresses: null,
  });
  expect(reloaded.content?.[0]?.content?.[0]?.attrs).toBeUndefined();
  expect(before.content?.some((node) => node.type === "heading" && node.content === undefined)).toBe(true);
  expect(reloaded.content?.some((node) => node.type === "heading" && node.content?.length === 0)).toBe(true);
  expect(playableBodyProtectedStructureMatches(before, reloaded, target)).toBe(true);

  const changedListAttribute = structuredClone(reloaded);
  const ordinaryItem = changedListAttribute.content?.[0]?.content?.[0];
  if (!ordinaryItem || ordinaryItem.type !== "listItem") throw new Error("Expected a protected ordinary list item.");
  ordinaryItem.attrs = { playableActivates: ["beat:changed"] };
  expect(playableBodyProtectedStructureMatches(before, changedListAttribute, target)).toBe(false);

  const changedSibling = structuredClone(reloaded);
  const choiceHeading = changedSibling.content?.[target.rootEndIndex];
  if (!choiceHeading?.content?.[0]) throw new Error("Expected a protected sibling heading text node.");
  choiceHeading.content[0].text = "Changed choice";
  expect(playableBodyProtectedStructureMatches(before, changedSibling, target)).toBe(false);

  const changedMarker = structuredClone(reloaded);
  const sceneHeading = changedMarker.content?.[target.rootStartIndex - 1];
  if (!sceneHeading?.attrs) throw new Error("Expected the protected Scene marker attributes.");
  sceneHeading.attrs.playableElementId = "scene:changed";
  expect(playableBodyProtectedStructureMatches(before, changedMarker, target)).toBe(false);

  const changedMark = structuredClone(reloaded);
  const changedChoice = changedMark.content?.[target.rootEndIndex];
  if (!changedChoice?.content?.[0]) throw new Error("Expected the protected sibling heading text node.");
  changedChoice.content[0].marks = [{ type: "bold" }];
  expect(playableBodyProtectedStructureMatches(before, changedMark, target)).toBe(false);

  const lostReference = structuredClone(reloaded);
  const sceneBody = lostReference.content?.[target.rootStartIndex];
  if (!sceneBody?.content) throw new Error("Expected the Scene body containing a protected Graph reference.");
  sceneBody.content = sceneBody.content.filter((node) => node.type !== "graphNodeReference");
  expect(playableBodyProtectedStructureMatches(before, lostReference, target)).toBe(false);

  const movedSibling = structuredClone(reloaded);
  const movedRoot = movedSibling.content;
  if (!movedRoot?.[target.rootEndIndex + 1]) throw new Error("Expected a protected sibling list after the Choice heading.");
  [movedRoot[target.rootEndIndex], movedRoot[target.rootEndIndex + 1]] = [
    movedRoot[target.rootEndIndex + 1]!,
    movedRoot[target.rootEndIndex]!,
  ];
  expect(playableBodyProtectedStructureMatches(before, movedSibling, target)).toBe(false);
});
