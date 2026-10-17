import { Node } from '@tiptap/core';
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from '@tiptap/react';
import { useEffect, useState } from 'react';
import { authenticatedApiFetch } from '../../api/liveApi';
import { MEDIA_ASSET_ID } from '../../media/mediaReferences';

function MediaImageView({ node }: NodeViewProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState('Loading image…');
  const id = String(node.attrs.assetId);
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
    style={{display:'inline-block',width:'100%',maxWidth:'100%'}}>
    <span data-drag-handle className="document-media-image__handle" title="Drag image to move" aria-label="Drag image to move">⠿</span>
    {url ? <img src={url} alt={String(node.attrs.alt)} loading="lazy" onError={() => { setUrl(null); setStatus('Image unavailable'); }} style={{display:'block',maxWidth:'100%',height:'auto',borderRadius:8}} />
      : <span role="status">{status}</span>}
  </NodeViewWrapper>;
}
export const MediaImageNode = Node.create({
  name:'mediaImage', group:'inline', inline:true, atom:true, selectable:true, draggable:true,
  addAttributes() { return {assetId:{default:'',rendered:false},alt:{default:'',rendered:false}}; },
  parseHTML() { return [{tag:'span[data-media-asset-id]',getAttrs: element => {
    const id=(element as HTMLElement).dataset.mediaAssetId ?? '';
    return MEDIA_ASSET_ID.test(id) ? {assetId:id,alt:element.querySelector('img')?.alt ?? ''} : false;
  }}]; },
  renderHTML({node}) { return ['span',{'data-media-asset-id':node.attrs.assetId},node.attrs.alt]; },
  addNodeView() { return ReactNodeViewRenderer(MediaImageView); },
});
