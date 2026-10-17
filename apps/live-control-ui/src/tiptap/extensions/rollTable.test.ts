import { expect, it } from 'vitest';
import { Editor } from '@tiptap/core';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { markdownToTiptapDoc } from '../markdown/markdownToTiptap';
import { readRollTable, rollFace } from './rollTable';

function read(rows: string, die = 'd20') {
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: markdownToTiptapDoc(`| ${die} | Soldier |\n| --- | --- |\n${rows}`).doc });
  try { return readRollTable(editor.state.doc.firstChild!); } finally { editor.destroy(); }
}
it('covers every face and selects the correct entry, including ranges', () => {
  const table = read('| 1-10 | Mara |\n| 11–20 | Pell |')!;
  expect(table.sides).toBe(20);
  for (let face = 1; face <= 20; face++) {
    expect(rollFace(20, () => face - 1)).toBe(face);
    expect(table.entries.find(row => face >= row.from && face <= row.to)?.text).toBe(face <= 10 ? 'Mara' : 'Pell');
  }
});
it('rejects missing, overlapping, out-of-range and ordinary tables', () => {
  expect(read('| 1-19 | Mara |')).toBeNull();
  expect(read('| 1-20 | Mara |\n| 20 | Pell |')).toBeNull();
  expect(read('| 0-20 | Mara |')).toBeNull();
  expect(read('| 1-21 | Mara |')).toBeNull();
  expect(read('| 1-20 | Mara |', 'Name')).toBeNull();
});
it('rejects the biased tail of the random domain', () => {
  const values = [0xffffffff, 19];
  expect(rollFace(20, () => values.shift()!)).toBe(20);
  expect(values).toEqual([]);
});
