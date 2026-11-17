import {hasPresentation,projectPresentation,hydratePresentation} from '../tiptap/pageComposer/presentation';
import {captureProseTargetCatalog, resolveProseTarget, type ProseTargetCatalog, type ResolvedProseTarget} from '../documentEditing/proseTargetCatalog';
import {readSavedConversationVariantTarget,savedConversationVariantHref,type SavedConversationVariantTarget} from "../statblocks/savedStatblockLocation";
import {workPlanFence,workPlanBelongsTo,parseWorkPlanFence,workPlanIdentity,type WorkPlanReference} from '../surface/workPlans/workPlanReference';
import { pickMediaInsertion,pickDocumentInsertion } from '../documentEditing/pickMediaInsertion';
import type { Editor } from '@tiptap/core';
import type { WorldBuildDraftSnapshotV1 } from '../api/types';
import { TextSelection } from '@tiptap/pm/state';
import {pageBodyReferences,preservePageBodyReferences} from './pageBodyTarget';
import type { BuildProposalBasis, BuildPageBodyTarget, BuildPageEndTarget, BuildProseTarget } from '../api/buildDocumentProposalApi';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {semanticMarkdownSerializationDiagnostics} from '../tiptap/markdown/semanticMarkdownSafety';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdown, insertReviewedMarkdownAtAnchor, prepareReviewedMarkdownAtAnchor } from '../documentEditing/markdownInsertion';

export interface BuildComposeEditorState {
  editor: Editor; worldId: string; documentId: string; revision: number; contentSha256: string;
  visibility: 'internal' | 'player_safe'; draftGeneration: number; selectionGeneration: number; canEdit: boolean;
}
export interface CapturedBuildInsertion {
  proseTarget?:BuildProseTarget;
  pageBodyOffer?:BuildPageBodyTarget; pageBodyTarget?:BuildPageBodyTarget;
  pageEndOffer?:BuildPageEndTarget; pageEndTarget?:BuildPageEndTarget;
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
export interface BuildProseNomination {
  readonly provenance: 'host_catalog_nomination';
  /** The actual author capture is not rewritten to impersonate a selection. */
  readonly actualBasis: Readonly<BuildProposalBasis>;
  readonly target: Readonly<ResolvedProseTarget>;
}
export interface BuildComposeBridge {
  captureProseInsertion?: (catalog:ProseTargetCatalog,selector:string)=>Promise<CapturedBuildInsertion>;
  captureProseTargets?: () => Promise<ProseTargetCatalog>;
  nominateProseTarget?: (catalog: ProseTargetCatalog, selector: string) => BuildProseNomination;
  pickWorkPlanInsertion?: (options:{signal:AbortSignal;operationId:string})=>Promise<CapturedBuildInsertion>;
  observeWorkPlan?: (reference:WorkPlanReference,onPresence:(present:boolean)=>void)=>()=>void;
  prepareWorkPlan?: (captured:CapturedBuildInsertion,reference:WorkPlanReference)=>Promise<PreparedWorkPlanPlacement>;
  applyWorkPlan?: (prepared:PreparedWorkPlanPlacement)=>void;
  captureContext: () => Promise<WorldBuildDraftSnapshotV1>;
  capture: () => Promise<CapturedBuildInsertion>;
  pickInsertion?: (options: { signal: AbortSignal; mode: 'click' | 'drag'; assetId: string }) => Promise<CapturedBuildInsertion>;
  insert: (captured: CapturedBuildInsertion, markdown: string) => void;
  placeSavedVariantLink?: (captured: CapturedBuildInsertion, variant: SavedConversationVariantTarget) => Promise<PreparedBuildProposal>;
  prepareProposal: (captured: CapturedBuildInsertion, markdown: string) => Promise<PreparedBuildProposal>;
  applyPrepared: (prepared: PreparedBuildProposal) => void;
  saveProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string, savedProjection?:SavedProposalProjection) => Promise<void>;
  inspectProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string) => Promise<ProposalInspection>;
  restore: (basis: BuildProposalBasis, pageBodyTarget?:BuildPageBodyTarget, pageEndTarget?:BuildPageEndTarget,proseTarget?:BuildProseTarget) => Promise<CapturedBuildInsertion>;
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

/** Appending must not join, replace or rewrite any existing editor node. */
function preservePrefix(before:ReturnType<Editor['getJSON']>,after:ReturnType<Editor['getJSON']>){
  const original=before.content??[];
  if(JSON.stringify((after.content??[]).slice(0,original.length))!==JSON.stringify(original))
    throw new Error('Page-end insertion would change existing content. Nothing was inserted.');
}

export function createBuildComposeBridge(getCurrent: () => BuildComposeEditorState | null, changed: (editor: Editor) => void, persist?: BuildComposeBridge['saveProposal'], options:{allowProseTargets?:boolean;allowProseBoundaries?:boolean}={}): BuildComposeBridge {
  function savedPageMatches(current: BuildComposeEditorState, basis: BuildProposalBasis, allowExactSave = false) {
    return (current.revision === basis.registry_revision && current.contentSha256 === basis.content_sha256)
      // Only proposal recovery may cross a save of this exact captured draft.
      // Callers independently check the complete editor document and anchor.
      || (allowExactSave && current.revision > basis.registry_revision && current.contentSha256 === basis.draft_sha256);
  }
  function assertSame(captured: CapturedBuildInsertion, originalAnchor = false) {
    const now = getCurrent(); const basis = captured.basis;
    if (!now?.canEdit || now.editor.isDestroyed || (captured.proseTarget && !now.editor.isEditable) || now.editor !== captured.editor
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
  const boundProse = new WeakSet<CapturedBuildInsertion>();
  function target(captured:CapturedBuildInsertion) {
    if(captured.proseTarget){
      if(!(captured.proseTarget.schema==='dmb_build_prose_boundary_target_v1'?options.allowProseBoundaries:options.allowProseTargets)||!boundProse.has(captured)||captured.basis.selection||captured.pageBodyTarget||captured.pageEndTarget)
        throw new Error('This prose target is not admitted by this editor.');
      return {from:captured.proseTarget.from,to:captured.proseTarget.to};
    }
    const {basis,pageBodyTarget,pageEndTarget}=captured;
    if(pageBodyTarget&&pageEndTarget)throw new Error('Conflicting page targets. Nothing was inserted.');
    if(pageEndTarget){
      if(pageEndTarget.end!==captured.editor.state.doc.content.size)throw new Error('The captured page end changed. Nothing was inserted.');
      admitMarkdownInsertion(captured.draftMarkdown);
      if(!canonicalProjection(captured.editor,captured.draftMarkdown))throw new Error('This page contains unsupported formatting. Nothing was inserted.');
      pageBodyReferences(JSON.parse(captured.editorJson));
      return pageEndTarget.end;
    }
    if(pageBodyTarget){
      if(pageBodyTarget.end!==captured.editor.state.doc.content.size)throw new Error('The captured page body changed. Nothing was replaced.');
      admitMarkdownInsertion(captured.draftMarkdown);
      if(!canonicalProjection(captured.editor,captured.draftMarkdown))throw new Error('This page contains unsupported formatting. Nothing was replaced.');
      pageBodyReferences(JSON.parse(captured.editorJson));
      return {from:0,to:pageBodyTarget.end};
    }
    return basis.selection ? {from:basis.caret,to:basis.selection.end} : basis.caret;
  }
  const proseCaptures = new WeakMap<ProseTargetCatalog, CapturedBuildInsertion>();
  const proseState = () => {
    const now = getCurrent();
    return now ? {editor: now.editor, canEdit: now.canEdit, draftGeneration: now.draftGeneration,
      scopeKey: JSON.stringify([now.worldId, now.documentId, now.revision, now.contentSha256, now.visibility])} : null;
  };
  async function bindProse(captured:CapturedBuildInsertion,binding:BuildProseTarget){
    if(!(binding.schema==='dmb_build_prose_boundary_target_v1'?options.allowProseBoundaries:options.allowProseTargets)||captured.basis.selection||captured.pageBodyTarget||captured.pageEndTarget)
      throw new Error('Prose targeting is not enabled for this captured page.');
    const catalog=captureProseTargetCatalog(proseState);
    const actual=resolveProseTarget(catalog,binding.alias,proseState);
    const choice=catalog.choices.find(row=>row.selector===binding.alias);
    const boundary=binding.schema==='dmb_build_prose_boundary_target_v1';
    if(!choice||(!boundary&&(binding.schema!=='dmb_build_prose_target_v1'||binding.operation!=='replace_paragraph'))
      ||boundary&&(binding.from!==binding.to||binding.from<0)
      ||actual.operation!==binding.operation||actual.from!==binding.from||actual.to!==binding.to
      ||binding.catalog_sha256!==await sha256(JSON.stringify(catalog.choices))
      ||binding.before_text_sha256!==await sha256(boundary?choice.passage:captured.editor.state.doc.textBetween(actual.from,actual.to,'\n')))
      throw new Error('The prose target differs from its exact offered occurrence.');
    assertSame(captured,true);
    const result={...captured,proseTarget:Object.freeze({...binding})};boundProse.add(result);return result;
  }
  function admitProse(captured:CapturedBuildInsertion,content:ReturnType<typeof admitMarkdownInsertion>['content']){
    if(captured.proseTarget&&(content.length!==1||content[0]?.type!=='paragraph'
      ||!(content[0].content??[]).every(node=>node.type==='text')))
      throw new Error('A prose edit must be one paragraph. Nothing was changed.');
    if(captured.proseTarget?.schema!=='dmb_build_prose_boundary_target_v1')return content;
    if(!captured.editor.schema.nodes.paragraph?.spec.attrs?.pageBlockId)throw new Error('This editor cannot retain the new paragraph identity.');
    const id=`page-prose-${captured.proseTarget.catalog_sha256.slice(0,32)}-${captured.proseTarget.operation}-${captured.proseTarget.from}`;
    let collision=false;captured.editor.state.doc.descendants(node=>{if(node.attrs.pageBlockId===id||node.attrs.id===id)collision=true;});
    if(collision)throw new Error('The new paragraph identity is already present. Nothing was changed.');
    return [{...content[0]!,attrs:{...content[0]!.attrs,pageBlockId:id}}];
  }
  function preserveProseOutside(captured:CapturedBuildInsertion,result:ReturnType<Editor['getJSON']>){
    if(!captured.proseTarget)return;
    const before=JSON.parse(captured.editorJson).content??[],after=result.content??[];
    const index=captured.editor.state.doc.resolve(captured.proseTarget.from).index(0);
    if(captured.proseTarget.schema==='dmb_build_prose_boundary_target_v1'){
      if(!hasPresentation(JSON.parse(captured.editorJson)))throw new Error('This proof requires an existing saved page composition to preserve block identities. Nothing was changed.');
      const projection=projectPresentation(result,captured.draftMarkdown,JSON.parse(captured.editorJson));
      const reopened=captured.editor.schema.nodeFromJSON(hydratePresentation(projection.markdown,projection.presentation)).toJSON();
      if(JSON.stringify(reopened)!==JSON.stringify(result))throw new Error('Saving this insertion would normalize page structure or identities. Nothing was changed.');
      if(after.length!==before.length+1||after[index]?.type!=='paragraph'
        ||before.some((node:unknown,i:number)=>JSON.stringify(node)!==JSON.stringify(after[i<index?i:i+1])))
        throw new Error('The insertion would change unrelated page structure. Nothing was changed.');
      return;
    }
    if(before.length!==after.length||JSON.stringify(before[index]?.attrs??{})!==JSON.stringify(after[index]?.attrs??{})
      ||before.some((node:unknown,i:number)=>i!==index&&JSON.stringify(node)!==JSON.stringify(after[i])))
      throw new Error('The replacement would change unrelated page structure. Nothing was changed.');
  }
  const applied = new WeakSet<CapturedBuildInsertion>();
  const bridge: BuildComposeBridge = {
    async captureProseInsertion(catalog,selector){
      const nomination=bridge.nominateProseTarget!(catalog,selector);
      const captured=proseCaptures.get(catalog)!;
      const choice=catalog.choices.find(row=>row.selector===selector)!;
      const common={catalog_sha256:await sha256(JSON.stringify(catalog.choices)),alias:selector,
        from:nomination.target.from,to:nomination.target.to,before_text_sha256:await sha256(choice.passage)};
      const binding:BuildProseTarget=nomination.target.operation==='replace_paragraph'
        ?{...common,schema:'dmb_build_prose_target_v1',operation:'replace_paragraph'}
        :{...common,schema:'dmb_build_prose_boundary_target_v1',operation:nomination.target.operation};
      return bindProse(captured,binding);
    },
    async captureProseTargets() {
      const captured = await bridge.capture();
      if (captured.basis.selection) throw new Error('Keep the explicitly selected passage as the target.');
      const catalog = captureProseTargetCatalog(proseState);
      assertSame(captured, true);
      proseCaptures.set(catalog, captured);
      return catalog;
    },
    nominateProseTarget(catalog, selector) {
      const captured = proseCaptures.get(catalog);
      if (!captured) throw new Error('This prose catalog belongs to another page capture.');
      assertSame(captured, true);
      const target = resolveProseTarget(catalog, selector, proseState);
      return Object.freeze({provenance: 'host_catalog_nomination' as const,
        actualBasis: Object.freeze({...captured.basis}), target});
    },
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
        if(canonicalProjection(now.editor,draftMarkdown)){
          captured.pageBodyOffer={end:now.editor.state.doc.content.size};
          captured.pageEndOffer={end:now.editor.state.doc.content.size};
        }
      }catch{/* Unsupported objects remain editable through their owning controls. */}
      return captured;
    },
    async placeSavedVariantLink(captured, variant) {
      assertSame(captured, true);
      if (captured.basis.selection || captured.basis.visibility !== "internal" ||
          captured.basis.world_id !== variant.worldId) {
        throw new Error("Choose an insertion point on the original GM page.");
      }
      const href = savedConversationVariantHref(variant);
      const text = "Open saved statblock variant";
      const content = [{ type: "paragraph", content: [
        { type: "text", text, marks: [{ type: "link", attrs: { href } }] },
      ] }];
      let present = false;
      captured.editor.state.doc.descendants(node => {
        for (const mark of node.marks) {
          const candidate = mark.attrs.href;
          if (mark.type.name !== "link" || typeof candidate !== "string" || !candidate.startsWith("/statblock?")) continue;
          const target = readSavedConversationVariantTarget(candidate);
          if (target && savedConversationVariantHref(target) === href) present = true;
        }
      });
      const after = present ? captured.editor.getJSON() :
        prepareReviewedMarkdownAtAnchor(captured.editor, captured.basis.caret, content, captured.editorJson);
      const prepared = {
        captured, markdown: `[${text}](${href})`,
        afterEditorSha256: await sha256(JSON.stringify(after)),
        afterDraftSha256: await sha256(tiptapJsonToSemanticMarkdown(after)),
      };
      assertSame(captured, true);
      if (!present) {
        insertReviewedMarkdownAtAnchor(captured.editor, captured.basis.caret, content, captured.editorJson);
        changed(captured.editor);
      }
      return prepared;
    },
    async prepareProposal(captured, markdown) {
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      const content=admitProse(captured,admitted.content);
      const result = prepareReviewedMarkdownAtAnchor(captured.editor,target(captured),content,captured.editorJson,{preserveComposer:!!captured.proseTarget});
      preserveProseOutside(captured,result);
      if(captured.pageBodyTarget)preservePageBodyReferences(JSON.parse(captured.editorJson),result);
      if(captured.pageEndTarget)preservePrefix(JSON.parse(captured.editorJson),result);
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
      if((options.allowProseTargets||options.allowProseBoundaries)&&!getCurrent()?.editor.isEditable)throw new Error('The page is no longer editable. Nothing was saved.');
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
    async restore(basis,pageBodyTarget,pageEndTarget,proseTarget) {
      if (!basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      const now = getCurrent();
      if (!now?.canEdit || now.editor.isDestroyed) throw new Error('Open the original editable Build page first.');
      const editorJson = JSON.stringify(now.editor.getJSON());
      const draftMarkdown = tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      const captured: CapturedBuildInsertion = {editor: now.editor, editorJson, draftMarkdown, pageBodyTarget, pageEndTarget,
        basis: {...basis, draft_generation: now.draftGeneration, selection_generation: now.selectionGeneration}};
      if (await sha256(editorJson) !== basis.editor_sha256 || await sha256(draftMarkdown) !== basis.draft_sha256
        || !Number.isInteger(basis.caret) || basis.caret < 0 || basis.caret > now.editor.state.doc.content.size) {
        throw new Error('This page has changed since the proposal. Nothing was inserted.');
      }
      assertSame(captured, true);
      target(captured);
      return proseTarget?bindProse(captured,proseTarget):captured;
    },
    insertProposal(captured, markdown) {
      if (!captured.basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      if (applied.has(captured)) throw new Error('This proposal has already been inserted.');
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      const range=target(captured);
      const content=admitProse(captured,admitted.content);
      if(captured.proseTarget)preserveProseOutside(captured,prepareReviewedMarkdownAtAnchor(captured.editor,range,content,captured.editorJson,{preserveComposer:true}));
      if(captured.pageBodyTarget||captured.pageEndTarget){
        const result=prepareReviewedMarkdownAtAnchor(captured.editor,range,admitted.content,captured.editorJson);
        if(captured.pageBodyTarget)preservePageBodyReferences(JSON.parse(captured.editorJson),result);
        if(captured.pageEndTarget)preservePrefix(JSON.parse(captured.editorJson),result);
      }
      insertReviewedMarkdownAtAnchor(captured.editor, range, content, captured.editorJson,{preserveComposer:!!captured.proseTarget});
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
