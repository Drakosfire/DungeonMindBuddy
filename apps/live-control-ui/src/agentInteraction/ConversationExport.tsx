import {useEffect,useRef,useState} from 'react';
import {collectConversationExport,downloadConversationExport,type ConversationExportFormat} from './conversationExport';

export function ConversationExport({worldId,conversationId}:{worldId:string;conversationId:string}){
 const binding=JSON.stringify([worldId,conversationId]);
 const owner=useRef({binding});if(owner.current.binding!==binding)owner.current={binding};
 const mounted=useRef(true),busyRef=useRef(false);
 const [busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[error,setError]=useState('');
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{busyRef.current=false;setBusy(false);setNotice('');setError('');},[binding]);
 async function save(format:ConversationExportFormat){
  if(busyRef.current)return;const captured=owner.current;
  const check=()=>{if(!mounted.current||owner.current!==captured)throw new Error('Export selection retired.');};
  busyRef.current=true;setBusy(true);setNotice('');setError('');
  try{const file=await collectConversationExport(worldId,conversationId,format,check);check();downloadConversationExport(file);setNotice('Conversation download prepared.');}
  catch(reason){if(mounted.current&&owner.current===captured)setError(reason instanceof Error?reason.message:'Conversation export is unavailable.');}
  finally{if(mounted.current&&owner.current===captured){busyRef.current=false;setBusy(false);}}
 }
 return <div role="group" aria-label="Export conversation">
  <button type="button" disabled={busy} onClick={()=>void save('readable')}>Export conversation</button>
  <button type="button" disabled={busy} onClick={()=>void save('diagnostic')}>Export with diagnostics</button>
  {busy&&<p role="status">Collecting the full retained conversation…</p>}
  {notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}</p>}
 </div>;
}
