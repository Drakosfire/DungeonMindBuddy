import { closeHistory } from '@tiptap/pm/history';
import type { Editor, JSONContent } from '@tiptap/core';
import type { Transaction } from '@tiptap/pm/state';
import { prepareReviewedBlockIdentities } from '../tiptap/pageComposer/PageRow';
import { flattenPresentation } from '../tiptap/pageComposer/presentation';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { semanticMarkdownSerializationDiagnostics } from '../tiptap/markdown/semanticMarkdownSafety';

/** Generated content is inert Markdown. Existing document identities remain untouched. */
export function admitMarkdownInsertion(markdown: string): { content: JSONContent[]; markdown: string } {
  if (/^ {0,3}(?:`{3,}|~{3,})dmb-work-plan-v1(?:[ \t]|$)/m.test(markdown)) throw new Error('Work-plan references require the typed author placement.');
  if (!markdown.trim()
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

function contentForTarget(editor:Editor,target:number | {from:number;to:number},content:JSONContent[]):JSONContent[] {
  if(typeof target==='number'||target.from===target.to)return content;
  const from=editor.state.doc.resolve(target.from),to=editor.state.doc.resolve(target.to);
  const paragraph=content.length===1&&content[0]?.type==='paragraph'?content[0]:null;
  // A textual revision inside one textblock stays inline, preserving its type and attributes.
  return paragraph&&from.sameParent(to)&&from.parent.isTextblock
    ? paragraph.content??[] : content;
}

function blockInsertionAnchor(editor: Editor, target: number | {from:number;to:number}, content: JSONContent[]) {
  if (typeof target !== 'number' || (content.length === 1 && content[0]?.type === 'paragraph')) return target;
  const position = editor.state.doc.resolve(target);
  // A block at the start of a heading belongs before it. Inserting into the
  // heading would split it and leave an empty heading in the saved document.
  return position.depth === 1 && position.parent.type.name === 'heading' && position.parentOffset === 0
    ? position.before() : target;
}

/** An exact snapshot authorizes its original position independently of today's selection. */
export function insertReviewedMarkdownAtAnchor(editor: Editor, caret: number | {from:number;to:number}, content: JSONContent[], expectedJson: string): void {
  const from = typeof caret === 'number' ? caret : caret.from;
  const to = typeof caret === 'number' ? caret : caret.to;
  if (editor.isDestroyed || JSON.stringify(editor.getJSON()) !== expectedJson
    || !Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to < from || to > editor.state.doc.content.size) {
    throw new Error('The page or original insertion point changed. Ask again before inserting.');
  }
  const transaction = prepareReviewedTransaction(editor, caret, content, expectedJson);
  const expected = transaction.doc;
  editor.view.dispatch(closeHistory(transaction));
  if (!editor.state.doc.eq(expected)) throw new Error('The insertion result needs inspection before continuing.');
}

export function prepareReviewedMarkdownAtAnchor(editor: Editor, caret: number | {from:number;to:number}, content: JSONContent[], expectedJson: string): JSONContent {
  return prepareReviewedTransaction(editor, caret, content, expectedJson).doc.toJSON();
}

function prepareReviewedTransaction(editor: Editor, caret: number | {from:number;to:number}, content: JSONContent[], expectedJson: string): Transaction {
  const from = typeof caret === 'number' ? caret : caret.from;
  const to = typeof caret === 'number' ? caret : caret.to;
  if (editor.isDestroyed || JSON.stringify(editor.getJSON()) !== expectedJson
    || !Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to < from || to > editor.state.doc.content.size) {
    throw new Error('The page or original insertion point changed.');
  }

  const preview: { transaction?: Transaction } = {};
  // Build the transaction with the mounted editor's schema and commands. The
  // regular Tiptap dispatch is suppressed until the resulting document passes admission.
  editor.commands.command(({ commands, tr }) => {
    tr.setMeta('preventDispatch', true);
    if (!commands.insertContentAt(blockInsertionAnchor(editor, caret, content), contentForTarget(editor, caret, content))) return false;
    preview.transaction = prepareReviewedBlockIdentities(tr);
    return true;
  });
  const prepared = preview.transaction;
  if (!prepared) throw new Error('Cannot insert at this position.');

  const body = flattenPresentation(prepared.doc.toJSON());
  const markdown = tiptapJsonToSemanticMarkdown(body);
  const reopened = markdownToTiptapDoc(markdown);
  if (semanticMarkdownSerializationDiagnostics(body).length
    || reopened.diagnostics.some(item => item.level === 'warning')
    || tiptapJsonToSemanticMarkdown(reopened.doc) !== markdown) {
    throw new Error('Inserting here would prevent the page from saving safely.');
  }
  return prepared;
}
