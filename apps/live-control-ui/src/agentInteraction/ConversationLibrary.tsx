import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {listConversations,readConversationName,readConversationTurns,renameConversation,type ConversationSummary,type LibraryTurn} from '../api/conversationLibraryApi';
import {WorldPlanAgentAnswer} from '../planSurface/components/WorldPlanAgentAnswer';
import {BuddyContextTraceLoader} from '../planSurface/components/BuddyContextTraceLoader';
import './ConversationLibrary.css';
const message=(error:unknown)=>error instanceof Error?error.message:'The conversation could not be read.';
export function ConversationLibrary({worldId,onClose}:{worldId:string;onClose:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null),mounted=useRef(true),scope=useRef({worldId});
 if(scope.current.worldId!==worldId)scope.current={worldId};
 const listEpoch=useRef(0),detailEpoch=useRef(0),pageBusy=useRef(false);
 const [filter,setFilter]=useState<'all'|'archived'>('all'),[items,setItems]=useState<ConversationSummary[]>([]),[listOwner,setListOwner]=useState(worldId);
 const [next,setNext]=useState<string|null>(null),[listing,setListing]=useState(true),[listError,setListError]=useState('');
 const [selected,setSelected]=useState<string|null>(null),[detail,setDetail]=useState<ConversationSummary|null>(null),[turns,setTurns]=useState<LibraryTurn[]>([]);
 const [before,setBefore]=useState<number|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const [title,setTitle]=useState(''),[saving,setSaving]=useState(false),[notice,setNotice]=useState('');
 useEffect(()=>{mounted.current=true;dialog.current?.showModal();return()=>{mounted.current=false;listEpoch.current++;detailEpoch.current++;};},[]);
 const alive=(owner:typeof scope.current)=>mounted.current&&scope.current===owner;
 async function select(id:string){
  const owner=scope.current,epoch=++detailEpoch.current;
  setSelected(id);setDetail(null);setTurns([]);setBefore(null);setLoading(true);setSaving(false);setError('');setNotice('');
  try{const [meta,page]=await Promise.all([readConversationName(worldId,id),readConversationTurns(worldId,id)]);
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
  try{const page=await readConversationTurns(worldId,id,cursor);if(!alive(owner)||epoch!==detailEpoch.current)return;
   setTurns(old=>[...new Map([...page.turns,...old].map(turn=>[turn.turn_id,turn])).values()].sort((a,b)=>a.sequence-b.sequence));setBefore(page.next_before_sequence);
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
  finally{if(alive(owner)&&epoch===detailEpoch.current)setLoading(false);}
 }
 async function save(){
  if(!detail||saving)return;
  const owner=scope.current,epoch=detailEpoch.current,id=detail.conversation_id;setSaving(true);setError('');setNotice('');
  try{const renamed=await renameConversation(worldId,id,title,detail.name_revision);if(!alive(owner)||epoch!==detailEpoch.current)return;
   setDetail(renamed);setItems(old=>old.map(item=>item.conversation_id===id?renamed:item));setNotice('Name saved.');
  }catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason)+' Your typed name is kept; retry or reload the saved name.');}
  finally{if(alive(owner)&&epoch===detailEpoch.current)setSaving(false);}
 }
 async function reloadName(){
  if(!selected)return;const owner=scope.current,epoch=++detailEpoch.current,id=selected;setSaving(false);setError('');setNotice('');
  try{const meta=await readConversationName(worldId,id);if(alive(owner)&&epoch===detailEpoch.current){setDetail(meta);setTitle(meta.title);}}
  catch(reason){if(alive(owner)&&epoch===detailEpoch.current)setError(message(reason));}
 }
 const ownDetail=detail?.world_id===worldId?detail:null;
 return createPortal(<dialog ref={dialog} className="conversation-library" aria-label="Conversations" onCancel={event=>{event.preventDefault();onClose();}}>
  <header><h2>Conversations</h2><button type="button" aria-label="Close conversations" onClick={onClose}>×</button></header>
  <div className="conversation-library__panes"><nav aria-label="Saved conversations">
   <label>Show<select value={filter} onChange={event=>setFilter(event.target.value as 'all'|'archived')}><option value="all">All conversations</option><option value="archived">Archived conversations</option></select></label>
   {listError&&<p role="alert">{listError}<button type="button" onClick={()=>void loadList()}>Retry list</button></p>}
   <ul>{(listOwner===worldId?items:[]).map(item=><li key={item.conversation_id}><button type="button" aria-pressed={selected===item.conversation_id} onClick={()=>void select(item.conversation_id)}>
    <strong>{item.title}</strong><span>{item.status==='active'?'Current':'Archived'} · {item.turn_count} turns · {new Date(item.updated_at).toLocaleDateString()}</span></button></li>)}</ul>
   {listing&&<p role="status">Loading conversations…</p>}{!listing&&!items.length&&!listError&&<p>No conversations yet.</p>}
   {next&&<button type="button" disabled={listing} onClick={()=>void loadList(true)}>More conversations</button>}
  </nav><section className="conversation-library__reader" aria-label="Selected conversation">
   {ownDetail&&<><form onSubmit={event=>{event.preventDefault();void save();}}><label>Conversation name<input value={title} onChange={event=>setTitle(event.target.value)} maxLength={160} disabled={saving}/></label>
    <button type="submit" disabled={saving||!title.trim()}>{saving?'Saving…':'Save name'}</button>{error&&<button type="button" onClick={()=>void reloadName()}>Reload saved name</button>}</form>
    <p>{ownDetail.status==='active'?'Current conversation':'Archived conversation'} · Read-only transcript</p>{notice&&<p role="status">{notice}</p>}</>}
   {error&&<p role="alert">{error}</p>}{loading&&<p role="status">Loading messages…</p>}
   {before!==null&&<button type="button" disabled={loading} onClick={()=>void olderTurns()}>Earlier messages</button>}
   {ownDetail&&turns.map(turn=><article key={turn.turn_id}><h3>You</h3><p className="conversation-library__question">{turn.user_text}</p><h3>Buddy</h3>
    {turn.assistant_text&&<WorldPlanAgentAnswer answer={turn.assistant_text}/>}
    {turn.reply_object?.kind==='questions'&&<section aria-label="Saved clarifying questions"><h4>Clarifying questions</h4><ol>{turn.reply_object.questions.map((q,i)=><li key={i}>{q.text}</li>)}</ol></section>}
    {turn.reply_object?.kind==='page_object'&&<p>{turn.reply_object.object_kind==='plan'?'Work plan proposed on page.':turn.reply_object.object_kind==='connected_page'?'Connected-page review prepared.':'Relationship review prepared.'}{' '}<a href={'/build?'+new URLSearchParams({world:turn.reply_object.source.world_id,documentId:turn.reply_object.source.document_id})}>Open source page</a></p>}
    {!turn.assistant_text&&!turn.reply_object&&<p>{['failed','interrupted'].includes(turn.status)?'This reply did not finish.':['accepted','running'].includes(turn.status)?'Reply in progress.':'No saved reply.'}</p>}
    <SavedTurnTrace worldId={worldId} conversationId={ownDetail.conversation_id} turnId={turn.turn_id}/>

   </article>)}
   {ownDetail&&!loading&&!turns.length&&<p>No messages in this conversation yet.</p>}
  </section></div>
 </dialog>,document.body);
}

function SavedTurnTrace({worldId,conversationId,turnId}:{worldId:string;conversationId:string;turnId:string}){
 const [open,setOpen]=useState(false);
 return <details onToggle={event=>setOpen(event.currentTarget.open)}><summary>Trace</summary>
  {open&&<BuddyContextTraceLoader enabled worldId={worldId} conversationId={conversationId} turnId={turnId}/>}
 </details>;
}
