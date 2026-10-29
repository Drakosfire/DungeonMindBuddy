import {workPlanFence,workPlanBelongsTo,parseWorkPlanFence,workPlanIdentity,type WorkPlanReference} from '../surface/workPlans/workPlanReference';
import { pickMediaInsertion,pickDocumentInsertion } from '../documentEditing/pickMediaInsertion';
import type { Editor } from '@tiptap/core';
import type { WorldBuildDraftSnapshotV1 } from '../api/types';
import { TextSelection } from '@tiptap/pm/state';
import {pageBodyReferences,preservePageBodyReferences} from './pageBodyTarget';
import type { BuildProposalBasis, BuildPageBodyTarget } from '../api/buildDocumentProposalApi';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {semanticMarkdownSerializationDiagnostics} from '../tiptap/markdown/semanticMarkdownSafety';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdown, insertReviewedMarkdownAtAnchor, prepareReviewedMarkdownAtAnchor } from '../documentEditing/markdownInsertion';

export interface BuildComposeEditorState {
  editor: Editor; worldId: string; documentId: string; revision: number; contentSha256: string;
  visibility: 'internal' | 'player_safe'; draftGeneration: number; selectionGeneration: number; canEdit: boolean;
}
export interface CapturedBuildInsertion {
  pageBodyOffer?:BuildPageBodyTarget; pageBodyTarget?:BuildPageBodyTarget;
  basis: BuildProposalBasis; draftMarkdown: string; editor: Editor; editorJson: string;
}
export interface PreparedBuildProposal {
  captured: CapturedBuildInsertion; markdown: string; afterEditorSha256: string; afterDraftSha256: string;
}
export interface PreparedWorkPlanPlacement {
  captured:CapturedBuildInsertion;reference:WorkPlanReference;afterEditorJson:string;afterEditorSha256:string;afterDraftSha256:string;
}
export interface SavedProposalProjection {
  editorSha256:string;
  /** Recheck edit admission and the complete live capture across source verification. */
  assertCurrent:()=>void;
}
export interface ProposalInspection {
  state:'before'|'after'|'changed';
  savedProjection?:SavedProposalProjection;
}
export interface BuildComposeBridge {
  pickWorkPlanInsertion?: (options:{signal:AbortSignal;operationId:string})=>Promise<CapturedBuildInsertion>;
  observeWorkPlan?: (reference:WorkPlanReference,onPresence:(present:boolean)=>void)=>()=>void;
  prepareWorkPlan?: (captured:CapturedBuildInsertion,reference:WorkPlanReference)=>Promise<PreparedWorkPlanPlacement>;
  applyWorkPlan?: (prepared:PreparedWorkPlanPlacement)=>void;
  captureContext: () => Promise<WorldBuildDraftSnapshotV1>;
  capture: () => Promise<CapturedBuildInsertion>;
  pickInsertion?: (options: { signal: AbortSignal; mode: 'click' | 'drag'; assetId: string }) => Promise<CapturedBuildInsertion>;
  insert: (captured: CapturedBuildInsertion, markdown: string) => void;
  prepareProposal: (captured: CapturedBuildInsertion, markdown: string) => Promise<PreparedBuildProposal>;
  applyPrepared: (prepared: PreparedBuildProposal) => void;
  saveProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string, savedProjection?:SavedProposalProjection) => Promise<void>;
  inspectProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string) => Promise<ProposalInspection>;
  restore: (basis: BuildProposalBasis, pageBodyTarget?:BuildPageBodyTarget) => Promise<CapturedBuildInsertion>;
  insertProposal: (captured: CapturedBuildInsertion, markdown: string) => void;
}
async function sha256(value: string) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), byte => byte.toString(16).padStart(2, '0')).join('');
}
/** Read context does not require a caret, text selection or permission to change the page. */
export async function captureBuildDraftSnapshot(getCurrent: () => BuildComposeEditorState | null): Promise<WorldBuildDraftSnapshotV1> {
  const current = getCurrent();
  if (!current || current.editor.isDestroyed) throw new Error('Open the current Build page before discussing it.');
  const start = { ...current };
  const editorJson = JSON.stringify(start.editor.getJSON());
  const draftMarkdown = tiptapJsonToSemanticMarkdown(start.editor.getJSON());
  const [draftDigest, editorDigest] = await Promise.all([sha256(draftMarkdown), sha256(editorJson)]);
  const now = getCurrent();
  if (!now || now.editor.isDestroyed || now.editor !== start.editor
    || now.worldId !== start.worldId || now.documentId !== start.documentId
    || now.revision !== start.revision || now.contentSha256 !== start.contentSha256
    || now.visibility !== start.visibility || now.draftGeneration !== start.draftGeneration
    || JSON.stringify(now.editor.getJSON()) !== editorJson) {
    throw new Error('The page changed while its working draft was captured. Send again to use the current page.');
  }
  return Object.freeze({schema:'dmb_build_draft_snapshot_v1', world_id:start.worldId,
    document_id:start.documentId, registry_revision:start.revision, content_sha256:start.contentSha256,
    visibility:start.visibility, draft_markdown:draftMarkdown, draft_sha256:draftDigest,
    editor_sha256:editorDigest, draft_generation:start.draftGeneration});
}

export function createBuildComposeBridge(getCurrent: () => BuildComposeEditorState | null, changed: (editor: Editor) => void, persist?: BuildComposeBridge['saveProposal']): BuildComposeBridge {
  function savedPageMatches(current: BuildComposeEditorState, basis: BuildProposalBasis, allowExactSave = false) {
    return (current.revision === basis.registry_revision && current.contentSha256 === basis.content_sha256)
      // Only proposal recovery may cross a save of this exact captured draft.
      // Callers independently check the complete editor document and anchor.
      || (allowExactSave && current.revision > basis.registry_revision && current.contentSha256 === basis.draft_sha256);
  }
  function assertSame(captured: CapturedBuildInsertion, originalAnchor = false) {
    const now = getCurrent(); const basis = captured.basis;
    if (!now?.canEdit || now.editor.isDestroyed || now.editor !== captured.editor
      || now.worldId !== basis.world_id || now.documentId !== basis.document_id
      || !savedPageMatches(now, basis, originalAnchor)
      || now.visibility !== basis.visibility || now.draftGeneration !== basis.draft_generation
      || (!originalAnchor && (now.selectionGeneration !== basis.selection_generation
        || now.editor.state.selection.from !== basis.caret
        || now.editor.state.selection.to !== (basis.selection?.end ?? basis.caret)))
      || JSON.stringify(now.editor.getJSON()) !== captured.editorJson) {
      throw new Error('The page or insertion point changed. Ask again before inserting.');
    }
    if (basis.selection && (!Number.isInteger(basis.selection.end) || basis.selection.end <= basis.caret
      || basis.selection.end > now.editor.state.doc.content.size
      || now.editor.state.doc.textBetween(basis.caret,basis.selection.end,'\n') !== basis.selection.text)) {
      throw new Error('The selected passage changed. Nothing was replaced.');
    }
  }
  function target(captured:CapturedBuildInsertion) {
    const {basis,pageBodyTarget}=captured;
    if(pageBodyTarget){
      if(pageBodyTarget.end!==captured.editor.state.doc.content.size)throw new Error('The captured page body changed. Nothing was replaced.');
      admitMarkdownInsertion(captured.draftMarkdown);
      if(!canonicalProjection(captured.editor,captured.draftMarkdown))throw new Error('This page contains unsupported formatting. Nothing was replaced.');
      pageBodyReferences(JSON.parse(captured.editorJson));
      return {from:0,to:pageBodyTarget.end};
    }
    return basis.selection ? {from:basis.caret,to:basis.selection.end} : basis.caret;
  }
  const applied = new WeakSet<CapturedBuildInsertion>();
  const bridge: BuildComposeBridge = {
    observeWorkPlan(reference,onPresence){
      const now=getCurrent();if(!now||!workPlanBelongsTo(reference,{worldId:now.worldId,documentId:now.documentId}))return ()=>{};
      const editor=now.editor;
      const inspect=()=>{
        const current=getCurrent();if(!current||current.editor!==editor||editor.isDestroyed||!workPlanBelongsTo(reference,{worldId:current.worldId,documentId:current.documentId})){onPresence(false);return;}
        let found=false;editor.state.doc.descendants(node=>{if(node.type.name==='surfaceWorkPlan'){
          try{if(workPlanIdentity(parseWorkPlanFence(String(node.attrs.source)))===workPlanIdentity(reference))found=true;}catch{/* malformed references remain inert */}
        }});onPresence(found);
      };inspect();editor.on('transaction',inspect);return()=>editor.off('transaction',inspect);
    },
    captureContext: () => captureBuildDraftSnapshot(getCurrent),
    async capture() {
      const now = getCurrent();
      if (!now?.canEdit || now.editor.isDestroyed) throw new Error('Save and open an editable Build page first.');
      const selection = now.editor.state.selection;
      const selectedText = selection.empty ? '' : now.editor.state.doc.textBetween(selection.from,selection.to,'\n');
      if (!selection.empty && (!(selection instanceof TextSelection) || !selectedText.trim())) {
        throw new Error('Select a text passage to revise, or place a caret to add something.');
      }
      const editorJson = JSON.stringify(now.editor.getJSON());
      const draftMarkdown = tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      const caret = now.editor.state.selection.from;
      const draftGeneration = now.draftGeneration; const selectionGeneration = now.selectionGeneration;
      const captured: CapturedBuildInsertion = { editor: now.editor, editorJson, draftMarkdown,
        basis: { world_id: now.worldId, document_id: now.documentId, registry_revision: now.revision,
          content_sha256: now.contentSha256, visibility: now.visibility, draft_sha256: await sha256(draftMarkdown),
          editor_sha256: await sha256(editorJson), caret, draft_generation: draftGeneration, selection_generation: selectionGeneration,
          ...(!selection.empty ? {selection:{end:selection.to,text:selectedText}} : {}) } };
      assertSame(captured);
      try{
        admitMarkdownInsertion(draftMarkdown);
        pageBodyReferences(JSON.parse(editorJson));
        if(canonicalProjection(now.editor,draftMarkdown))captured.pageBodyOffer={end:now.editor.state.doc.content.size};
      }catch{/* Unsupported objects remain editable through their owning controls. */}
      return captured;
    },
    async prepareProposal(captured, markdown) {
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      const result = prepareReviewedMarkdownAtAnchor(captured.editor,target(captured),admitted.content,captured.editorJson);
      if(captured.pageBodyTarget)preservePageBodyReferences(JSON.parse(captured.editorJson),result);
      const prepared = {captured, markdown: admitted.markdown, afterEditorSha256: await sha256(JSON.stringify(result)),
        afterDraftSha256: await sha256(tiptapJsonToSemanticMarkdown(result))};
      assertSame(captured, true);
      return prepared;
    },
    applyPrepared(prepared) { bridge.insertProposal(prepared.captured,prepared.markdown); },
    async prepareWorkPlan(captured,reference){
      assertSame(captured,true);
      if(captured.basis.selection||!workPlanBelongsTo(reference,{worldId:captured.basis.world_id,documentId:captured.basis.document_id}))
        throw new Error('Choose an insertion point on the original page for this plan.');
      const content=[{type:'surfaceWorkPlan',attrs:{source:workPlanFence(reference)}}];
      const after=prepareReviewedMarkdownAtAnchor(captured.editor,captured.basis.caret,content,captured.editorJson);
      const result={captured,reference:JSON.parse(JSON.stringify(reference)) as WorkPlanReference,afterEditorJson:JSON.stringify(after),afterEditorSha256:await sha256(JSON.stringify(after)),afterDraftSha256:await sha256(tiptapJsonToSemanticMarkdown(after))};
      assertSame(captured,true);return result;
    },
    applyWorkPlan(prepared){
      const {captured,reference}=prepared;assertSame(captured,true);
      if(applied.has(captured)||captured.basis.selection||!workPlanBelongsTo(reference,{worldId:captured.basis.world_id,documentId:captured.basis.document_id}))
        throw new Error('This plan placement is no longer available. Inspect the page first.');
      const content=[{type:'surfaceWorkPlan',attrs:{source:workPlanFence(reference)}}];
      const after=prepareReviewedMarkdownAtAnchor(captured.editor,captured.basis.caret,content,captured.editorJson);
      if(JSON.stringify(after)!==prepared.afterEditorJson)throw new Error('The prepared object changed. Nothing was inserted.');
      insertReviewedMarkdownAtAnchor(captured.editor,captured.basis.caret,content,captured.editorJson);
      applied.add(captured);changed(captured.editor);
    },
    async saveProposal(basis,afterEditor,afterDraft,savedProjection) {
      if(!persist)throw new Error('Page saving is unavailable. Your insertion is retained for recovery.');
      await persist(basis,afterEditor,afterDraft,savedProjection);
    },
    async inspectProposal(basis,afterEditor,afterDraft) {
      const now=getCurrent();
      if(!now?.canEdit||now.editor.isDestroyed||now.worldId!==basis.world_id||now.documentId!==basis.document_id
        ||now.visibility!==basis.visibility||now.revision<basis.registry_revision)return {state:'changed'};
      const start={...now};
      const json=JSON.stringify(now.editor.getJSON());const markdown=tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      function assertCurrent(){
        const current=getCurrent();
        if(!current?.canEdit||current.editor.isDestroyed||current.editor!==start.editor||current.worldId!==start.worldId
          ||current.documentId!==start.documentId||current.visibility!==start.visibility||current.revision!==start.revision
          ||current.contentSha256!==start.contentSha256||current.draftGeneration!==start.draftGeneration
          ||JSON.stringify(current.editor.getJSON())!==json)throw new Error('The page or edit permission changed during insertion verification. Check it again.');
      }
      const [editorDigest,draftDigest]=await Promise.all([sha256(json),sha256(markdown)]);
      try{assertCurrent();}catch{return {state:'changed'};}
      if(editorDigest===afterEditor&&draftDigest===afterDraft)return {state:'after'};
      if(draftDigest===afterDraft && canonicalProjection(now.editor,markdown)){
        // This is not authorization to replay or Save. The owner must prove the
        // intended body is ALREADY committed, while preserving frontmatter.
        return {state:'after',savedProjection:{editorSha256:editorDigest,assertCurrent}};
      }
      if(editorDigest===basis.editor_sha256&&draftDigest===basis.draft_sha256
        &&savedPageMatches(now,basis,true))return {state:'before'};
      return {state:'changed'};
    },
    async restore(basis,pageBodyTarget) {
      if (!basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      const now = getCurrent();
      if (!now?.canEdit || now.editor.isDestroyed) throw new Error('Open the original editable Build page first.');
      const editorJson = JSON.stringify(now.editor.getJSON());
      const draftMarkdown = tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      const captured: CapturedBuildInsertion = {editor: now.editor, editorJson, draftMarkdown, pageBodyTarget,
        basis: {...basis, draft_generation: now.draftGeneration, selection_generation: now.selectionGeneration}};
      if (await sha256(editorJson) !== basis.editor_sha256 || await sha256(draftMarkdown) !== basis.draft_sha256
        || !Number.isInteger(basis.caret) || basis.caret < 0 || basis.caret > now.editor.state.doc.content.size) {
        throw new Error('This page has changed since the proposal. Nothing was inserted.');
      }
      assertSame(captured, true);
      target(captured);
      return captured;
    },
    insertProposal(captured, markdown) {
      if (!captured.basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      if (applied.has(captured)) throw new Error('This proposal has already been inserted.');
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      const range=target(captured);
      if(captured.pageBodyTarget){
        const result=prepareReviewedMarkdownAtAnchor(captured.editor,range,admitted.content,captured.editorJson);
        preservePageBodyReferences(JSON.parse(captured.editorJson),result);
      }
      insertReviewedMarkdownAtAnchor(captured.editor, range, admitted.content, captured.editorJson);
      applied.add(captured); changed(captured.editor);
    },
    async pickWorkPlanInsertion(options){
      const initial=getCurrent(),start=initial?{...initial}:null;
      if(!start?.canEdit||start.editor.isDestroyed)throw new Error('Open the editable page before placing this plan.');
      return pickDocumentInsertion({...options,editor:start.editor,mode:'click',noun:'plan',dragMime:'application/x-dmb-work-plan-placement',capture:()=>bridge.capture(),isCurrent:()=>{
        const now=getCurrent();return !!now?.canEdit&&now.editor===start.editor&&now.worldId===start.worldId&&now.documentId===start.documentId
          &&now.revision===start.revision&&now.contentSha256===start.contentSha256;
      }});
    },
    async pickInsertion(options) {
      const initial = getCurrent(); const start = initial ? { ...initial } : null;
      if (!start?.canEdit || start.editor.isDestroyed) throw new Error('Open the editable page before placing this image.');
      return pickMediaInsertion({ ...options, editor: start.editor, capture: () => bridge.capture(), isCurrent: () => {
        const now = getCurrent();
        return !!now?.canEdit && now.editor === start.editor && now.worldId === start.worldId && now.documentId === start.documentId
          && now.revision === start.revision && now.contentSha256 === start.contentSha256;
      } });
    },
    insert(captured, markdown) {
      if (captured.basis.selection) throw new Error('Image placement requires a caret; selected text will not be replaced.');
      if (applied.has(captured)) throw new Error('This proposal has already been inserted.');
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured);
      insertReviewedMarkdown(captured.editor, captured.basis.caret, admitted.content, captured.editorJson);
      applied.add(captured); changed(captured.editor);
    },
  };
  return bridge;
}

/** A representable current projection cannot hide dropped nodes or attributes. */
function canonicalProjection(editor:Editor,markdown:string):boolean {
  try{
    const json=editor.getJSON(),parsed=markdownToTiptapDoc(markdown);
    if(semanticMarkdownSerializationDiagnostics(json).length || parsed.diagnostics.some(issue=>issue.level==='warning'))return false;
    const reopened=editor.schema.nodeFromJSON(parsed.doc).toJSON();
    const stable=(value:unknown):unknown=>Array.isArray(value)?value.map(stable)
      :value&&typeof value==='object'?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,stable(item)])):value;
    return JSON.stringify(stable(json))===JSON.stringify(stable(reopened)) && tiptapJsonToSemanticMarkdown(reopened)===markdown;
  }catch{return false;}
}
