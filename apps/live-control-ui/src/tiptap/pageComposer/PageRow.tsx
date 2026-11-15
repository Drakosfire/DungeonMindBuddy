import { Extension, Node, mergeAttributes, type Editor } from '@tiptap/core';
import { Fragment, type Node as PMNode } from '@tiptap/pm/model';
import { Plugin, Selection } from '@tiptap/pm/state';
import { closeHistory } from '@tiptap/pm/history';
import { useEffect, useState } from 'react';
import './PageRow.css';

const BLOCKS = ['paragraph', 'heading', 'blockquote', 'bulletList', 'orderedList', 'table', 'callout', 'horizontalRule'];
const newId = () => `page-${crypto.randomUUID()}`;
const clampWidth = (width: number) => Math.max(2, Math.min(10, Math.round(width)));

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
export function wrapPageRow(editor: Editor, dryRun = false): boolean {
  if (!editor.isEditable || rowAtSelection(editor)) return false;
  const { $from } = editor.state.selection;
  const index = $from.index(0);
  const first = editor.state.doc.maybeChild(index);
  const second = editor.state.doc.maybeChild(index + 1);
  if (!first || !second || !BLOCKS.includes(first.type.name) || !BLOCKS.includes(second.type.name)) return false;
  if (dryRun) return true;
  const slot = editor.schema.nodes.pageSlot;
  const rowType = editor.schema.nodes.pageRow;
  if (!slot || !rowType) return false;
  const row = rowType.create({ id: newId(), min_height: 0, line_mode: 'guide' }, [
    slot.create({ id: newId(), width: 6 }, first), slot.create({ id: newId(), width: 6 }, second),
  ]);
  let pos = 0;
  for (let i = 0; i < index; i++) pos += editor.state.doc.child(i).nodeSize;
  const tr = editor.state.tr.replaceWith(pos, pos + first.nodeSize + second.nodeSize, row);
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

export function resizePageRow(editor: Editor, pos: number, width: number): boolean {
  const row = editor.state.doc.nodeAt(pos);
  if (!editor.isEditable || row?.type.name !== 'pageRow' || row.childCount !== 2) return false;
  const left = clampWidth(width);
  if (row.child(0).attrs.width === left) return true;
  const tr = editor.state.tr;
  tr.setNodeMarkup(pos + 1, undefined, { ...row.child(0).attrs, width: left });
  tr.setNodeMarkup(pos + 1 + row.child(0).nodeSize, undefined, { ...row.child(1).attrs, width: 12 - left });
  editor.view.dispatch(closeHistory(tr));
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
  name: 'pageSlot', content: `(${BLOCKS.join('|')})*`, defining: true, isolating: true,
  addAttributes() { return { id: { default: null }, width: { default: 6 } }; },
  parseHTML() { return [{ tag: 'div[data-page-slot]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes(HTMLAttributes, { 'data-page-slot': '', class: 'page-composer-slot' }), 0]; },
});

export const PageRow = Node.create({
  name: 'pageRow', group: 'block', content: 'pageSlot pageSlot', defining: true, isolating: true,
  addAttributes() { return { id: { default: null }, min_height: { default: 0 }, line_mode: { default: 'guide' } }; },
  parseHTML() { return [{ tag: 'div[data-page-row]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes(HTMLAttributes, { 'data-page-row': '', class: 'page-composer-row' }), 0]; },
  addNodeView() {
    return ({ node: initial, editor, getPos }) => {
      let node = initial;
      const dom = document.createElement('div'); dom.className = 'page-composer-row'; dom.dataset.pageRow = '';
      const contentDOM = document.createElement('div'); contentDOM.className = 'page-composer-row__slots';
      const divider = document.createElement('button'); divider.type = 'button'; divider.className = 'page-composer-row__divider';
      divider.contentEditable = 'false'; divider.setAttribute('role', 'separator'); divider.setAttribute('aria-orientation', 'vertical');
      divider.setAttribute('aria-label', 'Resize row columns'); divider.setAttribute('aria-valuemin', '2'); divider.setAttribute('aria-valuemax', '10');
      divider.title = 'Drag to resize columns. Arrow keys resize; Home and End set limits.';
      dom.append(contentDOM, divider);
      let drag: { width: number; rect: DOMRect } | null = null;
      const paint = (width: number) => {
        dom.style.setProperty('--page-left', String(width)); dom.style.setProperty('--page-right', String(12 - width));
        divider.setAttribute('aria-valuenow', String(width)); divider.setAttribute('aria-valuetext', `${width} of 12 columns`);
      };
      const refresh = () => { paint(Number(node.child(0).attrs.width)); divider.disabled = !editor.isEditable; };
      refresh();
      const finish = (commit: boolean) => {
        const active = drag; drag = null;
        if (commit && active && !editor.isDestroyed) {
          const pos = getPos(); if (typeof pos === 'number') resizePageRow(editor, pos, active.width);
        }
        refresh();
      };
      divider.addEventListener('pointerdown', event => {
        if (!editor.isEditable || event.button !== 0) return;
        event.preventDefault();
        drag = { width: Number(node.child(0).attrs.width), rect: contentDOM.getBoundingClientRect() };
        if (drag.rect.width <= 0) { drag = null; return; }
        divider.setPointerCapture(event.pointerId);
      });
      divider.addEventListener('pointermove', event => {
        if (!drag) return;
        drag.width = clampWidth((event.clientX - drag.rect.left) / drag.rect.width * 12); paint(drag.width);
      });
      divider.addEventListener('pointerup', () => finish(true));
      divider.addEventListener('pointercancel', () => finish(false));
      divider.addEventListener('lostpointercapture', () => finish(false));
      divider.onkeydown = event => {
        const width = Number(node.child(0).attrs.width);
        const next = event.key === 'ArrowLeft' ? width - 1 : event.key === 'ArrowRight' ? width + 1
          : event.key === 'Home' ? 2 : event.key === 'End' ? 10 : null;
        if (next === null) return;
        event.preventDefault(); event.stopPropagation();
        const pos = getPos(); if (typeof pos === 'number') resizePageRow(editor, pos, next);
      };
      return { dom, contentDOM,
        update(next) { if (next.type !== node.type || next.childCount !== 2) return false; node = next; if (!drag) refresh(); return true; },
        stopEvent(event) { return divider.contains(event.target as globalThis.Node); },
        ignoreMutation(mutation) { return mutation.type !== 'selection' && (mutation.target === dom || divider.contains(mutation.target)); },
        destroy() { drag = null; },
      };
    };
  },
});

export const PAGE_COMPOSER_EXTENSIONS = [PageBlockIdentity, PageSlot, PageRow];

export function PageComposerTools({ editor, disabledReason }: { editor: Editor | null; disabledReason?: string | null }) {
  const [, refresh] = useState(0);
  useEffect(() => {
    if (!editor) return;
    const update = () => refresh(value => value + 1);
    editor.on('transaction', update); editor.on('selectionUpdate', update);
    return () => { editor.off('transaction', update); editor.off('selectionUpdate', update); };
  }, [editor]);
  const row = editor ? rowAtSelection(editor) : null;
  const disabled = !editor?.isEditable || !!disabledReason;
  return <div className="page-composer-tools" role="group" aria-label="Page layout">
    <button type="button" disabled={disabled || !editor || !wrapPageRow(editor, true)} title={disabledReason ?? 'Place this block and the next block side by side'} onClick={() => editor && wrapPageRow(editor)}>Two-column row</button>
    <button type="button" disabled={!editor?.isEditable || !row} onClick={() => editor && unwrapPageRow(editor)}>Unwrap row</button>
    <button type="button" disabled={!editor?.isEditable || !editor || !movePageBlock(editor, -1, true)} onClick={() => editor && movePageBlock(editor, -1)}>Move block earlier</button>
    <button type="button" disabled={!editor?.isEditable || !editor || !movePageBlock(editor, 1, true)} onClick={() => editor && movePageBlock(editor, 1)}>Move block later</button>
    <button type="button" disabled={!editor?.isEditable || !editor.can().undo()} onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
    <button type="button" disabled={!editor?.isEditable || !editor.can().redo()} onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
    {disabledReason ? <span role="status">{disabledReason}</span> : null}
  </div>;
}
