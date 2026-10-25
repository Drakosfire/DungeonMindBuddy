import {useEffect,useRef,useState} from 'react';
import type {ConversationRelationshipProposal} from '../../api/types';
import type {DocumentRelationshipIntent} from '../../api/graphDocumentRelationshipApi';
import {useRelationshipReviewHost} from '../../buildSurface/relationshipReviewHost';
export function ConversationRelationshipReview({worldId,documentId,source,proposal,disabled}:{worldId:string;documentId:string;source:DocumentRelationshipIntent['document_source'];proposal:ConversationRelationshipProposal;disabled:boolean}){
 const host=useRelationshipReviewHost(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const identity=JSON.stringify([worldId,documentId,source,proposal]);const current=useRef<string|null>(identity);current.current=identity;
 useEffect(()=>()=>{current.current=null;},[]);
 return <section className="conversation-workbook" aria-label="Proposed relationship"><h4>Relationship</h4><blockquote>{proposal.quote}</blockquote>
 <p>{proposal.source.label} → {proposal.label} → {proposal.target.label}</p><p>{proposal.context}</p>
 <p>Review identities and support before publishing.</p>{error&&<p role="alert">{error}</p>}
 <button type="button" disabled={disabled||busy||!host||host.worldId!==worldId||host.documentId!==documentId} onClick={()=>{
  if(!host)return;const captured=identity;setBusy(true);setError('');
  void host.open({world_id:worldId,document_source:source,quote:proposal.quote,source:{node_id:null,...proposal.source},target:{node_id:null,...proposal.target},predicate:proposal.predicate,label:proposal.label,context:proposal.context})
   .catch(e=>{if(current.current===captured)setError(e instanceof Error?e.message:String(e));}).finally(()=>{if(current.current===captured)setBusy(false);});
 }}>{busy?'Opening review…':'Review relationship'}</button></section>;
}
