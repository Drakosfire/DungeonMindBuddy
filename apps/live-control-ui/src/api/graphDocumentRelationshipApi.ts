import {authenticatedApiFetch,LiveApiError} from './liveApi';
import type {GraphObjectAuthoringPrepareRequest} from './types';
export type RelationshipEndpoint={node_id:string|null;label:string;kind:string};
export type DocumentRelationshipIntent={world_id:string;document_source:{documentId:string;revision:number;contentSha256:string};quote:string;source:RelationshipEndpoint;target:RelationshipEndpoint;predicate:string;label:string;context:string};
export async function graphDocumentRelationshipRequest(intent:DocumentRelationshipIntent):Promise<GraphObjectAuthoringPrepareRequest>{
 const {response}=await authenticatedApiFetch('/api/live/graph-authoring/document-relationship/request',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify(intent)});
 const value=await response.json();
 if(!response.ok)throw new LiveApiError(value.detail?.message??'The relationship source could not be reviewed.',response.status);
 if(value.worldId!==intent.world_id||value.campaignId!==intent.world_id||JSON.stringify(value.documentSource)!==JSON.stringify(intent.document_source)||!Array.isArray(value.proposals)||!value.proposals.length)throw new Error('The relationship request does not match this saved page.');
 return value;
}
