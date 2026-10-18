import { useEffect, useRef, useState } from 'react';
import { authenticatedApiFetch } from '../api/liveApi';
import type { BuildComposeBridge, CapturedBuildInsertion } from '../buildSurface/buildComposeBridge';
import type { BuildProposalBasis } from '../api/buildDocumentProposalApi';
import { MediaImageWizard, type GeneratedMediaImage } from './MediaImageWizard';
import { mediaMarkdown } from './mediaReferences';

export type PreparedImage = {schema_version:'dmb_build_image_preparation_v2';action_id:string;prompt:string;alt:string;purpose?:'illustration'|'map'|null;revision:number;
  asset_id:string|null;created_at:string;after_turn_sequence:number;reservation:{origin?:{durable_turn_id:string}|null;conversation_id:string;expected_pointer_revision:number;basis:BuildProposalBasis}};
async function mediaRequest(path: string, body?: unknown, signal?: AbortSignal) {
  const {response} = await authenticatedApiFetch('/api/live/media/images/'+path,
    body ? {method:'POST',body:JSON.stringify(body),signal} : {signal});
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The image action is unavailable.');
  return result;
}
export async function listPreparedImages(world: string, conversation: string, signal?: AbortSignal): Promise<PreparedImage[]> {
  return (await mediaRequest(`preparations/list?world_id=${encodeURIComponent(world)}&conversation_id=${encodeURIComponent(conversation)}`, undefined, signal)).items;
}
export function PreparedBuildImage({record,bridge,active}: {record:PreparedImage;bridge:BuildComposeBridge|null;active:boolean}) {
  const [open,setOpen] = useState(false);
  const [error,setError] = useState('');
  const [inserted,setInserted] = useState(false);
  const [prepared,setPrepared] = useState(record);
  const captured = useRef<CapturedBuildInsertion|null>(null);
  const busy = useRef(false);
  const studioEpoch = useRef(0);
  const current = useRef({record,bridge,active}); current.current={record,bridge,active};
  const mounted = useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  async function showStudio() {
    const start=current.current;
    if (!start.bridge || !start.active || busy.current) return;
    setError('');
    try {
      const capture=await start.bridge.capture();
      const expected=start.record.reservation.basis;
      if (capture.basis.world_id!==expected.world_id || capture.basis.document_id!==expected.document_id
        || capture.basis.registry_revision!==expected.registry_revision || capture.basis.content_sha256!==expected.content_sha256) throw new Error('Open the page used for this image direction, or ask for a new image here.');
      const fresh=await mediaRequest('preparations/'+start.record.action_id) as PreparedImage;
      if (!mounted.current || current.current.record.action_id!==start.record.action_id || !current.current.active || current.current.bridge!==start.bridge) return;
      if (fresh.reservation.conversation_id!==start.record.reservation.conversation_id || fresh.prompt!==start.record.prompt || fresh.alt!==start.record.alt || (fresh.purpose??null)!==(start.record.purpose??null)) throw new Error('The prepared direction changed. Reopen it.');
      captured.current=capture;setPrepared(fresh);setOpen(true);
    } catch(reason) {if(mounted.current) setError(reason instanceof Error?reason.message:'Image Studio unavailable.');}
  }
  useEffect(()=>{
    const key='dmb-image-studio-opened:'+record.action_id;
    if (active && bridge && Date.now()-Date.parse(record.created_at)<60000 && !sessionStorage.getItem(key)) {
      sessionStorage.setItem(key,'1');void showStudio();
    }
  },[record.action_id,active,bridge]);
  async function insert(image: GeneratedMediaImage, placement: {mode:'click'|'drag';signal:AbortSignal}) {
    const start=current.current;
    if (!start.active || !start.bridge?.pickInsertion || busy.current || inserted) throw new Error('Open the editable page before placing this image.');
    const epoch=studioEpoch.current;
    busy.current=true;
    try {
      const capture=await start.bridge.pickInsertion({...placement,assetId:image.asset_id});
      placement.signal.throwIfAborted();
      const expected=start.record.reservation.basis;
      if(capture.basis.world_id!==expected.world_id || capture.basis.document_id!==expected.document_id || capture.basis.registry_revision!==expected.registry_revision || capture.basis.content_sha256!==expected.content_sha256) throw new Error('Place this image on the page used for its image direction.');
      const asset=await mediaRequest(image.asset_id+'/metadata',undefined,placement.signal);
      if(asset.asset_id!==image.asset_id || asset.state!=='ready') throw new Error('Save this image before inserting it.');
      const selected=await mediaRequest('preparations/'+prepared.action_id+'/asset',{asset_id:image.asset_id,expected_revision:prepared.revision},placement.signal) as PreparedImage;
      setPrepared(selected);
      placement.signal.throwIfAborted();
      if(!mounted.current || studioEpoch.current!==epoch || !current.current.active || current.current.record.action_id!==start.record.action_id || current.current.bridge!==start.bridge) throw new Error('The page changed. Place the image again.');
      start.bridge.insert(capture,mediaMarkdown(asset.asset_id,prepared.alt));
      setInserted(true);setOpen(false);
    } finally {busy.current=false;}
  }
  return <article aria-label="Prepared image" className="build-compose-proposal">
    <p><strong>Image direction ready</strong></p><p>{record.alt}</p>
    <details><summary>Prepared prompt</summary><p>{record.prompt}</p></details>
    {inserted ? <p role="status">Image inserted into your draft. Save the page when ready.</p>
      : <button type="button" disabled={!active || !bridge} onClick={()=>void showStudio()}>Open Image Studio</button>}
    {error&&<p role="alert">{error}</p>}
    {open&&active&&<aside className="build-media-studio"><MediaImageWizard initialPrompt={prepared.prompt} initialPurpose={prepared.purpose??'illustration'} preparationId={prepared.action_id}
      onClose={()=>{studioEpoch.current++;captured.current=null;setOpen(false);}} onChoose={(image,_result,placement)=>insert(image,placement)} /></aside>}
  </article>;
}
