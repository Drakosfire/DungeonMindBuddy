import {readSavedConversationVariantTarget,savedConversationVariantHref,type SavedConversationVariantTarget} from "../statblocks/savedStatblockLocation";
import {workPlanFence,workPlanBelongsTo,parseWorkPlanFence,workPlanIdentity,type WorkPlanReference} from '../surface/workPlans/workPlanReference';
import { pickMediaInsertion,pickDocumentInsertion } from '../documentEditing/pickMediaInsertion';
import type { Editor, JSONContent } from '@tiptap/core';
import {closeHistory} from '@tiptap/pm/history';
import {Fragment} from '@tiptap/pm/model';
import type { WorldBuildDraftSnapshotV1 } from '../api/types';
import type { BuildGraphReferenceApply, BuildGraphReferencePlacement } from '../api/buildGraphReferenceReviewApi';
import type { BuildImageMoveCapture, BuildImageMovePlacement } from '../api/buildImageMoveReviewApi';
import { TextSelection } from '@tiptap/pm/state';
import {pageBodyReferences,preservePageBodyReferences} from './pageBodyTarget';
import {isBuildProseBoundaryTarget,type BuildProposalBasis,type BuildPageBodyTarget,type BuildPageEndTarget,type BuildProseBoundaryTarget} from '../api/buildDocumentProposalApi';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {semanticMarkdownSerializationDiagnostics} from '../tiptap/markdown/semanticMarkdownSafety';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdownAtAnchor, prepareReviewedMarkdownAtAnchor } from '../documentEditing/markdownInsertion';
import {captureProseTargetCatalog,resolveProseTarget} from '../documentEditing/proseTargetCatalog';
import {flattenPresentation,hasPresentation,hasEmptyParagraphs,hydratePresentation,presentationFingerprint,projectPresentation,type PagePresentation} from '../tiptap/pageComposer/presentation';
import {preserveLeadingYamlFrontmatter,stripLeadingYamlFrontmatter} from '../tiptap/markdown/stripLeadingYamlFrontmatter';
import {
  applyAgentImageMove, captureAgentImageMoves, matchAgentImageMove, preservePlainReviewBlockIdentities,
  previewAgentImageMove, selectedAgentImageBlock, type CapturedAgentImageMoves,
} from '../tiptap/pageComposer/PageRow';
import {isValidGraphNodeId,normalizeRunbookReferenceAttrs} from '../tiptap/references/runbookReferences';

export interface BuildComposeEditorState {
  editor: Editor; worldId: string; documentId: string; revision: number; contentSha256: string;
  visibility: 'internal' | 'player_safe'; draftGeneration: number; selectionGeneration: number; canEdit: boolean;
  pagePresentation?: PagePresentation | null;
  savedMarkdown?: string;
}
export interface CapturedBuildInsertion {
  pageBodyOffer?:BuildPageBodyTarget; pageBodyTarget?:BuildPageBodyTarget;
  pageEndOffer?:BuildPageEndTarget; pageEndTarget?:BuildPageEndTarget;
  proseTarget?:BuildProseBoundaryTarget;
  contextualProse?:true;
  basis: BuildProposalBasis; draftMarkdown: string; editor: Editor; editorJson: string;
}
export interface PreparedBuildProposal {
  captured: CapturedBuildInsertion; markdown: string; afterEditorSha256: string; afterDraftSha256: string;
}
export interface PreparedBuildGraphReference {
  captured: CapturedBuildInsertion;
  placement: BuildGraphReferencePlacement;
  afterEditorJson: string;
  afterDraft: string;
  postimage: Omit<BuildGraphReferenceApply,'apply_id'>;
}
export interface PreparedBuildImageMove {
  editorJson: string;
  afterEditorJson: string;
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
  captureImageMoves?: () => CapturedAgentImageMoves;
  applyImageMove?: (capture: CapturedAgentImageMoves, alias: string) => void;
  captureImageMoveTurn?: (conversationId: string, pointerRevision: number) => Promise<BuildImageMoveCapture | null>;
  canReviewImageMove?: (placement: BuildImageMovePlacement) => boolean;
  prepareImageMove?: (placement: BuildImageMovePlacement) => Promise<PreparedBuildImageMove>;
  applyPreparedImageMove?: (prepared: PreparedBuildImageMove) => void;
  canReviewGraphReference?: (worldId: string, documentId: string) => boolean;
  prepareGraphReference?: (placement: BuildGraphReferencePlacement) => Promise<PreparedBuildGraphReference>;
  applyGraphReference?: (prepared: PreparedBuildGraphReference) => void;
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
  saveProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string, savedProjection?:SavedProposalProjection,
    proseTarget?: BuildProseBoundaryTarget) => Promise<void>;
  inspectProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string,
    proseTarget?: BuildProseBoundaryTarget) => Promise<ProposalInspection>;
  restore: (basis: BuildProposalBasis, pageBodyTarget?:BuildPageBodyTarget, pageEndTarget?:BuildPageEndTarget,
    proseTarget?:BuildProseBoundaryTarget) => Promise<CapturedBuildInsertion>;
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

export function createBuildComposeBridge(getCurrent: () => BuildComposeEditorState | null, changed: (editor: Editor) => void, persist?: BuildComposeBridge['saveProposal']): BuildComposeBridge {
  function savedPageMatches(current: BuildComposeEditorState, basis: BuildProposalBasis, allowExactSave = false) {
    return (current.revision === basis.registry_revision && current.contentSha256 === basis.content_sha256)
      // Only proposal recovery may cross a save of this exact captured draft.
      // Callers independently check the complete editor document and anchor.
      || (allowExactSave && current.revision > basis.registry_revision && current.contentSha256 === basis.draft_sha256);
  }
  const boundProse = new WeakSet<CapturedBuildInsertion>();
  const preparedGraphs = new WeakSet<PreparedBuildGraphReference>();
  function proseState() {
    const now = getCurrent();
    return now ? {editor: now.editor, canEdit: now.canEdit, draftGeneration: now.draftGeneration,
      scopeKey: JSON.stringify([now.worldId, now.documentId, now.revision, now.contentSha256, now.visibility])} : null;
  }
  async function bindProse(captured: CapturedBuildInsertion, proof: BuildProseBoundaryTarget) {
    if (!isBuildProseBoundaryTarget(proof) || captured.basis.selection || captured.pageBodyTarget || captured.pageEndTarget)
      throw new Error('This suggestion does not have one exact Build paragraph boundary.');
    const catalog = captureProseTargetCatalog(proseState);
    const offered = catalog.choices.find(choice => choice.selector === proof.alias);
    const [catalogSha, passageSha] = await Promise.all([
      sha256(JSON.stringify(catalog.choices)), offered ? sha256(offered.passage) : Promise.resolve(null),
    ]);
    const target = resolveProseTarget(catalog, proof.alias, proseState);
    if (target.from !== proof.from || target.to !== proof.to || target.operation !== proof.operation
      || target.editorJson !== captured.editorJson || catalogSha !== proof.catalog_sha256 || passageSha !== proof.before_text_sha256)
      throw new Error('The exact offered passage differs. Ask again on the current page.');
    assertSame(captured, true);
    const saved = getCurrent()?.savedMarkdown;
    if (saved !== undefined && stripLeadingYamlFrontmatter(saved).markdown !== captured.draftMarkdown)
      throw new Error('The saved source differs from the exact editable Markdown. Save or recover the current page before requesting a paragraph insertion.');
    const result = {...captured, proseTarget:Object.freeze({...proof})};
    boundProse.add(result);
    return result;
  }
  function proseTransaction(captured: CapturedBuildInsertion, content: JSONContent[]) {
    const isProse = (node: JSONContent) => node.type === 'paragraph'
      && (node.content ?? []).every(child => child.type === 'text' || child.type === 'hardBreak');
    const isCallout = (node: JSONContent) => node.type === 'callout'
      && Boolean(node.content?.length) && (node.content ?? []).every(isProse);
    const singleParagraph = content.length === 1 && content[0].type === 'paragraph'
      && (content[0].content ?? []).every(node => node.type === 'text');
    const calloutFragment = content.some(isCallout) && content.every(node => isProse(node) || isCallout(node));
    if (!singleParagraph && !calloutFragment)
      throw new Error('This Build suggestion must add prose or semantic callouts at the offered root boundary.');
    return rootBoundaryTransaction(captured, content, 'page-prose');
  }
  function graphParagraph(placement: BuildGraphReferencePlacement): JSONContent {
    const {basis,reference}=placement;
    if (basis.visibility !== 'internal' || basis.world_id !== reference.managed_world_id
      || !isValidGraphNodeId(reference.node_id) || !reference.label.trim())
      throw new Error('Review the exact Graph identity on its original internal page.');
    return {type:'paragraph',content:[{type:'runbookReference',attrs:normalizeRunbookReferenceAttrs({
      kind:'ref',refType:'graph-node',refId:reference.node_id,label:reference.label,
    })}]};
  }
  function rootBoundaryTransaction(captured: CapturedBuildInsertion, content: JSONContent[], idPrefix: string) {
    const proof = captured.proseTarget;
    const editor = captured.editor;
    if (!proof || !boundProse.has(captured) || !editor.isEditable || editor.state.doc.resolve(proof.from).depth !== 0)
      throw new Error('This Build suggestion must use the offered root boundary.');
    const original = JSON.parse(captured.editorJson) as JSONContent;
    const current = getCurrent();
    const presentation = current?.pagePresentation;
    const retainPlain = presentation?.items.every(item => item.kind === 'block') === true;
    const retainsIds = hasPresentation(original) || retainPlain;
    const baseId = `${idPrefix}-${proof.catalog_sha256.slice(0,32)}-${proof.from}`;
    const inserted = content.map((node, index) => {
      if (!retainsIds) return editor.schema.nodeFromJSON(node);
      if (!node.type || !editor.schema.nodes[node.type]?.spec.attrs?.pageBlockId)
        throw new Error('This page editor cannot retain block identities.');
      const pageBlockId = index === 0 ? baseId : `${baseId}-${index}`;
      return editor.schema.nodeFromJSON({...node, attrs: {...node.attrs, pageBlockId}});
    });
    const transaction = editor.state.tr.insert(proof.from, Fragment.fromArray(inserted));
    if (!retainsIds) preservePlainReviewBlockIdentities(transaction);
    const after = transaction.doc.toJSON() as JSONContent;
    const before = original.content ?? [];
    const index = editor.state.doc.resolve(proof.from).index(0);
    if (after.content?.length !== before.length + inserted.length || before.some((node,i) =>
      JSON.stringify(node) !== JSON.stringify(after.content?.[i < index ? i : i + inserted.length])))
      throw new Error('The insertion would change an unrelated block.');
    const body = tiptapJsonToSemanticMarkdown(flattenPresentation(after));
    const savedMarkdown = current?.savedMarkdown ?? captured.draftMarkdown;
    const projectedBefore = presentation ? hydratePresentation(savedMarkdown, presentation) : original;
    const projection = retainsIds ? projectPresentation(after, savedMarkdown, projectedBefore, presentation, retainPlain) : null;
    const reopened = projection?.presentation ? hydratePresentation(projection.markdown, projection.presentation) : markdownToTiptapDoc(body).doc;
    if (semanticMarkdownSerializationDiagnostics(flattenPresentation(after)).length
      || JSON.stringify(editor.schema.nodeFromJSON(reopened).toJSON()) !== JSON.stringify(after))
      throw new Error('Saving this insertion would change existing structure or block identities.');
    return {transaction, after, body, projection, savedMarkdown};
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
  const applied = new WeakSet<CapturedBuildInsertion>();
  function imageMoveScope() {
    const current = getCurrent();
    if (!current || current.visibility !== "internal" || !current.pagePresentation?.items.some(item => item.kind === "row")) {
      throw new Error("Image movement requires an existing saved internal layout.");
    }
    return current;
  }
  const preparedImageMoves = new WeakMap<PreparedBuildImageMove, {capture: CapturedAgentImageMoves; alias: string}>();
  function savedImageMoveScope(current: BuildComposeEditorState) {
    if (!current.canEdit || !current.pagePresentation || current.savedMarkdown === undefined) {
      throw new Error('Open the saved editable composed Page.');
    }
    const initial = hydratePresentation(current.savedMarkdown, current.pagePresentation);
    const projection = projectPresentation(current.editor.getJSON(), current.savedMarkdown, initial, current.pagePresentation);
    if (projection.markdown !== current.savedMarkdown
      || presentationFingerprint(projection.presentation) !== presentationFingerprint(current.pagePresentation)) {
      throw new Error('Save the current Page before asking to move an image.');
    }
  }
  const bridge: BuildComposeBridge = {
    captureImageMoves: () => captureAgentImageMoves(imageMoveScope()),
    applyImageMove: (capture, alias) => applyAgentImageMove(imageMoveScope(), capture, alias),
    async captureImageMoveTurn(conversationId, pointerRevision) {
      const live = getCurrent();
      if (!live?.canEdit || live.visibility !== 'internal' || live.editor.isDestroyed
        || !live.pagePresentation?.items.some(item => item.kind === 'row')) return null;
      const start = {...live};
      const capture = captureAgentImageMoves(start);
      if (!capture.offers.length) return null;
      savedImageMoveScope(start);
      const editorJson = JSON.stringify(start.editor.getJSON());
      const selected = selectedAgentImageBlock(capture);
      const editorDigest = await sha256(editorJson);
      const current = imageMoveScope();
      if (current.editor !== start.editor || current.documentId !== start.documentId || current.worldId !== start.worldId
        || current.revision !== start.revision || current.contentSha256 !== start.contentSha256
        || current.draftGeneration !== start.draftGeneration || current.selectionGeneration !== start.selectionGeneration
        || JSON.stringify(current.editor.getJSON()) !== editorJson) {
        throw new Error('The editor changed while its image context was captured. Send again.');
      }
      return {
        conversation_id: conversationId, expected_pointer_revision: pointerRevision, editor_json: editorJson,
        author_selected_block_id: selected, basis: {
          world_id: start.worldId, document_id: start.documentId, registry_revision: start.revision,
          content_sha256: start.contentSha256, visibility: 'internal', draft_sha256: start.contentSha256,
          editor_sha256: editorDigest, caret: start.editor.state.selection.from,
          draft_generation: start.draftGeneration, selection_generation: start.selectionGeneration,
        },
      };
    },
    async prepareImageMove(placement) {
      const current = imageMoveScope(), basis = placement.basis;
      if (current.worldId !== basis.world_id || current.documentId !== basis.document_id
        || current.revision !== basis.registry_revision || current.contentSha256 !== basis.content_sha256
        || current.draftGeneration !== basis.draft_generation
        || presentationFingerprint(current.pagePresentation) !== placement.presentation_sha256) {
        throw new Error('The Page changed before the image move. Send the request again.');
      }
      savedImageMoveScope(current);
      const capture = captureAgentImageMoves(current);
      const alias = matchAgentImageMove(capture, placement);
      const editorJson = JSON.stringify(current.editor.getJSON());
      if (await sha256(editorJson) !== basis.editor_sha256) throw new Error('The editor no longer matches the image Review.');
      const afterEditorJson = previewAgentImageMove(imageMoveScope(), capture, alias);
      const prepared = {editorJson, afterEditorJson};
      preparedImageMoves.set(prepared, {capture, alias});
      return prepared;
    },
    canReviewImageMove(placement) {
      const current = getCurrent(), basis = placement.basis;
      return Boolean(current?.canEdit && !current.editor.isDestroyed && current.visibility === 'internal'
        && current.worldId === basis.world_id && current.documentId === basis.document_id
        && current.revision === basis.registry_revision && current.contentSha256 === basis.content_sha256
        && current.draftGeneration === basis.draft_generation);
    },
    applyPreparedImageMove(prepared) {
      const bound = preparedImageMoves.get(prepared);
      if (!bound) throw new Error('The prepared image move is unavailable.');
      preparedImageMoves.delete(prepared);
      applyAgentImageMove(imageMoveScope(), bound.capture, bound.alias);
    },
    canReviewGraphReference(worldId, documentId) {
      const current = getCurrent();
      return Boolean(current?.canEdit && !current.editor.isDestroyed && current.visibility === 'internal'
        && current.worldId === worldId && current.documentId === documentId);
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
      if (selection.empty && supportsRootProse(now.editor.getJSON()) &&
          canonicalProjection(now.editor, draftMarkdown, true)) {
        captured.contextualProse = true;
      }
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
      const prose = captured.proseTarget ? proseTransaction(captured, admitted.content) : null;
      const result = prose?.after ?? prepareReviewedMarkdownAtAnchor(captured.editor,target(captured),admitted.content,captured.editorJson);
      if(captured.pageBodyTarget)preservePageBodyReferences(JSON.parse(captured.editorJson),result);
      if(captured.pageEndTarget)preservePrefix(JSON.parse(captured.editorJson),result);
      const prepared = {captured, markdown: admitted.markdown, afterEditorSha256: await sha256(JSON.stringify(result)),
        afterDraftSha256: await sha256(prose?.body ?? tiptapJsonToSemanticMarkdown(result))};
      assertSame(captured, true);
      return prepared;
    },
    applyPrepared(prepared) { bridge.insertProposal(prepared.captured,prepared.markdown); },
    async prepareGraphReference(placement) {
      const captured = await bridge.restore(placement.basis, undefined, undefined, placement.boundary);
      const result = rootBoundaryTransaction(captured, [graphParagraph(placement)], 'page-graph-ref');
      const afterEditorJson = JSON.stringify(result.after);
      const [editor_sha256,draft_sha256,content_sha256] = await Promise.all([
        sha256(afterEditorJson), sha256(result.body),
        sha256(result.projection?.markdown ?? preserveLeadingYamlFrontmatter(result.savedMarkdown,result.body)),
      ]);
      assertSame(captured,true);
      const prepared = Object.freeze({captured,placement,afterEditorJson,afterDraft:result.body,postimage:Object.freeze({
        editor_sha256,draft_sha256,content_sha256,presentation_sha256:presentationFingerprint(result.projection?.presentation),
      })});
      preparedGraphs.add(prepared);
      return prepared;
    },
    applyGraphReference(prepared) {
      const {captured,placement} = prepared;
      assertSame(captured,true);
      if (!preparedGraphs.delete(prepared) || applied.has(captured))
        throw new Error('This reference placement is no longer available. Review the current page.');
      const result = rootBoundaryTransaction(captured,[graphParagraph(placement)],'page-graph-ref');
      if (JSON.stringify(result.after) !== prepared.afterEditorJson || result.body !== prepared.afterDraft)
        throw new Error('The prepared Graph reference changed. Review the current page.');
      captured.editor.view.dispatch(closeHistory(result.transaction));
      applied.add(captured);
      changed(captured.editor);
    },
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
    async saveProposal(basis,afterEditor,afterDraft,savedProjection,proseTarget) {
      if(!persist)throw new Error('Page saving is unavailable. Your insertion is retained for recovery.');
      if (proseTarget) await persist(basis,afterEditor,afterDraft,savedProjection,proseTarget);
      else await persist(basis,afterEditor,afterDraft,savedProjection);
    },
    async inspectProposal(basis,afterEditor,afterDraft,proseTarget) {
      const now=getCurrent();
      if(!now?.canEdit||now.editor.isDestroyed||now.worldId!==basis.world_id||now.documentId!==basis.document_id
        ||now.visibility!==basis.visibility||now.revision<basis.registry_revision)return {state:'changed'};
      const start={...now};
      const doc=now.editor.getJSON(),json=JSON.stringify(doc);
      const markdown=tiptapJsonToSemanticMarkdown(proseTarget ? flattenPresentation(doc) : doc);
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
      const draftMarkdown = tiptapJsonToSemanticMarkdown(proseTarget ? flattenPresentation(now.editor.getJSON()) : now.editor.getJSON());
      const captured: CapturedBuildInsertion = {editor: now.editor, editorJson, draftMarkdown, pageBodyTarget, pageEndTarget,
        basis: {...basis, draft_generation: now.draftGeneration, selection_generation: now.selectionGeneration}};
      if (await sha256(editorJson) !== basis.editor_sha256 || await sha256(draftMarkdown) !== basis.draft_sha256
        || !Number.isInteger(basis.caret) || basis.caret < 0 || basis.caret > now.editor.state.doc.content.size) {
        throw new Error('This page has changed since the proposal. Nothing was inserted.');
      }
      assertSame(captured, true);
      if (proseTarget) return bindProse(captured, proseTarget);
      target(captured);
      return captured;
    },
    insertProposal(captured, markdown) {
      if (!captured.basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      if (applied.has(captured)) throw new Error('This proposal has already been inserted.');
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      if (captured.proseTarget) {
        captured.editor.view.dispatch(closeHistory(proseTransaction(captured, admitted.content).transaction));
        applied.add(captured);changed(captured.editor);
        return;
      }
      const range=target(captured);
      if(captured.pageBodyTarget||captured.pageEndTarget){
        const result=prepareReviewedMarkdownAtAnchor(captured.editor,range,admitted.content,captured.editorJson);
        if(captured.pageBodyTarget)preservePageBodyReferences(JSON.parse(captured.editorJson),result);
        if(captured.pageEndTarget)preservePrefix(JSON.parse(captured.editorJson),result);
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
      const block = admitted.content.length === 1 ? admitted.content[0] : null;
      if (block?.type !== 'paragraph' || block.content?.length !== 1 || block.content[0]?.type !== 'mediaImage')
        throw new Error('Choose a saved image to place on this page.');
      const editor = captured.editor;
      const original = JSON.parse(captured.editorJson) as JSONContent;
      const position = editor.state.doc.resolve(captured.basis.caret);
      const anchor = position.depth > 0 ? position.after(1) : captured.basis.caret;
      const current = getCurrent(); const presentation = current?.pagePresentation;
      const retainPlain = presentation?.items.every(item => item.kind === 'block') === true;
      const retainsIds = hasPresentation(original) || retainPlain || presentation?.schema_version === 'dmb_page_presentation_v2' || hasEmptyParagraphs(original);
      if (retainsIds && !editor.schema.nodes.paragraph?.spec.attrs?.pageBlockId)
        throw new Error('This page editor cannot retain image block identities.');
      const imageBlock = retainsIds ? {...block,attrs:{...block.attrs,pageBlockId:`page-image-${crypto.randomUUID()}`}} : block;
      const transaction = editor.state.tr.insert(anchor,editor.schema.nodeFromJSON(imageBlock));
      if (!retainsIds) preservePlainReviewBlockIdentities(transaction);
      const after = transaction.doc.toJSON() as JSONContent;
      const before = original.content ?? [];
      const index = editor.state.doc.resolve(anchor).index(0);
      if (after.content?.length !== before.length + 1 || before.some((node,i) =>
        JSON.stringify(node) !== JSON.stringify(after.content?.[i < index ? i : i+1])))
        throw new Error('The image would change an unrelated block.');
      const body = tiptapJsonToSemanticMarkdown(flattenPresentation(after));
      const savedMarkdown = current?.savedMarkdown ?? captured.draftMarkdown;
      const projectedBefore = presentation ? hydratePresentation(savedMarkdown,presentation) : original;
      const projection = retainsIds ? projectPresentation(after,savedMarkdown,projectedBefore,presentation,retainPlain) : null;
      const reopened = projection?.presentation ? hydratePresentation(projection.markdown,projection.presentation) : markdownToTiptapDoc(body).doc;
      const reopenedJson = editor.schema.nodeFromJSON(reopened).toJSON() as JSONContent;
      // Enrollment gives previously anonymous plain blocks stable IDs. Compare
      // them as anonymous only when the live block truly had no ID; every
      // existing ID and all other structure must still match exactly.
      if (projection?.presentation?.schema_version === 'dmb_page_presentation_v2' && !hasPresentation(after)) {
        (reopenedJson.content ?? []).forEach((node, i) => {
          const live = after.content?.[i];
          if (live?.attrs?.pageBlockId == null && node.attrs) node.attrs.pageBlockId = null;
        });
      }
      if (semanticMarkdownSerializationDiagnostics(flattenPresentation(after)).length
        || JSON.stringify(reopenedJson) !== JSON.stringify(after))
        throw new Error('Saving this image would change existing structure or block identities.');
      closeHistory(transaction);
      // Installed editor plugins must be pure and deterministic: this preview and
      // the subsequent dispatch both run their transaction hooks.
      const simulated = editor.state.applyTransaction(transaction);
      if (!simulated.transactions.length || !simulated.state.doc.eq(transaction.doc))
        throw new Error('The editor cannot apply this image without changing the page.');
      editor.view.dispatch(transaction);
      applied.add(captured); changed(captured.editor);
    },
  };
  return bridge;
}

/** A representable current projection cannot hide dropped nodes or attributes. */
function supportsRootProse(doc: JSONContent): boolean {
  const prose = (node: JSONContent) => !!node.content?.some(child => child.type === 'text' && child.text?.trim())
    && node.content.every(child => child.type === 'hardBreak' ||
      child.type === 'text' && (child.marks ?? []).every(mark =>
        ['bold', 'italic', 'strike', 'code', 'underline', 'link'].includes(mark.type ?? '')));
  const protectedParagraph = (node: JSONContent) => node.type === 'paragraph'
    && (!node.content?.length || prose(node));
  return doc.type === 'doc' && !!doc.content?.length && doc.content.every(node => {
    if (node.type === 'callout') {
      return !!node.content?.length && node.content.every(protectedParagraph);
    }
    if (node.type === 'table') {
      return !!node.content?.length && node.content.every(row => row.type === 'tableRow'
        && !!row.content?.length && row.content.every(cell => cell.content?.length === 1
          && protectedParagraph(cell.content[0])));
    }
    // Canonical projection binds the artwork and its attributes. The server
    // independently checks the exact image reference before computing offsets.
    if (node.type === 'paragraph' && node.content?.length === 1
      && node.content[0].type === 'mediaImage') return true;
    if (Object.entries(node.attrs ?? {}).some(([key, value]) =>
      value != null && key !== 'pageBlockId' && key !== 'level')) return false;
    if (node.type === 'horizontalRule') return !node.content?.length;
    return (node.type === 'paragraph' || node.type === 'heading') && prose(node);
  });
}

function canonicalProjection(editor:Editor,markdown:string,ignorePageBlockIds=false):boolean {
  try{
    const json=editor.getJSON(),parsed=markdownToTiptapDoc(markdown);
    if(semanticMarkdownSerializationDiagnostics(json).length || parsed.diagnostics.some(issue=>issue.level==='warning'))return false;
    const reopened=editor.schema.nodeFromJSON(parsed.doc).toJSON();
    const stable=(value:unknown):unknown=>Array.isArray(value)?value.map(stable)
      :value&&typeof value==='object'?Object.fromEntries(Object.entries(value)
        .filter(([key])=>!ignorePageBlockIds || key!=='pageBlockId')
        .sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,stable(item)])):value;
    return JSON.stringify(stable(json))===JSON.stringify(stable(reopened)) && tiptapJsonToSemanticMarkdown(reopened)===markdown;
  }catch{return false;}
}
