import { isTableCaptionAt } from '../tiptap/markdown/tableCaption';
import type { Editor } from '@tiptap/core';
import { TextSelection, type EditorState } from '@tiptap/pm/state';
import { closeHistory } from '@tiptap/pm/history';
import type { Node as PMNode } from '@tiptap/pm/model';
import { generatePlayableElementId, validatePlayableHeadingAttrs } from '../tiptap/playable/playableElementIdentity';
import { indexPlayableStructure, indexPlayableStructureV2, type PlayableStructureIndexV2 } from '../tiptap/playable/playableStructureIndex';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { semanticMarkdownSerializationDiagnostics } from '../tiptap/markdown/semanticMarkdownSafety';
import { planCardScopeKey } from './planCardEditing';

type Kind = 'scene' | 'beat';
type Version = 'v1' | 'v2';
export type PlanStructureAction = {kind: Kind; operation: 'insert' | 'promote'; label: string; disabledReason: string | null};
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
  state.doc.forEach((node, pos, index) => {
    if (node.type.name === 'heading' && node.attrs.level <= 2
      && !isTableCaptionAt(json.content ?? [], index)) {
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

/** Selection must stay inside one top-level ordinary heading. */
function ordinaryHeading(state: EditorState) {
  if (!(state.selection instanceof TextSelection)) return null;
  const {$from,$to}=state.selection;
  if ($from.depth!==1 || $to.depth!==1 || $from.parent!==$to.parent
    || $from.parent.type.name!=='heading' || validatePlayableHeadingAttrs($from.parent.attrs).status!=='absent') return null;
  if (isTableCaptionAt(state.doc.toJSON().content ?? [], $from.index(0))) return null;
  return {node:$from.parent,position:$from.before(1)};
}

export function planStructureActions(editor: Editor | null): PlanStructureAction[] {
  const info = editor && !editor.isDestroyed ? outline(editor.state) : null;
  const heading=editor && !editor.isDestroyed ? ordinaryHeading(editor.state) : null;
  const version = info?.version ?? 'v2';
  const rootKind = version === 'v2' ? 'beat' : 'scene';
  return ([rootKind, rootKind === 'beat' ? 'scene' : 'beat'] as Kind[]).map(kind => {
    const promote=version==='v2' && heading?.node.attrs.level===(kind==='beat'?2:3);
    return {
      kind, operation:promote?'promote':'insert',
      label: promote ? `Make this a ${kind==='beat'?'Beat':'Scene'}` : kind === rootKind ? `Add ${kind === 'beat' ? 'Beat' : 'Scene'}` : version === 'v2' ? 'Add Scene to this Beat' : 'Add Beat to this Scene',
      disabledReason: !editor || !editor.isEditable || editor.isDestroyed ? 'Edit this Plan to add playable structure.'
        : planCardScopeKey.getState(editor.state)?.active ? 'Open Document to change playable structure.'
        : info?.error ?? (kind !== rootKind && info?.parentEnd == null ? `Place the cursor inside a ${version === 'v2' ? 'Beat' : 'Scene'} first.` : null),
    };
  });
}

/** Existing objects keep their exact parent relationships; only order may shift. */
function ownership(index: PlayableStructureIndexV2) {
  return new Map<string,string>([
    ...index.beats.map(x=>[x.beatId,JSON.stringify(['beat',x.beatKind])] as const),
    ...index.scenes.map(x=>[x.sceneId,JSON.stringify(['scene',x.beatId])] as const),
    ...index.choices.map(x=>[x.choiceId,JSON.stringify(['choice',x.beatId,x.sceneId])] as const),
    ...index.options.map(x=>[x.optionId,JSON.stringify(['option',x.choiceId,x.activates,x.suppresses])] as const),
  ]);
}

/** Explicit registration only; no text rewrite, Save, AI call or version conversion. */
export function promotePlanHeading(editor: Editor,kind: Kind,expectedState: EditorState) {
  if(editor.isDestroyed || !editor.isEditable) throw new Error('This Plan is not editable.');
  if(!editor.state.doc.eq(expectedState.doc)||!editor.state.selection.eq(expectedState.selection))
    throw new Error('The Plan or cursor changed. Choose the structure action again.');
  const info=outline(editor.state),heading=ordinaryHeading(editor.state);
  if(info.version!=='v2')throw new Error('Choose one ordinary heading in a current Beat-first Plan.');
  const action=planStructureActions(editor).find(x=>x.kind===kind)!;
  if(action.disabledReason)throw new Error(action.disabledReason);
  if(!heading||heading.node.attrs.level!==(kind==='beat'?2:3))
    throw new Error('Choose one ordinary heading in a current Beat-first Plan.');
  const before=indexPlayableStructureV2(editor.getJSON());
  if(before.status!=='ready')throw new Error('Fix the playable structure before making this heading playable.');
  const id=generatePlayableElementId(kind);
  const tr=editor.state.tr.setNodeMarkup(heading.position,undefined,{
    ...heading.node.attrs,playableElementKind:kind,playableElementId:id,playableElementVersion:'v2',
    ...(kind==='beat'?{playableBeatKind:'spine'}:{}),
  });
  const after=indexPlayableStructureV2(tr.doc.toJSON());
  if(after.status!=='ready')throw new Error('This heading cannot become playable without invalidating the Plan.');
  const next=ownership(after.index);
  for(const [existing,relation] of ownership(before.index)) {
    if(next.get(existing)!==relation)throw new Error('This would change an existing playable relationship. Keep its current Beat, Scene and Choice ownership.');
  }
  verifyRoundtrip(editor,tr.doc);
  editor.view.dispatch(closeHistory(tr).scrollIntoView());
  if(!editor.state.doc.eq(tr.doc))throw new Error('The current editor scope refused this structure change. Open Document.');
  editor.view.focus();
  return id;
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
