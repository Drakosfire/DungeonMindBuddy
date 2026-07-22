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

/** Commit policy for import diagnostics.

Default is advisory (plan/runbook). Worldbuilding sources use `worldbuilding_lossless`
so unsupported constructs block durable Markdown commit.
*/
export type MarkdownCommitPolicy = "advisory" | "worldbuilding_lossless";

/** Warning-level import diagnostics block durable Markdown commit only under lossless policy. */
export function isCommitBlockingDiagnostic(
  diagnostic: MarkdownImportDiagnostic,
  policy: MarkdownCommitPolicy = "advisory",
): boolean {
  if (policy !== "worldbuilding_lossless") {
    return false;
  }
  return diagnostic.level === "warning";
}

export function hasCommitBlockingDiagnostics(
  diagnostics: readonly MarkdownImportDiagnostic[],
  policy: MarkdownCommitPolicy = "advisory",
): boolean {
  return diagnostics.some((diagnostic) => isCommitBlockingDiagnostic(diagnostic, policy));
}

export function commitBlockingDiagnosticMessages(
  diagnostics: readonly MarkdownImportDiagnostic[],
  policy: MarkdownCommitPolicy = "advisory",
): string[] {
  return diagnostics
    .filter((diagnostic) => isCommitBlockingDiagnostic(diagnostic, policy))
    .map((diagnostic) => {
      const line = diagnostic.line != null ? `line ${diagnostic.line}: ` : "";
      return `${line}${diagnostic.message}`;
    });
}
