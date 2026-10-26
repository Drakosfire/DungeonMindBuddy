import {useEffect,useRef,useState} from 'react';
import type {ConversationConnectedPageProposal} from '../../api/types';
import {getAgentConnectedPageOrigin} from '../../api/liveApi';
import {exact} from '../../shared/sourcePassageProtocol';
import {useConnectedPageReviewHost} from '../../buildSurface/connectedPageReviewHost';
import type {SavedExcerptOrigin} from '../../api/connectedPageApi';

export async function connectedReviewOrigin(raw:unknown,worldId:string,turnId:string,p:ConversationConnectedPageProposal):Promise<SavedExcerptOrigin>{
 if(!exact(raw,['schema','world_id','turn_id','read_id','origin'])||raw.schema!=='dmb_agent_connected_page_origin_v1'||raw.world_id!==worldId||raw.turn_id!==turnId||raw.read_id!==p.read_id
   ||!exact(raw.origin,['kind','document_id','revision','content_sha256','line_start','line_end','selected_text']))throw new Error('This excerpt belongs to another source or turn.');
 const o=raw.origin;
 if(o.kind!=='saved_page_excerpt'||typeof o.document_id!=='string'||!/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(o.document_id)||!Number.isSafeInteger(o.revision)||(o.revision as number)<1
   ||typeof o.content_sha256!=='string'||!/^[a-f0-9]{64}$/.test(o.content_sha256)||!Number.isSafeInteger(o.line_start)||!Number.isSafeInteger(o.line_end)||(o.line_start as number)<1||(o.line_end as number)<(o.line_start as number)
   ||typeof o.selected_text!=='string'||!o.selected_text.trim()||o.selected_text.length>4000||o.selected_text.split('\n').length!==(o.line_end as number)-(o.line_start as number)+1)throw new Error('The captured saved excerpt is invalid.');
 const start=o.selected_text.indexOf(p.quote);
 if(start<0||o.selected_text.indexOf(p.quote,start+1)>=0)throw new Error('The proposed quote does not identify one exact saved occurrence.');
 return o as unknown as SavedExcerptOrigin;
}
export function ConversationConnectedPageReview({worldId,documentId,turnId,proposal,disabled}:{worldId:string;documentId:string;turnId:string;proposal:ConversationConnectedPageProposal;disabled:boolean}){
 const host=useConnectedPageReviewHost(),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null);
 const identity=JSON.stringify([worldId,documentId,turnId,proposal]);const current=useRef<string|null>(identity);current.current=identity;
 useEffect(()=>()=>{current.current=null;},[]);
 const active=useRef(host);active.current=host;
 return <section className="conversation-workbook" aria-label="Proposed connected page"><h4>{proposal.title}</h4><blockquote>{proposal.quote}</blockquote>
  {proposal.person_label&&<p>{proposal.person_label} → {proposal.relationships.join(' and ')} → {proposal.title}</p>}
  <p>Review names, identities and connections before creating the page.</p>
  {error&&<p role="alert">{error}</p>}
  <button type="button" disabled={disabled||busy||!host||host.worldId!==worldId||host.documentId!==documentId} onClick={()=>{const capturedHost=host,captured=identity;if(!capturedHost)return;setBusy(true);setError(null);void getAgentConnectedPageOrigin(worldId,turnId).then(raw=>connectedReviewOrigin(raw,worldId,turnId,proposal)).then(origin=>{if(current.current!==captured||active.current!==capturedHost)return;capturedHost.open({worldId,ownerDocumentId:documentId,sourceTurnId:turnId,proposal,origin});}).catch(e=>{if(current.current===captured)setError(e instanceof Error?e.message:String(e));}).finally(()=>{if(current.current===captured)setBusy(false);});}}>{busy?'Opening exact source…':'Review new page'}</button>
 </section>;
}
