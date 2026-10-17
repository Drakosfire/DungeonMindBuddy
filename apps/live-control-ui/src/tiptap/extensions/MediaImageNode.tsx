import { Node } from '@tiptap/core';
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from '@tiptap/react';
import { Plugin } from '@tiptap/pm/state';
import { mediaDragScroll } from './mediaImageDragScroll';
import './MediaImageNode.css';
import { useEffect, useRef, useState } from 'react';
import { authenticatedApiFetch } from '../../api/liveApi';
import { MEDIA_ASSET_ID, imagePresentation } from '../../media/mediaReferences';

export function MediaImageView({ node, editor, updateAttributes }: NodeViewProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState('Loading image…');
  const id = String(node.attrs.assetId);
  const [editable, setEditable] = useState(editor.isEditable);
  useEffect(() => {
    const sync = () => { setEditable(editor.isEditable && !editor.isDestroyed); if (!editor.isEditable) { resize.current = null; setPreviewWidth(null); } };
    editor.on('update', sync); editor.on('destroy', sync);
    return () => { editor.off('update', sync); editor.off('destroy', sync); };
  }, [editor]);
  const width = Number(node.attrs.width ?? 100);
  const collapsed = node.attrs.collapsed === true;
  const frame = useRef<HTMLElement | null>(null);
  const [previewWidth, setPreviewWidth] = useState<number | null>(null);
  const resize = useRef<{x: number; width: number; parent: number; next: number} | null>(null);
  const title = String(node.attrs.alt || 'Image');
  function finishResize(commit: boolean) {
    const active = resize.current;
    resize.current = null;
    setPreviewWidth(null);
    if (commit && active && editor.isEditable && !editor.isDestroyed) updateAttributes({width: active.next, collapsed});
  }
  useEffect(() => () => { resize.current = null; }, []);
  useEffect(() => {
    let active = true;
    setUrl(null); setStatus('Loading image…');
    if (!MEDIA_ASSET_ID.test(id)) { setStatus('Image unavailable'); return; }
    authenticatedApiFetch(`/api/live/media/images/${id}/metadata`).then(async ({ response }) => {
      if (!response.ok) throw new Error('Unavailable');
      const record = await response.json();
      const delivery = new URL(record.delivery_url);
      if (record.asset_id !== id || record.state !== 'ready' || delivery.protocol !== 'https:' || delivery.hostname !== 'imagedelivery.net') throw new Error('Unavailable');
      if (active) { setUrl(delivery.href); setStatus(''); }
    }).catch(() => { if (active) setStatus('Image unavailable. Open Image Studio to inspect the saved asset.'); });
    return () => { active = false; };
  }, [id]);
  return <NodeViewWrapper as="span" className="document-media-image" contentEditable={false} data-media-asset-id={id}
    ref={frame} style={{width: `${previewWidth ?? width}%`}}>
    <span className="document-media-image__toolbar">
      <span data-drag-handle draggable={editable} className="document-media-image__handle" title="Drag image to move" aria-label="Drag image to move">⠿</span>
      <span className="document-media-image__title" title={title}>{title}</span>
      <button type="button" aria-label={collapsed ? 'Expand image' : 'Collapse image'} aria-expanded={!collapsed}
        onMouseDown={event => event.preventDefault()} onClick={() => { if (editor.isEditable && !editor.isDestroyed) updateAttributes({width, collapsed: !collapsed}); }}
        disabled={!editable}>{collapsed ? 'Expand' : 'Collapse'}</button>
    </span>
    <span className="document-media-image__body" hidden={collapsed}>
      {url ? <img src={url} alt={String(node.attrs.alt)} draggable={false} loading="lazy" onError={() => { setUrl(null); setStatus('Image unavailable'); }} />
        : <span role="status">{status}</span>}
      {editable && <button type="button" className="document-media-image__resize" aria-label="Resize image" title="Drag to resize; arrow keys adjust size" role="slider" aria-valuemin={20} aria-valuemax={100} aria-valuenow={previewWidth ?? width}
        onPointerDown={event => {
          if (event.button !== 0 || !editor.isEditable || editor.isDestroyed) return;
          event.preventDefault(); event.stopPropagation();
          const parent = frame.current?.parentElement?.getBoundingClientRect().width ?? 0;
          if (parent <= 0) return;
          resize.current = {x: event.clientX, width, parent, next: width};
          event.currentTarget.setPointerCapture(event.pointerId);
        }} onPointerMove={event => {
          const active = resize.current;
          if (!active || !editor.isEditable || editor.isDestroyed) { finishResize(false); return; }
          active.next = Math.round(Math.max(20, Math.min(100, active.width + (event.clientX - active.x) / active.parent * 100)));
          setPreviewWidth(active.next);
        }} onPointerUp={() => finishResize(true)} onPointerCancel={() => finishResize(false)} onLostPointerCapture={() => finishResize(false)}
        onDragStart={event => event.preventDefault()}
        onKeyDown={event => {
          if (!editor.isEditable || editor.isDestroyed) return;
          if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
          event.preventDefault(); event.stopPropagation();
          const next = event.key === 'Home' ? 20 : event.key === 'End' ? 100 : Math.max(20, Math.min(100, width + (event.key === 'ArrowLeft' ? -5 : 5)));
          updateAttributes({width: next, collapsed});
        }}>↘</button>}
    </span>
  </NodeViewWrapper>;
}
export const MediaImageNode = Node.create({
  name:'mediaImage', group:'inline', inline:true, atom:true, selectable:true, draggable:true,
  addAttributes() { return {assetId:{default:'',rendered:false},alt:{default:'',rendered:false},width:{default:null,rendered:false},collapsed:{default:null,rendered:false}}; },
  parseHTML() { return [{tag:'span[data-media-asset-id]',getAttrs: element => {
    const id=(element as HTMLElement).dataset.mediaAssetId ?? '';
    const title = (element as HTMLElement).dataset.mediaPresentation;
    const presentation = imagePresentation(title);
    return MEDIA_ASSET_ID.test(id) && (!title || presentation) ? {assetId:id,alt:(element as HTMLElement).dataset.mediaAlt ?? element.querySelector('img')?.alt ?? '',...(presentation ?? {})} : false;
  }}]; },
  renderHTML({node}) { return ['span',{'data-media-asset-id':node.attrs.assetId,'data-media-alt':node.attrs.alt,...(node.attrs.width != null || node.attrs.collapsed != null ? {'data-media-presentation':`dmb-image:v1 width=${node.attrs.width} collapsed=${node.attrs.collapsed}`} : {})},node.attrs.alt]; },
  addProseMirrorPlugins() { return [new Plugin({view: view => {
    const destroy = mediaDragScroll(view.dom);
    return {destroy};
  }})]; },
  addNodeView() { return ReactNodeViewRenderer(MediaImageView); },
});
