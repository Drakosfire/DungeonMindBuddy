import { MEDIA_ASSET_ID } from '../media/mediaReferences';
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
    async pickInsertion({ signal, mode, assetId }) {
      const initial = getCurrent();
      const start = initial ? { ...initial } : null;
      if (!start?.canEdit || start.editor.isDestroyed || !MEDIA_ASSET_ID.test(assetId)) throw new Error('Open the editable page before placing this image.');
      const editor = start.editor; const dom = editor.view.dom;
      return new Promise<CapturedBuildInsertion>((resolve, reject) => {
        const cleanup = () => {
          dom.classList.remove('is-media-placement-target');
          dom.removeEventListener('pointerup', choose, true); dom.removeEventListener('drop', choose, true);
          dom.removeEventListener('dragover', over, true); document.removeEventListener('dragend', endDrag, true);
          signal.removeEventListener('abort', abort);
        };
        const fail = (reason: Error) => { cleanup(); reject(reason); };
        const abort = () => fail(new DOMException('Placement cancelled.', 'AbortError'));
        const endDrag = () => fail(new Error('The image was not dropped on the page. Try again.'));
        const over = (event: DragEvent) => { event.preventDefault(); if(event.dataTransfer)event.dataTransfer.dropEffect='copy'; };
        const choose = (event: Event) => {
          if (mode === 'drag') { event.preventDefault(); event.stopImmediatePropagation(); }
          try {
            if (signal.aborted) throw new DOMException('Placement cancelled.', 'AbortError');
            const now = getCurrent();
            if (!now?.canEdit || editor.isDestroyed || now.editor !== editor || now.worldId !== start.worldId || now.documentId !== start.documentId) throw new Error('The page changed. Choose the image again on its original page.');
            if (mode === 'drag' && (event as DragEvent).dataTransfer?.getData('application/x-dmb-media') !== assetId) throw new Error('Drop the selected saved image, not a file, link or outside image.');
            if (!editor.state.selection.empty) throw new Error('Click a single insertion point; selected text will not be replaced.');
            const pointer = event as MouseEvent;
            const target = editor.view.posAtCoords({ left: pointer.clientX, top: pointer.clientY });
            if (!target) throw new Error('Choose a position inside the page.');
            editor.commands.setTextSelection(target.pos);
            const expected = JSON.stringify(editor.getJSON()); const caret = editor.state.selection.from;
            cleanup();
            requestAnimationFrame(() => {
              if (signal.aborted) { reject(new DOMException('Placement cancelled.', 'AbortError')); return; }
              const latest=getCurrent();
              if (!latest?.canEdit || latest.editor!==editor || latest.worldId!==start.worldId || latest.documentId!==start.documentId || latest.revision!==start.revision || latest.contentSha256!==start.contentSha256 || editor.isDestroyed || JSON.stringify(editor.getJSON()) !== expected || editor.state.selection.from !== caret) { reject(new Error('The page changed before placement. Choose a position again.')); return; }
              bridge.capture().then(resolve, reject);
            });
          } catch (reason) { fail(reason instanceof Error ? reason : new Error('The image could not be placed.')); }
        };
        if (signal.aborted) { abort(); return; }
        dom.classList.add('is-media-placement-target'); signal.addEventListener('abort', abort, { once: true });
        if (mode === 'drag') { dom.addEventListener('drop', choose, true); dom.addEventListener('dragover', over, true); document.addEventListener('dragend', endDrag, true); }
        else dom.addEventListener('pointerup', choose, true);
      });
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
