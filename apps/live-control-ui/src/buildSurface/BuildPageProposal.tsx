import {useEffect,useRef,useState,type ReactNode} from 'react';
import type {BuildProposalRecord} from '../api/buildDocumentProposalApi';
import {proposalReview,type BuildProposalReview} from '../api/buildProposalReviewApi';
import type {BuildComposeBridge,CapturedBuildInsertion} from './buildComposeBridge';
import {buildProposalMarkdown} from './buildProposalMarkdown';
import {SurfacePageProposal,SurfaceProposalReview} from '../surface/SurfacePageProposal';
import {WorldPlanAgentAnswer} from '../planSurface/components/WorldPlanAgentAnswer';

export function BuildPageProposal({record,bridge,sourceKey,requestKey,onStatus,onComplete,inspector}: {
  record:BuildProposalRecord;bridge:BuildComposeBridge;sourceKey:string;requestKey:number;
  inspector:ReactNode;onStatus:(text:string)=>void;onComplete:(state:'applied'|'discarded')=>void;
}) {
  const [review,setReview]=useState<BuildProposalReview|null>(null);
  const [placement,setPlacement]=useState<CapturedBuildInsertion|null>(null);
  const [text,setText]=useState('');const [error,setError]=useState<string|null>(null);
  const [inspect,setInspect]=useState(false);
  const [conflict,setConflict]=useState(false);const [busy,setBusy]=useState(false);
  const active=useRef(true);const running=useRef<number|null>(null);const epoch=useRef(0);
  const callbacks=useRef({onStatus,onComplete});callbacks.current={onStatus,onComplete};
  const world=record.reservation.basis.world_id;
  const cacheKey=`dmb:proposal-review-draft:v1:${world}:${record.action_id}`;
  function cache(markdown:string,revision:number){
    try{sessionStorage.setItem(cacheKey,JSON.stringify({reservation:record.request_fingerprint,revision,markdown}));}
    catch{setError('This browser could not retain the unsaved suggestion. Save the suggestion before reloading.');}
  }
  function clearCache(){try{sessionStorage.removeItem(cacheKey);}catch{/* The durable review remains authoritative. */}}
  useEffect(()=>{
    active.current=true;const current=++epoch.current;
    setPlacement(null);setReview(null);setError(null);setConflict(false);setBusy(false);
    void (async()=>{
      try{
        const saved=await proposalReview(world,record.action_id,{operation:'open',expected_revision:0});
        if(!active.current||epoch.current!==current)return;
        if(saved.reservation_sha256!==record.request_fingerprint)throw new Error('The saved suggestion has a different page basis.');
        setReview(saved);setText(saved.markdown);
        if(saved.state==='discarded'||saved.state==='applied'){
          clearCache();callbacks.current.onStatus(saved.state==='discarded'?'Suggestion discarded':'Kept on page');return;
        }
        callbacks.current.onStatus(saved.state==='applying'?'Check insertion':'Review suggestion on page');
        if(saved.state==='editing'){
          try{
            const raw=sessionStorage.getItem(cacheKey);const local=raw?JSON.parse(raw):null;
            if(local?.reservation===record.request_fingerprint&&typeof local.markdown==='string'){
              setText(local.markdown);setConflict(local.revision!==saved.revision&&local.markdown!==saved.markdown);
            }
          }catch{setError('The local suggestion draft could not be read. The saved review remains available.');}
          const captured=await bridge.restore(record.reservation.basis);
          if(active.current&&epoch.current===current)setPlacement(captured);
        }
      }catch(reason){if(active.current&&epoch.current===current)setError(reason instanceof Error?reason.message:'Suggestion unavailable');}
    })();
    return()=>{active.current=false;epoch.current++;};
  },[world,record.action_id,record.request_fingerprint,bridge,sourceKey,requestKey]);
  function current(start:number){return active.current&&epoch.current===start;}
  async function checkSaved(start:number){
    const checked=await proposalReview(world,record.action_id);
    if(checked.reservation_sha256!==record.request_fingerprint)throw new Error('The saved suggestion has a different page basis.');
    if(!current(start))return;
    if(checked.state==='editing'&&review&&checked.revision!==review.revision&&checked.markdown!==text)setConflict(true);
    setReview(checked);
    if(checked.state==='applied'||checked.state==='discarded'){
      setPlacement(null);clearCache();callbacks.current.onStatus(checked.state==='applied'?'Kept on page':'Suggestion discarded');
      callbacks.current.onComplete(checked.state);
    }
  }
  async function transact(work:(saved:BuildProposalReview,start:number)=>Promise<void>){
    if(!review||running.current===epoch.current||conflict)return;
    const start=epoch.current;running.current=start;setBusy(true);setError(null);
    try{await work(review,start);}catch(reason){if(current(start)){
      setError(reason instanceof Error?reason.message:'The suggestion needs checking.');
      try{await checkSaved(start);}catch{/* Preserve the exact uncertain review; never repeat its mutation. */}
    }}
    finally{if(running.current===start)running.current=null;if(current(start))setBusy(false);}
  }
  async function save(saved:BuildProposalReview,markdown:string){
    if(saved.markdown===markdown)return saved;
    return proposalReview(world,record.action_id,{operation:'save',expected_revision:saved.revision,markdown});
  }
  async function confirm(saved:BuildProposalReview,start:number){
    const result=await proposalReview(world,record.action_id,{operation:'confirm',expected_revision:saved.revision,apply_id:saved.apply!.apply_id});
    // Acknowledgment is safe even if navigation occurred after the exact local transaction.
    if(current(start)){setReview(result);setPlacement(null);clearCache();callbacks.current.onStatus('Kept on page');callbacks.current.onComplete('applied');}
  }
  function keep(){void transact(async(saved,start)=>{
    if(saved.state!=='editing')return;
    const captured=await bridge.restore(record.reservation.basis);
    const prepared=await bridge.prepareProposal(captured,buildProposalMarkdown(text).markdown);
    if(!current(start))return;
    saved=await save(saved,prepared.markdown);
    if(!current(start))return;
    setReview(saved);setText(saved.markdown);clearCache();
    const pending=await proposalReview(world,record.action_id,{operation:'prepare',expected_revision:saved.revision,
      apply_id:crypto.randomUUID(),after_editor_sha256:prepared.afterEditorSha256,after_draft_sha256:prepared.afterDraftSha256});
    if(!current(start))return;
    setReview(pending);
    bridge.applyPrepared(prepared);
    await confirm(pending,start);
  });}
  function recover(){void transact(async(saved,start)=>{
    if(saved.state!=='applying'||!saved.apply)return;
    const state=await bridge.inspectProposal(record.reservation.basis,saved.apply.after_editor_sha256,saved.apply.after_draft_sha256);
    if(!current(start))return;
    if(state==='changed')throw new Error('The page differs from both insertion snapshots. Nothing was inserted. Keep this review for inspection.');
    if(state==='before'){
      const captured=await bridge.restore(record.reservation.basis);
      const prepared=await bridge.prepareProposal(captured,saved.markdown);
      if(!current(start))return;
      if(prepared.afterEditorSha256!==saved.apply.after_editor_sha256||prepared.afterDraftSha256!==saved.apply.after_draft_sha256)
        throw new Error('The prepared insertion differs from its saved receipt. Nothing was inserted.');
      bridge.applyPrepared(prepared);
    }
    await confirm(saved,start);
  });}
  const controls=<>
    {error?<button type="button" disabled={busy} onClick={()=>{void transact(async(_saved,start)=>{await checkSaved(start);});}}>Check saved suggestion</button>:null}
    {conflict?<div role="alert">This suggestion changed elsewhere. Your local draft is retained.
      <button type="button" onClick={()=>{setText(review!.markdown);setConflict(false);clearCache();}}>Use saved suggestion</button>
      <button type="button" onClick={()=>{setConflict(false);cache(text,review!.revision);}}>Review my local copy</button>
    </div>:null}
    <SurfaceProposalReview markdown={text} onChange={value=>{setText(value);cache(value,review!.revision);}}
      preview={<WorldPlanAgentAnswer answer={text}/>} busy={busy||conflict} error={error}
      onSave={()=>{void transact(async(saved,start)=>{const result=await save(saved,text);if(current(start)){setReview(result);clearCache();}});}}
      onKeep={keep} onDiscard={()=>{void transact(async(saved,start)=>{
        const result=await proposalReview(world,record.action_id,{operation:'discard',expected_revision:saved.revision});
        if(current(start)){setReview(result);setPlacement(null);clearCache();callbacks.current.onStatus('Suggestion discarded');}
      });}}/>
    {record.proposal?.assumptions.length?<details><summary>Creative assumptions</summary><ul>{record.proposal.assumptions.map((value,index)=><li key={index}>{value}</li>)}</ul></details>:null}
    <details onToggle={event=>setInspect(event.currentTarget.open)}><summary>Inspect suggestion</summary>{inspect?inspector:null}</details>
  </>;
  if(review?.state==='applied'||review?.state==='discarded')return null;
  if(review?.state==='applying')return <section className="surface-proposal-review" aria-label="Check suggestion insertion">
    <p>The insertion needs checking. This checks its exact snapshots before changing the page.</p>
    <button type="button" disabled={busy} onClick={recover}>Check insertion</button>{error?<p role="alert">{error}</p>:null}
  </section>;
  if(placement&&review?.state==='editing')return <SurfacePageProposal editor={placement.editor} position={placement.basis.caret}
    editorJson={placement.editorJson} onStale={()=>{if(running.current!==epoch.current){setPlacement(null);setError('The page changed. The saved suggestion is retained; request a new placement.');}}}>{controls}</SurfacePageProposal>;
  return error?<section aria-label="Suggestion placement unavailable" role="status"><p>{error}</p><p>The saved suggestion is retained.</p></section>:null;
}
