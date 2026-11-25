import type {Editor} from '@tiptap/core';
import {isTableCaptionAt} from '../tiptap/markdown/tableCaption';

/** Host-only authority supplied by the existing surface owner, never model input. */
export interface ProseTargetState {
  editor: Editor;
  scopeKey: string;
  draftGeneration: number;
  canEdit: boolean;
}
export interface ProseTargetChoice {
  selector: string;
  operation: 'insert_before' | 'insert_after';
  section: string;
  passage: string;
}
export interface ProseTargetCatalog {
  choices: readonly Readonly<ProseTargetChoice>[];
}
export interface ResolvedProseTarget {
  from: number;
  to: number;
  editorJson: string;
  operation: ProseTargetChoice['operation'];
}
type Binding = {
  state: ProseTargetState;
  doc: Editor['state']['doc'];
  editorJson: string;
  targets: Map<string, Readonly<ResolvedProseTarget>>;
};
const issued = new WeakMap<ProseTargetCatalog, Binding>();
function editable(state: ProseTargetState | null): state is ProseTargetState {
  return !!state && state.canEdit && !state.editor.isDestroyed && state.editor.isEditable;
}

/**
 * A host capability catalog, not a semantic router. Never infer which duplicate
 * the user means. Only ordinary root prose is eligible; nested/table/media/native
 * blocks remain with their existing owners. No document or selection mutations.
 */
export function captureProseTargetCatalog(getCurrent: () => ProseTargetState | null): ProseTargetCatalog {
  const current = getCurrent();
  if (!editable(current)) throw new Error('Open an editable page before choosing a prose target.');
  const state = {...current}, doc = state.editor.state.doc;
  const editorJson = JSON.stringify(state.editor.getJSON());
  const content = state.editor.getJSON().content ?? [];
  const choices: Readonly<ProseTargetChoice>[] = [];
  const targets = new Map<string, Readonly<ResolvedProseTarget>>();
  const headings: {level: number; text: string}[] = [];
  let occurrence = 0;
  doc.forEach((node, position, index) => {
    if (node.type.name === 'heading') {
      if (isTableCaptionAt(content, index)) return;
      const level = Number(node.attrs.level);
      if (!Number.isInteger(level) || level < 1 || level > 6) return;
      while (headings.length && headings[headings.length - 1]!.level >= level) headings.pop();
      headings.push({level, text: node.textContent});
      return;
    }
    if (node.type.name !== 'paragraph' || !node.textContent.trim()) return;
    // Atom, reference and citation blocks stay with their existing owners.
    let textOnly = true;
    node.forEach(child => {
      if (!child.isText || child.marks.some(mark => !['bold', 'italic', 'strike', 'code', 'underline'].includes(mark.type.name))) textOnly = false;
    });
    if (!textOnly) return;
    const next = index + 1 < doc.childCount ? doc.child(index + 1) : null;
    // A table can own the preceding paragraph as its caption.
    if (next?.type.name === 'table') return;
    const alias = `passage${++occurrence}`;
    const section = headings.map(item => item.text).join(' / ') || 'Before the first heading';
    const add = (operation: ProseTargetChoice['operation'], from: number, to: number) => {
      const selector = `${alias}:${operation}`;
      choices.push(Object.freeze({selector, operation, section, passage: node.textContent}));
      targets.set(selector, Object.freeze({operation, from, to, editorJson}));
    };
    add('insert_before', position, position);
    add('insert_after', position + node.nodeSize, position + node.nodeSize);
  });
  const catalog = Object.freeze({choices: Object.freeze(choices)});
  issued.set(catalog, {state, doc, editorJson, targets});
  return catalog;
}

/** Resolve only a catalog-issued alias against its still-current host snapshot. */
export function resolveProseTarget(
  catalog: ProseTargetCatalog, selector: string, getCurrent: () => ProseTargetState | null,
): Readonly<ResolvedProseTarget> {
  const binding = issued.get(catalog), now = getCurrent();
  if (!binding || !editable(now) || now.editor !== binding.state.editor
    || now.scopeKey !== binding.state.scopeKey || now.draftGeneration !== binding.state.draftGeneration
    || now.editor.state.doc !== binding.doc || JSON.stringify(now.editor.getJSON()) !== binding.editorJson) {
    throw new Error('The page changed. Choose a target from the current editable page.');
  }
  const target = binding.targets.get(selector);
  if (!target) throw new Error('That prose target was not offered. Clarify the intended passage.');
  return target;
}
