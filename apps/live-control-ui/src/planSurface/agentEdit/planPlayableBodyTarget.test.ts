import { Editor } from "@tiptap/core";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import bodyCodecFixture from "../../../../../tests/fixtures/plan_playable_body_codec_v1.json";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { resolvePlayableBodyTarget, type PlayableBodyTarget } from "./planPlayableBodyTarget";

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
