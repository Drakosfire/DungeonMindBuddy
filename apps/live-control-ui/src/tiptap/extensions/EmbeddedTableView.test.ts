import { Editor } from '@tiptap/core';
import { afterEach, expect, it, vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { markdownToTiptapDoc } from '../markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../markdown/calloutMarkdown';

const source = '# Edge\n\n| d20 | Soldier | Detail |\n| --- | --- | --- |\n| 1 | Mara | Gate guard |\n| 20 | Pell | Peacekeeper |';
let editor: Editor | undefined;
afterEach(() => { editor?.destroy(); editor = undefined; document.body.replaceChildren(); });
function mount() {
  const element = document.body.appendChild(document.createElement('div'));
  const onUpdate = vi.fn();
  editor = new Editor({ element, extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: markdownToTiptapDoc(source).doc, onUpdate });
  return { editor, onUpdate };
}
it('collapses only the view, keeps editable content and exports no presentation chrome', async () => {
  const { editor, onUpdate } = mount();
  const original = editor.getJSON();
  const markdown = tiptapJsonToSemanticMarkdown(original);
  const toggle = document.querySelector<HTMLButtonElement>('.embedded-content-frame__header button[aria-expanded]')!;
  const body = document.querySelector<HTMLElement>('.embedded-content-frame__body')!;
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  expect(document.querySelector('.embedded-content-frame__header')).toHaveTextContent('2 rows');
  expect(document.querySelectorAll('col.embedded-content-frame__numeric-column')).toHaveLength(1);
  toggle.click();
  await new Promise(resolve => setTimeout(resolve, 10));
  expect(body.hidden).toBe(true);
  expect(toggle).toHaveAttribute('aria-label', 'Expand table');
  expect(editor.getJSON()).toEqual(original);
  expect(onUpdate).not.toHaveBeenCalled();
  editor.createNodeViews();
  expect(document.querySelector('.embedded-content-frame__body')).toHaveAttribute('hidden');
  const reboundToggle = document.querySelector<HTMLButtonElement>('.embedded-content-frame__header button[aria-expanded]')!;
  reboundToggle.click();
  expect(document.querySelector<HTMLElement>('.embedded-content-frame__body')!.hidden).toBe(false);
  let position = -1;
  editor.state.doc.descendants((node, pos) => { if (node.isText && node.text === 'Mara') position = pos; });
  expect(position).toBeGreaterThan(0);
  editor.commands.insertContentAt({ from: position, to: position + 4 }, 'Nella');
  expect(document.querySelector('tbody')).toHaveTextContent('Nella');
  const saved = tiptapJsonToSemanticMarkdown(editor.getJSON());
  expect(saved).toContain('Nella');
  expect(saved).not.toContain('Collapse');
  expect(editor.getHTML()).not.toContain('embedded-content-frame');
  const reopened = markdownToTiptapDoc(saved);
  expect(reopened.diagnostics).toEqual([]);
  expect(tiptapJsonToSemanticMarkdown(reopened.doc)).toBe(saved);
  editor.commands.undo();
  expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(markdown);
});
it('keeps different tables independently collapsible and updates row counts', () => {
  const { editor } = mount();
  const second = markdownToTiptapDoc(source).doc.content!;
  editor.commands.insertContentAt(editor.state.doc.content.size, second);
  const toggles = document.querySelectorAll<HTMLButtonElement>('.embedded-content-frame__header button[aria-expanded]');
  expect(toggles).toHaveLength(2);
  toggles[0]!.click();
  expect(toggles[0]).toHaveAttribute('aria-expanded', 'false');
  expect(toggles[1]).toHaveAttribute('aria-expanded', 'true');
});

it('stores the editable frame title in ordinary Markdown and rolls without changing the document', () => {
  const { editor, onUpdate } = mount();
  // Complete range coverage enables the local die control.
  editor.commands.setContent(markdownToTiptapDoc('| d20 | Soldier | Detail |\n| --- | --- | --- |\n| 1-10 | Mara | Gate guard |\n| 11-20 | Pell | Peacekeeper |').doc);
  const input = document.querySelector<HTMLInputElement>('input[aria-label="Table title"]')!;
  input.value = 'Soldiers You Might Run Into in Edge';
  input.dispatchEvent(new Event('change', { bubbles: true }));
  const saved = tiptapJsonToSemanticMarkdown(editor.getJSON());
  expect(saved).toContain('## Soldiers You Might Run Into in Edge');
  const reopened = markdownToTiptapDoc(saved);
  expect(reopened.diagnostics).toEqual([]);
  expect(tiptapJsonToSemanticMarkdown(reopened.doc)).toBe(saved);
  editor.createNodeViews();
  expect(document.querySelector<HTMLInputElement>('input[aria-label="Table title"]')!.value).toBe('Soldiers You Might Run Into in Edge');
  const before = editor.getJSON(); onUpdate.mockClear();
  const roll = Array.from(document.querySelectorAll('button')).find(button => button.textContent === 'Roll d20')!;
  roll.click();
  const result = document.querySelector('[role="status"]')!;
  expect(result.textContent).toMatch(/d20 → \d+: (Mara · Gate guard|Pell · Peacekeeper)/);
  expect(editor.getJSON()).toEqual(before);
  expect(onUpdate).not.toHaveBeenCalled();
  const text = result.textContent;
  editor.createNodeViews();
  expect(document.querySelector('[role="status"]')!.textContent).toBe(text);
});

it('refreshes captions after sibling Undo/Redo without overwriting an actively typed title', () => {
  const { editor } = mount();
  editor.commands.setContent(markdownToTiptapDoc('## Original\n\n| d1 | Name |\n| --- | --- |\n| 1 | Mara |').doc);
  const input = () => document.querySelector<HTMLInputElement>('input[aria-label="Table title"]')!;
  input().value = 'Changed'; input().dispatchEvent(new Event('change', { bubbles: true }));
  expect(input().value).toBe('Changed');
  editor.commands.undo();
  expect(input().value).toBe('Original');
  editor.commands.redo(); expect(input().value).toBe('Changed');
  input().focus(); input().value = 'Typing a title';
  editor.commands.insertContentAt(editor.state.doc.content.size, { type: 'paragraph', content: [{ type: 'text', text: 'Other edit' }] });
  expect(input().value).toBe('Typing a title');
  input().blur(); expect(input().value).toBe('Changed');
});

it.each(['identity', 'reference'] as const)('never adopts or overwrites a protected %s heading', kind => {
  const { editor } = mount();
  const table = markdownToTiptapDoc('| d1 | Name |\n| --- | --- |\n| 1 | Mara |').doc.content![0]!;
  const heading = kind === 'identity'
    ? { type: 'heading', attrs: { level: 2, playableElementId: 'preserve-identity' }, content: [{ type: 'text', text: 'Protected scene' }] }
    : { type: 'heading', attrs: { level: 2 }, content: [{ type: 'graphNodeReference', attrs: { nodeId: 'npc:mara', label: 'Mara' } }] };
  editor.commands.setContent({ type: 'doc', content: [heading, table] });
  const original = editor.state.doc.firstChild!.toJSON();
  const input = document.querySelector<HTMLInputElement>('input[aria-label="Table title"]')!;
  expect(input.value).toBe('');
  input.value = 'Soldiers'; input.dispatchEvent(new Event('change', { bubbles: true }));
  expect(editor.state.doc.firstChild!.toJSON()).toEqual(original);
  expect(editor.state.doc.child(1).textContent).toBe('Soldiers');
  expect(editor.state.doc.child(2).type.name).toBe('table');
});
