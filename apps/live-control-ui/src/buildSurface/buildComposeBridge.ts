import { pickMediaInsertion } from '../documentEditing/pickMediaInsertion';
import type { Editor } from '@tiptap/core';
import type { BuildProposalBasis } from '../api/buildDocumentProposalApi';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { admitMarkdownInsertion, insertReviewedMarkdown } from '../documentEditing/markdownInsertion';

export interface BuildComposeEditorState {
  editor: Editor; worldId: string; documentId: string; revision: number; contentSha256: string;
  visibility: 'internal' | 'player_safe'; draftGeneration: number; selectionGeneration: number; canEdit: boolean;
}
export interface CapturedBuildInsertion {
  basis: BuildProposalBasis; draftMarkdown: string; editor: Editor; editorJson: string;
}
export interface BuildComposeBridge {
  capture: () => Promise<CapturedBuildInsertion>;
  pickInsertion?: (options: { signal: AbortSignal; mode: 'click' | 'drag'; assetId: string }) => Promise<CapturedBuildInsertion>;
  insert: (captured: CapturedBuildInsertion, markdown: string) => void;
}
async function sha256(value: string) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), byte => byte.toString(16).padStart(2, '0')).join('');
}
export function createBuildComposeBridge(getCurrent: () => BuildComposeEditorState | null, changed: (editor: Editor) => void): BuildComposeBridge {
  function assertSame(captured: CapturedBuildInsertion) {
    const now = getCurrent(); const basis = captured.basis;
    if (!now?.canEdit || now.editor.isDestroyed || now.editor !== captured.editor
      || now.worldId !== basis.world_id || now.documentId !== basis.document_id
      || now.revision !== basis.registry_revision || now.contentSha256 !== basis.content_sha256
      || now.visibility !== basis.visibility || now.draftGeneration !== basis.draft_generation
      || now.selectionGeneration !== basis.selection_generation
      || !now.editor.state.selection.empty || now.editor.state.selection.from !== basis.caret
      || JSON.stringify(now.editor.getJSON()) !== captured.editorJson) {
      throw new Error('The page or insertion point changed. Ask again before inserting.');
    }
  }
  const applied = new WeakSet<CapturedBuildInsertion>();
  const bridge: BuildComposeBridge = {
    async capture() {
      const now = getCurrent();
      if (!now?.canEdit || now.editor.isDestroyed) throw new Error('Save and open an editable Build page first.');
      if (!now.editor.state.selection.empty) throw new Error('Place the caret where the new text should go; selected text will not be replaced.');
      const editorJson = JSON.stringify(now.editor.getJSON());
      const draftMarkdown = tiptapJsonToSemanticMarkdown(now.editor.getJSON());
      const caret = now.editor.state.selection.from;
      const draftGeneration = now.draftGeneration; const selectionGeneration = now.selectionGeneration;
      const captured: CapturedBuildInsertion = { editor: now.editor, editorJson, draftMarkdown,
        basis: { world_id: now.worldId, document_id: now.documentId, registry_revision: now.revision,
          content_sha256: now.contentSha256, visibility: now.visibility, draft_sha256: await sha256(draftMarkdown),
          caret, draft_generation: draftGeneration, selection_generation: selectionGeneration } };
      assertSame(captured);
      return captured;
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
      if (applied.has(captured)) throw new Error('This proposal has already been inserted.');
      const admitted = admitMarkdownInsertion(markdown);
      assertSame(captured);
      insertReviewedMarkdown(captured.editor, captured.basis.caret, admitted.content, captured.editorJson);
      applied.add(captured); changed(captured.editor);
    },
  };
  return bridge;
}
