import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { EditorContent } from '@tiptap/react';
import { wrapPageImageText, unwrapPageImageText, updatePageImageText } from './PageImageText';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { NodeSelection } from "@tiptap/pm/state";
import { Editor, type JSONContent } from '@tiptap/core';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { PAGE_COMPOSER_EXTENSIONS, PageComposerTools, applyAgentImageMove, captureAgentImageMoves, movePageBlock, resizePageRow, unwrapPageRow, wrapPageRow, updatePageRowPresentation } from './PageRow';
import { flattenPresentation } from './presentation';
import { requiresManualSave } from '../../workspaceDocument/draftSavePolicy';

const paragraph = (text: string, id = text): JSONContent => ({ type: 'paragraph', attrs: { pageBlockId: id }, content: [{ type: 'text', text }] });
let editor: Editor;
afterEach(() => { cleanup(); editor?.destroy(); });
function create(content: JSONContent[] = [paragraph('First'), paragraph('Second'), paragraph('Third')], editable = true) {
  editor = new Editor({ editable, extensions: [...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, ...PAGE_COMPOSER_EXTENSIONS], content: { type: 'doc', content } });
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


describe('Image and text stack transactions', () => {
  const art: JSONContent = { type: 'paragraph', attrs: { pageBlockId: 'art' }, content: [{ type: 'mediaImage', attrs: { assetId: '11111111-1111-4111-8111-111111111111', alt: 'Forest', width: 80, collapsed: false } }] };
  it('wraps existing image then editable text, changes anchors and unwraps with identities preserved', () => {
    create([art, paragraph('Forest title', 'title')]);
    expect(wrapPageImageText(editor)).toBe(true);
    expect(editor.state.doc.child(0).type.name).toBe('pageImageText');
    expect(editor.state.doc.child(0).child(0).attrs.pageBlockId).toBe('art');
    expect(editor.state.doc.child(0).child(1).attrs.pageBlockId).toBe('title');
    expect(editor.state.doc.textContent).toBe('Forest title');
    expect(updatePageImageText(editor, { anchor: 'bottom-right', inset: 'medium', backing: 'none' })).toBe(true);
    expect(editor.state.doc.child(0).attrs).toMatchObject({ anchor: 'bottom-right', inset: 'medium', backing: 'none' });
    editor.commands.undo();
    expect(editor.state.doc.child(0).attrs.anchor).toBe('middle-center');
    expect(unwrapPageImageText(editor)).toBe(true);
    expect(editor.state.doc.childCount).toBe(2);
    expect(editor.state.doc.child(0).attrs.pageBlockId).toBe('art');
    expect(editor.state.doc.child(1).attrs.pageBlockId).toBe('title');
  });
  it('rejects non-image starts and nesting within callouts', () => {
    create([paragraph('Words'), paragraph('More')]);
    expect(wrapPageImageText(editor)).toBe(false);
    editor.commands.setContent({ type: 'doc', content: [{ type: 'callout', content: [art, paragraph('Caption')] }] });
    editor.commands.setTextSelection(2);
    expect(wrapPageImageText(editor)).toBe(false);
  });
  it('rejects unsupported presentation without mutation and retains actual editable title', () => {
    create([art, paragraph('Caption')]); wrapPageImageText(editor);
    const before = editor.state.doc;
    expect(updatePageImageText(editor, { anchor: 'bad' as 'top-left' })).toBe(false);
    expect(editor.state.doc).toBe(before);
    editor.commands.insertContent('New ');
    expect(editor.state.doc.textContent).toBe('New Caption');
    expect(editor.state.doc.child(0).child(0).child(0).attrs.width).toBe(80);
    expect(wrapPageImageText(editor)).toBe(false);
  });
  it('wraps and unstacks inside an existing slot without nesting rows or changing source order',()=>{
    create([{type:'pageRow',attrs:{id:'row',min_height:0,line_mode:'guide'},content:[{type:'pageSlot',attrs:{id:'slot',width:12},content:[art,paragraph('Title','caption')]}]}]);
    editor.commands.setTextSelection(3);expect(wrapPageImageText(editor)).toBe(true);
    expect(editor.state.doc.child(0).child(0).child(0).type.name).toBe('pageImageText');
    expect(editor.state.doc.textContent).toBe('Title');expect(unwrapPageImageText(editor)).toBe(true);
    expect(editor.state.doc.child(0).child(0).childCount).toBe(2);
    expect(editor.state.doc.child(0).child(0).child(0).attrs.pageBlockId).toBe('art');
    expect(editor.state.doc.child(0).child(0).child(1).attrs.pageBlockId).toBe('caption');
  });

});


describe('Explicit contextual layout controls', () => {
  function mountRow() {
    create(); wrapPageRow(editor);
    render(<><EditorContent editor={editor} /><PageComposerTools editor={editor} /></>);
    return screen.getByRole('button', { name: 'Row layout options' });
  }
  it('keeps normal caret placement quiet and details closed until explicitly requested', () => {
    const handle = mountRow();
    act(() => editor.commands.setTextSelection(4));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(handle);
    expect(screen.getByRole('dialog', { name: 'Row layout' })).toBeInTheDocument();
    expect(screen.getByText('Row settings').parentElement).not.toHaveAttribute('open');
    expect(handle).toHaveAttribute('aria-expanded', 'true');
  });
  it('preserves a native multiline selection and focuses the trigger without scrolling on Escape', () => {
    const handle = mountRow();
    act(() => editor.commands.setTextSelection({ from: 3, to: 14 }));
    const before = editor.state.selection.toJSON();
    fireEvent.click(handle);
    expect(editor.state.selection.toJSON()).toEqual(before);
    const focus = vi.spyOn(handle, 'focus');
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(editor.state.selection.toJSON()).toEqual(before);
  });
  it('dismisses outside without restoring trigger focus or stealing the next paragraph caret', () => {
    const handle = mountRow(); fireEvent.click(handle);
    const focus = vi.spyOn(handle, 'focus');
    fireEvent.pointerDown(editor.view.dom.lastElementChild!);
    act(() => { editor.commands.setTextSelection(editor.state.doc.content.size - 1); editor.commands.insertContent(' typed'); });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(focus).not.toHaveBeenCalled();
    expect(editor.state.doc.lastChild?.textContent).toBe('Third typed');
  });
  it('updates row presentation, preserves semantic content and supports one-step undo', () => {
    const handle = mountRow(); const before = editor.getText();
    fireEvent.click(handle); fireEvent.click(screen.getByText('Row settings'));
    fireEvent.change(screen.getByLabelText('Row lines'), { target: { value: 'clean' } });
    expect(editor.state.doc.firstChild?.attrs.line_mode).toBe('clean');
    expect(editor.getText()).toBe(before);
    fireEvent.click(screen.getByRole('button', { name: 'Undo', exact: true }));
    expect(editor.state.doc.firstChild?.attrs.line_mode).toBe('guide');
  });
  it('cancels an uncommitted height field on Escape', () => {
    const handle = mountRow(); fireEvent.click(handle); fireEvent.click(screen.getByText('Row settings'));
    act(() => screen.getByLabelText('Minimum row height').focus());
    fireEvent.change(screen.getByLabelText('Minimum row height'), { target: { value: '240' } });
    fireEvent.keyDown(screen.getByLabelText('Minimum row height'), { key: 'Escape' });
    expect(editor.state.doc.firstChild?.attrs.min_height).toBe(0);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
  it('dismisses when the selected row is removed or the editor becomes read-only', () => {
    const handle = mountRow(); fireEvent.click(handle);
    act(() => editor.setEditable(false));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(handle);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    act(() => { editor.setEditable(true); editor.commands.setContent({ type: 'doc', content: [paragraph('Replacement')] }); });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
  it('keeps image text settings explicit and preserves artwork identity on style changes', () => {
    const art = { type: 'paragraph', attrs: { pageBlockId: 'art' }, content: [{ type: 'mediaImage', attrs: { assetId: '11111111-1111-4111-8111-111111111111', alt: 'Known artwork' } }] };
    create([art, paragraph('Editable title')]); editor.commands.setTextSelection(1); wrapPageImageText(editor);
    render(<><EditorContent editor={editor} /><PageComposerTools editor={editor} /></>);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Image and text options' }));
    expect(screen.getByText('Image text settings').parentElement).not.toHaveAttribute('open');
    fireEvent.click(screen.getByText('Image text settings'));
    fireEvent.change(screen.getByLabelText('Text anchor'), { target: { value: 'bottom-right' } });
    expect(editor.state.doc.firstChild?.attrs.anchor).toBe('bottom-right');
    expect(editor.state.doc.firstChild?.firstChild?.firstChild?.attrs.assetId).toBe('11111111-1111-4111-8111-111111111111');
    fireEvent.click(screen.getByRole('button', { name: 'Unstack image and text' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(editor.state.doc.childCount).toBe(2);
    expect(editor.state.doc.lastChild?.textContent).toBe('Editable title');
  });
});


describe('Silent composer editability lifecycle', () => {
  const art: JSONContent = { type: 'paragraph', attrs: { pageBlockId: 'art' }, content: [{ type: 'mediaImage', attrs: { assetId: '11111111-1111-4111-8111-111111111111', alt: 'Artwork' } }] };
  for (const kind of ['pageRow', 'pageImageText'] as const) {
    it(`mounts ${kind} read-only, restores silently, closes its popup and hides controls without writes`, () => {
      const content: JSONContent = kind === 'pageRow'
        ? { type: 'pageRow', attrs: { id: 'row' }, content: [{ type: 'pageSlot', attrs: { id: 'slot', width: 12 }, content: [paragraph('First')] }] }
        : { type: 'pageImageText', attrs: { id: 'image-text' }, content: [art, paragraph('Title')] };
      create([content], false);
      render(<><EditorContent editor={editor} /><PageComposerTools editor={editor} /></>);
      const handle = editor.view.dom.querySelector('.page-layout-handle') as HTMLButtonElement;
      expect(handle.hidden).toBe(true);
      const before = editor.getJSON(), transaction = vi.fn(), update = vi.fn();
      editor.on('transaction', transaction); editor.on('update', update);
      act(() => editor.setEditable(true, false));
      expect(handle.hidden).toBe(false);
      fireEvent.click(handle);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      transaction.mockClear();
      act(() => editor.setEditable(false, false));
      expect(handle.hidden).toBe(true);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(handle).toHaveAttribute('aria-expanded', 'false');
      expect(editor.view.dom.querySelector('[data-layout-selected]')).toBeNull();
      for (const control of editor.view.dom.querySelectorAll<HTMLButtonElement>('[role=separator]')) {
        expect(control.hidden).toBe(true); expect(control.disabled).toBe(true);
      }
      act(() => editor.setEditable(true, false));
      expect(handle.hidden).toBe(false);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(transaction).not.toHaveBeenCalled(); expect(update).not.toHaveBeenCalled();
      expect(editor.getJSON()).toEqual(before);
    });
  }
  it('cancels an active divider preview across silent read-only and editable transitions', () => {
    create(); wrapPageRow(editor);
    const divider = editor.view.dom.querySelector('[role=separator]') as HTMLButtonElement;
    const slots = editor.view.dom.querySelector('.page-composer-row__slots') as HTMLElement;
    vi.spyOn(slots, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 120 } as DOMRect);
    divider.setPointerCapture = vi.fn();
    const pointer = (type: string, x: number) => {
      const event = new Event(type, { bubbles: true });
      Object.defineProperties(event, { clientX: { value: x }, pointerId: { value: 1 }, button: { value: 0 } });
      divider.dispatchEvent(event);
    };
    const before = editor.getJSON(), transaction = vi.fn(); editor.on('transaction', transaction);
    pointer('pointerdown', 60); pointer('pointermove', 80);
    expect(divider.getAttribute('aria-valuenow')).toBe('8');
    editor.setEditable(false, false);
    expect(divider.hidden).toBe(true); expect(divider.getAttribute('aria-valuenow')).toBe('6');
    editor.setEditable(true, false);
    pointer('pointermove', 90); pointer('pointerup', 90);
    expect(divider.hidden).toBe(false); expect(divider.getAttribute('aria-valuenow')).toBe('6');
    expect(transaction).not.toHaveBeenCalled(); expect(editor.getJSON()).toEqual(before);
  });
});


describe('Build exact image occurrence moves', () => {
  const assetId = '11111111-1111-4111-8111-111111111111';
  function art(id: string, alt: string): JSONContent {
    return {type:'paragraph',attrs:{pageBlockId:id},content:[{type:'mediaImage',attrs:{assetId,alt,width:80,collapsed:false}}]};
  }
  function row(id: string, left: JSONContent[], right: JSONContent[] = []): JSONContent {
    return {type:'pageRow',attrs:{id,min_height:16,line_mode:'border'},content:[
      {type:'pageSlot',attrs:{id:`${id}-left`,width:7},content:left},
      {type:'pageSlot',attrs:{id:`${id}-right`,width:5},content:right},
    ]};
  }
  const scope = () => ({editor,worldId:'world',documentId:'page',revision:1,draftGeneration:0,canEdit:true});

  it('moves one of two occurrences of the same asset, preserving reading order and one Undo unit', () => {
    create([
      row('entrance',[paragraph('At the entrance'),art('entrance-map','Marsh map beside the entrance')]),
      row('notes',[paragraph('Measurements'),art('notes-map','Marsh map beside the measurements')]),
    ]);
    const before=editor.getJSON();
    const capture=captureAgentImageMoves(scope());
    expect(capture.selected).toBeNull();
    expect(capture.offers.map(offer=>[offer.alias,offer.rowContext,offer.destination])).toEqual([
      ['image1','At the entrance','empty_right'],['image2','Measurements','empty_right'],
    ]);
    expect(JSON.stringify(capture)).not.toContain(assetId);
    const holdObserved=vi.fn();
    editor.on('update',()=>holdObserved(requiresManualSave(editor)));
    applyAgentImageMove(scope(),capture,'image2');
    const after=editor.getJSON();
    expect(holdObserved).toHaveBeenCalledExactlyOnceWith(true);
    expect(after.content?.[0]).toEqual(before.content?.[0]);
    expect(after.content?.[1].content?.[1].content?.[0]).toEqual(before.content?.[1].content?.[0].content?.[1]);
    expect(flattenPresentation(after)).toEqual(flattenPresentation(before));
    expect(editor.commands.undo()).toBe(true);
    expect(editor.getJSON()).toEqual(before);
    expect(()=>applyAgentImageMove(scope(),capture,'image2')).toThrow('not offered');
    expect(editor.commands.redo()).toBe(true);
    expect(editor.getJSON()).toEqual(after);
  });

  it('keeps a deliberately selected image distinct after selection changes', () => {
    create([row('first',[art('a','Same asset')]),row('second',[art('b','Same asset')])]);
    editor.view.dispatch(editor.state.tr.setSelection(NodeSelection.create(editor.state.doc,3)));
    const capture=captureAgentImageMoves(scope());
    expect(capture.selected).toBe('image1');
    const secondPosition=editor.state.doc.child(0).nodeSize+3;
    editor.view.dispatch(editor.state.tr.setSelection(NodeSelection.create(editor.state.doc,secondPosition)));
    applyAgentImageMove(scope(),capture,capture.selected!);
    expect(editor.state.doc.child(0).child(1).child(0).attrs.pageBlockId).toBe('a');
    expect(editor.state.doc.child(1).child(0).child(0).attrs.pageBlockId).toBe('b');
  });

  it('refuses occupied, order-changing, foreign and stale moves without beginning the hold', () => {
    create([
      row('occupied',[art('a','A')],[paragraph('Occupied')]),
      row('reorder',[art('b','B'),paragraph('Follows B')]),
      row('legal',[art('c','C')]),
    ]);
    const capture=captureAgentImageMoves(scope());
    const before=editor.getJSON();
    expect(capture.offers.map(offer=>offer.destination)).toEqual(['occupied','changes_reading_order','empty_right']);
    for(const alias of ['image1','image2','image99']) expect(()=>applyAgentImageMove(scope(),capture,alias)).toThrow();
    expect(()=>applyAgentImageMove({...scope(),worldId:'foreign'},capture,'image3')).toThrow();
    expect(()=>applyAgentImageMove({...scope(),canEdit:false},capture,'image3')).toThrow();
    expect(editor.getJSON()).toEqual(before);
    expect(requiresManualSave(editor)).toBe(false);
    editor.commands.insertContent('edit');
    const edited=editor.getJSON();
    expect(()=>applyAgentImageMove(scope(),capture,'image3')).toThrow('captured Page changed');
    expect(editor.getJSON()).toEqual(edited);
    expect(requiresManualSave(editor)).toBe(false);
  });
});
