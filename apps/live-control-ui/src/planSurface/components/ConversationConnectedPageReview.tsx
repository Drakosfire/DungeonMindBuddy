import {useEffect,useRef,useState} from 'react';
import type {ConversationConnectedPageProposal} from '../../api/types';
import {getAgentRelatedPage} from '../../api/liveApi';
import {exact} from '../../shared/sourcePassageProtocol';
import {useConnectedPageReviewHost} from '../../buildSurface/connectedPageReviewHost';
import type {SavedExcerptOrigin} from '../../api/connectedPageApi';

export async function connectedReviewOrigin(raw:unknown,worldId:string,turnId:string,p:ConversationConnectedPageProposal):Promise<SavedExcerptOrigin>{
 if(!exact(raw,['schema','world_id','turn_id','read_id','page','markdown'])||raw.schema!=='dmb_agent_related_page_read_v1'||raw.world_id!==worldId||raw.turn_id!==turnId||raw.read_id!==p.read_id||typeof raw.markdown!=='string'
   ||!exact(raw.page,['world_id','document_id','registry_revision','title','visibility','content_sha256'])||raw.page.world_id!==worldId||typeof raw.page.document_id!=='string'||!/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(raw.page.document_id)||!Number.isSafeInteger(raw.page.registry_revision)||(raw.page.registry_revision as number)<1||typeof raw.page.title!=='string'||!raw.page.title.trim()||!['internal','player_safe'].includes(String(raw.page.visibility)))throw new Error('This excerpt belongs to another source or turn.');
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw.markdown))),b=>b.toString(16).padStart(2,'0')).join('');
 if(hash!==raw.page.content_sha256)throw new Error('The captured page differs from its saved hash.');
 const start=raw.markdown.indexOf(p.quote);if(start<0||raw.markdown.indexOf(p.quote,start+1)>=0)throw new Error('The proposed quote does not identify one exact saved occurrence.');
 const first=raw.markdown.slice(0,start).split('\n').length,last=raw.markdown.slice(0,start+p.quote.length-1).split('\n').length;
 const selected=raw.markdown.split(/\r?\n/).slice(first-1,last).join('\n');
 if(!selected.trim()||selected.length>4000)throw new Error('The excerpt exceeds the existing page-creation source capacity.');
 return {kind:'saved_page_excerpt',document_id:raw.page.document_id,revision:raw.page.registry_revision as number,content_sha256:hash,line_start:first,line_end:last,selected_text:selected};
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
  <button type="button" disabled={disabled||busy||!host||host.worldId!==worldId||host.documentId!==documentId} onClick={()=>{const capturedHost=host,captured=identity;if(!capturedHost)return;setBusy(true);setError(null);void getAgentRelatedPage(worldId,turnId,proposal.read_id).then(raw=>connectedReviewOrigin(raw,worldId,turnId,proposal)).then(origin=>{if(current.current!==captured||active.current!==capturedHost)return;capturedHost.open({worldId,ownerDocumentId:documentId,sourceTurnId:turnId,proposal,origin});}).catch(e=>{if(current.current===captured)setError(e instanceof Error?e.message:String(e));}).finally(()=>{if(current.current===captured)setBusy(false);});}}>{busy?'Opening exact source…':'Review new page'}</button>
 </section>;
}
