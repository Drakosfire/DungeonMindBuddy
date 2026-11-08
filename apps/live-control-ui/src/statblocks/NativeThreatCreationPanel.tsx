import {useEffect,useRef,useState} from 'react';
import {prepareNativeThreat,confirmNativeThreat,getNativeThreat,LiveApiError} from '../api/liveApi';
import {verifyNativeThreatReply,type PreparedNativeThreat,type PublishedNativeThreat} from '../api/nativeThreatCreation';
import type {ThreatDraftV2} from '../api/types';

export function NativeThreatCreationPanel({draft}:{draft:ThreatDraftV2}) {
  return <Creation key={JSON.stringify([draft.world_id,draft.draft_id])} draft={draft}/>;
}
function Creation({draft}:{draft:ThreatDraftV2}) {
  const key=`dmb.nativeThreat.review:${draft.world_id}:${draft.draft_id}`;
  const [initial]=useState(()=>{try{return {raw:localStorage.getItem(key),error:''};}catch{return {raw:null,error:'Browser recovery is unavailable. Keep your draft and try another browser.'};}});
  const [raw,setRaw]=useState<string|null>(initial.raw),[packet,setPacket]=useState<PreparedNativeThreat|null>(null);
  const [created,setCreated]=useState<PublishedNativeThreat|null>(null),[ready,setReady]=useState(!initial.raw&&!initial.error);
  const [busy,setBusy]=useState(false),[error,setError]=useState(initial.error),[message,setMessage]=useState(''),[conflict,setConflict]=useState(false);
  const live=useRef(true),flight=useRef(false);
  useEffect(()=>{
    live.current=true;
    if(initial.raw)void (async()=>{try{
      const value=await verifyNativeThreatReply(JSON.parse(initial.raw!),draft.world_id,draft.draft_id);
      if(value.state!=='prepared')throw new Error('The retained review has an unexpected state.');
      if(live.current){setPacket(value);setReady(true);}
    }catch(e){if(live.current)setError(String(e));}})();
    return()=>{live.current=false;};
  },[]);
  async function store(expected:string|null,next:string|null) {
    if(!navigator.locks)throw new Error('This browser cannot safely retain a native creature review.');
    await navigator.locks.request(key,()=>{
      if(localStorage.getItem(key)!==expected)throw new Error('Another view retained a different review. Reload before continuing.');
      if(next===null)localStorage.removeItem(key);else localStorage.setItem(key,next);
    });
  }
  async function run(action:'prepare'|'confirm'|'status') {
    if(flight.current||!ready)return;
    flight.current=true;setBusy(true);setError('');setMessage('');
    const captured=packet,expected=raw;
    try {
      const result=action==='prepare'?await prepareNativeThreat(draft.draft_id,draft.world_id,draft.version)
        :action==='confirm'&&captured?await confirmNativeThreat(captured):await getNativeThreat(draft.draft_id,draft.world_id);
      if(result?.state==='published'){
        // A completed old-scope action may settle only its own retained packet;
        // it never changes the next draft's UI or another tab's recovery record.
        if(expected!==null)await store(expected,null);
        if(live.current){setCreated(result);setPacket(null);setRaw(null);setConflict(false);}
      }else if(result?.state==='prepared'){
        if(!live.current)return; // Source admission alone creates no creature.
        const next=JSON.stringify(result);await store(expected,next);
        if(live.current){setPacket(result);setRaw(next);setConflict(false);}
      }else if(live.current)setMessage('No native creature has been created for this draft yet.');
    }catch(e){if(live.current){setError(String(e));setConflict(e instanceof LiveApiError&&e.status===409);}}
    finally{flight.current=false;if(live.current)setBusy(false);}
  }
  return <section className="statblock-section" aria-label="Create World creature">
    <h3>Create a proposed creature in the World Graph</h3>
    <p>Review the saved concept before creating its identity. It remains proposed material, not a played event.</p>
    {created?<p role="status">Creature created in the World Graph. Load creatures under “Associate saved mechanics” and choose this creature to connect its statblock.</p>:<>
      {!packet&&<button type="button" disabled={busy||!ready} onClick={()=>void run('prepare')}>Review creature creation</button>}
      {packet&&<>
        <h4>{packet.review.label}</h4>
        <blockquote style={{whiteSpace:'pre-wrap'}}>{packet.source_text}</blockquote>
        <button type="button" disabled={busy} onClick={()=>void run('confirm')}>{error?'Recover same creation':'Create proposed creature'}</button>
        {conflict&&<button type="button" disabled={busy} onClick={()=>void run('prepare')}>Prepare a new review</button>}
      </>}
      <button type="button" disabled={busy||!ready} onClick={()=>void run('status')}>Check existing creature</button>
    </>}
    {busy&&<p role="status">{packet?'Checking the reviewed creature…':'Preparing the creature review…'}</p>}
    {message&&<p role="status">{message}</p>}
    {error&&<p role="alert">{error}</p>}
  </section>;
}
