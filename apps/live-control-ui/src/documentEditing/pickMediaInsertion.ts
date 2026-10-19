import type { Editor } from '@tiptap/core';
import { MEDIA_ASSET_ID } from '../media/mediaReferences';

/** Pick a real editor position; the owner retains capture and write authority. */
export function pickMediaInsertion<T>({ editor, assetId, signal, mode, isCurrent, capture }: {
  editor: Editor; assetId: string; signal: AbortSignal; mode: 'click' | 'drag';
  isCurrent: () => boolean; capture: () => Promise<T>;
}): Promise<T> {
  if (editor.isDestroyed || !isCurrent() || !MEDIA_ASSET_ID.test(assetId)) return Promise.reject(new Error('Open the editable page before placing this image.'));
  const dom = editor.view.dom;
  return new Promise<T>((resolve, reject) => {
    const cleanup = () => {
      dom.classList.remove('is-media-placement-target');
      dom.removeEventListener('pointerup', choose, true); dom.removeEventListener('drop', choose, true);
      dom.removeEventListener('dragover', over, true); document.removeEventListener('dragend', endDrag, true);
      signal.removeEventListener('abort', abort);
    };
    const fail = (reason: Error) => { cleanup(); reject(reason); };
    const abort = () => fail(new DOMException('Placement cancelled.', 'AbortError'));
    const endDrag = () => fail(new Error('The image was not dropped on the page. Try again.'));
    const over = (event: DragEvent) => { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'; };
    const choose = (event: Event) => {
      if (mode === 'drag') { event.preventDefault(); event.stopImmediatePropagation(); }
      try {
        signal.throwIfAborted();
        if (editor.isDestroyed || !isCurrent()) throw new Error('The page changed. Choose the image again on its original page.');
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
          if (editor.isDestroyed || !isCurrent() || JSON.stringify(editor.getJSON()) !== expected || !editor.state.selection.empty || editor.state.selection.from !== caret) {
            reject(new Error('The page changed before placement. Choose a position again.')); return;
          }
          capture().then(value => {
            if (signal.aborted) reject(new DOMException('Placement cancelled.', 'AbortError'));
            else resolve(value);
          }, reject);
        });
      } catch (reason) { fail(reason instanceof Error ? reason : new Error('The image could not be placed.')); }
    };
    if (signal.aborted) { abort(); return; }
    dom.classList.add('is-media-placement-target'); signal.addEventListener('abort', abort, { once: true });
    if (mode === 'drag') { dom.addEventListener('drop', choose, true); dom.addEventListener('dragover', over, true); document.addEventListener('dragend', endDrag, true); }
    else dom.addEventListener('pointerup', choose, true);
  });
}
