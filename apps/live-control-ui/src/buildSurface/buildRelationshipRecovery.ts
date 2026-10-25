import type {DocumentRelationshipIntent} from '../api/graphDocumentRelationshipApi';
import type {GraphObjectAuthoringPrepareRequest,GraphObjectAuthoringPrepareResponse,GraphObjectAuthoringCommitResponse} from '../api/types';
export type RelationshipSeed=Pick<DocumentRelationshipIntent,'document_source'|'quote'>;
export type RelationshipReview={schema:'dmb_saved_relationship_review_v1';intent:DocumentRelationshipIntent;request:GraphObjectAuthoringPrepareRequest|null;prepared:GraphObjectAuthoringPrepareResponse|null;submitted:boolean;receipt:GraphObjectAuthoringCommitResponse|null};
export const relationshipKey=(world:string,document:string)=>'dmb:saved-relationship-review:v1:'+JSON.stringify([world,document]);
export function readRelationshipReview(raw:string|null,world:string,document:string):RelationshipReview|null{
 if(raw===null)return null;
 const v=JSON.parse(raw) as RelationshipReview,i=v.intent;
 const fail=()=>{throw new Error('The retained relationship review is unreadable. Its bytes were kept.');};
 if(v.schema!=='dmb_saved_relationship_review_v1'||Object.keys(v).sort().join(',')!=='intent,prepared,receipt,request,schema,submitted'||!i||i.world_id!==world||i.document_source?.documentId!==document||!Number.isSafeInteger(i.document_source.revision)||i.document_source.revision<1||!/^[a-f0-9]{64}$/.test(i.document_source.contentSha256)||typeof v.submitted!=='boolean')fail();
 if(!['quote','predicate','label','context'].every(k=>typeof i[k as keyof typeof i]==='string')||![i.source,i.target].every(e=>!!e&&typeof e.label==='string'&&typeof e.kind==='string'&&(e.node_id===null||typeof e.node_id==='string')))fail();
 if(v.request&&(v.request.worldId!==world||v.request.campaignId!==world||JSON.stringify(v.request.documentSource)!==JSON.stringify(i.document_source)||!Array.isArray(v.request.proposals)||!v.request.proposals.length))fail();
 if(v.prepared&&(!v.request||!v.prepared.prepared||v.prepared.campaign_id!==world||!v.prepared.world_id||!v.prepared.authority_operation_id||!v.prepared.confirm_token||v.prepared.expressibility!=='EXPRESSIBLE'||!Array.isArray(v.prepared.assertions_preview)))fail();
 if(v.submitted&&!v.prepared||v.receipt&&(!v.submitted||!v.receipt.committed||v.receipt.campaign_id!==world||v.receipt.world_id!==v.prepared?.world_id||v.receipt.operation_id!==v.prepared?.authority_operation_id||!v.receipt.published_revision_id))fail();
 return v;
}
