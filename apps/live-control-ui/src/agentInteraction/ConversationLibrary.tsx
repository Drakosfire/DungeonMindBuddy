import {SurfaceGraphReferenceInput} from '../surface/SurfaceGraphReferenceInput';
import {ConversationExport} from './ConversationExport';
import {LiveApiError} from '../api/liveApi';
import {groupRetryLineage} from './conversationAttemptGroups';
import {ConversationRetryAttempts} from './ConversationRetryAttempts';
import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {listConversations,readConversationName,readConversationTurns,readConversationMessages,renameConversation,type ConversationSummary,type LibraryTurn,type ResumeConversationCommand,type ConversationLifecycleOperation} from '../api/conversationLibraryApi';
import {WorldPlanAgentAnswer} from '../planSurface/components/WorldPlanAgentAnswer';
import {BuddyContextTraceLoader} from '../planSurface/components/BuddyContextTraceLoader';
import {BuddyTurnInspection} from '../planSurface/components/BuddyTurnInspection';
import './ConversationLibrary.css';
const message=(error:unknown)=>error instanceof Error?error.message:'The conversation could not be read.';
export function ConversationLibrary({worldId,onClose,pointer,onContinue,onLifecycle,continueDisabledReason}:{worldId:string;onClose:()=>void;pointer?:{revision:number;activeId:string|null};onContinue?:(command:ResumeConversationCommand)=>Promise<void>;onLifecycle?:(command:ResumeConversationCommand,operation:ConversationLifecycleOperation)=>Promise<void>;continueDisabledReason?:string|null}){
 const [renaming,setRenaming]=useState(false);
 const actionMenu=useRef<HTMLDetailsElement>(null);
 const [fullDetails,setFullDetails]=useState(false);
 const [continuing,setContinuing]=useState(false);
 const pendingOperation=useRef<'reopen'|ConversationLifecycleOperation|null>(null);
 const pendingResume=useRef<ResumeConversationCommand|null>(null),continueInFlight=useRef(false);
 useEffect(()=>{pendingResume.current=null;pendingOperation.current=null;continueInFlight.current=false;setContinuing(false);},[worldId]);
 const dialog=useRef<HTMLDialogElement>(null),mounted=useRef(true),scope=useRef({worldId});
 if(scope.current.worldId!==worldId)scope.current={worldId};
 const listEpoch=useRef(0),detailEpoch=useRef(0),pageBusy=useRef(false);
 const [filter,setFilter]=useState<'all'|'archived'|'trashed'>('all'),[items,setItems]=useState<ConversationSummary[]>([]),[listOwner,setListOwner]=useState(worldId);
 const [next,setNext]=useState<string|null>(null),[listing,setListing]=useState(true),[listError,setListError]=useState('');
 const [selected,setSelected]=useState<string|null>(null),[detail,setDetail]=useState<ConversationSummary|null>(null),[turns,setTurns]=useState<LibraryTurn[]>([]);
 const [before,setBefore]=useState<number|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const [title,setTitle]=useState(''),[saving,setSaving]=useState(false),[notice,setNotice]=useState('');
 useEffect(()=>{mounted.current=true;dialog.current?.showModal();return()=>{mounted.current=false;listEpoch.current++;detailEpoch.current++;};},[]);
 const alive=(owner:typeof scope.current)=>mounted.current&&scope.current===owner;
 async function readPage(id:string,before?:number,details=fullDetails){
  if(details)return readConversationTurns(worldId,id,before);
  const page=await readConversationMessages(worldId,id,before);
  return {turns:page.messages.map(row=>({...row,reply_object:null,retry_context:null})),next_before_sequence:page.next_before_sequence};
 }
 async function select(id:string,details=fullDetails){
  const owner=scope.current,epoch=++detailEpoch.current;
  setSelected(id);setRenaming(false);if(id!==selected||detail?.world_id!==worldId)setDetail(null);setTurns([]);setBefore(null);setLoading(true);setSaving(false);setError('');setNotice('');
  try{const [meta,page]=await Promise.all([readConversationName(worldId,id),readPage(id,undefined,details)]);
   if(!alive(owner)||epoch!==detailEpoch.current)return;setDetail(meta);setTitle(meta.title);setTurns(page.turns);setBefore(page.next_before_sequence);
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
  finally{if(alive(owner)&&epoch===detailEpoch.current)setLoading(false);}
 }
 async function loadList(older=false){
  if(older&&pageBusy.current)return;
  const owner=scope.current,epoch=++listEpoch.current;pageBusy.current=true;setListing(true);setListError('');
  try{const page=await listConversations(worldId,filter,older?next??undefined:undefined);
   if(!alive(owner)||epoch!==listEpoch.current)return;
   setListOwner(worldId);setItems(old=>older?[...new Map([...old,...page.items].map(item=>[item.conversation_id,item])).values()]:page.items);setNext(page.next_before);
   if(!older&&page.items.length)void select(page.items.find(item=>item.status==='active')?.conversation_id??page.items[0].conversation_id);
  }catch(reason){if(alive(owner)&&epoch===listEpoch.current)setListError(message(reason));}
  finally{if(alive(owner)&&epoch===listEpoch.current){setListing(false);pageBusy.current=false;}}
 }
 useEffect(()=>{detailEpoch.current++;setItems([]);setSelected(null);setDetail(null);setTurns([]);setNext(null);void loadList();return()=>{listEpoch.current++;detailEpoch.current++;};},[worldId,filter]);
 async function olderTurns(){
  if(!selected||before===null||loading)return;
  const owner=scope.current,epoch=detailEpoch.current,id=selected,cursor=before;setLoading(true);setError('');
  try{const page=await readPage(id,cursor);if(!alive(owner)||epoch!==detailEpoch.current)return;
   setTurns(old=>[...new Map([...page.turns,...old].map(turn=>[turn.turn_id,turn])).values()].sort((a,b)=>a.sequence-b.sequence));setBefore(page.next_before_sequence);
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
  finally{if(alive(owner)&&epoch===detailEpoch.current)setLoading(false);}
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
  try{const meta=await readConversationName(worldId,id);if(alive(owner)&&epoch===detailEpoch.current){setDetail(meta);setTitle(meta.title);}}
  catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
 }
 async function continueSelected(operation:'reopen'|ConversationLifecycleOperation='reopen'){
  if(!detail||!pointer||continueInFlight.current||continuing||continueDisabledReason)return;
  if(operation==='reopen'?(detail.status!=='archived'||!onContinue):!onLifecycle)return;
  const owner=scope.current,id=detail.conversation_id;
  if(pendingResume.current&&(pendingResume.current.conversation_id!==id||pendingOperation.current!==operation)){setError('Refresh the current conversation before switching to another.');return;}
  const command=pendingResume.current??{world_id:worldId,conversation_id:id,command_id:crypto.randomUUID(),expected_pointer_revision:pointer.revision,expected_active_conversation_id:pointer.activeId};
  pendingResume.current=command;pendingOperation.current=operation;continueInFlight.current=true;setContinuing(true);setError('');
  try{if(operation==='reopen')await onContinue!(command);else await onLifecycle!(command,operation);if(alive(owner)){pendingResume.current=null;pendingOperation.current=null;void loadList();}}
  catch(reason){if(alive(owner)){
   if(reason instanceof LiveApiError&&reason.status===409){pendingResume.current=null;pendingOperation.current=null;setError('The switch was rejected because the conversation changed. Refresh conversations, then choose Continue again.');}
   else setError(message(reason)+' Refresh conversations to check the current selection, or retry this same switch.');
  }}
  finally{if(alive(owner)){continueInFlight.current=false;setContinuing(false);}}
 }
 const ownDetail=detail?.world_id===worldId?detail:null;
 return createPortal(<dialog ref={dialog} className="conversation-library" aria-label="Conversations" onKeyDown={event=>{
  if(event.key==='Escape'&&actionMenu.current?.open){event.preventDefault();event.stopPropagation();actionMenu.current.open=false;actionMenu.current.querySelector('summary')?.focus();}
 }} onCancel={event=>{event.preventDefault();onClose();}}>
  <header className="conversation-library__shell-header"><h2>Conversations</h2><button type="button" className="conversation-library__close" aria-label="Close conversations" onClick={onClose}>×</button></header>
  <div className="conversation-library__panes"><nav aria-label="Saved conversations">
   <div className="conversation-library__list-tools"><label>Show<select value={filter} onChange={event=>setFilter(event.target.value as 'all'|'archived'|'trashed')}><option value="all">All conversations</option><option value="archived">Archived conversations</option><option value="trashed">Trash</option></select></label>
    <button type="button" className="conversation-library__refresh" aria-label="Refresh conversations" title="Refresh conversations" disabled={listing||continuing} onClick={()=>void loadList()}>↻</button></div>
   {listError&&<p role="alert">{listError}<button type="button" onClick={()=>void loadList()}>Retry list</button></p>}
   <div className="conversation-library__list"><ul>{(listOwner===worldId?items:[]).map(item=><li key={item.conversation_id}><button type="button" aria-pressed={selected===item.conversation_id} title={item.title} onClick={()=>void select(item.conversation_id)}>
    <strong>{item.title}</strong><span><span className={item.status==='active'?'conversation-library__current':undefined}>{item.status==='active'?'Current':item.status==='trashed'?'Trash':'Archived'}</span> · {item.turn_count} {item.turn_count===1?'turn':'turns'} · {new Date(item.updated_at).toLocaleDateString()}</span></button></li>)}</ul>
   {listing&&<p role="status">Loading conversations…</p>}{!listing&&!items.length&&!listError&&<p>No conversations yet.</p>}
   {next&&<button type="button" className="conversation-library__more" disabled={listing} onClick={()=>void loadList(true)}>More conversations</button>}</div>
  </nav><section className="conversation-library__reader" aria-label="Selected conversation">
   {ownDetail&&<header className="conversation-library__conversation-header">
    <div className="conversation-library__heading"><h3 title={ownDetail.title}>{ownDetail.title}</h3><p>{ownDetail.status==='active'?'Current conversation':ownDetail.status==='trashed'?'In Trash':'Archived conversation'} · Read-only transcript</p></div>
    <div className="conversation-library__actions">
     {onContinue&&ownDetail.status==='archived'&&<button type="button" className="conversation-library__primary" aria-label="Continue conversation" title={continueDisabledReason??'Your unsent message and references are kept. Saved pages and previous actions stay unchanged.'} disabled={loading||continuing||!pointer||Boolean(continueDisabledReason)} onClick={()=>void continueSelected()}>{continuing?'Continuing…':'Continue conversation'}</button>}
     {onLifecycle&&ownDetail.status==='trashed'&&<button type="button" className="conversation-library__primary" disabled={loading||continuing||!pointer||Boolean(continueDisabledReason)} onClick={()=>void continueSelected('restore')}>{continuing?'Restoring…':'Restore conversation'}</button>}
     <details key={`${worldId}:${ownDetail.conversation_id}`} ref={actionMenu} className="conversation-library__action-menu"><summary aria-label="Conversation actions" title="Conversation actions">•••</summary><div className="conversation-library__menu">
      <button type="button" disabled={loading||continuing} onClick={()=>{setRenaming(true);if(actionMenu.current)actionMenu.current.open=false;}}>Rename conversation</button>
      <fieldset className="conversation-library__exports" disabled={loading||continuing}><ConversationExport key={`${worldId}:${ownDetail.conversation_id}`} worldId={worldId} conversationId={ownDetail.conversation_id}/></fieldset>
      {onLifecycle&&ownDetail.status!=='trashed'&&<div className="conversation-library__trash-action"><button type="button" disabled={loading||continuing||!pointer||Boolean(continueDisabledReason)} onClick={()=>void continueSelected('trash')}>{continuing?'Updating…':'Move to Trash'}</button><p>Recoverable in Trash. Saved pages are kept.</p></div>}
     </div></details>
    </div>
    {continueDisabledReason&&<p className="conversation-library__availability" role="status">{continueDisabledReason}</p>}
    {ownDetail.status==='trashed'&&<p className="conversation-library__availability">Restore to history, then choose Continue when ready.</p>}
   </header>}
   {ownDetail&&renaming&&<form className="conversation-library__rename" onSubmit={event=>{event.preventDefault();void save();}}><label>Conversation name<input autoFocus value={title} onChange={event=>setTitle(event.target.value)} maxLength={160} disabled={saving}/></label><button type="submit" disabled={saving||!title.trim()}>{saving?'Saving…':'Save name'}</button><button type="button" disabled={saving} onClick={()=>{setTitle(ownDetail.title);setRenaming(false);}}>Cancel</button>{error&&<button type="button" onClick={()=>void reloadName()}>Reload saved name</button>}</form>}
   {ownDetail&&<div className="conversation-library__view-bar"><span>{fullDetails?'Full saved details':'Saved-message preview'}</span><button type="button" disabled={loading||continuing} title={fullDetails?'Return to the saved messages.':'Include references, saved objects and previous attempts.'} onClick={()=>{const details=!fullDetails;setFullDetails(details);void select(ownDetail.conversation_id,details);}}>{fullDetails?'Show message preview':'Load saved details'}</button></div>}
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
 </dialog>,document.body);
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
