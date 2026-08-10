import { Extension } from "@tiptap/core";
import type { JSONContent } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

import { markdownToTiptapDoc, type MarkdownImportDiagnostic } from "../markdown/markdownToTiptap";
import { splitLeadingYamlFrontmatter } from "../markdown/stripLeadingYamlFrontmatter";

const markdownPasteKey = new PluginKey("semanticMarkdownPaste");

const SEMANTIC_INTERCEPT_NODE_TYPES = new Set([
  "heading",
  "bulletList",
  "orderedList",
  "callout",
  "decisionConsequence",
  "table",
]);

function hasBlockingImportDiagnostics(diagnostics: MarkdownImportDiagnostic[]): boolean {
  return diagnostics.some((diagnostic) => diagnostic.level === "warning");
}

function hasSemanticBlockWorthIntercepting(content: JSONContent[] | undefined): boolean {
  if (!content || content.length === 0) return false;
  return content.some((node) => SEMANTIC_INTERCEPT_NODE_TYPES.has(String(node.type)));
}

/**
 * Importer/projection-backed predicate: true only when Markdown converts cleanly
 * and the projected doc contains a semantic block worth pasting as structure.
 */
export function looksLikeSemanticMarkdown(text: string): boolean {
  const sample = text.replace(/^\uFEFF/, "").trim();
  if (!sample || sample.length < 2) return false;
  if (splitLeadingYamlFrontmatter(sample).frontmatter) return false;

  const { doc, diagnostics } = markdownToTiptapDoc(text);
  if (hasBlockingImportDiagnostics(diagnostics)) return false;
  const content = doc.content;
  if (!Array.isArray(content)) return false;
  return hasSemanticBlockWorthIntercepting(content);
}

/**
 * Paste handler: when clipboard is semantic Markdown with zero blocking import
 * diagnostics, import to TipTap nodes instead of inserting raw markers as text.
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
            const html = event.clipboardData.getData("text/html");
            if (html && /data-md-callout|data-md-decision-consequence|ProseMirror/i.test(html)) {
              return false;
            }
            const text = event.clipboardData.getData("text/plain") ?? "";
            if (splitLeadingYamlFrontmatter(text).frontmatter) return false;
            if (!looksLikeSemanticMarkdown(text)) return false;

            const { doc, diagnostics } = markdownToTiptapDoc(text);
            if (hasBlockingImportDiagnostics(diagnostics)) return false;
            const content = doc.content;
            if (!Array.isArray(content) || content.length === 0) return false;
            if (!hasSemanticBlockWorthIntercepting(content)) return false;

            editor.commands.insertContent(content);
            return true;
          },
        },
      }),
    ];
  },
});
