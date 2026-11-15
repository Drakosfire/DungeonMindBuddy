import { PAGE_IMAGE_TEXT_EXTENSIONS, PageImageTextTools } from './PageImageText';
import { Extension, Node, mergeAttributes, type Editor } from '@tiptap/core';
import { Fragment, type Node as PMNode } from '@tiptap/pm/model';
import { Plugin, Selection } from '@tiptap/pm/state';
import { closeHistory } from '@tiptap/pm/history';
import { useEffect, useState } from 'react';
import './PageRow.css';

const BLOCKS = ['paragraph', 'heading', 'blockquote', 'bulletList', 'orderedList', 'table', 'callout', 'horizontalRule'];
const SLOT_BLOCKS = [...BLOCKS, 'pageImageText'];
const newId = () => `page-${crypto.randomUUID()}`;
const clampWidth = (width: number, total = 12) => Math.max(2, Math.min(total - 2, Math.round(width)));

function rowAtSelection(editor: Editor) {
  const { $from } = editor.state.selection;
  for (let depth = $from.depth; depth > 0; depth--) {
    if ($from.node(depth).type.name === 'pageRow') return { row: $from.node(depth), pos: $from.before(depth), depth };
  }
  const selected = editor.state.doc.nodeAt(editor.state.selection.from);
  return selected?.type.name === 'pageRow' ? { row: selected, pos: editor.state.selection.from, depth: 0 } : null;
}

function replaceRow(editor: Editor, pos: number, row: PMNode, replacement: Fragment | PMNode, selectionOffset = 1) {
  const tr = editor.state.tr.replaceWith(pos, pos + row.nodeSize, replacement);
  tr.setSelection(Selection.near(tr.doc.resolve(Math.min(pos + selectionOffset, tr.doc.content.size))));
  editor.view.dispatch(closeHistory(tr).scrollIntoView());
  return true;
}

/** Wrap only adjacent top-level blocks. Never move a nested table cell or callout paragraph. */
export function wrapPageRow(editor: Editor, dryRun = false, columns: 1 | 2 | 3 = 2): boolean {
  if (!editor.isEditable || rowAtSelection(editor)) return false;
  const { $from } = editor.state.selection;
  const index = $from.index(0);
  if (![1, 2, 3].includes(columns)) return false;
  const blocks = Array.from({ length: columns }, (_, i) => editor.state.doc.maybeChild(index + i));
  if (blocks.some(block => !block || !SLOT_BLOCKS.includes(block.type.name))) return false;
  if (dryRun) return true;
  const slot = editor.schema.nodes.pageSlot;
  const rowType = editor.schema.nodes.pageRow;
  if (!slot || !rowType) return false;
  const row = rowType.create({ id: newId(), min_height: 0, line_mode: 'guide' },
    blocks.map(block => slot.create({ id: newId(), width: 12 / columns }, block!)));
  let pos = 0;
  for (let i = 0; i < index; i++) pos += editor.state.doc.child(i).nodeSize;
  const tr = editor.state.tr.replaceWith(pos, pos + blocks.reduce((sum, block) => sum + block!.nodeSize, 0), row);
  tr.setSelection(Selection.near(tr.doc.resolve(pos + 3)));
  editor.view.dispatch(closeHistory(tr).scrollIntoView());
  return true;
}

export function unwrapPageRow(editor: Editor): boolean {
  const found = rowAtSelection(editor);
  if (!found || !editor.isEditable) return false;
  const blocks: PMNode[] = [];
  found.row.forEach(slot => slot.forEach(block => blocks.push(block)));
  return replaceRow(editor, found.pos, found.row, Fragment.fromArray(blocks));
}

/** Explicitly exchange adjacent blocks in reading order, retaining nonempty slots. */
export function movePageBlock(editor: Editor, direction: -1 | 1, dryRun = false): boolean {
  const found = rowAtSelection(editor);
  if (!found || !editor.isEditable) return false;
  const { $from } = editor.state.selection;
  if ($from.depth < found.depth + 2) return false;
  const slotIndex = $from.index(found.depth);
  const blockIndex = $from.index(found.depth + 1);
  const blocks: PMNode[] = [];
  const counts: number[] = [];
  found.row.forEach(slot => { counts.push(slot.childCount); slot.forEach(block => blocks.push(block)); });
  const index = counts.slice(0, slotIndex).reduce((a, b) => a + b, 0) + blockIndex;
  let target = index + direction;
  // A deliberately empty adjacent slot is a valid placement target even when
  // there is no next/previous semantic block to exchange with.
  const emptyTarget = slotIndex + direction;
  const intoEmpty = emptyTarget >= 0 && emptyTarget < counts.length && counts[emptyTarget] === 0
    && (direction === 1 ? blockIndex === counts[slotIndex] - 1 : blockIndex === 0);
  if (!intoEmpty && (target < 0 || target >= blocks.length)) return false;
  if (dryRun) return true;
  if (intoEmpty) {
    counts[slotIndex] -= 1; counts[emptyTarget] += 1; target = index;
  } else {
    [blocks[index], blocks[target]] = [blocks[target], blocks[index]];
  }
  let cursor = 0;
  const slots: PMNode[] = [];
  let selectionOffset = 2;
  found.row.forEach((slot, _offset, i) => {
    const content = blocks.slice(cursor, cursor + counts[i]);
    if (target >= cursor && target < cursor + counts[i]) {
      selectionOffset = 2 + slots.reduce((sum, item) => sum + item.nodeSize, 0)
        + content.slice(0, target - cursor).reduce((sum, item) => sum + item.nodeSize, 0) + 1;
    }
    slots.push(slot.copy(Fragment.fromArray(content))); cursor += counts[i];
  });
  return replaceRow(editor, found.pos, found.row, found.row.copy(Fragment.fromArray(slots)), selectionOffset);
}

function validRow(row: PMNode | null | undefined): row is PMNode {
  if (!row || row.type.name !== 'pageRow' || row.childCount < 1 || row.childCount > 3) return false;
  const widths: number[] = []; row.forEach(slot => widths.push(slot.attrs.width));
  return widths.every(width => Number.isInteger(width) && width >= 2 && width <= 12)
    && widths.reduce((a, b) => a + b, 0) === 12
    && Number.isInteger(row.attrs.min_height) && row.attrs.min_height >= 0 && row.attrs.min_height <= 640 && row.attrs.min_height % 8 === 0
    && ['guide', 'border', 'clean'].includes(row.attrs.line_mode);
}

export function resizePageRow(editor: Editor, pos: number, width: number, dividerIndex = 0): boolean {
  const row = editor.state.doc.nodeAt(pos);
  if (!editor.isEditable || !validRow(row) || !Number.isFinite(width)
    || !Number.isInteger(dividerIndex) || dividerIndex < 0 || dividerIndex >= row.childCount - 1) return false;
  const total = row.child(dividerIndex).attrs.width + row.child(dividerIndex + 1).attrs.width;
  const left = clampWidth(width, total);
  if (row.child(dividerIndex).attrs.width === left) return true;
  let offset = pos + 1;
  for (let i = 0; i < dividerIndex; i++) offset += row.child(i).nodeSize;
  const tr = editor.state.tr;
  tr.setNodeMarkup(offset, undefined, { ...row.child(dividerIndex).attrs, width: left });
  tr.setNodeMarkup(offset + row.child(dividerIndex).nodeSize, undefined, { ...row.child(dividerIndex + 1).attrs, width: total - left });
  editor.view.dispatch(closeHistory(tr));
  return true;
}

export function updatePageRowPresentation(editor: Editor, pos: number, attrs: { min_height?: number; line_mode?: 'guide' | 'border' | 'clean' }): boolean {
  const row = editor.state.doc.nodeAt(pos);
  if (!editor.isEditable || !validRow(row) || Object.keys(attrs).some(key => key !== 'min_height' && key !== 'line_mode')) return false;
  const next = { ...row.attrs, ...attrs };
  if (typeof next.min_height !== 'number' || !Number.isInteger(next.min_height) || next.min_height < 0 || next.min_height > 640 || next.min_height % 8 !== 0
    || typeof next.line_mode !== 'string' || !['guide', 'border', 'clean'].includes(next.line_mode)) return false;
  if (next.min_height === row.attrs.min_height && next.line_mode === row.attrs.line_mode) return true;
  editor.view.dispatch(closeHistory(editor.state.tr.setNodeMarkup(pos, undefined, next)));
  return true;
}

export const PageBlockIdentity = Extension.create({
  name: 'pageBlockIdentity',
  addGlobalAttributes() { return [{ types: BLOCKS, attributes: { pageBlockId: { default: null, rendered: false } } }]; },
  addProseMirrorPlugins() {
    return [new Plugin({
      appendTransaction(transactions, _oldState, state) {
        // Never change untouched hydration. Stamp only after a real document
        // transaction and only source-level blocks, not paragraphs inside tables.
        if (!transactions.some(transaction => transaction.docChanged)) return null;
        const seen = new Set<string>();
        const tr = state.tr;
        const stamp = (block: PMNode, pos: number) => {
          if (block.type.name === 'pageImageText') { block.forEach((child, offset) => stamp(child, pos + 1 + offset)); return; }
          if (!BLOCKS.includes(block.type.name)) return;
          let id = block.attrs.pageBlockId;
          if (typeof id !== 'string' || !id || seen.has(id)) {
            id = newId(); tr.setNodeMarkup(pos, undefined, { ...block.attrs, pageBlockId: id });
          }
          seen.add(id);
        };
        state.doc.forEach((block, pos) => {
          if (block.type.name !== 'pageRow') { stamp(block, pos); return; }
          block.forEach((slot, slotOffset) => slot.forEach((child, childOffset) => stamp(child, pos + 2 + slotOffset + childOffset)));
        });
        return tr.docChanged ? tr : null;
      },
    })];
  },
});

export const PageSlot = Node.create({
  name: 'pageSlot', content: `(${SLOT_BLOCKS.join('|')})*`, defining: true, isolating: true,
  addAttributes() { return { id: { default: null }, width: { default: 6 } }; },
  parseHTML() { return [{ tag: 'div[data-page-slot]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes(HTMLAttributes, { 'data-page-slot': '', class: 'page-composer-slot' }), 0]; },
});

export const PageRow = Node.create({
  name: 'pageRow', group: 'block', content: 'pageSlot{1,3}', defining: true, isolating: true,
  addAttributes() { return { id: { default: null }, min_height: { default: 0 }, line_mode: { default: 'guide' } }; },
  parseHTML() { return [{ tag: 'div[data-page-row]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes(HTMLAttributes, { 'data-page-row': '', class: 'page-composer-row' }), 0]; },
  addNodeView() {
    return ({ node: initial, editor, getPos }) => {
      let node = initial;
      const dom = document.createElement('div'); dom.className = 'page-composer-row'; dom.dataset.pageRow = '';
      const contentDOM = document.createElement('div'); contentDOM.className = 'page-composer-row__slots';
      dom.append(contentDOM);
      const controls: HTMLButtonElement[] = [];
      let drag: { index: number; width: number; rect: DOMRect; height?: number; startY?: number; baseHeight?: number } | null = null;
      const widths = () => { const values: number[] = []; node.forEach(slot => values.push(Number(slot.attrs.width))); return values; };
      const paint = (values = widths(), height = node.attrs.min_height) => {
        contentDOM.style.gridTemplateColumns = values.map(width => `minmax(0, ${width}fr)`).join(' ');
        contentDOM.style.setProperty('--page-min-height', `${height}px`);
        dom.dataset.lineMode = node.attrs.line_mode;
        let left = 0;
        controls.forEach((control, index) => {
          control.disabled = !editor.isEditable || !validRow(node);
          if (index < values.length - 1) {
            left += values[index]; control.style.left = `${left / 12 * 100}%`;
            control.setAttribute('aria-valuenow', String(values[index]));
            control.setAttribute('aria-valuemax', String(values[index] + values[index + 1] - 2));
            control.setAttribute('aria-valuetext', `${values[index]} of 12 columns`);
          } else {
            control.setAttribute('aria-valuenow', String(height));
            control.setAttribute('aria-valuetext', height ? `Minimum ${height} pixels` : 'Automatic height');
          }
        });
      };
      const finish = (commit: boolean) => {
        const active = drag; drag = null;
        if (commit && active && !editor.isDestroyed) {
          const pos = getPos();
          if (typeof pos === 'number') {
            if (active.height !== undefined) updatePageRowPresentation(editor, pos, { min_height: active.height });
            else resizePageRow(editor, pos, active.width, active.index);
          }
        }
        paint();
      };
      for (let index = 0; index < node.childCount; index++) {
        const horizontal = index === node.childCount - 1;
        const divider = document.createElement('button'); divider.type = 'button';
        divider.className = horizontal ? 'page-composer-row__height' : 'page-composer-row__divider';
        divider.contentEditable = 'false'; divider.setAttribute('role', 'separator');
        divider.setAttribute('aria-orientation', horizontal ? 'horizontal' : 'vertical');
        divider.setAttribute('aria-label', horizontal ? 'Resize minimum row height' : node.childCount === 2 ? 'Resize row columns' : `Resize columns ${index + 1} and ${index + 2}`);
        divider.setAttribute('aria-valuemin', horizontal ? '0' : '2'); divider.setAttribute('aria-valuemax', horizontal ? '640' : '10');
        divider.title = horizontal ? 'Drag row height; arrow keys adjust by 8 pixels. Home resets to Auto.' : 'Drag to resize columns. Arrow keys resize; Home and End set limits.';
        controls.push(divider); dom.append(divider);
        divider.addEventListener('pointerdown', event => {
          if (!editor.isEditable || !validRow(node) || event.button !== 0) return;
          event.preventDefault();
          drag = { index, width: Number(node.child(Math.min(index, node.childCount - 1)).attrs.width), rect: contentDOM.getBoundingClientRect(),
            ...(horizontal ? { height: node.attrs.min_height, startY: event.clientY, baseHeight: Math.max(node.attrs.min_height, contentDOM.getBoundingClientRect().height) } : {}) };
          if (drag.rect.width <= 0) { drag = null; return; }
          divider.setPointerCapture(event.pointerId);
        });
        divider.addEventListener('pointermove', event => {
          if (!drag) return;
          if (horizontal) {
            drag.height = Math.max(0, Math.min(640, Math.round(((drag.baseHeight ?? node.attrs.min_height) + event.clientY - (drag.startY ?? 0)) / 8) * 8));
            paint(widths(), drag.height);
          } else {
            const values = widths(); const prefix = values.slice(0, index).reduce((a, b) => a + b, 0); const total = values[index] + values[index + 1];
            drag.width = clampWidth((event.clientX - drag.rect.left) / drag.rect.width * 12 - prefix, total);
            values[index] = drag.width; values[index + 1] = total - drag.width; paint(values);
          }
        });
        divider.addEventListener('pointerup', () => finish(true));
        divider.addEventListener('pointercancel', () => finish(false));
        divider.addEventListener('lostpointercapture', () => finish(false));
        divider.onkeydown = event => {
          const width = Number(node.child(Math.min(index, node.childCount - 1)).attrs.width);
          const next = horizontal
            ? event.key === 'ArrowUp' ? node.attrs.min_height - 8 : event.key === 'ArrowDown' ? node.attrs.min_height + 8 : event.key === 'Home' ? 0 : event.key === 'End' ? 640 : null
            : event.key === 'ArrowLeft' ? width - 1 : event.key === 'ArrowRight' ? width + 1 : event.key === 'Home' ? 2 : event.key === 'End' ? width + node.child(index + 1).attrs.width - 2 : null;
          if (next === null) return;
          event.preventDefault(); event.stopPropagation();
          const pos = getPos(); if (typeof pos === 'number') {
            if (horizontal) updatePageRowPresentation(editor, pos, { min_height: Math.max(0, Math.min(640, next)) });
            else resizePageRow(editor, pos, next, index);
          }
        };
      }
      paint();
      return { dom, contentDOM,
        update(next) { if (next.type !== node.type || next.childCount !== node.childCount) return false; node = next; if (!drag) paint(); return true; },
        stopEvent(event) { return controls.some(control => control.contains(event.target as globalThis.Node)); },
        ignoreMutation(mutation) { return mutation.type !== 'selection' && (mutation.target === dom || (mutation.target === contentDOM && mutation.type === 'attributes') || controls.some(control => control.contains(mutation.target))); },
        destroy() { drag = null; },
      };
    };
  },
});

export const PAGE_COMPOSER_EXTENSIONS = [PageBlockIdentity, PageSlot, PageRow, ...PAGE_IMAGE_TEXT_EXTENSIONS];

export function PageComposerTools({ editor, disabledReason }: { editor: Editor | null; disabledReason?: string | null }) {
  const [, refresh] = useState(0);
  useEffect(() => {
    if (!editor) return;
    const update = () => refresh(value => value + 1);
    editor.on('transaction', update); editor.on('selectionUpdate', update);
    return () => { editor.off('transaction', update); editor.off('selectionUpdate', update); };
  }, [editor]);
  const row = editor ? rowAtSelection(editor) : null;
  const [heightDraft, setHeightDraft] = useState('0');
  const rowHeight = row?.row.attrs.min_height ?? 0;
  const rowId = row?.row.attrs.id ?? null;
  useEffect(() => { setHeightDraft(String(rowHeight)); }, [rowHeight, rowId]);
  const commitHeight = () => {
    if (!editor || !row || heightDraft.trim() === '' || !updatePageRowPresentation(editor, row.pos, { min_height: Number(heightDraft) })) setHeightDraft(String(rowHeight));
  };
  const disabled = !editor?.isEditable || !!disabledReason;
  return <div className="page-composer-tools" role="group" aria-label="Page layout">
    <button type="button" disabled={disabled || !editor || !wrapPageRow(editor, true, 1)} onClick={() => editor && wrapPageRow(editor, false, 1)}>One-column row</button>
    <button type="button" disabled={disabled || !editor || !wrapPageRow(editor, true)} title={disabledReason ?? 'Place this block and the next block side by side'} onClick={() => editor && wrapPageRow(editor)}>Two-column row</button>
    <button type="button" disabled={disabled || !editor || !wrapPageRow(editor, true, 3)} onClick={() => editor && wrapPageRow(editor, false, 3)}>Three-column row</button>
    <button type="button" disabled={!editor?.isEditable || !row} onClick={() => editor && unwrapPageRow(editor)}>Unwrap row</button>
    <button type="button" disabled={!editor?.isEditable || !editor || !movePageBlock(editor, -1, true)} onClick={() => editor && movePageBlock(editor, -1)}>Move block earlier</button>
    <button type="button" disabled={!editor?.isEditable || !editor || !movePageBlock(editor, 1, true)} onClick={() => editor && movePageBlock(editor, 1)}>Move block later</button>
    <button type="button" disabled={!editor?.isEditable || !editor.can().undo()} onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
    <button type="button" disabled={!editor?.isEditable || !editor.can().redo()} onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
    <label>Minimum row height <input type="number" min={0} max={640} step={8} value={heightDraft} disabled={!editor?.isEditable || !row}
      onChange={event => setHeightDraft(event.target.value)} onBlur={commitHeight}
      onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); commitHeight(); } if (event.key === 'Escape') { setHeightDraft(String(rowHeight)); } }} /></label>
    <button type="button" disabled={!editor?.isEditable || !row} onClick={() => { if (editor && row) updatePageRowPresentation(editor, row.pos, { min_height: 0 }); }}>Auto height</button>
    <label>Row lines <select value={row?.row.attrs.line_mode ?? 'guide'} disabled={!editor?.isEditable || !row}
      onChange={event => { if (editor && row) updatePageRowPresentation(editor, row.pos, { line_mode: event.target.value as 'guide' | 'border' | 'clean' }); }}>
      <option value="guide">Dotted guide</option><option value="border">Bordered</option><option value="clean">Clean</option>
    </select></label>
    <PageImageTextTools editor={editor} disabledReason={disabledReason} />
    {disabledReason ? <span role="status">{disabledReason}</span> : null}
  </div>;
}
