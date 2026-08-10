import type { JSONContent } from "@tiptap/core";

import {
  analyzeMarkdownBody,
  type MarkdownAdmissionResult,
} from "./markdownAdmission";
import { stripLeadingYamlFrontmatter } from "./stripLeadingYamlFrontmatter";

export type {
  MarkdownImportDiagnostic,
  MarkdownImportOptions,
} from "./markdownAdmission";

import type { MarkdownImportDiagnostic, MarkdownImportOptions } from "./markdownAdmission";

export type MarkdownImportResult = {
  doc: JSONContent;
  diagnostics: MarkdownImportDiagnostic[];
};

/**
 * Thin orchestration over the AST admission boundary (handoff §24):
 *
 *   raw source ──► strip leading YAML frontmatter (byte-exact, owned upstream)
 *              ──► normalize newlines
 *              ──► parseMarkdownAst (the ONLY structural parse)
 *              ──► analyzeMarkdownBody (admission + TipTap projection)
 *
 * Diagnostic line numbers are shifted back into original-document coordinates
 * so a stripped frontmatter envelope never moves the reported line (§7).
 */
export function markdownToTiptapDoc(
  markdown: string,
  options: MarkdownImportOptions = {},
): MarkdownImportResult {
  const split = stripLeadingYamlFrontmatter(markdown);
  const frontmatterLineOffset = (markdown.slice(0, split.removedLength).match(/\r\n|\r|\n/g) ?? []).length;
  const body = split.markdown.replace(/\r\n?/g, "\n");
  const analyzed: MarkdownAdmissionResult = analyzeMarkdownBody(body, options, frontmatterLineOffset);
  return { doc: { type: "doc", content: analyzed.content } as JSONContent, diagnostics: analyzed.diagnostics };
}

export function hasBlockingMarkdownImportDiagnostics(markdown: string): boolean {
  return markdownToTiptapDoc(markdown).diagnostics.some((diagnostic) => diagnostic.level === "warning");
}
