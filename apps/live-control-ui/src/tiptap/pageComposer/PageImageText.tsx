import { Node, mergeAttributes, type Editor } from '@tiptap/core';
import { type Node as PMNode } from '@tiptap/pm/model';
import { Selection } from '@tiptap/pm/state';
import { closeHistory } from '@tiptap/pm/history';
import { useEffect, useState } from 'react';
import './PageImageText.css';
import { layoutHandle, LAYOUT_EDITABILITY_EVENT } from './contextualLayout';
import { validateImageTextContent } from './presentation';

export const IMAGE_TEXT_ANCHORS = ['top-left', 'top-center', 'top-right', 'middle-left', 'middle-center', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right'] as const;
export type ImageTextAnchor = typeof IMAGE_TEXT_ANCHORS[number];
export type ImageTextPresentation = { anchor?: ImageTextAnchor; inset?: 'none' | 'small' | 'medium'; backing?: 'none' | 'contrast' };
const isImage = (node: PMNode | null | undefined) => node?.type.name === 'paragraph' && node.childCount === 1 && node.child(0).type.name === 'mediaImage';
const isText = (node: PMNode | null | undefined) => !!node && node.textContent.trim().length > 0 && ['paragraph', 'heading'].includes(node.type.name) && Array.from({ length: node.childCount }, (_, i) => node.child(i)).every(child => child.type.name === 'text' || child.type.name === 'hardBreak');
export function stackAtSelection(editor: Editor) {
  const { $from } = editor.state.selection;
  for (let depth = $from.depth; depth > 0; depth--) {
    if ($from.node(depth).type.name === 'pageImageText') return { node: $from.node(depth), pos: $from.before(depth) };
  }
  const node = editor.state.doc.nodeAt(editor.state.selection.from);
  return node?.type.name === 'pageImageText' ? { node, pos: editor.state.selection.from } : null;
}
export function wrapPageImageText(editor: Editor, dryRun = false): boolean {
  if (editor.isDestroyed || !editor.isEditable || stackAtSelection(editor)) return false;
  const { $from } = editor.state.selection;
  const depth = ['paragraph', 'heading'].includes($from.parent.type.name) ? $from.depth - 1 : $from.depth;
  const parent = $from.node(depth);
  if (!['doc', 'pageSlot'].includes(parent.type.name)) return false;
  const index = $from.index(depth);
  const image = parent.maybeChild(index); const text = parent.maybeChild(index + 1);
  if (!isImage(image) || !isText(text)) return false;
  try { validateImageTextContent([image!.toJSON(), text!.toJSON()]); } catch { return false; }
  if (dryRun) return true;
  const type = editor.schema.nodes.pageImageText;
  if (!type || !image || !text) return false;
  let pos = depth === 0 ? 0 : $from.start(depth);
  for (let i = 0; i < index; i++) pos += parent.child(i).nodeSize;
  const node = type.create({ id: `image-text-${crypto.randomUUID()}`, anchor: 'middle-center', inset: 'small', backing: 'contrast' }, [image, text]);
  const tr = editor.state.tr.replaceWith(pos, pos + image.nodeSize + text.nodeSize, node);
  tr.setSelection(Selection.near(tr.doc.resolve(pos + 1 + image.nodeSize + 1)));
  editor.view.dispatch(closeHistory(tr).scrollIntoView());
  return true;
}
export function unwrapPageImageText(editor: Editor): boolean {
  if (editor.isDestroyed || !editor.isEditable) return false;
  const found = stackAtSelection(editor);
  if (editor.isDestroyed || !found || !editor.isEditable) return false;
  const tr = editor.state.tr.replaceWith(found.pos, found.pos + found.node.nodeSize, found.node.content);
  tr.setSelection(Selection.near(tr.doc.resolve(found.pos + 1)));
  editor.view.dispatch(closeHistory(tr).scrollIntoView()); return true;
}
export function updatePageImageText(editor: Editor, attrs: ImageTextPresentation): boolean {
  if (editor.isDestroyed || !editor.isEditable) return false;
  const found = stackAtSelection(editor);
  if (editor.isDestroyed || !editor.isEditable || !found || Object.keys(attrs).some(key => !['anchor', 'inset', 'backing'].includes(key))) return false;
  const next = { ...found.node.attrs, ...attrs };
  if (typeof next.anchor !== 'string' || typeof next.inset !== 'string' || typeof next.backing !== 'string' || !IMAGE_TEXT_ANCHORS.includes(next.anchor) || !['none', 'small', 'medium'].includes(next.inset) || !['none', 'contrast'].includes(next.backing)) return false;
  if (JSON.stringify(next) === JSON.stringify(found.node.attrs)) return true;
  editor.view.dispatch(closeHistory(editor.state.tr.setNodeMarkup(found.pos, undefined, next))); return true;
}

export const PageImageText = Node.create({
  name: 'pageImageText', group: 'block', content: 'paragraph (paragraph|heading)', defining: true, isolating: true,
  addAttributes() { return { id: { default: null }, anchor: { default: 'middle-center' }, inset: { default: 'small' }, backing: { default: 'contrast' } }; },
  parseHTML() { return [{ tag: 'div[data-page-image-text]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes(HTMLAttributes, { 'data-page-image-text': '', class: 'page-image-text' }), 0]; },
  addNodeView() {
    return ({ node: initial, editor, getPos, view }) => {
      let node = initial;
      const dom = document.createElement('div'); dom.className = 'page-image-text'; dom.dataset.pageImageText = ''; dom.dataset.overlay = 'false';
      const contentDOM = document.createElement('div'); contentDOM.className = 'page-image-text__content'; dom.append(contentDOM);
      const handle = layoutHandle(editor, getPos, 'pageImageText'); dom.append(handle);
      handle.hidden = !editor.options.editable;
      const editorDOM = view.dom;
      const editableChanged = (event: Event) => { handle.hidden = !(event as CustomEvent<boolean>).detail; };
      editorDOM.addEventListener(LAYOUT_EDITABILITY_EVENT, editableChanged);
      let frame: number | null = null; let destroyed = false;
      let observedImage: HTMLImageElement | null = null; let observedText: HTMLElement | null = null;
      const set = (key: string, value: string) => { if (dom.style.getPropertyValue(key) !== value) dom.style.setProperty(key, value); };
      const measure = () => {
        frame = null; if (destroyed) return;
        handle.hidden = editor.isDestroyed || !editor.isEditable;
        const image = contentDOM.children[0]?.querySelector('img') as HTMLImageElement | null;
        const text = contentDOM.children[1] as HTMLElement | undefined;
        if (image !== observedImage) { if (observedImage) observer?.unobserve(observedImage); observedImage = image; if (image) observer?.observe(image); }
        if (text !== observedText) { if (observedText) observer?.unobserve(observedText); observedText = text ?? null; if (text) observer?.observe(text); }
        dom.dataset.backing = node.attrs.backing; dom.dataset.anchor = node.attrs.anchor;
        const inset = node.attrs.inset === 'medium' ? 16 : node.attrs.inset === 'small' ? 8 : 0;
        const rect = image?.getBoundingClientRect(); const origin = contentDOM.getBoundingClientRect();
        if (!rect || !text || rect.width <= 0 || rect.height <= 0 || !isImage(node.child(0)) || !isText(node.child(1))) { dom.dataset.overlay = 'false'; return; }
        const width = Math.max(0, rect.width - inset * 2);
        set('--image-text-width', `${width}px`);
        const height = text.getBoundingClientRect().height;
        const available = rect.height - inset * 2;
        // Never shrink letters or crop. A long title and a narrow image use the
        // same editable text below the image, returning to overlay when it fits.
        const fits = width >= 180 && height > 0 && height <= available && text.scrollWidth <= width + 1;
        dom.dataset.overlay = fits ? 'true' : 'false';
        if (!fits) return;
        const [vertical, horizontal] = String(node.attrs.anchor).split('-');
        const x = rect.left - origin.left + inset;
        const y = rect.top - origin.top + inset + (vertical === 'middle' ? (available - height) / 2 : vertical === 'bottom' ? available - height : 0);
        set('--image-text-x', `${x}px`); set('--image-text-y', `${y}px`);
        set('--image-text-align', horizontal === 'left' ? 'left' : horizontal === 'right' ? 'right' : 'center');
      };
      const schedule = () => { if (!destroyed && frame === null) frame = requestAnimationFrame(measure); };
      const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(schedule);
      observer?.observe(contentDOM);
      contentDOM.addEventListener('load', schedule, true);
      // React managed images arrive asynchronously; observe child insertion but
      // never consume or suppress the editor's own content mutations.
      const mutations = new MutationObserver(schedule); mutations.observe(contentDOM, { childList: true, subtree: true, characterData: true, attributes: true });
      schedule();
      return { dom, contentDOM,
        update(next) { if (next.type !== node.type) return false; node = next; schedule(); return true; },
        stopEvent(event) { return handle.contains(event.target as globalThis.Node); },
        ignoreMutation(mutation) { return handle.contains(mutation.target) || (mutation.type === 'attributes' && mutation.target === dom); },
        destroy() { editorDOM.removeEventListener(LAYOUT_EDITABILITY_EVENT, editableChanged); destroyed = true; if (frame !== null) cancelAnimationFrame(frame); observer?.disconnect(); mutations.disconnect(); contentDOM.removeEventListener('load', schedule, true); },
      };
    };
  },
});
export const PAGE_IMAGE_TEXT_EXTENSIONS = [PageImageText];
export function PageImageTextTools({ editor }: { editor: Editor | null }) {
  const [, refresh] = useState(0);
  useEffect(() => {
    if (!editor) return; const update = () => refresh(value => value + 1);
    editor.on('transaction', update); editor.on('selectionUpdate', update);
    return () => { editor.off('transaction', update); editor.off('selectionUpdate', update); };
  }, [editor]);
  const found = editor && !editor.isDestroyed ? stackAtSelection(editor) : null;
  const current = () => editor && !editor.isDestroyed && editor.isEditable && found
    && stackAtSelection(editor)?.node.attrs.id === found.node.attrs.id;
  return <div className="page-image-text-tools" role="group" aria-label="Image and text layout">
    <button type="button" disabled={!editor?.isEditable || !found} onClick={() => current() && editor && unwrapPageImageText(editor)}>Unstack image and text</button>
    <details><summary>Image text settings</summary><label>Text anchor <select disabled={!editor?.isEditable || !found} value={found?.node.attrs.anchor ?? 'middle-center'} onChange={event => current() && editor && updatePageImageText(editor, { anchor: event.target.value as ImageTextAnchor })}>
      {IMAGE_TEXT_ANCHORS.map(anchor => <option key={anchor} value={anchor}>{anchor.replace('-', ' ')}</option>)}
    </select></label>
    <label>Inset <select disabled={!editor?.isEditable || !found} value={found?.node.attrs.inset ?? 'small'} onChange={event => current() && editor && updatePageImageText(editor, { inset: event.target.value as 'none' | 'small' | 'medium' })}>
      <option value="none">None</option><option value="small">Small</option><option value="medium">Medium</option>
    </select></label>
    <label>Text backing <select disabled={!editor?.isEditable || !found} value={found?.node.attrs.backing ?? 'contrast'} onChange={event => current() && editor && updatePageImageText(editor, { backing: event.target.value as 'none' | 'contrast' })}>
      <option value="none">None</option><option value="contrast">Contrast</option>
    </select></label></details>
  </div>;
}
