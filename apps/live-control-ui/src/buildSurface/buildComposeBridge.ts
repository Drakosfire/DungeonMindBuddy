import { pickMediaInsertion } from '../documentEditing/pickMediaInsertion';
import type { Editor } from '@tiptap/core';
import type { WorldBuildDraftSnapshotV1 } from '../api/types';
import { TextSelection } from '@tiptap/pm/state';
import type { BuildProposalBasis } from '../api/buildDocumentProposalApi';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdown, insertReviewedMarkdownAtAnchor, prepareReviewedMarkdownAtAnchor } from '../documentEditing/markdownInsertion';

export interface BuildComposeEditorState {
  editor: Editor; worldId: string; documentId: string; revision: number; contentSha256: string;
  visibility: 'internal' | 'player_safe'; draftGeneration: number; selectionGeneration: number; canEdit: boolean;
}
export interface CapturedBuildInsertion {
  basis: BuildProposalBasis; draftMarkdown: string; editor: Editor; editorJson: string;
}
export interface PreparedBuildProposal {
  captured: CapturedBuildInsertion; markdown: string; afterEditorSha256: string; afterDraftSha256: string;
}
export interface BuildComposeBridge {
  capture: () => Promise<CapturedBuildInsertion>;
  pickInsertion?: (options: { signal: AbortSignal; mode: 'click' | 'drag'; assetId: string }) => Promise<CapturedBuildInsertion>;
  insert: (captured: CapturedBuildInsertion, markdown: string) => void;
  prepareProposal: (captured: CapturedBuildInsertion, markdown: string) => Promise<PreparedBuildProposal>;
  applyPrepared: (prepared: PreparedBuildProposal) => void;
  inspectProposal: (basis: BuildProposalBasis, afterEditor: string, afterDraft: string) => Promise<'before'|'after'|'changed'>;
  restore: (basis: BuildProposalBasis) => Promise<CapturedBuildInsertion>;
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

export function createBuildComposeBridge(getCurrent: () => BuildComposeEditorState | null, changed: (editor: Editor) => void): BuildComposeBridge {
  function assertSame(captured: CapturedBuildInsertion, originalAnchor = false) {
    const now = getCurrent(); const basis = captured.basis;
    if (!now?.canEdit || now.editor.isDestroyed || now.editor !== captured.editor
      || now.worldId !== basis.world_id || now.documentId !== basis.document_id
      || now.revision !== basis.registry_revision || now.contentSha256 !== basis.content_sha256
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
  function target(basis:BuildProposalBasis) {
    return basis.selection ? {from:basis.caret,to:basis.selection.end} : basis.caret;
  }
  const applied = new WeakSet<CapturedBuildInsertion>();
  const bridge: BuildComposeBridge = {
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
      return captured;
    },
    async prepareProposal(captured, markdown) {
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      const result = prepareReviewedMarkdownAtAnchor(captured.editor,target(captured.basis),admitted.content,captured.editorJson);
      const prepared = {captured, markdown: admitted.markdown, afterEditorSha256: await sha256(JSON.stringify(result)),
        afterDraftSha256: await sha256(tiptapJsonToSemanticMarkdown(result))};
      assertSame(captured, true);
      return prepared;
    },
    applyPrepared(prepared) { bridge.insertProposal(prepared.captured,prepared.markdown); },
    async inspectProposal(basis,afterEditor,afterDraft) {
      const now=getCurrent();
      if(!now||now.editor.isDestroyed||now.worldId!==basis.world_id||now.documentId!==basis.document_id||now.visibility!==basis.visibility)return 'changed';
      const json=JSON.stringify(now.editor.getJSON());const markdown=tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      const editorDigest=await sha256(json);const draftDigest=await sha256(markdown);
      const current=getCurrent();
      if(!current||current.editor!==now.editor||current.worldId!==now.worldId||current.documentId!==now.documentId
        ||current.visibility!==now.visibility||JSON.stringify(current.editor.getJSON())!==json)return 'changed';
      if(editorDigest===afterEditor&&draftDigest===afterDraft)return 'after';
      if(editorDigest===basis.editor_sha256&&draftDigest===basis.draft_sha256
        &&current.revision===basis.registry_revision&&current.contentSha256===basis.content_sha256)return 'before';
      return 'changed';
    },
    async restore(basis) {
      if (!basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      const now = getCurrent();
      if (!now?.canEdit || now.editor.isDestroyed) throw new Error('Open the original editable Build page first.');
      const editorJson = JSON.stringify(now.editor.getJSON());
      const draftMarkdown = tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      const captured: CapturedBuildInsertion = {editor: now.editor, editorJson, draftMarkdown,
        basis: {...basis, draft_generation: now.draftGeneration, selection_generation: now.selectionGeneration}};
      if (await sha256(editorJson) !== basis.editor_sha256 || await sha256(draftMarkdown) !== basis.draft_sha256
        || !Number.isInteger(basis.caret) || basis.caret < 0 || basis.caret > now.editor.state.doc.content.size) {
        throw new Error('This page has changed since the proposal. Nothing was inserted.');
      }
      assertSame(captured, true);
      return captured;
    },
    insertProposal(captured, markdown) {
      if (!captured.basis.editor_sha256) throw new Error('This earlier proposal has no saved insertion anchor. Ask again where you want the new text.');
      if (applied.has(captured)) throw new Error('This proposal has already been inserted.');
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured, true);
      insertReviewedMarkdownAtAnchor(captured.editor, target(captured.basis), admitted.content, captured.editorJson);
      applied.add(captured); changed(captured.editor);
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
