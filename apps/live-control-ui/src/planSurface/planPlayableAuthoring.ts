import type { Editor } from '@tiptap/core';
import { TextSelection, type EditorState } from '@tiptap/pm/state';
import type { Node as PMNode } from '@tiptap/pm/model';
import { generatePlayableElementId, validatePlayableHeadingAttrs } from '../tiptap/playable/playableElementIdentity';
import { indexPlayableStructure, indexPlayableStructureV2 } from '../tiptap/playable/playableStructureIndex';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { semanticMarkdownSerializationDiagnostics } from '../tiptap/markdown/semanticMarkdownSafety';

type Kind = 'scene' | 'beat';
type Version = 'v1' | 'v2';
export type PlanStructureAction = {kind: Kind; label: string; disabledReason: string | null};
type Outline = {version: Version; marked: boolean; parentEnd: number | null; error: string | null};

function outline(state: EditorState): Outline {
  const json = state.doc.toJSON();
  let marked = false, v2 = false;
  state.doc.descendants(node => {
    if (node.attrs.playableElementKind || node.attrs.playableElementId) marked = true;
    if (node.attrs.playableElementVersion === 'v2') v2 = true;
  });
  const version = !marked || v2 ? 'v2' : 'v1';
  const indexed = version === 'v2' ? indexPlayableStructureV2(json) : indexPlayableStructure(json);
  if (indexed.status !== 'ready') return {version, marked, parentEnd:null, error:'Fix the unsupported or invalid playable structure before adding a Scene or Beat.'};
  const rootKind = version === 'v2' ? 'beat' : 'scene';
  let currentRoot: {pos: number; end: number} | null = null;
  let selectedRoot: {pos: number; end: number} | null = null;
  state.doc.forEach((node, pos) => {
    if (node.type.name === 'heading' && node.attrs.level <= 2) {
      if (currentRoot) currentRoot.end = pos;
      const validated = validatePlayableHeadingAttrs(node.attrs);
      currentRoot = validated.status === 'canonical' && validated.identity.kind === rootKind
        ? {pos, end:state.doc.content.size} : null;
    }
    if (pos <= state.selection.from && state.selection.from <= pos + node.nodeSize) selectedRoot = currentRoot;
  });
  // Resolve the end from the same root scan, rather than using the caret as a drop position.
  const parent = selectedRoot as {pos:number; end:number} | null;
  return {version, marked, parentEnd: parent && state.selection.to <= parent.end && state.selection.from >= parent.pos ? parent.end : null, error:null};
}

export function planStructureActions(editor: Editor | null): PlanStructureAction[] {
  const info = editor && !editor.isDestroyed ? outline(editor.state) : null;
  const version = info?.version ?? 'v2';
  const rootKind = version === 'v2' ? 'beat' : 'scene';
  return ([rootKind, rootKind === 'beat' ? 'scene' : 'beat'] as Kind[]).map(kind => ({
    kind,
    label: kind === rootKind ? `Add ${kind === 'beat' ? 'Beat' : 'Scene'}` : version === 'v2' ? 'Add Scene to this Beat' : 'Add Beat to this Scene',
    disabledReason: !editor || !editor.isEditable || editor.isDestroyed ? 'Edit this Plan to add playable structure.' : info?.error ?? (kind !== rootKind && info?.parentEnd == null ? `Place the cursor inside a ${version === 'v2' ? 'Beat' : 'Scene'} first.` : null),
  }));
}

function verifyRoundtrip(editor: Editor, doc: PMNode) {
  if (semanticMarkdownSerializationDiagnostics(doc.toJSON()).length) throw new Error('This draft contains unsupported content. Resolve it before adding playable structure.');
  const parsed = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(doc.toJSON()));
  if (parsed.diagnostics.some(item => item.level === 'warning') || !doc.eq(editor.schema.nodeFromJSON(parsed.doc))) {
    throw new Error('This draft cannot round-trip without changing existing content. Resolve its formatting before adding playable structure.');
  }
}

/** One synchronous Plan-owned insertion; no conversion, Save, Graph call or Run mutation. */
export function insertPlanStructure(editor: Editor, kind: Kind, expectedState: EditorState) {
  if (editor.isDestroyed || !editor.isEditable) throw new Error('This Plan is not editable.');
  if (!editor.state.doc.eq(expectedState.doc) || !editor.state.selection.eq(expectedState.selection)) throw new Error('The Plan or cursor changed. Choose the structure action again.');
  const info = outline(editor.state);
  const action = planStructureActions(editor).find(item => item.kind === kind)!;
  if (action.disabledReason) throw new Error(action.disabledReason);
  const rootKind = info.version === 'v2' ? 'beat' : 'scene';
  const position = kind === rootKind ? editor.state.doc.content.size : info.parentEnd!;
  const id = generatePlayableElementId(kind);
  const heading = editor.schema.nodes.heading.create({
    level:kind === rootKind ? 2 : 3,
    playableElementKind:kind,
    playableElementId:id,
    playableElementVersion:info.version === 'v2' ? 'v2' : null,
    ...(kind === 'beat' && info.version === 'v2' ? {playableBeatKind:'spine'} : {}),
  }, editor.schema.text(`New ${kind === 'beat' ? 'Beat' : 'Scene'}`));
  const blank = editor.state.doc.childCount === 1 && editor.state.doc.firstChild?.eq(editor.schema.nodes.paragraph.create());
  const tr = blank ? editor.state.tr.replaceWith(0, editor.state.doc.content.size, heading) : editor.state.tr.insert(position, heading);
  const next = info.version === 'v2' ? indexPlayableStructureV2(tr.doc.toJSON()) : indexPlayableStructure(tr.doc.toJSON());
  if (next.status !== 'ready') throw new Error('The new playable structure is invalid. Nothing was inserted.');
  verifyRoundtrip(editor, tr.doc);
  const start = blank ? 0 : position;
  tr.setSelection(TextSelection.create(tr.doc, start + 1, start + heading.nodeSize - 1));
  editor.view.dispatch(tr.scrollIntoView());
  editor.view.focus();
  return id;
}
