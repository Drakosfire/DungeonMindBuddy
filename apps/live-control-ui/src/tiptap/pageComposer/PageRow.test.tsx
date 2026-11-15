import { afterEach, describe, expect, it, vi } from 'vitest';
import { Editor, type JSONContent } from '@tiptap/core';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { PAGE_COMPOSER_EXTENSIONS, movePageBlock, resizePageRow, unwrapPageRow, wrapPageRow, updatePageRowPresentation } from './PageRow';

const paragraph = (text: string, id = text): JSONContent => ({ type: 'paragraph', attrs: { pageBlockId: id }, content: [{ type: 'text', text }] });
let editor: Editor;
afterEach(() => editor?.destroy());
function create(content: JSONContent[] = [paragraph('First'), paragraph('Second'), paragraph('Third')]) {
  editor = new Editor({ extensions: [...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, ...PAGE_COMPOSER_EXTENSIONS], content: { type: 'doc', content } });
  return editor;
}

describe('Page row editor transactions', () => {
  it('wraps adjacent blocks in reading order, unwraps, and preserves block identities', () => {
    create();
    expect(wrapPageRow(editor)).toBe(true);
    expect(editor.state.doc.child(0).type.name).toBe('pageRow');
    expect(editor.state.doc.textContent).toBe('FirstSecondThird');
    expect(editor.state.doc.child(0).child(0).child(0).attrs.pageBlockId).toBe('First');
    expect(unwrapPageRow(editor)).toBe(true);
    expect(editor.state.doc.childCount).toBe(3);
    expect(editor.state.doc.child(0).attrs.pageBlockId).toBe('First');
    expect(editor.commands.undo()).toBe(true);
    expect(editor.state.doc.child(0).type.name).toBe('pageRow');
    expect(editor.commands.redo()).toBe(true);
    expect(editor.state.doc.child(0).type.name).toBe('paragraph');
  });

  it('snaps divider widths and undoes only the resize', () => {
    create(); wrapPageRow(editor);
    expect(resizePageRow(editor, 0, 8.1)).toBe(true);
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(8);
    expect(editor.state.doc.child(0).child(1).attrs.width).toBe(4);
    expect(editor.commands.undo()).toBe(true);
    expect(editor.state.doc.child(0).type.name).toBe('pageRow');
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(6);
    editor.commands.redo();
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(8);
    resizePageRow(editor, 0, 100);
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(10);
  });

  it('moves only by an explicit command and keeps native text editing', () => {
    create(); wrapPageRow(editor);
    expect(movePageBlock(editor, -1)).toBe(false);
    expect(movePageBlock(editor, 1)).toBe(true);
    expect(editor.state.doc.textContent).toBe('SecondFirstThird');
    expect(editor.state.selection.$from.parent.textContent).toBe('First');
    editor.commands.insertContent('X');
    expect(editor.state.doc.textContent).toBe('SecondXFirstThird');
  });

  it('refuses wrapping a row or the last block', () => {
    create(); wrapPageRow(editor);
    expect(wrapPageRow(editor)).toBe(false);
    editor.commands.setTextSelection(editor.state.doc.content.size - 1);
    expect(wrapPageRow(editor)).toBe(false);
  });

  it('retains actual table and callout nodes rather than substituting layout cells', () => {
    const table: JSONContent = { type: 'table', content: [{ type: 'tableRow', content: [{ type: 'tableHeader', content: [paragraph('Header')] }] }] };
    const callout: JSONContent = { type: 'callout', attrs: { kind: 'gm-note' }, content: [paragraph('Note')] };
    create([table, callout]);
    expect(wrapPageRow(editor)).toBe(true);
    expect(editor.state.doc.child(0).child(0).child(0).type.name).toBe('table');
    expect(editor.state.doc.child(0).child(1).child(0).type.name).toBe('callout');
    expect(editor.schema.nodes.pageSlot.validContent(editor.state.doc.content)).toBe(false);
  });

  it('exposes a keyboard separator', () => {
    create(); wrapPageRow(editor);
    const divider = editor.view.dom.querySelector('[role=separator]') as HTMLButtonElement;
    expect(divider.getAttribute('aria-label')).toBe('Resize row columns');
    divider.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(5);
    divider.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(10);
  });

  it('previews pointer movement without changing state and commits a drag in one undo', () => {
    create(); wrapPageRow(editor);
    const divider = editor.view.dom.querySelector('[role=separator]') as HTMLButtonElement;
    const slots = editor.view.dom.querySelector('.page-composer-row__slots') as HTMLElement;
    vi.spyOn(slots, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 120 } as DOMRect);
    divider.setPointerCapture = vi.fn();
    function pointer(type: string, x: number) {
      const event = new Event(type, { bubbles: true });
      Object.defineProperties(event, { clientX: { value: x }, pointerId: { value: 1 }, button: { value: 0 } });
      divider.dispatchEvent(event);
    }
    pointer('pointerdown', 60); pointer('pointermove', 70); pointer('pointermove', 80);
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(6);
    expect(divider.getAttribute('aria-valuenow')).toBe('8');
    pointer('pointerup', 80);
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(8);
    editor.commands.undo();
    expect(editor.state.doc.child(0).type.name).toBe('pageRow');
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(6);
  });

  it('stamps missing source block IDs after editing, preserves them on move, and heals pasted duplicates', () => {
    create([{ type: 'paragraph', content: [{ type: 'text', text: 'First' }] }, { type: 'paragraph', content: [{ type: 'text', text: 'Second' }] }]);
    expect(editor.state.doc.child(0).attrs.pageBlockId).toBeNull();
    wrapPageRow(editor);
    const id = editor.state.doc.child(0).child(0).child(0).attrs.pageBlockId;
    expect(id).toMatch(/^page-/);
    movePageBlock(editor, 1);
    expect(editor.state.doc.child(0).child(1).child(0).attrs.pageBlockId).toBe(id);
    unwrapPageRow(editor);
    const copy = editor.state.doc.child(1).toJSON();
    editor.commands.insertContentAt(editor.state.doc.content.size, copy);
    const ids: string[] = []; editor.state.doc.forEach(block => ids.push(block.attrs.pageBlockId));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('places a block into an explicitly empty neighboring slot without inventing text', () => {
    create([{ type: 'pageRow', attrs: { id: 'row' }, content: [
      { type: 'pageSlot', attrs: { id: 'left', width: 6 }, content: [paragraph('Only')] },
      { type: 'pageSlot', attrs: { id: 'right', width: 6 } },
    ] }]);
    editor.commands.setTextSelection(3);
    expect(movePageBlock(editor, 1)).toBe(true);
    expect(editor.state.doc.child(0).child(0).childCount).toBe(0);
    expect(editor.state.doc.child(0).child(1).child(0).attrs.pageBlockId).toBe('Only');
    expect(editor.state.doc.textContent).toBe('Only');
    expect(movePageBlock(editor, -1)).toBe(true);
    expect(editor.state.doc.child(0).child(1).childCount).toBe(0);
  });

  it('wraps three slots and resizes adjacent pairs without changing the third', () => {
    create(); expect(wrapPageRow(editor, false, 3)).toBe(true);
    expect(editor.state.doc.child(0).childCount).toBe(3);
    expect(editor.state.doc.textContent).toBe('FirstSecondThird');
    expect(resizePageRow(editor, 0, 6, 0)).toBe(true);
    expect([0, 1, 2].map(i => editor.state.doc.child(0).child(i).attrs.width)).toEqual([6, 2, 4]);
    expect(resizePageRow(editor, 0, 3, 1)).toBe(true);
    expect([0, 1, 2].map(i => editor.state.doc.child(0).child(i).attrs.width)).toEqual([6, 3, 3]);
    editor.commands.undo();
    expect([0, 1, 2].map(i => editor.state.doc.child(0).child(i).attrs.width)).toEqual([6, 2, 4]);
    expect(editor.state.doc.textContent).toBe('FirstSecondThird');
  });

  it('supports a single full-width row and independent row presentation', () => {
    create(); expect(wrapPageRow(editor, false, 1)).toBe(true);
    expect(editor.state.doc.child(0).child(0).attrs.width).toBe(12);
    expect(resizePageRow(editor, 0, 4)).toBe(false);
    expect(updatePageRowPresentation(editor, 0, { min_height: 160, line_mode: 'border' })).toBe(true);
    expect(editor.state.doc.child(0).attrs).toMatchObject({ min_height: 160, line_mode: 'border' });
    expect(editor.view.dom.querySelector('[data-page-row]')?.getAttribute('data-line-mode')).toBe('border');
    expect((editor.view.dom.querySelector('.page-composer-row__slots') as HTMLElement).style.getPropertyValue('--page-min-height')).toBe('160px');
    editor.commands.undo();
    expect(editor.state.doc.child(0).attrs).toMatchObject({ min_height: 0, line_mode: 'guide' });
    editor.commands.redo();
    updatePageRowPresentation(editor, 0, { min_height: 0, line_mode: 'clean' });
    expect(editor.state.doc.child(0).attrs).toMatchObject({ min_height: 0, line_mode: 'clean' });
  });

  it('rejects invalid row presentation and nonfinite widths without a transaction', () => {
    create(); wrapPageRow(editor);
    const before = editor.state.doc;
    for (const min_height of [-8, 7, 648, NaN, Infinity]) expect(updatePageRowPresentation(editor, 0, { min_height })).toBe(false);
    expect(updatePageRowPresentation(editor, 0, { line_mode: 'invalid' as 'clean' })).toBe(false);
    expect(resizePageRow(editor, 0, NaN)).toBe(false);
    expect(resizePageRow(editor, 0, 4, 4)).toBe(false);
    expect(editor.state.doc).toBe(before);
  });

  it('exposes keyboard height resizing with auto reset, retaining editor selection', () => {
    create(); wrapPageRow(editor);
    const from = editor.state.selection.from;
    const height = editor.view.dom.querySelector('[aria-label="Resize minimum row height"]') as HTMLButtonElement;
    height.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    expect(editor.state.doc.child(0).attrs.min_height).toBe(8);
    expect(editor.state.selection.from).toBe(from);
    height.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
    expect(editor.state.doc.child(0).attrs.min_height).toBe(0);
    expect(height.getAttribute('aria-valuetext')).toBe('Automatic height');
  });

  it('starts height drag at the visible content bottom when height is automatic', () => {
    create(); wrapPageRow(editor);
    const height = editor.view.dom.querySelector('[aria-label="Resize minimum row height"]') as HTMLButtonElement;
    const slots = editor.view.dom.querySelector('.page-composer-row__slots') as HTMLElement;
    vi.spyOn(slots, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 120, height: 300 } as DOMRect);
    height.setPointerCapture = vi.fn();
    function pointer(type: string, y: number) {
      const event = new Event(type, { bubbles: true });
      Object.defineProperties(event, { clientY: { value: y }, pointerId: { value: 1 }, button: { value: 0 } });
      height.dispatchEvent(event);
    }
    pointer('pointerdown', 300); pointer('pointermove', 400);
    expect(editor.state.doc.child(0).attrs.min_height).toBe(0);
    expect(height.getAttribute('aria-valuenow')).toBe('400');
    pointer('pointerup', 400);
    expect(editor.state.doc.child(0).attrs.min_height).toBe(400);
    editor.commands.undo();
    expect(editor.state.doc.child(0).attrs.min_height).toBe(0);
  });

  it('does not allow commands on a read-only editor', () => {
    create(); editor.setEditable(false);
    expect(wrapPageRow(editor)).toBe(false);
    expect(movePageBlock(editor, 1)).toBe(false);
    expect(unwrapPageRow(editor)).toBe(false);
    expect(resizePageRow(editor, 0, 8)).toBe(false);
  });
});
