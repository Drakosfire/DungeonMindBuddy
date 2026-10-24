import { closeHistory } from '@tiptap/pm/history';
import { Editor, type JSONContent } from '@tiptap/core';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { semanticMarkdownSerializationDiagnostics } from '../tiptap/markdown/semanticMarkdownSafety';

/** Generated content is inert Markdown. Existing document identities remain untouched. */
export function admitMarkdownInsertion(markdown: string): { content: JSONContent[]; markdown: string } {
  if (!markdown.trim() || markdown.length > 12000
    || /<\/?[A-Za-z][^>]*>|<!--[\s\S]*?-->|dmb-node:|graphNodeReference|\bnode:[a-z0-9_-]+/i.test(markdown)
    || /^---\s*$/m.test(markdown)
    || /\[[^\]]*\]\((?:file:|\.{1,2}\/|\/)/i.test(markdown)) {
    throw new Error('This proposal contains unsupported markup or a document identity. Ask again.');
  }
  const parsed = markdownToTiptapDoc(markdown);
  if (parsed.diagnostics.some(item => item.level === 'warning')
    || semanticMarkdownSerializationDiagnostics(parsed.doc).length) {
    throw new Error('This proposal cannot be safely edited and saved as Markdown.');
  }
  const canonical = tiptapJsonToSemanticMarkdown(parsed.doc);
  const reopened = markdownToTiptapDoc(canonical);
  if (reopened.diagnostics.some(item => item.level === 'warning')
    || tiptapJsonToSemanticMarkdown(reopened.doc) !== canonical) {
    throw new Error('This proposal cannot round-trip through the editor.');
  }
  return { content: parsed.doc.content ?? [], markdown: canonical };
}

/** Validate the full resulting document before the one real editor transaction. */
export function insertReviewedMarkdown(editor: Editor, caret: number, content: JSONContent[], expectedJson: string): void {
  if (editor.isDestroyed || JSON.stringify(editor.getJSON()) !== expectedJson
    || !editor.state.selection.empty || editor.state.selection.from !== caret) {
    throw new Error('The page or insertion point changed. Ask again before inserting.');
  }
  insertReviewedMarkdownAtAnchor(editor, caret, content, expectedJson);
}

/** An exact snapshot authorizes its original position independently of today's selection. */
export function insertReviewedMarkdownAtAnchor(editor: Editor, caret: number, content: JSONContent[], expectedJson: string): void {
  if (editor.isDestroyed || JSON.stringify(editor.getJSON()) !== expectedJson
    || !Number.isInteger(caret) || caret < 0 || caret > editor.state.doc.content.size) {
    throw new Error('The page or original insertion point changed. Ask again before inserting.');
  }
  const simulated = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: editor.getJSON() });
  try {
    if (!simulated.commands.insertContentAt(caret, content)) throw new Error('Cannot insert at this position.');
    const result = simulated.getJSON();
    const markdown = tiptapJsonToSemanticMarkdown(result);
    const reopened = markdownToTiptapDoc(markdown);
    if (semanticMarkdownSerializationDiagnostics(result).length
      || reopened.diagnostics.some(item => item.level === 'warning')
      || tiptapJsonToSemanticMarkdown(reopened.doc) !== markdown) {
      throw new Error('Inserting here would prevent the page from saving safely.');
    }
  } finally { simulated.destroy(); }
  editor.view.dispatch(closeHistory(editor.state.tr));
  if (!editor.commands.insertContentAt(caret, content)) throw new Error('The editor could not insert this proposal.');
}
