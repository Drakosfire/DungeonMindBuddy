import {useEffect,useRef,useState,type ReactNode} from 'react';
import type {BuildProposalRecord} from '../api/buildDocumentProposalApi';
import {proposalReview,type BuildProposalReview} from '../api/buildProposalReviewApi';
import type {BuildComposeBridge,CapturedBuildInsertion} from './buildComposeBridge';
import {buildProposalMarkdown} from './buildProposalMarkdown';
import {SurfacePageProposal,SurfaceProposalReview} from '../surface/SurfacePageProposal';

export function BuildPageProposal({record,bridge,sourceKey,requestKey,onStatus,onComplete,inspector}: {
  record:BuildProposalRecord;bridge:BuildComposeBridge;sourceKey:string;requestKey:number;
  inspector:ReactNode;onStatus:(text:string)=>void;onComplete:(state:'applied'|'discarded')=>void;
}) {
  const [review,setReview]=useState<BuildProposalReview|null>(null);
  const [placement,setPlacement]=useState<CapturedBuildInsertion|null>(null);
  const [text,setText]=useState('');const [error,setError]=useState<string|null>(null);
  const [inspect,setInspect]=useState(false);const [choosing,setChoosing]=useState(false);
  const [conflict,setConflict]=useState(false);const [busy,setBusy]=useState(false);
  const active=useRef(true);const running=useRef<number|null>(null);const epoch=useRef(0);
  const callbacks=useRef({onStatus,onComplete});callbacks.current={onStatus,onComplete};
  const world=record.reservation.basis.world_id;
  function basisFor(saved:BuildProposalReview){return saved.placement?.basis??record.reservation.basis;}
  const picker=useRef<AbortController|null>(null);
  const cacheKey=`dmb:proposal-review-draft:v1:${world}:${record.action_id}`;
  function cache(markdown:string,revision:number){
    try{sessionStorage.setItem(cacheKey,JSON.stringify({reservation:record.request_fingerprint,revision,markdown}));}
    catch{setError('This browser could not retain the unsaved suggestion. Save before reloading.');}
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
          clearCache();callbacks.current.onStatus(saved.state==='discarded'?'Suggestion discarded':'Added to page');return;
        }
        callbacks.current.onStatus(saved.state==='applying'?'Check insertion':'Review suggestion on page');
        if(saved.state==='editing'){
          try{
            const raw=sessionStorage.getItem(cacheKey);const local=raw?JSON.parse(raw):null;
            if(local?.reservation===record.request_fingerprint&&typeof local.markdown==='string'){
              setText(local.markdown);setConflict(local.revision!==saved.revision&&local.markdown!==saved.markdown);
            }
          }catch{setError('The local suggestion could not be read. The saved review remains available.');}
          const captured=await bridge.restore({...basisFor(saved),caret:saved.placement_caret});
          if(active.current&&epoch.current===current)setPlacement(captured);
        }
      }catch(reason){if(active.current&&epoch.current===current)setError(reason instanceof Error?reason.message:'Suggestion unavailable');}
    })();
    return()=>{active.current=false;epoch.current++;picker.current?.abort();};
  },[world,record.action_id,record.request_fingerprint,bridge,sourceKey,requestKey]);
  function current(start:number){return active.current&&epoch.current===start;}
  async function checkSaved(start:number){
    const checked=await proposalReview(world,record.action_id);
    if(checked.reservation_sha256!==record.request_fingerprint)throw new Error('The saved suggestion has a different page basis.');
    if(!current(start))return;
    if(checked.state==='editing'&&review&&checked.revision!==review.revision&&checked.markdown!==text)setConflict(true);
    setReview(checked);
    if(checked.state==='editing'){
      setPlacement(null);
      const captured=await bridge.restore({...basisFor(checked),caret:checked.placement_caret});
      if(current(start))setPlacement(captured);
    }
    if(checked.state==='applying')callbacks.current.onStatus('Check insertion');
    if(checked.state==='applied'||checked.state==='discarded'){
      setPlacement(null);clearCache();callbacks.current.onStatus(checked.state==='applied'?'Added to page':'Suggestion discarded');
      callbacks.current.onComplete(checked.state);
    }
  }
  async function transact(work:(saved:BuildProposalReview,start:number)=>Promise<void>){
    if(!review||running.current===epoch.current||conflict)return;
    const start=epoch.current;running.current=start;setBusy(true);setError(null);
    try{
      if(!navigator.locks)throw new Error('This browser cannot coordinate safe suggestion writes between tabs. Your work is retained.');
      await navigator.locks.request(`dmb:proposal-review:${world}:${record.action_id}`,async()=>{
        if(!current(start))return;
        const latest=await proposalReview(world,record.action_id);
        if(!current(start))return;
        if(latest.revision!==review.revision){await checkSaved(start);throw new Error('This suggestion changed in another tab. Review its current placement before continuing.');}
        await work(latest,start);
      });
    }catch(reason){if(current(start)){
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
    await bridge.saveProposal(basisFor(saved),saved.apply!.after_editor_sha256,saved.apply!.after_draft_sha256);
    if(!current(start))return;
    const result=await proposalReview(world,record.action_id,{operation:'confirm',expected_revision:saved.revision,apply_id:saved.apply!.apply_id});
    // Acknowledgment is safe even if navigation occurred after the exact local transaction.
    if(current(start)){setReview(result);setPlacement(null);clearCache();callbacks.current.onStatus('Saved to page');callbacks.current.onComplete('applied');}
  }
  function keep(){void transact(async(saved,start)=>{
    if(saved.state!=='editing')return;
    const captured=await bridge.restore({...basisFor(saved),caret:saved.placement_caret});
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
    const state=await bridge.inspectProposal({...basisFor(saved),caret:saved.placement_caret},saved.apply.after_editor_sha256,saved.apply.after_draft_sha256);
    if(!current(start))return;
    if(state==='changed')throw new Error('The current page differs from the earlier insertion snapshots. Its outcome is unresolved. Review the retained text before choosing a new position.');
    if(state==='before'){
      const captured=await bridge.restore({...basisFor(saved),caret:saved.placement_caret});
      const prepared=await bridge.prepareProposal(captured,saved.markdown);
      if(!current(start))return;
      if(prepared.afterEditorSha256!==saved.apply.after_editor_sha256||prepared.afterDraftSha256!==saved.apply.after_draft_sha256)
        throw new Error('The prepared insertion differs from its saved receipt. Nothing was inserted.');
      bridge.applyPrepared(prepared);
    }
    await confirm(saved,start);
  });}
  function move(position:number){void transact(async(saved,start)=>{
    if(saved.state!=='editing')return;
    // Validate the chosen position against the same original page before persisting it.
    await bridge.restore({...basisFor(saved),caret:position});
    if(!current(start))return;
    saved=await save(saved,text);
    if(!current(start))return;
    const result=await proposalReview(world,record.action_id,{operation:'move',expected_revision:saved.revision,placement_caret:position});
    if(!current(start))return;
    const captured=await bridge.restore({...basisFor(result),caret:result.placement_caret});
    if(current(start)){setReview(result);setPlacement(captured);clearCache();}
  });}
  function replacePlacement(replaceSelection=false){void transact(async(saved,start)=>{
    if(!['editing','applying'].includes(saved.state))return;
    if(saved.state==='applying'&&saved.apply){
      const state=await bridge.inspectProposal({...basisFor(saved),caret:saved.placement_caret},saved.apply.after_editor_sha256,saved.apply.after_draft_sha256);
      if(!current(start))return;
      if(state==='after'){await confirm(saved,start);return;}
      if(state==='before')throw new Error('The original placement is still current. Check insertion to resume it.');
    }
    if(saved.state==='editing'){
      saved=await save(saved,buildProposalMarkdown(text).markdown);
      if(!current(start))return;
      setReview(saved);
    }
    const controller=new AbortController();picker.current=controller;setChoosing(true);
    try{
      const captured=replaceSelection?await bridge.capture():await bridge.pickInsertion?.({signal:controller.signal,mode:'click',assetId:record.action_id});
      if(!current(start))return;
      if(!captured||replaceSelection&&!captured.basis.selection)throw new Error('Select the exact passage to replace, then choose Replace selected text.');
      if(captured.basis.world_id!==world||captured.basis.document_id!==record.reservation.basis.document_id)
        throw new Error('Open the original page before choosing a new position.');
      // Restore verifies the complete live draft again after the placement gesture.
      await bridge.restore(captured.basis);
      if(!current(start))return;
      const next=await proposalReview(world,record.action_id,{operation:'replace_placement',expected_revision:saved.revision,
        placement:{command_id:crypto.randomUUID(),conversation_id:record.reservation.conversation_id,
          expected_pointer_revision:record.reservation.expected_pointer_revision,basis:captured.basis,draft_markdown:captured.draftMarkdown}});
      if(!current(start))return;
      const restored=await bridge.restore({...basisFor(next),caret:next.placement_caret});
      if(current(start)){setReview(next);setText(next.markdown);setPlacement(restored);setError(null);clearCache();callbacks.current.onStatus('Review suggestion on page');}
    }finally{if(picker.current===controller)picker.current=null;if(current(start))setChoosing(false);}
  });}
  const replacementControls=<>
    <p>The earlier attempt stays in the trace. Choosing a new position does not remove any text already on the page.</p>
    <button type="button" disabled={busy} onClick={()=>replacePlacement()}>Choose a new position</button>
    <button type="button" disabled={busy} onClick={()=>replacePlacement(true)}>Replace selected text</button>
    {choosing?<p role="status">Click a position on the page. Escape cancels.</p>:null}
  </>;
  const controls=<>
    {review&&basisFor(review).selection ? <>
      <p role="note">Replaces your selected passage when you Save.</p>
      <details><summary>Original passage</summary><blockquote>{review&&basisFor(review).selection?.text}</blockquote></details>
    </> : null}
    {error?<button type="button" disabled={busy} onClick={()=>{void transact(async(_saved,start)=>{await checkSaved(start);});}}>Check saved suggestion</button>:null}
    {conflict?<div role="alert">This suggestion changed elsewhere. Your local edits are retained.
      <button type="button" onClick={()=>{setText(review!.markdown);setConflict(false);clearCache();}}>Use saved suggestion</button>
      <button type="button" onClick={()=>{setConflict(false);cache(text,review!.revision);}}>Review my local copy</button>
    </div>:null}
    <SurfaceProposalReview markdown={text} onChange={value=>{setText(value);cache(value,review!.revision);}}
      busy={busy||conflict} error={error}
      onSave={keep} onDiscard={()=>{void transact(async(saved,start)=>{
        const result=await proposalReview(world,record.action_id,{operation:'discard',expected_revision:saved.revision});
        if(current(start)){setReview(result);setPlacement(null);clearCache();callbacks.current.onStatus('Suggestion discarded');}
      });}}/>
    <details onToggle={event=>setInspect(event.currentTarget.open)}><summary>Debug</summary>{inspect?<>
      {record.proposal?.assumptions.length?<><strong>Creative assumptions</strong><ul>{record.proposal.assumptions.map((value,index)=><li key={index}>{value}</li>)}</ul></>:null}
      {inspector}
    </>:null}</details>
  </>;
  if(review?.state==='applied'||review?.state==='discarded')return null;
  if(review?.state==='applying')return <section className="surface-proposal-review" aria-label="Check suggestion insertion">
    <p>Check that this insertion is saved. Your working copy is retained; the page is checked before anything is inserted again.</p>
    <details><summary>Retained suggestion</summary><blockquote>{review.markdown}</blockquote></details>
    {replacementControls}
    <button type="button" disabled={busy} onClick={recover}>Check insertion</button>{error?<p role="alert">{error}</p>:null}
  </section>;
  if(placement&&review?.state==='editing')return <SurfacePageProposal editor={placement.editor} position={placement.basis.caret}
    editorJson={placement.editorJson} placementId={record.action_id} onMove={basisFor(review).selection ? undefined : move} busy={busy||conflict} revealKey={requestKey} onStale={()=>{if(running.current!==epoch.current){setPlacement(null);setError('The page changed. The saved suggestion is retained; request a new placement.');}}}>{controls}</SurfacePageProposal>;
  return error?<section aria-label="Suggestion placement unavailable" role="status"><p>{error}</p><p>The saved suggestion is retained.</p><blockquote>{text}</blockquote>{review&&replacementControls}</section>:null;
}
