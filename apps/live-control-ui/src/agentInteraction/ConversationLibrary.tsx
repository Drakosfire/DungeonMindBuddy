import {SurfaceGraphReferenceInput} from '../surface/SurfaceGraphReferenceInput';
import {ConversationExport} from './ConversationExport';
import {LiveApiError} from '../api/liveApi';
import {groupRetryLineage} from './conversationAttemptGroups';
import {ConversationRetryAttempts} from './ConversationRetryAttempts';
import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {listConversations,readConversationName,readConversationTurns,readConversationMessages,renameConversation,type ConversationSummary,type LibraryTurn,type ResumeConversationCommand,type ConversationLifecycleOperation,type ConversationLibraryFilter} from '../api/conversationLibraryApi';
import {WorldPlanAgentAnswer} from '../planSurface/components/WorldPlanAgentAnswer';
import {BuddyContextTraceLoader} from '../planSurface/components/BuddyContextTraceLoader';
import {BuddyTurnInspection} from '../planSurface/components/BuddyTurnInspection';
import type {BulkConversationOperation, BulkConversationPlan, BulkConversationResult} from './conversationBulkLifecycle';
import './ConversationLibrary.css';
const message=(error:unknown)=>error instanceof Error?error.message:'The conversation could not be read.';
export function ConversationLibrary({worldId,onClose,pointer,onContinue,onLifecycle,onBulkLifecycle,continueDisabledReason}:{worldId:string;onClose:()=>void;pointer?:{revision:number;activeId:string|null};onContinue?:(command:ResumeConversationCommand)=>Promise<void>;onLifecycle?:(command:ResumeConversationCommand,operation:ConversationLifecycleOperation)=>Promise<void>;onBulkLifecycle?:(plan:BulkConversationPlan,isCurrent:()=>boolean)=>Promise<BulkConversationResult>;continueDisabledReason?:string|null}){
 const [renaming,setRenaming]=useState(false);
 const actionMenu=useRef<HTMLDetailsElement>(null);
 const filterControl=useRef<HTMLSelectElement>(null);
 const [lifecycleNotice,setLifecycleNotice]=useState('');
 const [bulkMode,setBulkMode]=useState(false);
 const [bulkSelection,setBulkSelection]=useState<Map<string,string>>(new Map());
 const [bulkResult,setBulkResult]=useState<BulkConversationResult|null>(null);
 const [bulkError,setBulkError]=useState('');
 const [bulkOperation,setBulkOperation]=useState<BulkConversationOperation|null>(null);
 const [deletePlan,setDeletePlan]=useState<BulkConversationPlan|null>(null);
 const [bulkBusy,setBulkBusy]=useState(false);
 const bulkInFlight=useRef(false);
 const bulkRetry=bulkResult?.retry??null;
 const [fullDetails,setFullDetails]=useState(false);
 const [continuing,setContinuing]=useState(false);
 const pendingOperation=useRef<'reopen'|ConversationLifecycleOperation|null>(null);
 const pendingResume=useRef<ResumeConversationCommand|null>(null),continueInFlight=useRef(false);
 useEffect(()=>{pendingResume.current=null;pendingOperation.current=null;continueInFlight.current=false;setContinuing(false);},[worldId]);
 const dialog=useRef<HTMLDialogElement>(null),mounted=useRef(true),scope=useRef({worldId});
 if(scope.current.worldId!==worldId)scope.current={worldId};
 const detailRequest=useRef<AbortController|null>(null);
 const listRequest=useRef<AbortController|null>(null);
 const listEpoch=useRef(0),detailEpoch=useRef(0),pageBusy=useRef(false);
 const [filter,setFilter]=useState<Exclude<ConversationLibraryFilter,'all'|'archived'>>('recent'),[items,setItems]=useState<ConversationSummary[]>([]),[listOwner,setListOwner]=useState(worldId);
 const [next,setNext]=useState<string|null>(null),[listing,setListing]=useState(true),[listError,setListError]=useState('');
 const [selected,setSelected]=useState<string|null>(null),[detail,setDetail]=useState<ConversationSummary|null>(null),[turns,setTurns]=useState<LibraryTurn[]>([]);
 const [before,setBefore]=useState<number|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const [title,setTitle]=useState(''),[saving,setSaving]=useState(false),[notice,setNotice]=useState('');
 useEffect(()=>{mounted.current=true;dialog.current?.showModal();return()=>{mounted.current=false;listEpoch.current++;detailEpoch.current++;};},[]);
 const alive=(owner:typeof scope.current)=>mounted.current&&scope.current===owner;
 function startDetailRead(){
  detailRequest.current?.abort();
  const request=new AbortController();
  detailRequest.current=request;
  return request;
 }
 async function readPage(id:string,before?:number,details=fullDetails,signal?:AbortSignal){
  if(details)return readConversationTurns(worldId,id,before,signal);
  const page=await readConversationMessages(worldId,id,before,signal);
  return {turns:page.messages.map(row=>({...row,reply_object:null,retry_context:null})),next_before_sequence:page.next_before_sequence};
 }
 async function select(id:string,details=fullDetails,summary?:ConversationSummary){
  const owner=scope.current,epoch=++detailEpoch.current;
  setSelected(id);setRenaming(false);if(id!==selected||detail?.world_id!==worldId)setDetail(null);setTurns([]);setBefore(null);setLoading(true);setSaving(false);setError('');setNotice('');
  const request=startDetailRead();
  try{const [meta,page]=await Promise.all([summary ?? readConversationName(worldId,id,request.signal),readPage(id,undefined,details,request.signal)]);
   if(!alive(owner)||epoch!==detailEpoch.current)return;setDetail(meta);setTitle(meta.title);setTurns(page.turns);setBefore(page.next_before_sequence);
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
  finally{if(detailRequest.current===request){request.abort();detailRequest.current=null;}if(alive(owner)&&epoch===detailEpoch.current)setLoading(false);}
 }
 async function loadList(older=false){
  if(older&&pageBusy.current)return;
  const owner=scope.current,epoch=++listEpoch.current;pageBusy.current=true;setListing(true);setListError('');
  listRequest.current?.abort();
  const request=new AbortController();
  listRequest.current=request;
  try{const page=await listConversations(worldId,filter,older?next??undefined:undefined,request.signal);
   if(!alive(owner)||epoch!==listEpoch.current)return;
   setListOwner(worldId);setItems(old=>older?[...new Map([...old,...page.items].map(item=>[item.conversation_id,item])).values()]:page.items);setNext(page.next_before);
   if(!older&&page.items.length){
    const initial=page.items.find(item=>item.status==='active')??page.items[0];
    void select(initial.conversation_id,fullDetails,initial);
   }
  }catch(reason){if(alive(owner)&&epoch===listEpoch.current)setListError(message(reason));}
  finally{if(listRequest.current===request)listRequest.current=null;if(alive(owner)&&epoch===listEpoch.current){setListing(false);pageBusy.current=false;}}
 }
 useEffect(()=>{detailEpoch.current++;setLifecycleNotice('');setItems([]);
  setBulkSelection(new Map());setBulkResult(null);setBulkError('');setBulkOperation(null);setDeletePlan(null);setBulkMode(false);setBulkBusy(false);bulkInFlight.current=false;setSelected(null);setDetail(null);setTurns([]);setNext(null);void loadList();return()=>{listEpoch.current++;detailEpoch.current++;listRequest.current?.abort();detailRequest.current?.abort();};},[worldId,filter]);
 async function olderTurns(){
  if(!selected||before===null||loading)return;
  const owner=scope.current,epoch=detailEpoch.current,id=selected,cursor=before;setLoading(true);setError('');
  const request=startDetailRead();
  try{const page=await readPage(id,cursor,fullDetails,request.signal);if(!alive(owner)||epoch!==detailEpoch.current)return;
   setTurns(old => {
    const incomingIds = new Set(page.turns.map(turn => turn.turn_id));
    if (
      incomingIds.size === page.turns.length &&
      (!old.length || !page.turns.length || page.turns[page.turns.length - 1].sequence < old[0].sequence) &&
      old.every(turn => {
       if (incomingIds.has(turn.turn_id)) return false;
       incomingIds.add(turn.turn_id);
       return true;
      })
    ) {
      return [...page.turns, ...old];
    }
    return [...new Map([...page.turns, ...old].map(turn => [turn.turn_id, turn])).values()]
      .sort((a, b) => a.sequence - b.sequence);
   });
   setBefore(page.next_before_sequence);
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
  finally{if(detailRequest.current===request){request.abort();detailRequest.current=null;}if(alive(owner)&&epoch===detailEpoch.current)setLoading(false);}
 }
 async function save(){
  if(!detail||saving)return;
  const owner=scope.current,epoch=detailEpoch.current,id=detail.conversation_id;setSaving(true);setError('');setNotice('');
  try{const renamed=await renameConversation(worldId,id,title,detail.name_revision);if(!alive(owner)||epoch!==detailEpoch.current)return;
   setDetail(renamed);setItems(old=>old.map(item=>item.conversation_id===id?renamed:item));setNotice('Name saved.');setRenaming(false);
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason)+' Your typed name is kept; retry or reload the saved name.');}
  finally{if(alive(owner)&&epoch===detailEpoch.current)setSaving(false);}
 }
 async function reloadName(){
  if(!selected)return;const owner=scope.current,epoch=++detailEpoch.current,id=selected;setSaving(false);setError('');setNotice('');
  const request=startDetailRead();
  setLoading(false);
  try{const meta=await readConversationName(worldId,id,request.signal);if(alive(owner)&&epoch===detailEpoch.current){setDetail(meta);setTitle(meta.title);}}
  catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
  finally{if(detailRequest.current===request)detailRequest.current=null;}
 }
 async function continueSelected(operation:'reopen'|ConversationLifecycleOperation='reopen'){
  if(!detail||!pointer||continueInFlight.current||continuing||bulkInFlight.current||bulkMode||bulkRetry||continueDisabledReason)return;
  if(operation==='reopen'?(detail.status!=='archived'||!onContinue):!onLifecycle)return;
  const owner=scope.current,id=detail.conversation_id;
  if(pendingResume.current&&(pendingResume.current.conversation_id!==id||pendingOperation.current!==operation)){setError('Refresh the current conversation before switching to another.');return;}
  const command=pendingResume.current??{world_id:worldId,conversation_id:id,command_id:crypto.randomUUID(),expected_pointer_revision:pointer.revision,expected_active_conversation_id:pointer.activeId};
  pendingResume.current=command;pendingOperation.current=operation;continueInFlight.current=true;setContinuing(true);setError('');setLifecycleNotice('');
  try{
   if(operation==='reopen')await onContinue!(command);else await onLifecycle!(command,operation);
   if(!alive(owner))return;
   pendingResume.current=null;pendingOperation.current=null;
   if(operation!=='reopen'){
    detailEpoch.current++;detailRequest.current?.abort();
    setSelected(null);setDetail(null);setTurns([]);setBefore(null);setLoading(false);setRenaming(false);
    setItems(old=>old.filter(item=>item.conversation_id!==id));
    setLifecycleNotice(operation==='archive'?'Conversation archived.':operation==='trash'?'Conversation moved to Trash.'
     :detail.library_archived?'Conversation restored to Archived.':'Conversation restored to Recent.');
   }
   void loadList();
  }
  catch(reason){if(alive(owner)){
   if(reason instanceof LiveApiError&&[401,403,404,409,422].includes(reason.status)){
    pendingResume.current=null;pendingOperation.current=null;
    setError(reason.status===409&&reason.message!=='This conversation has a reply in progress.'
     ? 'The conversation changed. Refresh conversations before trying again.'
     : message(reason));
   }else setError(message(reason)+' Refresh conversations to check the result, or retry this same action.');
  }}
  finally{if(alive(owner)){continueInFlight.current=false;setContinuing(false);}}
 }
 function toggleBulkSelection(item:ConversationSummary){
  setBulkSelection(previous=>{
   const selection=new Map(previous);
   if(selection.has(item.conversation_id))selection.delete(item.conversation_id);
   else selection.set(item.conversation_id,item.title);
   return selection;
  });
 }

 function makePlan(operation:BulkConversationOperation,selection:ReadonlyMap<string,string>):BulkConversationPlan|null{
  if(!pointer||!selection.size)return null;
  return {
   worldId, pointer, operation,
   targets:Array.from(selection,([conversationId,title])=>({conversationId,title,commandId:crypto.randomUUID()})),
  };
 }

 async function applyBulk(plan:BulkConversationPlan|null){
  if(!onBulkLifecycle||!plan||plan.worldId!==worldId||!pointer||bulkInFlight.current||
   continueInFlight.current||continueDisabledReason||pendingResume.current)return;
  if(plan.operation==='delete'&&filter!=='trashed')return;
  const owner=scope.current;
  setDeletePlan(null);
  if(!bulkRetry)setBulkResult(null);
  bulkInFlight.current=true;setBulkBusy(true);setBulkOperation(plan.operation);setBulkError('');setLifecycleNotice('');
  try{
   const result=await onBulkLifecycle(plan,()=>alive(owner));
   if(!alive(owner))return;
   const applied=new Set(result.applied.map(target=>target.conversationId));
   setBulkSelection(previous=>new Map([...previous].filter(([id])=>!applied.has(id))));
   setBulkResult(previous=>bulkRetry&&previous
    ? {...result,applied:[...previous.applied,...result.applied],failed:[...previous.failed,...result.failed]}
    :result);
   setItems(previous=>previous.filter(item=>!applied.has(item.conversation_id)));
   if(selected&&applied.has(selected)){
    detailEpoch.current++;detailRequest.current?.abort();
    setSelected(null);setDetail(null);setTurns([]);setBefore(null);setRenaming(false);setLoading(false);
   }
   void loadList();
  }catch(reason){if(alive(owner))setBulkError(message(reason));}
  finally{if(alive(owner)){bulkInFlight.current=false;setBulkBusy(false);}}
 }

 useEffect(()=>{
  const singleDeleteFinished=bulkOperation==='delete'&&!bulkMode&&!bulkBusy&&bulkResult?.applied.length;
  if(lifecycleNotice&&!continuing||singleDeleteFinished)filterControl.current?.focus();
 },[lifecycleNotice,continuing,bulkOperation,bulkMode,bulkBusy,bulkResult]);
 const ownDetail=detail?.world_id===worldId?detail:null;
 const libraryBusy=continuing||bulkBusy;
 const bulkAction=filter==='trashed'?'restore':'trash';
 const bulkActionLabel=bulkAction==='restore'?'Restore selected':'Move selected to Trash';
 const appliedLabel=bulkOperation==='delete'?'permanently deleted':bulkOperation==='restore'?'restored':'moved to Trash';
 const batchDisabled=libraryBusy||!pointer||Boolean(continueDisabledReason)||Boolean(pendingResume.current);
 const confirmPlan=deletePlan?.worldId===worldId&&filter==='trashed'?deletePlan:null;
 return createPortal(<dialog ref={dialog} className="conversation-library" aria-label="Conversations" onKeyDown={event=>{
  if(!confirmPlan&&event.key==='Escape'&&actionMenu.current?.open){event.preventDefault();event.stopPropagation();actionMenu.current.open=false;actionMenu.current.querySelector('summary')?.focus();}
 }} onCancel={event=>{event.preventDefault();if(!bulkBusy&&!bulkRetry)onClose();}}>
  <header className="conversation-library__shell-header"><h2>Conversations</h2><button type="button" className="conversation-library__close" aria-label="Close conversations" disabled={bulkBusy||Boolean(bulkRetry)} onClick={onClose}>×</button></header>
  <div className="conversation-library__panes"><nav aria-label="Saved conversations">
   <div className="conversation-library__list-tools"><label>Show<select ref={filterControl} disabled={libraryBusy||Boolean(bulkRetry)} value={filter} onChange={event=>setFilter(event.target.value as Exclude<ConversationLibraryFilter,'all'|'archived'>)}><option value="recent">Recent</option><option value="explicitly_archived">Archived</option><option value="trashed">Trash</option></select></label>
    <button type="button" className="conversation-library__refresh" aria-label="Refresh conversations" title="Refresh conversations" disabled={listing||libraryBusy} onClick={()=>void loadList()}>↻</button></div>
   {onBulkLifecycle&&<div className="conversation-library__bulk">
    <button type="button" aria-pressed={bulkMode} disabled={libraryBusy||Boolean(bulkRetry)||Boolean(pendingResume.current)} onClick={()=>{
     setBulkMode(!bulkMode);setBulkSelection(new Map());setBulkResult(null);setBulkError('');setBulkOperation(null);
    }}>{bulkMode?'Done selecting':'Select conversations'}</button>
    {bulkMode&&<>
     <p role="status">{bulkSelection.size} selected in {filter==='trashed'?'Trash':filter==='explicitly_archived'?'Archived':'Recent'}</p>
     {!bulkRetry&&<button type="button" disabled={batchDisabled||!bulkSelection.size}
      onClick={()=>void applyBulk(makePlan(bulkAction,bulkSelection))}>{bulkActionLabel}</button>}
     {filter==='trashed'&&!bulkRetry&&<button type="button" disabled={batchDisabled||!bulkSelection.size}
      onClick={()=>setDeletePlan(makePlan('delete',bulkSelection))}>Delete selected permanently</button>}
    </>}
    {bulkRetry&&<>
     <button type="button" disabled={batchDisabled} onClick={()=>void applyBulk(bulkRetry)}>Retry unconfirmed action</button>
     <button type="button" disabled={bulkBusy} onClick={()=>{
      setBulkResult(previous=>previous&&{...previous,retry:null});setBulkSelection(new Map());void loadList();
     }}>Clear selection and refresh</button>
    </>}
    {bulkBusy&&<p role="status">{bulkOperation==='delete'?'Deleting conversations…':'Updating conversations…'}</p>}
    {bulkError&&<p role="alert">{bulkError}</p>}
    {bulkResult&&<>
     <p role="status">{bulkResult.applied.length} {appliedLabel}. {bulkResult.failed.length} failed. {bulkResult.stopped.length} {bulkRetry?'unconfirmed or waiting':'skipped'}.</p>
     <details><summary>Results by conversation</summary><ul>
      {bulkResult.applied.map(target=><li key={target.commandId}>{target.title}: {appliedLabel}</li>)}
      {bulkResult.failed.map(({target,reason})=><li key={target.commandId}>{target.title}: {reason}</li>)}
      {bulkResult.stopped.map((target,index)=><li key={target.commandId}>{target.title}: {bulkRetry&&index===0?'Result unconfirmed':'Awaiting your action'}</li>)}
     </ul></details>
    </>}
   </div>}
   {lifecycleNotice&&<p role="status">{lifecycleNotice}</p>}
   {listError&&<p role="alert">{listError}<button type="button" onClick={()=>void loadList()}>Retry list</button></p>}
   <div className="conversation-library__list"><ul>{(listOwner===worldId?items:[]).map(item=><li key={item.conversation_id} className={bulkMode?'conversation-library__selectable-row':undefined}>
    {bulkMode&&<input type="checkbox" aria-label={`Select ${item.title}`} checked={bulkSelection.has(item.conversation_id)}
     disabled={libraryBusy||Boolean(bulkRetry)} onChange={()=>toggleBulkSelection(item)}/>}
    <button type="button" disabled={libraryBusy} aria-pressed={selected===item.conversation_id} title={item.title} onClick={()=>void select(item.conversation_id)}>
    <strong>{item.title}</strong><span><span className={item.status==='active'?'conversation-library__current':undefined}>{item.status==='active'?'Current':item.status==='trashed'?'Trash':item.library_archived?'Archived':'Saved'}</span> · {item.turn_count} {item.turn_count===1?'turn':'turns'} · {new Date(item.updated_at).toLocaleDateString()}</span></button></li>)}</ul>
   {listing&&<p role="status">Loading conversations…</p>}{!listing&&!items.length&&!listError&&<p>{filter==='trashed'?'Trash is empty.':filter==='explicitly_archived'?'No archived conversations.':'No recent conversations.'}</p>}
   {next&&<button type="button" className="conversation-library__more" disabled={listing||libraryBusy} onClick={()=>void loadList(true)}>More conversations</button>}</div>
  </nav><section className="conversation-library__reader" aria-label="Selected conversation">
   {ownDetail&&<header className="conversation-library__conversation-header">
    <div className="conversation-library__heading"><h3 title={ownDetail.title}>{ownDetail.title}</h3><p>{ownDetail.status==='active'?'Current conversation':ownDetail.status==='trashed'?'In Trash':ownDetail.library_archived?'Archived conversation':'Saved conversation'} · Read-only transcript</p></div>
    <div className="conversation-library__actions">
     {onContinue&&ownDetail.status==='archived'&&<button type="button" className="conversation-library__primary" aria-label="Continue conversation" title={continueDisabledReason??'Your unsent message and references are kept. Saved pages and previous actions stay unchanged.'} disabled={loading||libraryBusy||bulkMode||!pointer||Boolean(continueDisabledReason)} onClick={()=>void continueSelected()}>{continuing?'Continuing…':'Continue conversation'}</button>}
     {onLifecycle&&ownDetail.status==='trashed'&&<button type="button" className="conversation-library__primary" disabled={loading||batchDisabled||bulkMode||Boolean(bulkRetry)} onClick={()=>void continueSelected('restore')}>{continuing?'Restoring…':'Restore conversation'}</button>}
     <details key={`${worldId}:${ownDetail.conversation_id}`} ref={actionMenu} className="conversation-library__action-menu"><summary aria-label="Conversation actions" title="Conversation actions">•••</summary><div className="conversation-library__menu">
      <button type="button" disabled={loading||libraryBusy} onClick={()=>{setRenaming(true);if(actionMenu.current)actionMenu.current.open=false;}}>Rename conversation</button>
      {onBulkLifecycle&&filter==='trashed'&&ownDetail.status==='trashed'&&<button type="button"
       disabled={loading||batchDisabled||bulkMode||Boolean(bulkRetry)} onClick={()=>
        setDeletePlan(makePlan('delete',new Map([[ownDetail.conversation_id,ownDetail.title]])))}>
       Delete permanently
      </button>}
      <fieldset className="conversation-library__exports" disabled={loading||libraryBusy}><ConversationExport key={`${worldId}:${ownDetail.conversation_id}`} worldId={worldId} conversationId={ownDetail.conversation_id}/></fieldset>
      {onLifecycle&&ownDetail.status!=='trashed'&&!ownDetail.library_archived&&<button type="button" disabled={loading||libraryBusy||bulkMode||!pointer||Boolean(continueDisabledReason)} onClick={()=>void continueSelected('archive')}>Archive conversation</button>}
      {onLifecycle&&ownDetail.status!=='trashed'&&<div className="conversation-library__trash-action"><button type="button" disabled={loading||libraryBusy||bulkMode||!pointer||Boolean(continueDisabledReason)} onClick={()=>void continueSelected('trash')}>{continuing?'Updating…':'Move to Trash'}</button><p>Recoverable in Trash. Saved pages are kept.</p></div>}
     </div></details>
    </div>
    {continueDisabledReason&&<p className="conversation-library__availability" role="status">{continueDisabledReason}</p>}
    {ownDetail.status==='trashed'&&<p className="conversation-library__availability">Restore this conversation to return it to history.</p>}
   </header>}
   {ownDetail&&renaming&&<form className="conversation-library__rename" onSubmit={event=>{event.preventDefault();void save();}}><label>Conversation name<input autoFocus value={title} onChange={event=>setTitle(event.target.value)} maxLength={160} disabled={saving}/></label><button type="submit" disabled={saving||!title.trim()}>{saving?'Saving…':'Save name'}</button><button type="button" disabled={saving} onClick={()=>{setTitle(ownDetail.title);setRenaming(false);}}>Cancel</button>{error&&<button type="button" onClick={()=>void reloadName()}>Reload saved name</button>}</form>}
   {ownDetail&&<div className="conversation-library__view-bar"><span>{fullDetails?'Full saved details':'Saved-message preview'}</span><button type="button" disabled={loading||libraryBusy||saving} title={fullDetails?'Return to the saved messages.':'Include references, saved objects and previous attempts.'} onClick={()=>{const details=!fullDetails;setFullDetails(details);void select(ownDetail.conversation_id,details,ownDetail);}}>{fullDetails?'Show message preview':'Load saved details'}</button></div>}
   <div className="conversation-library__transcript" aria-busy={loading}>
   {notice&&<p role="status">{notice}</p>}
   {error&&<p role="alert">{error}</p>}{loading&&<p role="status">Loading messages…</p>}
   {before!==null&&<button type="button" disabled={loading} onClick={()=>void olderTurns()}>Earlier messages</button>}
   {ownDetail&&groupRetryLineage(turns,t=>t.retry_context).map(({item:turn,historical})=>{const content=<article key={turn.turn_id}>
    <h3>You</h3><p className="conversation-library__question">{turn.user_text}</p>
    {turn.authored_references&&<SurfaceGraphReferenceInput worldId={worldId} label="Message references" readOnly value={turn.authored_references.references} onChange={()=>{}}/>}<h3>Buddy</h3>
    {turn.assistant_text&&<WorldPlanAgentAnswer answer={turn.assistant_text}/>}
    {turn.reply_object?.kind==='questions'&&<section aria-label="Saved clarifying questions"><h4>Clarifying questions</h4><ol>{turn.reply_object.questions.map((q,i)=><li key={i}>{q.text}</li>)}</ol></section>}
    {turn.reply_object?.kind==='page_object'&&<p>{turn.reply_object.object_kind==='plan'?'Work plan proposed on page.':turn.reply_object.object_kind==='connected_page'?'Connected-page review prepared.':'Relationship review prepared.'}{' '}<a href={'/'+turn.reply_object.source.surface_id+'?'+new URLSearchParams({world:turn.reply_object.source.world_id,documentId:turn.reply_object.source.document_id})}>Open source page</a></p>}
    {!turn.assistant_text&&!turn.reply_object&&<p>{!fullDetails&&turn.status==='completed'?'Load saved details to inspect this reply.':['failed','interrupted'].includes(turn.status)?'This reply did not finish.':['accepted','running'].includes(turn.status)?'Reply in progress.':'No saved reply.'}</p>}
    {fullDetails&&turn.retry_context&&<ConversationRetryAttempts context={turn.retry_context}/>}
    {fullDetails&&<SavedTurnTrace worldId={worldId} conversationId={ownDetail.conversation_id} turnId={turn.turn_id} status={turn.status}/>}

   </article>;return historical?<details key={turn.turn_id}><summary>Earlier attempt of a request with a later response</summary>{content}</details>:content;})}
   {ownDetail&&!loading&&!turns.length&&<p>No messages in this conversation yet.</p>}
  </div></section></div>
  {confirmPlan&&<ConfirmConversationDeletion plan={confirmPlan} disabled={batchDisabled}
   onDismiss={()=>setDeletePlan(null)} onConfirm={()=>void applyBulk(confirmPlan)}/>}
 </dialog>,document.body);
}

function ConfirmConversationDeletion({plan,disabled,onDismiss,onConfirm}:{
 plan:BulkConversationPlan;disabled:boolean;onDismiss:()=>void;onConfirm:()=>void;
}){
 const dialog=useRef<HTMLDialogElement>(null);
 useLayoutEffect(()=>{
  const element=dialog.current;
  element?.showModal();
  return ()=>{if(element?.open)element.close();};
 },[]);
 const count=plan.targets.length;
 return <dialog ref={dialog} className="conversation-library__delete-confirm"
  aria-labelledby="conversation-delete-title" aria-describedby="conversation-delete-impact"
  onCancel={event=>{event.preventDefault();event.stopPropagation();onDismiss();}}>
  <h3 id="conversation-delete-title">Permanently delete {count===1?'this conversation':count+' conversations'}?</h3>
  <ul aria-label="Conversations to delete">
   {plan.targets.map(target=><li key={target.conversationId}>{target.title}</li>)}
  </ul>
  <p id="conversation-delete-impact">
   Messages, drafts, and traces will be removed from Buddy. Saved World work stays available.
   Recovery backups may retain copies. You can’t undo this.
  </p>
  <div className="conversation-library__delete-actions">
   <button type="button" onClick={onDismiss}>Cancel</button>
   <button type="button" className="conversation-library__delete-submit" disabled={disabled} onClick={onConfirm}>Delete permanently</button>
  </div>
 </dialog>;
}

function SavedTurnTrace({worldId,conversationId,turnId,status}:{worldId:string;conversationId:string;turnId:string;status:string}){
 const [open,setOpen]=useState(false);
 const lifecycle=(['accepted','running','completed','failed','interrupted'] as const).find(value=>value===status);
 const view=<details onToggle={event=>setOpen(event.currentTarget.open)}><summary>Trace</summary>
  {open&&(lifecycle?<BuddyContextTraceLoader enabled worldId={worldId} conversationId={conversationId} turnId={turnId}/>
   :<p role="alert">This saved turn has an unsupported status. Its trace cannot be inspected.</p>)}
 </details>;
 return lifecycle?<BuddyTurnInspection worldId={worldId} conversationId={conversationId} turnId={turnId} lifecycle={lifecycle}>{view}</BuddyTurnInspection>:view;
}
