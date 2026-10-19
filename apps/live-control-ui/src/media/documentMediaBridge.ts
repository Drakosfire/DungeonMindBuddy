import type { Editor } from '@tiptap/core';
import { admitMarkdownInsertion, insertReviewedMarkdown } from '../documentEditing/markdownInsertion';
import { pickMediaInsertion } from '../documentEditing/pickMediaInsertion';
import { mediaMarkdown, MEDIA_ASSET_ID } from './mediaReferences';

export type DocumentMediaState = { editor: Editor; identity: string; version: string; canEdit: boolean };
export type DocumentMediaCapture = { editor: Editor; identity: string; version: string; caret: number; editorJson: string };
export type DocumentMediaBridge = {
  pickInsertion: (options: { assetId: string; signal: AbortSignal; mode: 'click' | 'drag' }) => Promise<DocumentMediaCapture>;
  insert: (capture: DocumentMediaCapture, assetId: string, alt: string) => void;
};

/** No document/store semantics here: the mounted host owns its writer and version. */
export function createDocumentMediaBridge(getCurrent: () => DocumentMediaState | null): DocumentMediaBridge {
  const applied = new WeakSet<DocumentMediaCapture>();
  function same(start: DocumentMediaState) {
    const now = getCurrent();
    return !!now?.canEdit && !now.editor.isDestroyed && now.editor.isEditable && now.editor === start.editor
      && now.identity === start.identity && now.version === start.version;
  }
  return {
    async pickInsertion(options) {
      const current = getCurrent(); const start = current ? { ...current } : null;
      if (!start || !same(start)) throw new Error('Open the editable document before placing this image.');
      return pickMediaInsertion({ ...options, editor: start.editor, isCurrent: () => same(start), capture: async () => {
        if (!same(start) || !start.editor.state.selection.empty) throw new Error('The document or insertion point changed. Place the image again.');
        return { editor: start.editor, identity: start.identity, version: start.version,
          caret: start.editor.state.selection.from, editorJson: JSON.stringify(start.editor.getJSON()) };
      } });
    },
    insert(capture, assetId, alt) {
      if (applied.has(capture)) throw new Error('This image has already been placed.');
      if (!same({ ...capture, canEdit: true }) || !MEDIA_ASSET_ID.test(assetId)) throw new Error('The document changed. Place the image again.');
      const admitted = admitMarkdownInsertion(mediaMarkdown(assetId, alt));
      insertReviewedMarkdown(capture.editor, capture.caret, admitted.content, capture.editorJson);
      applied.add(capture);
    },
  };
}
