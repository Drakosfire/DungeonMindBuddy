import type {DocumentRelationshipIntent, NativeRelationshipPreparation, NativeRelationshipReceipt} from '../api/graphDocumentRelationshipApi';
import type {GraphObjectAuthoringPrepareRequest,GraphObjectAuthoringPrepareResponse,GraphObjectAuthoringCommitResponse} from '../api/types';
export type RelationshipSeed=Pick<DocumentRelationshipIntent,'document_source'|'quote'>;
export type NativeRelationshipRecovery = {
 operationId: string;
 preparation: NativeRelationshipPreparation | null;
 receipt: NativeRelationshipReceipt | null;
};
export type RelationshipReview={schema:'dmb_saved_relationship_review_v1';intent:DocumentRelationshipIntent;request:GraphObjectAuthoringPrepareRequest|null;prepared:GraphObjectAuthoringPrepareResponse|null;submitted:boolean;receipt:GraphObjectAuthoringCommitResponse|null;native?:NativeRelationshipRecovery};
export const relationshipKey=(world:string,document:string)=>'dmb:saved-relationship-review:v1:'+JSON.stringify([world,document]);
export function readRelationshipReview(raw:string|null,world:string,document:string):RelationshipReview|null{
 if(raw===null)return null;
 const v=JSON.parse(raw),i=v?.intent;
 const object=(v:unknown):v is Record<string,any>=>!!v&&typeof v==='object'&&!Array.isArray(v);
 const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0;
 const fail=()=>{throw new Error('The retained relationship review is unreadable. Its bytes were kept.');};
 if(!object(v)||v.schema!=='dmb_saved_relationship_review_v1'||Object.keys(v).filter(key=>key!=='native').sort().join(',')!=='intent,prepared,receipt,request,schema,submitted'||!object(i)||i.world_id!==world||!object(i.document_source)||i.document_source.documentId!==document||!Number.isSafeInteger(i.document_source.revision)||i.document_source.revision<1||typeof i.document_source.contentSha256!=='string'||!/^[a-f0-9]{64}$/.test(i.document_source.contentSha256)||typeof v.submitted!=='boolean')fail();
 if(!['quote','predicate','label','context'].every(k=>typeof i[k]==='string')||![i.source,i.target].every(e=>object(e)&&Object.keys(e).sort().join(',')==='kind,label,node_id'&&typeof e.label==='string'&&typeof e.kind==='string'&&(e.node_id===null||text(e.node_id))))fail();
 if(v.request!==null&&(!object(v.request)||v.request.worldId!==world||v.request.campaignId!==world||JSON.stringify(v.request.documentSource)!==JSON.stringify(i.document_source)||!Array.isArray(v.request.proposals)||!v.request.proposals.length||!v.request.proposals.every((p:unknown)=>object(p)&&text(p.localProposalId)&&['object','relationship'].includes(p.proposalKind)&&object(p.selection)&&p.selection.selectedText===i.quote)))fail();
 if(v.prepared!==null&&(!object(v.prepared)||!v.request||v.prepared.prepared!==true||v.prepared.campaign_id!==world||!text(v.prepared.world_id)||!text(v.prepared.authority_operation_id)||!text(v.prepared.confirm_token)||!(v.prepared.current_overlay_token===null||text(v.prepared.current_overlay_token))||v.prepared.expressibility!=='EXPRESSIBLE'||!Array.isArray(v.prepared.assertions_preview)||!v.prepared.assertions_preview.every((r:unknown)=>object(r)&&text(r.assertion_id)&&typeof r.summary==='string')))fail();
 if(Object.hasOwn(v,'native')){
  const n=v.native;
  if(!object(n)||Object.keys(n).sort().join(',')!=='operationId,preparation,receipt'||!text(n.operationId)
    ||! /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(n.operationId)
    ||v.request!==null||v.prepared!==null||v.receipt!==null
    ||n.preparation!==null&&(!object(n.preparation)||!object(n.preparation.prepared)||!text(n.preparation.confirm_token))
    ||v.submitted&&!n.preparation
    ||n.receipt!==null&&(!v.submitted||!object(n.receipt)||!text(n.receipt.child_revision_id)
      ||n.receipt.dungeonmind_publication_id!==`dmb-build-relationship:v1:${n.operationId}`))fail();
  return v;
 }
 if(v.submitted&&!v.prepared||v.receipt!==null&&(!object(v.receipt)||!v.submitted||v.receipt.committed!==true||v.receipt.campaign_id!==world||v.receipt.world_id!==v.prepared?.world_id||v.receipt.operation_id!==v.prepared?.authority_operation_id||!text(v.receipt.published_revision_id)))fail();
 return v;
}
