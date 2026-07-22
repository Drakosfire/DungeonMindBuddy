import { tiptapJsonToSemanticMarkdown } from "./markdown/calloutMarkdown";
import {
  markdownToTiptapDoc,
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
