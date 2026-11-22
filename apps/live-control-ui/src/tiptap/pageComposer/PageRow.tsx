import { PAGE_IMAGE_TEXT_EXTENSIONS, PageImageTextTools, stackAtSelection, wrapPageImageText } from './PageImageText';
import { Extension, Node, mergeAttributes, type Editor } from '@tiptap/core';
import { Fragment, type Node as PMNode } from '@tiptap/pm/model';
import { NodeSelection, Plugin, Selection, type Transaction } from '@tiptap/pm/state';
import { closeHistory, isHistoryTransaction } from '@tiptap/pm/history';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { layoutHandle, layoutEditabilityPlugin, LAYOUT_EDITABILITY_EVENT, LAYOUT_CONTROLS_EVENT, type LayoutRequest } from './contextualLayout';
import { requireManualSave } from '../../workspaceDocument/draftSavePolicy';
import './PageRow.css';

const BLOCKS = ['paragraph', 'heading', 'blockquote', 'bulletList', 'orderedList', 'table', 'callout', 'horizontalRule'];
const SLOT_BLOCKS = [...BLOCKS, 'pageImageText'];
const newId = () => `page-${crypto.randomUUID()}`;
const PLAIN_REVIEW_INSERTION = 'dmbPlainReviewInsertion';

export function preservePlainReviewBlockIdentities(transaction: Transaction): Transaction {
  return transaction.setMeta(PLAIN_REVIEW_INSERTION, true);
}
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
  if (editor.isDestroyed || !editor.isEditable || rowAtSelection(editor)) return false;
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
  if (editor.isDestroyed || !editor.isEditable) return false;
  const found = rowAtSelection(editor);
  if (editor.isDestroyed || !found || !editor.isEditable) return false;
  const blocks: PMNode[] = [];
  found.row.forEach(slot => slot.forEach(block => blocks.push(block)));
  return replaceRow(editor, found.pos, found.row, Fragment.fromArray(blocks));
}

/** Explicitly exchange adjacent blocks in reading order, retaining nonempty slots. */
export function movePageBlock(editor: Editor, direction: -1 | 1, dryRun = false): boolean {
  if (editor.isDestroyed || !editor.isEditable) return false;
  const found = rowAtSelection(editor);
  if (editor.isDestroyed || !found || !editor.isEditable) return false;
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

export interface AgentImageMoveScope {
  editor: Editor;
  worldId: string;
  documentId: string;
  revision: number;
  draftGeneration: number;
  canEdit: boolean;
}

export interface AgentImageMoveOffer {
  alias: string;
  alt: string;
  rowContext: string;
  sourceColumn: number;
  destination: "empty_right" | "occupied" | "unavailable" | "changes_reading_order";
}

export interface CapturedAgentImageMoves {
  offers: readonly Readonly<AgentImageMoveOffer>[];
  selected: string | null;
}

interface BoundAgentImageMove {
  source: PMNode;
  position: number;
  destination: number | null;
  location: AgentImageMoveLocation;
}

export interface AgentImageMoveLocation {
  row_id: string;
  source_slot_id: string;
  destination_slot_id: string | null;
  image_block_id: string;
}

const issuedImageMoves = new WeakMap<CapturedAgentImageMoves, {
  scope: AgentImageMoveScope;
  document: PMNode;
  targets: ReadonlyMap<string, BoundAgentImageMove>;
}>();

/** Enumerate actual standalone occurrences. No editor positions or asset IDs are public offers. */
export function captureAgentImageMoves(scope: AgentImageMoveScope): CapturedAgentImageMoves {
  const {editor} = scope;
  if (!scope.canEdit || editor.isDestroyed || !editor.isEditable || !scope.worldId || !scope.documentId
    || !Number.isInteger(scope.revision) || scope.revision < 1
    || !Number.isInteger(scope.draftGeneration) || scope.draftGeneration < 0) {
    throw new Error("An authorized editable Page is required.");
  }
  const {doc, selection} = editor.state;
  const identities = new Set<string>();
  doc.descendants((node, _position, parent) => {
    const layoutNode = node.type.name === "pageRow" || node.type.name === "pageSlot" || node.type.name === "pageImageText";
    const layoutBlock = BLOCKS.includes(node.type.name) && (
      parent?.type.name === "doc" || parent?.type.name === "pageSlot" || parent?.type.name === "pageImageText"
    );
    if (!layoutNode && !layoutBlock) return;
    const identity = layoutNode ? node.attrs.id : node.attrs.pageBlockId;
    if (typeof identity !== "string" || !identity.trim() || identities.has(identity)) {
      throw new Error("Page layout identities are missing or ambiguous.");
    }
    identities.add(identity);
  });
  const offers: AgentImageMoveOffer[] = [];
  const targets = new Map<string, BoundAgentImageMove>();
  let selected: string | null = null;
  doc.forEach((row, rowPosition) => {
    if (!validRow(row) || !row.attrs.id) return;
    const rowContext = row.textBetween(0, row.content.size, " ").trim().slice(0, 500);
    row.forEach((slot, slotOffset, index) => {
      if (slot.type.name !== "pageSlot" || !slot.attrs.id) return;
      const right = row.maybeChild(index + 1);
      slot.forEach((block, blockOffset, blockIndex) => {
        if (block.type.name !== "paragraph" || !block.attrs.pageBlockId
          || block.childCount !== 1 || block.firstChild?.type.name !== "mediaImage") return;
        const position = rowPosition + slotOffset + blockOffset + 2;
        const destination = !right || right.type.name !== "pageSlot" || !right.attrs.id ? "unavailable"
          : right.childCount ? "occupied"
          : blockIndex !== slot.childCount - 1 ? "changes_reading_order" : "empty_right";
        const alias = `image${offers.length + 1}`;
        offers.push(Object.freeze({
          alias, alt: String(block.firstChild.attrs.alt ?? ""), rowContext, sourceColumn: index + 1, destination,
        }));
        targets.set(alias, {
          source: block, position,
          destination: destination === "empty_right" ? rowPosition + slotOffset + slot.nodeSize + 2 : null,
          location: {
            row_id: row.attrs.id, source_slot_id: slot.attrs.id, destination_slot_id: right?.attrs.id ?? null,
            image_block_id: block.attrs.pageBlockId,
          },
        });
        if (selection instanceof NodeSelection && selection.from === position + 1) selected = alias;
      });
    });
  });
  const capture = Object.freeze({offers: Object.freeze(offers), selected});
  issuedImageMoves.set(capture, {scope: {...scope}, document: doc, targets});
  return capture;
}

export function selectedAgentImageBlock(capture: CapturedAgentImageMoves): string | null {
  return capture.selected ? issuedImageMoves.get(capture)?.targets.get(capture.selected)?.location.image_block_id ?? null : null;
}

export function matchAgentImageMove(capture: CapturedAgentImageMoves, location: AgentImageMoveLocation): string {
  const candidates = Array.from(issuedImageMoves.get(capture)?.targets ?? []);
  const matches = candidates.filter(([, target]) => (
    target.destination !== null
    && target.location.row_id === location.row_id
    && target.location.source_slot_id === location.source_slot_id
    && target.location.destination_slot_id === location.destination_slot_id
    && target.location.image_block_id === location.image_block_id
  ));
  if (matches.length !== 1) throw new Error("The reviewed occurrence and adjacent slot changed.");
  return matches[0][0];
}

function agentImageMoveTransaction(
  scope: AgentImageMoveScope, capture: CapturedAgentImageMoves, alias: string,
) {
  const bound = issuedImageMoves.get(capture);
  const target = bound?.targets.get(alias);
  if (!bound || !target || target.destination === null) throw new Error("The image move was not offered.");
  const {editor} = scope;
  const prior = bound.scope;
  if (!scope.canEdit || editor.isDestroyed || !editor.isEditable || editor !== prior.editor
    || scope.worldId !== prior.worldId || scope.documentId !== prior.documentId
    || scope.revision !== prior.revision || scope.draftGeneration !== prior.draftGeneration
    || editor.state.doc !== bound.document || editor.state.doc.nodeAt(target.position) !== target.source) {
    throw new Error("The captured Page changed. Nothing moved.");
  }
  const tr = editor.state.tr.delete(target.position, target.position + target.source.nodeSize);
  tr.insert(tr.mapping.map(target.destination), target.source);
  return tr;
}

export function previewAgentImageMove(
  scope: AgentImageMoveScope, capture: CapturedAgentImageMoves, alias: string,
): string {
  return JSON.stringify(agentImageMoveTransaction(scope, capture, alias).doc.toJSON());
}

/** Apply exactly one offered move. Undo cannot make the old capture executable again. */
export function applyAgentImageMove(
  scope: AgentImageMoveScope, capture: CapturedAgentImageMoves, alias: string,
): void {
  const tr = agentImageMoveTransaction(scope, capture, alias);
  requireManualSave(scope.editor);
  issuedImageMoves.delete(capture);
  scope.editor.view.dispatch(closeHistory(tr));
}

export function resizePageRow(editor: Editor, pos: number, width: number, dividerIndex = 0): boolean {
  if (editor.isDestroyed || !editor.isEditable) return false;
  const row = editor.state.doc.nodeAt(pos);
  if (editor.isDestroyed || !editor.isEditable || !validRow(row) || !Number.isFinite(width)
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
  if (editor.isDestroyed || !editor.isEditable) return false;
  const row = editor.state.doc.nodeAt(pos);
  if (editor.isDestroyed || !editor.isEditable || !validRow(row) || Object.keys(attrs).some(key => key !== 'min_height' && key !== 'line_mode')) return false;
  const next = { ...row.attrs, ...attrs };
  if (typeof next.min_height !== 'number' || !Number.isInteger(next.min_height) || next.min_height < 0 || next.min_height > 640 || next.min_height % 8 !== 0
    || typeof next.line_mode !== 'string' || !['guide', 'border', 'clean'].includes(next.line_mode)) return false;
  if (next.min_height === row.attrs.min_height && next.line_mode === row.attrs.line_mode) return true;
  editor.view.dispatch(closeHistory(editor.state.tr.setNodeMarkup(pos, undefined, next)));
  return true;
}

function forEachSourceBlock(doc: PMNode, visit: (block: PMNode, pos: number) => void) {
  const walk = (block: PMNode, pos: number) => {
    if (block.type.name === 'pageImageText') {
      block.forEach((child, offset) => walk(child, pos + 1 + offset));
    } else if (BLOCKS.includes(block.type.name)) {
      visit(block, pos);
    }
  };
  doc.forEach((block, pos) => {
    if (block.type.name !== 'pageRow') {
      walk(block, pos);
    } else {
      block.forEach((slot, slotOffset) => slot.forEach((child, childOffset) =>
        walk(child, pos + 2 + slotOffset + childOffset)));
    }
  });
}

function hasSourceBlockIdentities(doc: PMNode): boolean {
  let hasIdentities = false;
  doc.forEach(block => {
    if (!BLOCKS.includes(block.type.name) || block.attrs.pageBlockId) hasIdentities = true;
  });
  return hasIdentities;
}

function stampSourceBlockIdentities(tr: Transaction, allocate: (position: number) => string) {
  const seen = new Set<string>();
  forEachSourceBlock(tr.doc, (block, pos) => {
    let id = block.attrs.pageBlockId;
    if (typeof id !== 'string' || !id || seen.has(id)) {
      id = allocate(pos);
      tr.setNodeMarkup(pos, undefined, { ...block.attrs, pageBlockId: id });
    }
    seen.add(id);
  });
}

/** Bind the same new identities each time Review prepares this exact draft and insertion. */
export function prepareReviewedBlockIdentities(tr: Transaction): Transaction {
  if (!tr.doc.type.schema.nodes.paragraph?.spec.attrs?.pageBlockId) return tr;
  if (!hasSourceBlockIdentities(tr.doc)) return preservePlainReviewBlockIdentities(tr);

  const reserved = new Set<string>();
  forEachSourceBlock(tr.doc, block => {
    if (typeof block.attrs.pageBlockId === 'string') reserved.add(block.attrs.pageBlockId);
  });
  stampSourceBlockIdentities(tr, position => {
    const prefix = `page-review-${position}`;
    let id = prefix;
    for (let index = 1; reserved.has(id); index++) id = `${prefix}-${index}`;
    reserved.add(id);
    return id;
  });
  return tr;
}

export const PageBlockIdentity = Extension.create({
  name: 'pageBlockIdentity',
  addGlobalAttributes() { return [{ types: BLOCKS, attributes: { pageBlockId: { default: null, rendered: false } } }]; },
  addProseMirrorPlugins() {
    return [new Plugin({
      appendTransaction(transactions, _oldState, state) {
        // Never change untouched hydration. Stamp only after a real document
        // transaction and only source-level blocks, not paragraphs inside tables.
        const changed = transactions.filter(transaction => transaction.docChanged);
        if (!changed.length) return null;
        // Exact reviewed insertion and history keep plain pages free of the sidecar.
        if (!hasSourceBlockIdentities(state.doc) && changed.every(transaction =>
          transaction.getMeta(PLAIN_REVIEW_INSERTION) === true || isHistoryTransaction(transaction))) return null;
        const tr = state.tr;
        stampSourceBlockIdentities(tr, newId);
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
  addProseMirrorPlugins() { return [layoutEditabilityPlugin()]; },
  name: 'pageRow', group: 'block', content: 'pageSlot{1,3}', defining: true, isolating: true,
  addAttributes() { return { id: { default: null }, min_height: { default: 0 }, line_mode: { default: 'guide' } }; },
  parseHTML() { return [{ tag: 'div[data-page-row]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes(HTMLAttributes, { 'data-page-row': '', class: 'page-composer-row' }), 0]; },
  addNodeView() {
    return ({ node: initial, editor, getPos, view }) => {
      let node = initial;
      const dom = document.createElement('div'); dom.className = 'page-composer-row'; dom.dataset.pageRow = '';
      const contentDOM = document.createElement('div'); contentDOM.className = 'page-composer-row__slots';
      dom.append(contentDOM);
      const handle = layoutHandle(editor, getPos, 'pageRow'); dom.append(handle);
      const controls: HTMLButtonElement[] = [];
      let drag: { index: number; width: number; rect: DOMRect; height?: number; startY?: number; baseHeight?: number } | null = null;
      const widths = () => { const values: number[] = []; node.forEach(slot => values.push(Number(slot.attrs.width))); return values; };
      let editable = editor.options.editable;
      const paint = (values = widths(), height = node.attrs.min_height) => {
        contentDOM.style.gridTemplateColumns = values.map(width => `minmax(0, ${width}fr)`).join(' ');
        contentDOM.style.setProperty('--page-min-height', `${height}px`);
        dom.dataset.lineMode = node.attrs.line_mode;
        handle.hidden = editor.isDestroyed || !editable;
        let left = 0;
        controls.forEach((control, index) => {
          control.disabled = editor.isDestroyed || !editable || !validRow(node);
          control.hidden = !editable;
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
          if (editor.isDestroyed || !editor.isEditable || !validRow(node) || event.button !== 0) return;
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
      const editorDOM = view.dom;
      const editableChanged = (event: Event) => {
        editable = (event as CustomEvent<boolean>).detail;
        if (!editable) drag = null;
        paint();
      };
      editorDOM.addEventListener(LAYOUT_EDITABILITY_EVENT, editableChanged);
      paint();
      return { dom, contentDOM,
        update(next) { if (next.type !== node.type || next.childCount !== node.childCount) return false; node = next; if (!drag) paint(); return true; },
        stopEvent(event) { return handle.contains(event.target as globalThis.Node) || controls.some(control => control.contains(event.target as globalThis.Node)); },
        ignoreMutation(mutation) { return mutation.type !== 'selection' && (handle.contains(mutation.target) || mutation.target === dom || (mutation.target === contentDOM && mutation.type === 'attributes') || controls.some(control => control.contains(mutation.target))); },
        destroy() { drag = null; editorDOM.removeEventListener(LAYOUT_EDITABILITY_EVENT, editableChanged); },
      };
    };
  },
});

export const PAGE_COMPOSER_EXTENSIONS = [PageBlockIdentity, PageSlot, PageRow, ...PAGE_IMAGE_TEXT_EXTENSIONS];

/** Shared Edit discovery; each action rechecks the current selection at invocation. */
export function pageComposerActions(editor: Editor) {
  const safe = !editor.isDestroyed && editor.isEditable;
  return [
    ...([1, 2, 3] as const).map(columns => ({ id: `row-${columns}`, label: `${['One', 'Two', 'Three'][columns - 1]}-column row`,
      enabled: safe && wrapPageRow(editor, true, columns), invoke: () => wrapPageRow(editor, false, columns) })),
    { id: 'image-text', label: 'Text on image', enabled: safe && wrapPageImageText(editor, true), invoke: () => wrapPageImageText(editor) },
  ];
}

export function PageComposerTools({ editor, disabledReason }: { editor: Editor | null; disabledReason?: string | null }) {
  const [, refresh] = useState(0);
  const [request, setRequest] = useState<LayoutRequest | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const cancelHeightCommit = useRef(false);
  const [placement, setPlacement] = useState({ left: 8, top: 8 });
  useEffect(() => {
    if (!editor) return;
    const update = () => refresh(value => value + 1);
    const open = (event: Event) => { if (!editor.isDestroyed && editor.isEditable && !disabledReason) setRequest((event as CustomEvent<LayoutRequest>).detail); };
    const editorDOM = editor.view.dom;
    editorDOM.addEventListener(LAYOUT_CONTROLS_EVENT, open);
    const editableChanged = () => { if (!editor.isEditable) setRequest(null); update(); };
    editorDOM.addEventListener(LAYOUT_EDITABILITY_EVENT, editableChanged);
    editor.on('transaction', update); editor.on('selectionUpdate', update); editor.on('update', update); editor.on('destroy', update);
    return () => { editorDOM.removeEventListener(LAYOUT_EDITABILITY_EVENT, editableChanged); editorDOM.removeEventListener(LAYOUT_CONTROLS_EVENT, open); editor.off('transaction', update); editor.off('selectionUpdate', update); editor.off('update', update); editor.off('destroy', update); setRequest(null); };
  }, [editor, disabledReason]);
  const liveEditor = editor && !editor.isDestroyed && editor.isEditable && !disabledReason ? editor : null;
  const row = liveEditor ? rowAtSelection(liveEditor) : null;
  const stack = liveEditor ? stackAtSelection(liveEditor) : null;
  const valid = !!request && !!liveEditor && request.trigger.isConnected && (request.kind === 'pageRow' ? row?.row.attrs.id : stack?.node.attrs.id) === request.id;
  useLayoutEffect(() => {
    if (!request || !valid) { if (request) setRequest(null); return; }
    const trigger = request.trigger;
    const owner = trigger.parentElement;
    cancelHeightCommit.current = false;
    trigger.setAttribute('aria-expanded', 'true'); owner?.setAttribute('data-layout-selected', 'true');
    const place = () => {
      const anchor = trigger.getBoundingClientRect(); const rect = panel.current?.getBoundingClientRect();
      const height = rect?.height ?? 220; const width = rect?.width ?? 300;
      setPlacement({ left: Math.max(8, Math.min(anchor.left, (document.documentElement.clientWidth || window.innerWidth) - width - 8)),
        top: Math.max(8, anchor.bottom + height + 8 <= window.innerHeight ? anchor.bottom + 4 : anchor.top - height - 4) });
    };
    place(); panel.current?.querySelector<HTMLElement>('button, select, input')?.focus({ preventScroll: true });
    const outside = (event: Event) => {
      const target = event.target as HTMLElement;
      if (panel.current?.contains(target) || trigger.contains(target) || (owner?.contains(target) && target.closest('[role=separator]'))) return;
      setRequest(null); // Never restore focus on an outside click or native text selection.
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault(); event.stopPropagation(); cancelHeightCommit.current = true; setRequest(null); trigger.focus({ preventScroll: true });
    };
    document.addEventListener('pointerdown', outside, true); document.addEventListener('focusin', outside);
    document.addEventListener('keydown', escape, true);
    window.addEventListener('resize', place); window.addEventListener('scroll', place, true);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(place);
    if (panel.current) observer?.observe(panel.current);
    return () => {
      trigger.setAttribute('aria-expanded', 'false'); owner?.removeAttribute('data-layout-selected');
      document.removeEventListener('pointerdown', outside, true); document.removeEventListener('focusin', outside); document.removeEventListener('keydown', escape, true);
      window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true); observer?.disconnect();
    };
  }, [request, valid]);
  const [heightDraft, setHeightDraft] = useState('0');
  const rowHeight = row?.row.attrs.min_height ?? 0;
  const rowId = row?.row.attrs.id ?? null;
  useEffect(() => { setHeightDraft(String(rowHeight)); }, [rowHeight, rowId]);
  const currentRow = () => !!liveEditor && !liveEditor.isDestroyed && liveEditor.isEditable && !!row
    && rowAtSelection(liveEditor)?.row.attrs.id === row.row.attrs.id
    && liveEditor.state.doc.nodeAt(row.pos)?.attrs.id === row.row.attrs.id;
  const commitHeight = () => {
    if (cancelHeightCommit.current) { setHeightDraft(String(rowHeight)); return; }
    if (!currentRow() || !liveEditor || !row || heightDraft.trim() === '' || !updatePageRowPresentation(liveEditor, row.pos, { min_height: Number(heightDraft) })) setHeightDraft(String(rowHeight));
  };
  if (!valid || !liveEditor) return null;
  return createPortal(<div ref={panel} className="page-composer-tools page-layout-popover" role="dialog" aria-label={request.kind === 'pageRow' ? 'Row layout' : 'Image and text layout'}
    style={{ left: placement.left, top: placement.top }}>
    <header><strong>{request.kind === 'pageRow' ? 'Row layout' : 'Image and text'}</strong><button type="button" aria-label="Close layout options" onClick={() => { setRequest(null); request.trigger.focus({ preventScroll: true }); }}>×</button></header>
    {request.kind === 'pageRow' ? <>
    <button type="button" disabled={!editor?.isEditable || !row} onClick={() => currentRow() && editor && unwrapPageRow(editor)}>Unwrap row</button>
    <button type="button" disabled={!editor?.isEditable || !editor || !movePageBlock(editor, -1, true)} onClick={() => currentRow() && editor && movePageBlock(editor, -1)}>Move block earlier</button>
    <button type="button" disabled={!editor?.isEditable || !editor || !movePageBlock(editor, 1, true)} onClick={() => currentRow() && editor && movePageBlock(editor, 1)}>Move block later</button>
    <button type="button" disabled={!editor?.isEditable || !editor.can().undo()} onClick={() => currentRow() && editor?.commands.undo()}>Undo</button>
    <button type="button" disabled={!editor?.isEditable || !editor.can().redo()} onClick={() => currentRow() && editor?.commands.redo()}>Redo</button>
    <details><summary>Row settings</summary><label>Minimum row height <input type="number" min={0} max={640} step={8} value={heightDraft} disabled={!editor?.isEditable || !row}
      onChange={event => setHeightDraft(event.target.value)} onBlur={commitHeight}
      onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); commitHeight(); } if (event.key === 'Escape') { setHeightDraft(String(rowHeight)); } }} /></label>
    <button type="button" disabled={!editor?.isEditable || !row} onClick={() => { if (currentRow() && editor && row) updatePageRowPresentation(editor, row.pos, { min_height: 0 }); }}>Auto height</button>
    <label>Row lines <select value={row?.row.attrs.line_mode ?? 'guide'} disabled={!editor?.isEditable || !row}
      onChange={event => { if (currentRow() && editor && row) updatePageRowPresentation(editor, row.pos, { line_mode: event.target.value as 'guide' | 'border' | 'clean' }); }}>
      <option value="guide">Dotted guide</option><option value="border">Bordered</option><option value="clean">Clean</option>
    </select></label></details>
    </> : <PageImageTextTools editor={liveEditor} />}
  </div>, document.body);
}
