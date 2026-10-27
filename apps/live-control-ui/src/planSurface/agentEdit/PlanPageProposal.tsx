import {useEffect,useRef,useState} from 'react';
import {SurfacePageProposal,SurfaceProposalReview} from '../../surface/SurfacePageProposal';
import {commandPlanAuthoringReview,readPlanAuthoringReview,PlanReviewRequestError,
  type PlanAuthoredProposal,type PlanAuthoringReview,type PlanReviewCommand,type PlanReviewOperation} from '../../api/planAuthoringReviewApi';
import type {CapturedPlanAuthoringTarget,ExpectedWorldPlanEditAgentBinding,PlanAuthoringIdentity,
  WorldPlanEditAgentBinding,WorldPlanEditBridge} from './planAgentEditProposal';

/** The same generated Plan action is shown on the page; chat owns only recovery controls. */
export function PlanPageProposal({proposal,bridge,identity,expectedBinding,getBinding,disabled,onVisible}: {
  proposal:PlanAuthoredProposal;bridge:WorldPlanEditBridge;identity:PlanAuthoringIdentity;
  expectedBinding:ExpectedWorldPlanEditAgentBinding;getBinding:()=>WorldPlanEditAgentBinding;
  disabled:boolean;onVisible:()=>void;
}) {
  const world=proposal.capture.world_id,action=proposal.origin.action_id;
  const scope=JSON.stringify([world,action,proposal.capture.document_id,identity.conversationId,identity.pointerRevision]);
  const current=useRef({scope,disabled,bridge,identity,expectedBinding,getBinding,onVisible});
  current.current={scope,disabled,bridge,identity,expectedBinding,getBinding,onVisible};
  const [review,setReview]=useState<PlanAuthoringReview|null>(null);
  const [text,setText]=useState(proposal.replacement_markdown);
  const [placement,setPlacement]=useState<CapturedPlanAuthoringTarget|null>(null);
  const [error,setError]=useState<string|null>(null),[busy,setBusy]=useState(false);
  const [pending,setPending]=useState<PlanReviewCommand|null>(null),[conflict,setConflict]=useState(false);
  const [inspected,setInspected]=useState(false);
  const generation=useRef(0),running=useRef(false),textRef=useRef(text);textRef.current=text;
  const key=`dmb:plan-proposal-review:v1:${encodeURIComponent(world)}:${action}`;
  const commandKey=`${key}:command`;
  function alive(epoch:number){return generation.current===epoch&&current.current.scope===scope;}
  function cache(markdown:string,revision:number){
    const bytes=JSON.stringify({action,origin:proposal.origin,revision,markdown});
    sessionStorage.setItem(key,bytes);
    if(sessionStorage.getItem(key)!==bytes)throw new Error('The local suggestion could not be retained. Its saved review is still available.');
  }
  function pendingCommand(){
    const raw=sessionStorage.getItem(commandKey);if(!raw)return null;
    const saved=JSON.parse(raw);
    if(saved.world!==world||saved.action!==action||!saved.command||typeof saved.command.command_id!=='string')
      throw new Error('The retained suggestion operation needs inspection. It was not resent.');
    return saved.command as PlanReviewCommand;
  }
  async function command(saved:PlanAuthoringReview|null,operation:PlanReviewOperation,origin:string,epoch:number){
    if(!alive(epoch)||current.current.disabled)throw new Error('Open the current Plan conversation before changing this suggestion.');
    if(pendingCommand())throw new Error('Check the previous suggestion operation before continuing.');
    const request={...operation,command_id:crypto.randomUUID(),origin_sha256:origin,expected_revision:saved?.revision??0} as PlanReviewCommand;
    return dispatch(request,epoch);
  }
  async function dispatch(request:PlanReviewCommand,epoch:number){
    const bytes=JSON.stringify({world,action,command:request});
    sessionStorage.setItem(commandKey,bytes);
    if(sessionStorage.getItem(commandKey)!==bytes)throw new Error('The operation was not sent because its exact identity could not be retained.');
    if(alive(epoch))setPending(request);
    try {
      const result=await commandPlanAuthoringReview(world,action,request);
      if(sessionStorage.getItem(commandKey)===bytes)sessionStorage.removeItem(commandKey);
      if(alive(epoch)){setPending(null);setReview(result);}
      return result;
    } catch(reason){
      // A definite server refusal did not mutate this command. A lost response
      // retains the exact command; only explicit retry may resend it.
      if(reason instanceof PlanReviewRequestError&&reason.status>=400&&reason.status<500){
        if(sessionStorage.getItem(commandKey)===bytes)sessionStorage.removeItem(commandKey);
        if(alive(epoch))setPending(null);
      }
      throw reason;
    }
  }
  async function show(saved:PlanAuthoringReview,epoch:number){
    if(saved.state!=='editing'||current.current.disabled)return;
    const capture=await current.current.bridge.captureAuthoring?.(current.current.identity);
    if(!alive(epoch))return;
    if(!capture||capture.capture.editor_json!==saved.capture.editor_json
      ||capture.capture.draft_sha256!==saved.capture.draft_sha256
      ||capture.capture.base_revision!==saved.capture.base_revision
      ||capture.capture.base_content_sha256!==saved.capture.base_content_sha256){
      setPlacement(null);throw new Error('The page changed. Inspect the current draft, then choose where this suggestion should go.');
    }
    // Display is inert and may use the old selection. Only explicit Save restores it.
    setPlacement({...capture,capture:saved.capture});current.current.onVisible();
  }
  async function check(epoch:number,initial=false){
    const snapshot=await readPlanAuthoringReview(world,action);
    if(!alive(epoch))return;
    let saved=snapshot.review;
    let retained=pendingCommand();
    if(retained&&saved?.last_command_id===retained.command_id){sessionStorage.removeItem(commandKey);setPending(null);retained=null;}
    else setPending(retained);
    if(!saved&&!retained&&!current.current.disabled)saved=await command(null,{operation:'open'},snapshot.origin_sha256,epoch);
    if(!alive(epoch)||!saved)return;
    if(saved.capture.document_id!==proposal.capture.document_id)throw new Error('The saved suggestion belongs to a different Plan.');
    setReview(saved);setPlacement(null);
    const raw=sessionStorage.getItem(key),local=raw?JSON.parse(raw):null;
    if(local&&(local.action!==action||JSON.stringify(local.origin)!==JSON.stringify(proposal.origin)||typeof local.markdown!=='string'))
      throw new Error('The local suggestion copy belongs to another result. Both copies were preserved.');
    const localText=initial?(local?.markdown??saved.markdown):textRef.current;
    setText(localText);textRef.current=localText;
    const differs=localText!==saved.markdown&&(local?.revision??review?.revision)!==saved.revision;
    setConflict(differs);
    if(saved.state==='editing'&&!retained&&!differs)await show(saved,epoch);
  }
  useEffect(()=>{
    const epoch=++generation.current;setReview(null);setPlacement(null);setError(null);setPending(null);setConflict(false);setInspected(false);
    void check(epoch,true).catch(reason=>{if(alive(epoch))setError(reason instanceof Error?reason.message:'Suggestion review unavailable.');});
    return()=>{generation.current++;};
  },[scope,bridge]);
  async function work(run:(saved:PlanAuthoringReview,epoch:number)=>Promise<void>){
    if(running.current||current.current.disabled||!review)return;
    const epoch=generation.current;running.current=true;setBusy(true);setError(null);
    try {
      const snapshot=await readPlanAuthoringReview(world,action);if(!alive(epoch))return;
      if(!snapshot.review||snapshot.review.revision!==review.revision){
        setConflict(true);setPlacement(null);throw new Error('This suggestion changed in another tab. Check its saved review before continuing.');
      }
      await run(snapshot.review,epoch);
    } catch(reason){if(alive(epoch))setError(reason instanceof Error?reason.message:'Suggestion needs checking.');}
    finally{running.current=false;if(alive(epoch))setBusy(false);}
  }
  function keep(){void work(async(saved,epoch)=>{
    if(saved.state!=='editing'||conflict||pending)throw new Error('Resolve the saved review before applying.');
    const host=current.current;
    if(!host.bridge.restoreAuthoring||!host.bridge.prepareAuthoring||!host.bridge.saveAuthoring||!host.bridge.authoringTitle)
      throw new Error('This Plan has no proposal Save owner. The suggestion is retained.');
    const restored=await host.bridge.restoreAuthoring(saved.capture,host.identity);if(!alive(epoch))return;
    const prepared=await host.bridge.prepareAuthoring(restored.target,textRef.current,action,host.expectedBinding,host.getBinding);
    if(!alive(epoch))return;
    saved=await command(saved,{operation:'move',capture:restored.capture},saved.origin_sha256,epoch);
    if(!alive(epoch))return;
    if(saved.markdown!==prepared.admitted.canonicalMarkdown)
      saved=await command(saved,{operation:'save',markdown:prepared.admitted.canonicalMarkdown},saved.origin_sha256,epoch);
    if(!alive(epoch))return;
    setText(saved.markdown);textRef.current=saved.markdown;cache(saved.markdown,saved.revision);
    saved=await command(saved,{operation:'prepare',application_id:crypto.randomUUID(),after_editor_json:prepared.afterEditorJson,
      after_editor_sha256:prepared.afterEditorSha256,after_markdown:prepared.afterMarkdown,after_draft_sha256:prepared.afterDraftSha256,
      after_title:host.bridge.authoringTitle()},saved.origin_sha256,epoch);
    if(!alive(epoch))return;
    const application=saved.applications.at(-1)!;setPlacement(null);
    const result=await host.bridge.saveAuthoring(restored.target,prepared,application,host.expectedBinding,host.getBinding,
      ()=>command(saved,{operation:'confirm',application_id:application.application_id},saved.origin_sha256,epoch));
    if(alive(epoch)){setReview(result);setError(null);sessionStorage.removeItem(key);}
  });}
  function choosePlacement(){void work(async(saved,epoch)=>{
    if(pending||conflict)throw new Error('Check the saved review and retained command before choosing placement.');
    const application=saved.applications.at(-1);
    if(saved.state==='applying'&&!inspected)throw new Error('Inspect the current draft before retiring its pending placement.');
    const captured=await current.current.bridge.captureAuthoring?.(current.current.identity,saved.state==='applying'?application?.application_id:undefined);
    if(!alive(epoch))return;if(!captured)throw new Error('Choose a saved Plan target before continuing.');
    if(saved.state==='applying'){
      saved=await command(saved,{operation:'recover_placement',application_id:application!.application_id,capture:captured.capture},saved.origin_sha256,epoch);
      await current.current.bridge.reconcileAuthoring?.(action,application!.application_id);
    }else if(saved.state==='editing')saved=await command(saved,{operation:'move',capture:captured.capture},saved.origin_sha256,epoch);
    else throw new Error('This suggestion already has a terminal outcome.');
    if(alive(epoch)){setReview(saved);setPlacement({...captured,capture:saved.capture});setInspected(false);cache(textRef.current,saved.revision);current.current.onVisible();}
  });}
  function move(position:number){void work(async(saved,epoch)=>{
    if(saved.state!=='editing'||pending||conflict)throw new Error('Resolve the saved review before moving this suggestion.');
    const captured=await current.current.bridge.captureAuthoringAt?.(position,current.current.identity);
    if(!alive(epoch))return;if(!captured)throw new Error('This Plan has no placement owner.');
    saved=await command(saved,{operation:'move',capture:captured.capture},saved.origin_sha256,epoch);
    if(alive(epoch)){setReview(saved);setPlacement({...captured,capture:saved.capture});cache(textRef.current,saved.revision);}
  });}
  function finish(){void work(async(saved,epoch)=>{
    const application=saved.applications.at(-1);if(!application)throw new Error('No retained application is available.');
    const host=current.current,matches=await host.bridge.matchesAuthoringAfter?.(application);
    if(!alive(epoch))return;
    if(saved.state==='applying'&&!matches)throw new Error('The current draft differs from the pending after-copy. Inspect both copies and choose a new placement; it was not inserted again.');
    if(saved.state==='applying')saved=await command(saved,{operation:'confirm',application_id:application.application_id},saved.origin_sha256,epoch);
    if(saved.state!=='applied')throw new Error('The application has not been saved.');
    await host.bridge.acknowledgeAuthoring?.(saved.applications.at(-1)!);
    if(alive(epoch)){setReview(saved);setPlacement(null);sessionStorage.removeItem(key);}
  });}
  const locked=busy||disabled;
  return <>
    {placement&&review?.state==='editing'&&!conflict?<SurfacePageProposal editor={placement.target.editor} position={review.capture.from}
      editorJson={review.capture.editor_json} placementId={`plan-proposal:${action}`} revealKey={1} busy={locked}
      onMove={bridge.captureAuthoringAt?move:undefined}
      onStale={()=>{if(running.current)return;setPlacement(null);setError('The page changed. Inspect it and choose a new placement for this retained suggestion.');}}>
      <SurfaceProposalReview markdown={text} busy={locked||Boolean(pending)} error={error}
        onChange={next=>{try{cache(next,review.revision);setText(next);textRef.current=next;}catch(reason){setError(String(reason));}}}
        onSave={keep} onDiscard={()=>{void work(async(saved,epoch)=>{const result=await command(saved,{operation:'discard'},saved.origin_sha256,epoch);
          if(alive(epoch)){setReview(result);setPlacement(null);sessionStorage.removeItem(key);}});}}/>
    </SurfacePageProposal>:null}
    <div className="plan-proposal-status" aria-label="Plan suggestion">
      <span>{review?.state==='applied'?'Suggestion saved on the Plan.':review?.state==='discarded'?'Suggestion discarded.':placement?'Review the suggestion on your Plan.':'Your Plan suggestion is retained.'}</span>
      <button type="button" disabled={busy} onClick={()=>{const epoch=generation.current;setError(null);void check(epoch).catch(reason=>{if(alive(epoch))setError(String(reason));});}}>Check saved review</button>
      {conflict?<><p>The saved review and your local edit differ.</p>
        <button type="button" disabled={locked||Boolean(pending)} onClick={()=>{if(review){cache(text,review.revision);setConflict(false);void show(review,generation.current).catch(reason=>setError(String(reason)));}}}>Keep my local edit</button>
        <button type="button" disabled={locked||Boolean(pending)} onClick={()=>{if(review){cache(review.markdown,review.revision);setText(review.markdown);textRef.current=review.markdown;setConflict(false);void show(review,generation.current).catch(reason=>setError(String(reason)));}}}>Use saved review</button></>:null}
      {pending?<button type="button" disabled={locked} onClick={()=>{const epoch=generation.current;setBusy(true);void dispatch(pending,epoch)
        .then(()=>check(epoch)).catch(reason=>{if(alive(epoch))setError(String(reason));}).finally(()=>{if(alive(epoch))setBusy(false);});}}>Retry exact {pending.operation} operation</button>:null}
      {!placement&&review?.state==='editing'?<button type="button" disabled={locked||conflict||Boolean(pending)} onClick={choosePlacement}>Use current page placement</button>:null}
      {review?.state==='applying'?<><label><input type="checkbox" checked={inspected} disabled={locked} onChange={event=>setInspected(event.target.checked)}/>I inspected the current draft and retained suggestion.</label>
        <button type="button" disabled={locked||!inspected||Boolean(pending)} onClick={choosePlacement}>Retire pending placement</button>
        <button type="button" disabled={locked||Boolean(pending)} onClick={finish}>Finish pending Save</button></>:null}
      {review?.state==='applied'?<button type="button" disabled={locked||Boolean(pending)} onClick={finish}>Acknowledge saved result</button>:null}
      {!placement&&error?<p role="alert">{error}</p>:null}
    </div>
  </>;
}
