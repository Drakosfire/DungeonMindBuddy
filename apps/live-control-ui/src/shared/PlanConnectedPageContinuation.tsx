import {useState} from 'react';
import type {ConnectedPageOperation} from '../api/connectedPageApi';
import {useConversationComposerDrafts} from '../agentInteraction/conversationComposerDrafts';
import {navigatePrimaryAppHref} from '../chrome/appNavigation';

/** Continue only after confirmed creation; the existing Build composer owns the next Ask. */
export function PlanConnectedPageContinuation({operation,worldId,ownerDocumentId,originalRequest}:{
 operation:ConnectedPageOperation;worldId:string;ownerDocumentId:string;originalRequest?:string;
}) {
 const {composerDrafts,setComposerDrafts,composerDraftWarning}=useConversationComposerDrafts(worldId);
 const [error,setError]=useState('');
 if(operation.phase!=='complete'||!operation.page||operation.intent.world_id!==worldId
   ||operation.page.world_id!==worldId||!('kind' in operation.intent.origin)
   ||typeof originalRequest!=='string'||!originalRequest.trim())return null;
 const destination=operation.intent.origin.document_id;
 const message=`The page “${operation.intent.title}” has been created. Keep it as a scaffold; do not recreate or develop it. Continue only the remaining requested edits on this source page.

Original request:
${originalRequest}`;
 return <section aria-label="Continue page work">
  <p>Continue on the saved source page in Build. Review the remaining request before sending.</p>
  {error&&<p role="alert">{error}</p>}
  <button type="button" onClick={()=>{
   const query=new URLSearchParams(window.location.search);
   if(window.location.pathname!=='/plan'||query.get('world')!==worldId||query.get('documentId')!==ownerDocumentId){setError('The Plan destination changed. Reopen its completed page review.');return;}
   const key=`build:${destination}`,existing=composerDrafts[key]??'';
   if(composerDraftWarning){setError(composerDraftWarning);return;}
   if(existing&&existing!==message){setError('Build has an unsent message on this page. Keep or send it before continuing this request.');return;}
   setComposerDrafts(drafts=>drafts[key]===message?drafts:{...drafts,[key]:message});
   navigatePrimaryAppHref('/build?'+new URLSearchParams({world:worldId,documentId:destination,campaign:worldId}));
  }}>Continue on source page in Build</button>
 </section>;
}
