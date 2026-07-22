import { tiptapJsonToSemanticMarkdown } from "./markdown/calloutMarkdown";
import {
  markdownToTiptapDoc,
  type MarkdownImportDiagnostic,
  type MarkdownImportOptions,
  type MarkdownImportResult,
} from "./markdown/markdownToTiptap";

export type MarkdownDocumentAdapter = {
  importMarkdown(markdown: string, options?: MarkdownImportOptions): MarkdownImportResult;
  exportMarkdown(doc: unknown): string;
};

export const defaultMarkdownDocumentAdapter: MarkdownDocumentAdapter = {
  importMarkdown: (markdown, options) => markdownToTiptapDoc(markdown, options),
  exportMarkdown: (doc) => tiptapJsonToSemanticMarkdown(doc),
};

export function importMarkdownWithAdapter(
  markdown: string,
  options?: MarkdownImportOptions,
  adapter: MarkdownDocumentAdapter = defaultMarkdownDocumentAdapter,
): MarkdownImportResult {
  return adapter.importMarkdown(markdown, options);
}

export function exportMarkdownWithAdapter(
  doc: unknown,
  adapter: MarkdownDocumentAdapter = defaultMarkdownDocumentAdapter,
): string {
  return adapter.exportMarkdown(doc);
}

/** Warning-level import diagnostics block durable Markdown commit. */
export function isCommitBlockingDiagnostic(diagnostic: MarkdownImportDiagnostic): boolean {
  return diagnostic.level === "warning";
}

export function hasCommitBlockingDiagnostics(
  diagnostics: readonly MarkdownImportDiagnostic[],
): boolean {
  return diagnostics.some(isCommitBlockingDiagnostic);
}

export function commitBlockingDiagnosticMessages(
  diagnostics: readonly MarkdownImportDiagnostic[],
): string[] {
  return diagnostics
    .filter(isCommitBlockingDiagnostic)
    .map((diagnostic) => {
      const line = diagnostic.line != null ? `line ${diagnostic.line}: ` : "";
      return `${line}${diagnostic.message}`;
    });
}
