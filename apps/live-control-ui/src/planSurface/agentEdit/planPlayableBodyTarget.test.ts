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

it("allows only schema-empty heading content to normalize across protected Markdown reload", async () => {
  const markdown = [
    "# ",
    "",
    "<!-- dmb-playable-element:v2 kind=beat id=beat:smoke beat_kind=spine -->",
    "## Smoke",
    "",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:smoke -->",
    "### Quiet scene",
    "",
    "The original body.",
    "",
    "<!-- dmb-playable-element:v2 kind=choice id=choice:smoke scene=scene:smoke -->",
    "### Choose",
    "",
    "<!-- dmb-playable-element:v2 kind=option id=option:smoke -->",
    "- Continue.",
    "",
  ].join("\n");
  const imported = markdownToTiptapDoc(markdown);
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: imported.doc });
  editors.push(editor);
  const target = await resolvePlayableBodyTarget(editor, { kind: "scene", id: "scene:smoke" });
  const before = editor.getJSON();
  const reloaded = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(before)).doc;

  expect(before.content?.[0]).toMatchObject({ type: "heading" });
  expect(before.content?.[0]?.content).toBeUndefined();
  expect(reloaded.content?.[0]).toMatchObject({ type: "heading", content: [] });
  expect(playableBodyProtectedStructureMatches(before, reloaded, target)).toBe(true);

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
});
