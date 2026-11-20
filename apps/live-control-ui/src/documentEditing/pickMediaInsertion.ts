import type { Editor } from '@tiptap/core';
import { MEDIA_ASSET_ID } from '../media/mediaReferences';

type MediaPicker<T>={editor:Editor;assetId:string;signal:AbortSignal;mode:'click'|'drag';isCurrent:()=>boolean;capture:()=>Promise<T>};
/** Existing media wrapper keeps its asset validation and drag contract. */
export function pickMediaInsertion<T>(options:MediaPicker<T>):Promise<T>{
  if(!MEDIA_ASSET_ID.test(options.assetId))return Promise.reject(new Error('Open the editable page before placing this image.'));
  return pickDocumentInsertion({...options,operationId:options.assetId,noun:'image',dragMime:'application/x-dmb-media'});
}
/** A UUID identifies a local picker operation, not an asset or an execution receipt. */
export function pickDocumentInsertion<T>({ editor, operationId, signal, mode, isCurrent, capture,noun,dragMime }: {
  editor:Editor;operationId:string;signal:AbortSignal;mode:'click'|'drag';isCurrent:()=>boolean;capture:()=>Promise<T>;
  noun:'image'|'plan';dragMime:string;
}):Promise<T>{
  if (editor.isDestroyed || !isCurrent() || !/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(operationId)) return Promise.reject(new Error(`Open the editable page before placing this ${noun}.`));
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
    const endDrag = () => fail(new Error(`The ${noun} was not dropped on the page. Try again.`));
    const over = (event: DragEvent) => { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'; };
    const choose = (event: Event) => {
      if (mode === 'drag') { event.preventDefault(); event.stopImmediatePropagation(); }
      try {
        signal.throwIfAborted();
        if (editor.isDestroyed || !isCurrent()) throw new Error(`The page changed. Choose the ${noun} again on its original page.`);
        if (mode === 'drag' && (event as DragEvent).dataTransfer?.getData(dragMime) !== operationId) throw new Error(`Drop the selected saved ${noun}, not a file, link or outside ${noun}.`);
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
      } catch (reason) { fail(reason instanceof Error ? reason : new Error(`The ${noun} could not be placed.`)); }
    };
    if (signal.aborted) { abort(); return; }
    dom.classList.add('is-media-placement-target'); signal.addEventListener('abort', abort, { once: true });
    if (mode === 'drag') { dom.addEventListener('drop', choose, true); dom.addEventListener('dragover', over, true); document.addEventListener('dragend', endDrag, true); }
    else dom.addEventListener('pointerup', choose, true);
  });
}
