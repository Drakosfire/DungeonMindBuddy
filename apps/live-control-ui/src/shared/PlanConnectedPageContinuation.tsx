import {useEffect,useId,useState} from 'react';
import {listWorkspaceDocuments} from '../api/liveApi';
import type {WorkspaceDocumentRecord} from '../api/types';
import type {ConnectedPageOperation} from '../api/connectedPageApi';
import {useConversationComposerDrafts} from '../agentInteraction/conversationComposerDrafts';
import {navigatePrimaryAppHref} from '../chrome/appNavigation';

/** Continue only after confirmed creation; the existing Build composer owns the next Ask. */
export function PlanConnectedPageContinuation({operation,worldId,ownerDocumentId,originalRequest}:{
 operation:ConnectedPageOperation;worldId:string;ownerDocumentId:string;originalRequest?:string;
}) {
 const {composerDrafts,setComposerDrafts,composerDraftWarning}=useConversationComposerDrafts(worldId);
 const [error,setError]=useState(''),[documents,setDocuments]=useState<{world:string;records:WorkspaceDocumentRecord[]}|null>(null),[destination,setDestination]=useState(''),[retry,setRetry]=useState(0);
 const selectId=useId(),hasRequest=typeof originalRequest==='string'&&Boolean(originalRequest.trim());
 useEffect(()=>{
  let current=true;setDocuments(null);setDestination('');setError('');
  if(operation.phase!=='complete'||operation.intent.world_id!==worldId||operation.page?.world_id!==worldId||!hasRequest)return;
  listWorkspaceDocuments({world_id:worldId,kind:'worldbuilding_source',status:'active'}).then(list=>{
   if(current)setDocuments({world:worldId,records:list.records.filter(record=>record.world_id===worldId&&record.kind==='worldbuilding_source'&&record.status==='active'&&record.document_id!==operation.page!.document_id)});
  }).catch(()=>{if(current)setError('Build pages could not be loaded.');});
  return()=>{current=false;};
 },[worldId,operation.operation_id,operation.phase,operation.page?.document_id,operation.page?.world_id,operation.intent.world_id,hasRequest,retry]);
 if(operation.phase!=='complete'||!operation.page||operation.intent.world_id!==worldId
   ||operation.page.world_id!==worldId||!('kind' in operation.intent.origin)
   ||!hasRequest)return null;
 const pages=documents?.world===worldId?documents.records:[];
 const chosen=pages.find(page=>page.document_id===destination);
 const message=`The page “${operation.intent.title}” has been created. Keep it as a scaffold; do not recreate or develop it. Continue only the remaining requested edits on this selected page.

Original request:
${originalRequest}`;
 return <section aria-label="Continue page work">
  <p>Choose where to finish the remaining edits in Build. Review the request before sending.</p>
  <label htmlFor={selectId}>Continue work on</label><select id={selectId} value={destination} onChange={event=>setDestination(event.target.value)} disabled={!documents}><option value="">Choose an existing page</option>{pages.map(page=><option key={page.document_id} value={page.document_id}>{page.title}</option>)}</select>
  {error&&<p role="alert">{error}</p>}
  {error==='Build pages could not be loaded.'&&<button type="button" onClick={()=>setRetry(n=>n+1)}>Retry Build pages</button>}
  <button type="button" disabled={!chosen} onClick={()=>{
   const query=new URLSearchParams(window.location.search);
   if(window.location.pathname!=='/plan'||query.get('world')!==worldId||query.get('documentId')!==ownerDocumentId){setError('The Plan destination changed. Reopen its completed page review.');return;}
   if(!chosen)return;
   const key=`build:${chosen.document_id}`,existing=composerDrafts[key]??'';
   if(composerDraftWarning){setError(composerDraftWarning);return;}
   if(existing&&existing!==message){setError('Build has an unsent message on this page. Keep or send it before continuing this request.');return;}
   setComposerDrafts(drafts=>drafts[key]===message?drafts:{...drafts,[key]:message});
   navigatePrimaryAppHref('/build?'+new URLSearchParams({world:worldId,documentId:chosen.document_id,campaign:worldId}));
  }}>Continue in Build</button>
 </section>;
}
