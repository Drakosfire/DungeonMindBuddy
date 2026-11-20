import type { Editor } from '@tiptap/core';
import { Plugin, Selection } from '@tiptap/pm/state';

export const LAYOUT_EDITABILITY_EVENT = 'page-layout-editability';

/** setEditable(..., false) updates PluginViews without emitting a TipTap update. */
export function layoutEditabilityPlugin() {
  return new Plugin({ view: view => {
    let editable = view.editable;
    const notify = () => view.dom.dispatchEvent(new CustomEvent(LAYOUT_EDITABILITY_EVENT, { detail: editable }));
    notify();
    return { update: next => {
      if (editable === next.editable) return;
      editable = next.editable;
      notify();
    } };
  } });
}

export const LAYOUT_CONTROLS_EVENT = 'page-layout-controls';
export type LayoutRequest = { kind: 'pageRow' | 'pageImageText'; id: string; trigger: HTMLButtonElement };

/** Explicit handles preserve an existing text selection inside their object. */
export function layoutHandle(editor: Editor, getPos: () => number | undefined, kind: LayoutRequest['kind']) {
  const button = document.createElement('button');
  button.type = 'button'; button.contentEditable = 'false'; button.className = 'page-layout-handle';
  button.textContent = kind === 'pageRow' ? '⋮ Row' : '⋮ Image';
  button.setAttribute('aria-label', kind === 'pageRow' ? 'Row layout options' : 'Image and text options');
  button.setAttribute('aria-haspopup', 'dialog'); button.setAttribute('aria-expanded', 'false');
  button.addEventListener('pointerdown', event => event.preventDefault());
  button.addEventListener('click', () => {
    if (editor.isDestroyed || !editor.isEditable || !button.isConnected) return;
    const pos = getPos(); const node = typeof pos === 'number' ? editor.state.doc.nodeAt(pos) : null;
    if (typeof pos !== 'number' || node?.type.name !== kind || !node.attrs.id) return;
    const selection = editor.state.selection;
    if (selection.from <= pos || selection.to >= pos + node.nodeSize) {
      editor.view.dispatch(editor.state.tr.setSelection(Selection.near(editor.state.doc.resolve(pos + 1))));
    }
    editor.view.dom.dispatchEvent(new CustomEvent<LayoutRequest>(LAYOUT_CONTROLS_EVENT, {
      detail: { kind, id: node.attrs.id, trigger: button },
    }));
  });
  return button;
}
