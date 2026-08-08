import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";

const markdownPasteKey = new PluginKey("semanticMarkdownPaste");

/** Heuristic: clipboard text looks like Plan/semantic Markdown, not plain prose. */
export function looksLikeSemanticMarkdown(text: string): boolean {
  const sample = text.replace(/^\uFEFF/, "").trim();
  if (!sample || sample.length < 2) return false;
  if (/^#{1,6}\s+\S/m.test(sample)) return true;
  if (/^>\s*\[![^\]]+\]/m.test(sample)) return true;
  if (/^---[ \t]*\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/.test(sample)) return true;
  if (/^[-*]\s+\S/m.test(sample) && /\n[-*]\s+\S/.test(sample)) return true;
  if (/^\d+[.)]\s+\S/m.test(sample) && /\n\d+[.)]\s+\S/.test(sample)) return true;
  return false;
}

/**
 * Paste handler: when clipboard is semantic Markdown, import to TipTap nodes
 * instead of inserting raw `>`, `#!`, and callout markers as plain text.
 */
export const SemanticMarkdownPaste = Extension.create({
  name: "semanticMarkdownPaste",

  addProseMirrorPlugins() {
    const editor = this.editor;
    return [
      new Plugin({
        key: markdownPasteKey,
        props: {
          handlePaste(_view, event) {
            if (!event.clipboardData) return false;
            // Prefer rich HTML from other TipTap docs; only intercept plain text.
            const html = event.clipboardData.getData("text/html");
            if (html && /data-md-callout|data-md-decision-consequence|ProseMirror/i.test(html)) {
              return false;
            }
            const text = event.clipboardData.getData("text/plain") ?? "";
            if (!looksLikeSemanticMarkdown(text)) return false;

            const { doc } = markdownToTiptapDoc(text);
            const content = doc.content;
            if (!Array.isArray(content) || content.length === 0) return false;

            editor.commands.insertContent(content);
            return true;
          },
        },
      }),
    ];
  },
});
