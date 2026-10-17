import { Editor } from '@tiptap/core';
import { afterEach, expect, it, vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { markdownToTiptapDoc } from '../markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../markdown/calloutMarkdown';
import { tableMoveRange, moveTable } from './EmbeddedTableMove';
let editor: Editor | undefined;
afterEach(() => { editor?.destroy(); document.body.replaceChildren(); });
function mount() {
  editor = new Editor({ element: document.body.appendChild(document.createElement('div')), extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: markdownToTiptapDoc('Before.\n\n## Soldiers\n\n| d2 | Name |\n| --- | --- |\n| 1 | Mara |\n| 2 | Pell |\n\nAfter.').doc });
  return editor;
}
function position(editor: Editor) {
  let result = -1; editor.state.doc.forEach((node, pos) => { if (node.type.name === 'table') result = pos; }); return result;
}
function dragEvent(type: string, dataTransfer: object) {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.defineProperties(event, { dataTransfer: { value: dataTransfer }, clientX: { value: 0 }, clientY: { value: 0 } });
  return event;
}
it('moves the caption and whole table atomically and restores them with Undo', () => {
  const editor = mount(); const before = editor.getJSON();
  const range = tableMoveRange(editor.view, position(editor))!;
  expect(moveTable(editor.view, range, editor.state.doc.content.size)).toBe(true);
  const markdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
  expect(markdown.indexOf('After.')).toBeLessThan(markdown.indexOf('## Soldiers'));
  expect(markdown).toContain('Mara'); expect(markdown).toContain('Pell');
  editor.commands.undo(); expect(editor.getJSON()).toEqual(before);
});
it('routes actual handle drag events through a same-editor drop and rejects stale drags', () => {
  const editor = mount();
  const values = new Map<string, string>();
  const transfer = { setData: (type: string, value: string) => values.set(type, value), getData: (type: string) => values.get(type) ?? '', types: ['application/x-dungeonbuddy-table-move'] };
  vi.spyOn(editor.view, 'posAtCoords').mockImplementation(() => ({ pos: editor.state.doc.content.size, inside: -1 }));
  document.querySelector('[aria-label="Move table"]')!.dispatchEvent(dragEvent('dragstart', transfer));
  editor.createNodeViews(); // dragging state survives frame reattachment
  editor.view.dom.dispatchEvent(dragEvent('drop', transfer));
  expect(tiptapJsonToSemanticMarkdown(editor.getJSON()).indexOf('After.')).toBeLessThan(tiptapJsonToSemanticMarkdown(editor.getJSON()).indexOf('## Soldiers'));
  document.querySelector('[aria-label="Move table"]')!.dispatchEvent(dragEvent('dragstart', transfer));
  editor.commands.insertContentAt(1, 'Changed ');
  const before = editor.getJSON();
  editor.view.dom.dispatchEvent(dragEvent('drop', transfer));
  expect(editor.getJSON()).toEqual(before);
});
it('supports keyboard movement and refuses an interior drop', () => {
  const editor = mount(); const before = editor.getJSON();
  const range = tableMoveRange(editor.view, position(editor))!;
  expect(moveTable(editor.view, range, range.from + 1)).toBe(false);
  expect(editor.getJSON()).toEqual(before);
  document.querySelector('[aria-label="Move table"]')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', altKey: true, bubbles: true }));
  expect(editor.state.doc.firstChild?.textContent).toBe('Soldiers');
});

it('never splits adjacent titled tables during Up, Down or an interior-caption drop', () => {
  const editor = mount();
  editor.commands.setContent(markdownToTiptapDoc('## A\n\n| d1 | Name |\n| --- | --- |\n| 1 | Mara |\n\n## B\n\n| d1 | Name |\n| --- | --- |\n| 1 | Pell |').doc);
  const before = editor.getJSON();
  const pairs = () => {
    const values: string[] = []; editor.state.doc.forEach(node => values.push(node.type.name === 'heading' ? node.textContent : node.lastChild!.lastChild!.textContent)); return values;
  };
  document.querySelectorAll('[aria-label="Move table"]')[0]!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', altKey: true, bubbles: true }));
  expect(pairs()).toEqual(['B', 'Pell', 'A', 'Mara']);
  editor.commands.undo(); expect(editor.getJSON()).toEqual(before);
  document.querySelectorAll('[aria-label="Move table"]')[1]!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', altKey: true, bubbles: true }));
  expect(pairs()).toEqual(['B', 'Pell', 'A', 'Mara']);
  editor.commands.undo(); expect(editor.getJSON()).toEqual(before);
  const positions: number[] = []; editor.state.doc.forEach((node, pos) => { if (node.type.name === 'table') positions.push(pos); });
  moveTable(editor.view, tableMoveRange(editor.view, positions[1]!)!, positions[0]!);
  expect(pairs()).toEqual(['B', 'Pell', 'A', 'Mara']);
  editor.commands.undo(); expect(editor.getJSON()).toEqual(before);
});
