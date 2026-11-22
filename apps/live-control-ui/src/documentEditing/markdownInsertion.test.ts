import { Editor } from '@tiptap/core';
import { afterEach, expect, it } from 'vitest';
import { PAGE_COMPOSER_EXTENSIONS } from '../tiptap/pageComposer/PageRow';
import { flattenPresentation } from '../tiptap/pageComposer/presentation';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdown, insertReviewedMarkdownAtAnchor, prepareReviewedMarkdownAtAnchor } from './markdownInsertion';
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

it('inserts a block table before a heading without splitting the heading', () => {
  const editor = page();
  editor.commands.setTextSelection(1);
  const before = editor.getJSON();
  const proposal = admitMarkdownInsertion('| NPC | Job |\n| --- | --- |\n| Nella | Ferrier |\n');
  insertReviewedMarkdown(editor, 1, proposal.content, JSON.stringify(before));
  expect(editor.getJSON().content?.map(node => node.type)).toEqual(['table', 'heading', 'paragraph', 'paragraph']);
  expect(editor.getJSON().content?.slice(1)).toEqual(before.content);
  editor.commands.undo();
  expect(editor.getJSON()).toEqual(before);
});

it('reopens an inline callout rewrite with its kind, title, and neighboring GM note', () => {
  const source = '> [!READ-ALOUD] First sight\n> Original spoken passage.\n\n> [!GM-NOTE] Pause\n> Wait for the players.\n';
  const editor = new Editor({
    extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: markdownToTiptapDoc(source).doc,
  });
  editors.push(editor);
  const original = 'Original spoken passage.';
  let from = -1;
  editor.state.doc.descendants((node, position) => {
    if (node.isText && node.text === original) from = position;
  });
  expect(from).toBeGreaterThan(0);
  const replacement = '**Mist** gathers along the boardwalk.';
  insertReviewedMarkdownAtAnchor(
    editor,
    { from, to: from + original.length },
    admitMarkdownInsertion(replacement).content,
    JSON.stringify(editor.getJSON()),
  );
  const saved = tiptapJsonToSemanticMarkdown(editor.getJSON());
  const reopened = markdownToTiptapDoc(saved);
  expect(reopened.diagnostics).toEqual([]);
  expect(tiptapJsonToSemanticMarkdown(reopened.doc)).toBe(source.replace(original, replacement));
});

it('prepares and inserts the same callouts on an illustrated Build page with block identities', () => {
  const source = 'Arrival paragraph.\n\n| Signal | Status |\n| --- | --- |\n| Lantern | Lit |\n\n![Boardwalk](dmb-media:00000000-0000-4000-8000-000000000001)\n';
  const parsed = markdownToTiptapDoc(source).doc;
  const editor = new Editor({
    extensions: [...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, ...PAGE_COMPOSER_EXTENSIONS],
    content: {
      ...parsed,
      content: parsed.content?.map((node, index) => ({
        ...node, attrs: { ...node.attrs, pageBlockId: `fixture-${index}` },
      })),
    },
  });
  editors.push(editor);
  const before = editor.getJSON();
  expect(before.content?.[2].content?.[0].type).toBe('mediaImage');
  const caret = editor.state.doc.firstChild!.nodeSize - 1;
  const proposal = admitMarkdownInsertion('> [!READ-ALOUD] Boardwalk\n> Reeds stir.\n\n> [!GM-NOTE] Pause\n> Wait for the players.\n');
  const prepared = prepareReviewedMarkdownAtAnchor(editor, caret, proposal.content, JSON.stringify(before));
  expect(prepareReviewedMarkdownAtAnchor(editor, caret, proposal.content, JSON.stringify(before))).toEqual(prepared);
  expect(editor.getJSON()).toEqual(before);
  insertReviewedMarkdownAtAnchor(editor, caret, proposal.content, JSON.stringify(before));
  expect(editor.getJSON()).toEqual(prepared);
  const blocks = editor.getJSON().content!;
  expect([blocks[0], ...blocks.slice(3)]).toEqual(before.content);
  const ids = blocks.map(node => node.attrs?.pageBlockId);
  expect(ids.every(Boolean)).toBe(true);
  expect(new Set(ids).size).toBe(blocks.length);
  const saved = tiptapJsonToSemanticMarkdown(flattenPresentation(editor.getJSON()));
  expect(tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(saved).doc)).toBe(saved);
  editor.commands.undo();
  expect(editor.getJSON()).toEqual(before);
});
