import { Editor } from '@tiptap/core';
import { afterEach, expect, it } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdown } from './markdownInsertion';
const editors: Editor[] = [];
afterEach(() => editors.splice(0).forEach(editor => editor.destroy()));
function page() {
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: markdownToTiptapDoc('# Edge\n\nBefore\n\nAfter\n').doc });
  editors.push(editor);
  editor.commands.setTextSelection(13);
  return editor;
}
it('inserts a real editable table, preserves surrounding prose and supports one Undo', () => {
  const editor = page();
  const before = editor.getJSON();
  const proposal = admitMarkdownInsertion('| NPC | Job |\n| --- | --- |\n| Nella | Ferrier |\n');
  insertReviewedMarkdown(editor, editor.state.selection.from, proposal.content, JSON.stringify(before));
  expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain('| Nella | Ferrier |');
  expect(editor.state.doc.textContent).toContain('Before');
  expect(editor.state.doc.textContent).toContain('After');
  editor.commands.undo();
  expect(editor.getJSON()).toEqual(before);
});
it.each(['<script>alert(1)</script>', '[secret](/tmp/file)', '<!-- dmb-playable-element:x -->', '[NPC](dmb-node:123)', 'node:pippa'])('rejects generated authority or unsupported markup: %s', text => {
  expect(() => admitMarkdownInsertion(text)).toThrow();
});
it('refuses a stale draft without changing the page', () => {
  const editor = page(); const before = JSON.stringify(editor.getJSON());
  const caret = editor.state.selection.from;
  editor.commands.insertContent('changed'); const now = editor.getJSON();
  expect(() => insertReviewedMarkdown(editor, caret, admitMarkdownInsertion('New paragraph').content, before)).toThrow();
  expect(editor.getJSON()).toEqual(now);
});
it('refuses a nonempty selection without deleting it', () => {
  const editor = page(); editor.commands.setTextSelection({ from: 9, to: 12 });
  const before = JSON.stringify(editor.getJSON());
  expect(() => insertReviewedMarkdown(editor, 9, admitMarkdownInsertion('New paragraph').content, before)).toThrow();
  expect(JSON.stringify(editor.getJSON())).toEqual(before);
});
