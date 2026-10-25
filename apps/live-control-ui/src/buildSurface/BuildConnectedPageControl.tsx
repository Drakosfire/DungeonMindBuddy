import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {useOptionalMarkdownCanvasSession} from '../markdownCanvas/MarkdownCanvasSession';
import {useOptionalAgentInteraction} from '../agentInteraction/AgentInteractionProvider';
import {SurfaceSelectionActions,captureSurfaceTextSelection} from '../surfaceInteraction/SurfaceSelectionActions';
import {prepareConnectedPage,confirmConnectedPage,recoverConnectedPage,type ConnectedPageIntent,type ConnectedPageOperation} from '../api/connectedPageApi';
import {LiveApiError,postManagedWorldGraphProjection} from '../api/liveApi';
import {verifyManagedWorldGraphProjectionResponse} from '../worldGraph/verifyManagedWorldGraphProjectionResponse';
import type {WorldGraphProjectionNodeView} from '../api/types';
import {readConnectedPageRecovery,retainConnectedPageRequest,clearConnectedPageRequest,queueConnectedPageBuildOut} from './connectedPageAuthoring';
import {publishConnectedPageReviewHost,type ConnectedPageReviewSeed} from './connectedPageReviewHost';
import {validConnectedPageIntent} from '../api/connectedPageApi';
import {isCollaboration} from '../shared/sourcePassageProtocol';
import './BuildConnectedPageControl.css';
const errorText=(reason:unknown)=>reason instanceof Error?reason.message:'The page request could not finish.';
export function BuildConnectedPageControl({selectDocument,refreshDocuments,relationshipsHost=null}:{relationshipsHost?:HTMLElement|null;selectDocument:(id:string)=>Promise<boolean>;refreshDocuments:()=>unknown}){
  const session=useOptionalMarkdownCanvasSession(),agent=useOptionalAgentInteraction();
  const current=useRef(session);current.current=session;
  const dialog=useRef<HTMLDialogElement>(null),busyRef=useRef<number|null>(null),mounted=useRef(true);
  const [open,setOpen]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [origin,setOrigin]=useState<ConnectedPageIntent['origin']|null>(null),[retained,setRetained]=useState<ConnectedPageIntent|null>(null);
  const [operation,setOperation]=useState<ConnectedPageOperation|null>(null),[pageOperation,setPageOperation]=useState<ConnectedPageOperation|null>(null);
  const [title,setTitle]=useState(''),[personLabel,setPersonLabel]=useState(''),[personChoice,setPersonChoice]=useState('');
  const [placeChoice,setPlaceChoice]=useState('__new__'),[relationships,setRelationships]=useState<('owns'|'operates')[]>([]);
  const [mode,setMode]=useState<'scaffold'|'build_out'>('scaffold'),[instructions,setInstructions]=useState('');
  const [reviewSeed,setReviewSeed]=useState<ConnectedPageReviewSeed|null>(null);
  const [reviewDraftError,setReviewDraftError]=useState('');
  const [canStartFresh,setCanStartFresh]=useState(false);
  const [nodes,setNodes]=useState<WorldGraphProjectionNodeView[]>([]),[loading,setLoading]=useState(false);
  const world=session?.record?.world_id,documentId=session?.record?.document_id;
  const scope=useRef({world,documentId,epoch:0});
  if(scope.current.world!==world||scope.current.documentId!==documentId)scope.current={world,documentId,epoch:scope.current.epoch+1};
  const openReviewRef=useRef<(seed:ConnectedPageReviewSeed)=>void>(()=>{});
  openReviewRef.current=seed=>{if(!world||!documentId||seed.worldId!==world||seed.ownerDocumentId!==documentId||busyRef.current!==null)throw new Error('The page review destination changed.');
    if(reviewDraftError)throw new Error(reviewDraftError);
    if(reviewSeed){if(reviewSeed.sourceTurnId===seed.sourceTurnId&&JSON.stringify(reviewSeed.proposal)===JSON.stringify(seed.proposal)){setOpen(true);return;}throw new Error('Resolve the existing page review before opening another.');}
    if(readConnectedPageRecovery(world,documentId))throw new Error('Resolve the retained page creation before opening another review.');
    setReviewSeed(seed);setOrigin(seed.origin);setTitle(seed.proposal.title);setPersonLabel(seed.proposal.person_label??'');setPersonChoice('');setPlaceChoice('__new__');setRelationships(seed.proposal.relationships);setInstructions(seed.proposal.instructions);setMode('scaffold');setError('');setOpen(true);void loadCandidates(world);};
  useLayoutEffect(()=>{if(!world||!documentId)return;return publishConnectedPageReviewHost({worldId:world,documentId,open:seed=>openReviewRef.current(seed)});},[world,documentId]);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;scope.current.epoch+=1;};},[]);
  const captureScope=()=>{const epoch=scope.current.epoch;return()=>mounted.current&&scope.current.epoch===epoch;};
  useEffect(()=>{if(open&&dialog.current&&!dialog.current.open)dialog.current.showModal();},[open]);
  useEffect(()=>{
    let active=true;busyRef.current=null;setBusy(false);setOpen(false);setOrigin(null);setRetained(null);setOperation(null);setPageOperation(null);setError('');setReviewSeed(null);setReviewDraftError('');setCanStartFresh(false);
    if(!world||!documentId)return;
    try{
      const saved=readConnectedPageRecovery(world,documentId);
      if(saved){setRetained(saved);void recoverConnectedPage(saved).then(result=>{if(active)setOperation(result);}).catch(()=>{/* Unknown outcomes retain the exact request; absence is not cancellation. */});}
      else {const raw=sessionStorage.getItem('dmb:connected-page-review-draft:v1:'+JSON.stringify([world,documentId]));
        if(raw!==null){const v=JSON.parse(raw),seed=v.seed,f=v.fields;
          if(v.schema!=='dmb_connected_page_review_draft_v1'||seed?.worldId!==world||seed?.ownerDocumentId!==documentId||!isCollaboration(seed?.proposal,true)||seed.proposal.kind!=='connected_page'||!f||!validConnectedPageIntent({operation_id:'11111111-1111-4111-8111-111111111111',world_id:world,title:f.title,origin:seed.origin,place:{node_id:null,label:f.title,kind:'location'},person:null,relationships:[],mode:f.mode,instructions:f.instructions})||typeof f.personLabel!=='string'||typeof f.personChoice!=='string'||typeof f.placeChoice!=='string'||!Array.isArray(f.relationships)||f.relationships.some((x:unknown)=>!['owns','operates'].includes(String(x))))throw new Error('The local page review could not be restored; its bytes were kept.');
          setReviewSeed(seed);setOrigin(seed.origin);setTitle(f.title);setPersonLabel(f.personLabel);setPersonChoice(f.personChoice);setPlaceChoice(f.placeChoice);setRelationships(f.relationships);setInstructions(f.instructions);setMode(f.mode);void loadCandidates(world);
        }}
    }catch(reason){setError(errorText(reason));setReviewDraftError(errorText(reason));}
    return()=>{active=false;};
  },[world,documentId]);
  useEffect(()=>{
    if(!reviewSeed||!world||!documentId||reviewSeed.worldId!==world||reviewSeed.ownerDocumentId!==documentId||retained||reviewDraftError)return;
    try{const key='dmb:connected-page-review-draft:v1:'+JSON.stringify([world,documentId]),bytes=JSON.stringify({schema:'dmb_connected_page_review_draft_v1',seed:reviewSeed,fields:{title,personLabel,personChoice,placeChoice,relationships,mode,instructions}});sessionStorage.setItem(key,bytes);if(sessionStorage.getItem(key)!==bytes)throw new Error('Local page review could not be retained.');}
    catch(reason){setReviewDraftError(errorText(reason));setError(errorText(reason));}
  },[reviewSeed,world,documentId,title,personLabel,personChoice,placeChoice,relationships,mode,instructions,retained,reviewDraftError]);
  // A page carries the immutable operation ID. Its origin and acknowledged
  // connections remain inspectable after reload, without replaying a write.
  useEffect(()=>{
    let active=true;
    const id=session?.record?.connected_page_operation_id;
    if(!id||!world||!documentId)return;
    // The operation's full exact intent is recovered by its source tab request
    // for retries. A scoped read for the newly-created page is resolved below.
    void import('../api/connectedPageApi').then(async api=>{
      const result=await api.readConnectedPageForPage(id,world,documentId);
      if(active)setPageOperation(result);
    }).catch(reason=>{if(active)setError(errorText(reason));});
    return()=>{active=false;};
  },[world,documentId,session?.record?.connected_page_operation_id]);
  async function loadCandidates(scope:string){
    setLoading(true);
    try{
      const graph=await postManagedWorldGraphProjection({schema:'dmb_managed_world_graph_projection_request_v1',managedWorldId:scope});
      const invalid=verifyManagedWorldGraphProjectionResponse({managedWorldId:scope,request:{schema:'dmb_world_graph_projection_request_v1',
        worldId:scope,campaignId:'',scopeMode:'world',focus:{kind:'none',sessionId:null},admissibility:'gm'},response:graph,revisionKind:'head'});
      if(invalid)throw new Error(invalid);
      if(current.current?.record?.world_id!==scope)return;
      setNodes(graph.projection.nodes);
    }catch(reason){if(mounted.current)setError(errorText(reason));}
    finally{if(mounted.current)setLoading(false);}
  }
  async function start(){
    const before=current.current,editor=before?.editor;
    if(!before?.record?.world_id||!before.snapshot||!editor||before.activeCommand)return;
    if(retained){setOrigin(retained.origin);setOpen(true);return;}
    if(reviewDraftError){setError(reviewDraftError);return;}
    if(reviewSeed){setOpen(true);return;}
    try{
      const capture=await captureSurfaceTextSelection(editor,()=>current.current?.editor===editor
        &&current.current?.record?.document_id===before.record!.document_id
        &&current.current?.snapshot?.loaded_revision===before.snapshot!.loaded_revision);
      const name=capture.selected_text.trim().replace(/:\s*$/,'');
      setOrigin({...capture,document_id:before.record.document_id,revision:before.snapshot.loaded_revision,content_sha256:before.snapshot.content_sha256});
      setTitle(name);setPersonLabel(name.match(/^([^’']+)[’']s\b/)?.[1]??'');setPersonChoice('');setPlaceChoice('__new__');
      setRelationships([]);setInstructions('');setMode('scaffold');setError('');setOpen(true);
      void loadCandidates(before.record.world_id);
    }catch(reason){setError(errorText(reason));}
  }
  const matches=(label:string,kind:string)=>nodes.filter(n=>n.kind===kind&&(n.label.toLowerCase()===label.trim().toLowerCase()
    ||n.aliases?.some(alias=>alias.toLowerCase()===label.trim().toLowerCase())));
  const people=matches(personLabel,'npc'),places=matches(title,'location');
  async function openCreated(result:ConnectedPageOperation,buildOut:boolean,isCurrent=captureScope()){
    if(!isCurrent())return;
    if(!result.page)throw new Error("The created page is not available yet.");
    refreshDocuments();
    const applied=await selectDocument(result.page.document_id);
    if(!applied)throw new Error("The page was created. Open it again to continue.");
    if(!mounted.current)return;
    if(buildOut){queueConnectedPageBuildOut(result);agent?.setPaneOpen(true);}
    if(result.phase==='complete'){
      const pending=readConnectedPageRecovery(result.intent.world_id,documentId!);
      if(pending?.operation_id===result.operation_id)clearConnectedPageRequest(pending,documentId!);
      sessionStorage.removeItem('dmb:connected-page-review-draft:v1:'+JSON.stringify([result.intent.world_id,documentId]));
    }
  }
  async function create(){
    if(busyRef.current!==null||!world||!documentId||!origin||reviewDraftError)return;
    const isCurrent=captureScope();
    const epoch=scope.current.epoch;busyRef.current=epoch;setBusy(true);setError('');setCanStartFresh(false);
    try{
      let request=retained;
      if(!request){
        if(current.current?.record?.document_id!==documentId||!('kind' in origin)&&JSON.stringify(current.current?.editor?.getJSON())!==origin.editor_json)
          throw new Error('The source changed. Close this form and select the passage again.');
        const person=relationships.length?(personChoice==='__new__'?{label:personLabel.trim(),kind:'npc' as const}
          :people.find(n=>n.nodeId===personChoice)):null;
        if(relationships.length&&!person)throw new Error('Choose the existing person or explicitly create a new one.');
        const place=placeChoice==='__new__'?{label:title.trim(),kind:'location' as const}:places.find(n=>n.nodeId===placeChoice);
        if(!place)throw new Error('Choose the location identity.');
        request={operation_id:crypto.randomUUID(),world_id:world,title:title.trim(),origin,
          place:{label:place.label,kind:'location',node_id:'nodeId'in place?place.nodeId:null},
          person:person?{label:person.label,kind:'npc',node_id:'nodeId'in person?person.nodeId:null}:null,
          relationships,mode,instructions};
        retainConnectedPageRequest(request,documentId);setRetained(request);
      }
      let result=await prepareConnectedPage(request);
      if(!isCurrent())return;
      setOperation(result);
      if(result.phase==='prepared')result=await confirmConnectedPage(result);
      if(!isCurrent())return;
      if(result.phase!=='complete')throw new Error('The created page is retained; its connections have not finished.');
      if(mounted.current)setOperation(result);
      await openCreated(result,request.mode==='build_out',isCurrent);
      if(isCurrent()){setOpen(false);setRetained(null);}
    }catch(reason){
      if(!isCurrent())return;
      setError(errorText(reason));
      try{
        const saved=readConnectedPageRecovery(world,documentId);
        if(saved){const recovered=await recoverConnectedPage(saved);if(isCurrent())setOperation(recovered);}
      }catch(recoveryError){if(isCurrent()&&reason instanceof LiveApiError&&[409,422].includes(reason.status)&&recoveryError instanceof LiveApiError&&recoveryError.status===404)setCanStartFresh(true);/* Unknown outcomes never authorize replacement. */}
    }finally{if(busyRef.current===epoch)busyRef.current=null;if(isCurrent())setBusy(false);}
  }
  async function startFreshReview(){
    if(!canStartFresh||!retained||!world||!documentId||busyRef.current!==null)return;
    const isCurrent=captureScope(),request=retained;setBusy(true);busyRef.current=scope.current.epoch;
    try{try{await recoverConnectedPage(request);throw new Error('The page operation now exists. Resume it instead.');}
      catch(reason){if(!(reason instanceof LiveApiError)||reason.status!==404)throw reason;}
      if(!isCurrent())return;
      const key='dmb:connected-page-review-history:v1:'+JSON.stringify([world,documentId,request.operation_id]),bytes=JSON.stringify(request);sessionStorage.setItem(key,bytes);if(sessionStorage.getItem(key)!==bytes)throw new Error('The previous request could not be preserved.');
      clearConnectedPageRequest(request,documentId);sessionStorage.removeItem('dmb:connected-page-review-draft:v1:'+JSON.stringify([world,documentId]));setRetained(null);setReviewSeed(null);setOrigin(null);setOperation(null);setCanStartFresh(false);setOpen(false);setError('Previous review preserved. Ask Buddy to reread the changed source before creating a fresh review.');
    }catch(reason){if(isCurrent())setError(errorText(reason));}
    finally{if(isCurrent()){busyRef.current=null;setBusy(false);}}
  }
  if(!session?.editor||!world||!documentId)return null;
  const frozen=!!retained;
  const displayed=retained;
  return <>
    <SurfaceSelectionActions editor={session.editor} actions={open?[]:[{id:'new-page',label:'＋ New page',invoke:()=>{void start();}}]}/>
    {!open&&reviewSeed&&!retained&&<aside className="connected-page-recovery"><button type="button" onClick={()=>setOpen(true)}>Resume page review</button></aside>}
    {!open&&retained&&<aside className="connected-page-recovery"><button type="button" onClick={()=>{setOrigin(retained.origin);setOpen(true);}}>Resume page creation</button>
      {operation?.page&&<button type="button" onClick={()=>void openCreated(operation,false)}>Open created page</button>}</aside>}
    {!open&&error&&<p role="alert">{error}</p>}
    {pageOperation&&relationshipsHost&&createPortal(<details className="connected-page-connections"><summary>{pageOperation.phase==='complete'?'Relationships & origin':'Connections pending'}</summary>
      <a href={'/build?'+new URLSearchParams({world,documentId:pageOperation.intent.origin.document_id,campaign:world})}>Original passage</a>
      {pageOperation.intent.relationships.map(predicate=><p key={predicate}>{pageOperation.intent.person?.label} → {predicate} → {pageOperation.intent.place.label}</p>)}
    </details>,relationshipsHost)}
    {open&&createPortal(<dialog ref={dialog} className="connected-page-dialog" aria-label="New page from selection" onCancel={()=>setOpen(false)} onClose={()=>setOpen(false)}>
      <header><h2>New page</h2><button type="button" aria-label="Close new page" onClick={()=>setOpen(false)}>×</button></header>
      <blockquote>{displayed?.origin.selected_text??origin?.selected_text}</blockquote>
      <form onSubmit={event=>{event.preventDefault();void create();}}>
        <fieldset disabled={busy||frozen}>
          <label>Page title<input value={displayed?.title??title} onChange={event=>{setTitle(event.target.value);setPlaceChoice('__new__');}} required maxLength={200}/></label>
          <label>Location<select value={displayed?.place.node_id??(displayed?'__new__':placeChoice)} onChange={event=>setPlaceChoice(event.target.value)}>
            <option value="__new__">New location: {displayed?.place.label??title}</option>{places.map(n=><option key={n.nodeId} value={n.nodeId}>Existing: {n.label} ({n.nodeId})</option>)}
          </select></label>
          <label>Related person (optional)<input value={displayed?.person?.label??personLabel} onChange={event=>{setPersonLabel(event.target.value);setPersonChoice('');}} placeholder="Who owns or runs this place?"/></label>
          {(personLabel||displayed?.person)&&<><label>Person identity<select value={displayed?.person?.node_id??(displayed?.person?'__new__':personChoice)} onChange={event=>setPersonChoice(event.target.value)}>
            <option value="">Choose a person</option>{people.map(n=><option key={n.nodeId} value={n.nodeId}>Existing: {n.label} ({n.nodeId})</option>)}
            <option value="__new__">New person: {personLabel}</option></select></label>
            <div className="connected-page-relationships">{(['owns','operates'] as const).map(predicate=><label key={predicate}><input type="checkbox" checked={(displayed?.relationships??relationships).includes(predicate)}
              onChange={event=>setRelationships(before=>event.target.checked?[...before,predicate]:before.filter(p=>p!==predicate))}/>{displayed?.person?.label??personLabel} {predicate} {displayed?.title??title}</label>)}</div></>}
          <label>Anything to guide the writing? (optional)<textarea value={displayed?.instructions??instructions} onChange={event=>setInstructions(event.target.value)} placeholder="Mood, important details, or things to leave open…" maxLength={8000}/></label>
          <div className="connected-page-modes" role="group" aria-label="How much to create">
            <label><input type="radio" name="page-mode" checked={(displayed?.mode??mode)==='scaffold'} onChange={()=>setMode('scaffold')}/>Scaffold — leave room to write</label>
            <label><input type="radio" name="page-mode" checked={(displayed?.mode??mode)==='build_out'} onChange={()=>setMode('build_out')}/>Build out — let Buddy develop it</label>
          </div>
        </fieldset>
        {loading&&<p role="status">Finding existing people and places…</p>}
        {error&&<p role="alert">{error}</p>}
        {reviewDraftError&&reviewSeed&&<button type="button" onClick={()=>{setReviewDraftError('');setError('');}}>Try retaining review again</button>}
        {canStartFresh&&<button type="button" disabled={busy} onClick={()=>{void startFreshReview();}}>Start a fresh review</button>}
        <footer><button type="submit" disabled={busy||loading||!!reviewDraftError||!origin||(!retained&&(!title.trim()||relationships.length>0&&(!personLabel.trim()||!personChoice)))}>{busy?'Creating…':retained?'↻ Retry':'Create page'}</button>
          {operation?.page&&<button type="button" onClick={()=>void openCreated(operation!,false)}>Open created page</button>}
        </footer>
      </form>
    </dialog>,document.body)}
  </>;
}
