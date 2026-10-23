import type { GraphAuthoringSelection } from '../planSurface/graphReviewWorkbench/graphAuthoringSelection';
import type { GraphObjectAuthoringPrepareRequest, GraphObjectAuthoringPrepareResponse, GraphObjectAuthoringCommitResponse, WorldbuildingFrozenSpanCatalog } from '../api/types';

export type ManualKnowledgeScope = {worldId:string; documentId:string; revision:number; hash:string; runId:string; artifactId:string};
export type ManualKnowledgeRecovery = {schema:'dmb_build_manual_knowledge_v1'; scope:ManualKnowledgeScope;
  request:GraphObjectAuthoringPrepareRequest; prepared:GraphObjectAuthoringPrepareResponse|null;
  submitted:boolean; receipt:GraphObjectAuthoringCommitResponse|null};
export const normalizeKnowledgeText=(text:string)=>text.replace(/\s+/g,' ').trim();
export const knowledgeKey=(scope:ManualKnowledgeScope)=>'dmb.buildManualKnowledge.v1:'+JSON.stringify(scope);

export function selectionForFrozenText(scope:ManualKnowledgeScope, catalog:WorldbuildingFrozenSpanCatalog, text:string):GraphAuthoringSelection {
  const selected=normalizeKnowledgeText(text);
  if(!selected)throw new Error('Select text in the document, or choose a frozen passage below.');
  const matches=catalog.spans.filter(span=>normalizeKnowledgeText(span.paragraphText).includes(selected));
  if(matches.length!==1)throw new Error('This text does not identify one frozen passage. Choose a unique source selection.');
  const normalized=normalizeKnowledgeText(matches[0].paragraphText),start=normalized.indexOf(selected);
  if(normalized.indexOf(selected,start+1)!==-1)throw new Error('This text occurs more than once in its passage. Select more context.');
  return {campaignId:scope.worldId,sessionId:'',selectionKind:'text_span',selectedText:text,
    normalizedSelectedText:selected,sourceArtifactId:scope.artifactId,sourceArtifactSha256:scope.hash,
    sourceSpanRefId:matches[0].sourceSpanRefId,laneRole:'authored'};
}

/** Browser records carry no evidence authority; signed server confirmation remains mandatory. */
export function readKnowledgeRecovery(raw:string|null,scope:ManualKnowledgeScope):ManualKnowledgeRecovery|null {
  if(raw===null)return null;
  const value=JSON.parse(raw) as ManualKnowledgeRecovery;
  const request=value?.request;
  if(value?.schema!=='dmb_build_manual_knowledge_v1'||JSON.stringify(value.scope)!==JSON.stringify(scope)
    ||request?.worldId!==scope.worldId||request.campaignId!==scope.worldId||request.sourceRunId!==scope.runId
    ||request.recapArtifactId||request.sessionId||!Array.isArray(request.proposals)||request.proposals.length!==1
    ||typeof value.submitted!=='boolean'||(value.submitted&&!value.prepared)
    ||(value.prepared!==null&&(!value.prepared?.confirm_token||value.prepared.expressibility!=='EXPRESSIBLE'
      ||value.prepared.campaign_id!==scope.worldId||value.prepared.source_artifact_id!==scope.artifactId
      ||typeof value.prepared.world_id!=='string'||!value.prepared.world_id||typeof value.prepared.authority_operation_id!=='string'||!value.prepared.authority_operation_id
      ||!Array.isArray(value.prepared.assertions_preview)||value.prepared.assertions_preview.length!==1
      ||value.prepared.assertions_preview.some(row=>!row||typeof row.assertion_id!=='string'||typeof row.summary!=='string')))
    ||(value.receipt!==null&&(value.receipt?.committed!==true||!value.prepared
      ||value.receipt.world_id!==value.prepared.world_id||value.receipt.operation_id!==value.prepared.authority_operation_id
      ||value.receipt.campaign_id!==scope.worldId||!value.receipt.published_revision_id)))throw new Error('Saved manual authoring does not match this exact source. It is retained; no request was sent.');
  const proposal=request.proposals[0];
  const record=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
  const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0;
  const endpoint=(v:unknown)=>record(v)&&v.refKind==='existing_graph_node'&&text(v.nodeId)&&text(v.label);
  if(!record(proposal)||!text(proposal.localProposalId)
    ||(proposal.proposalKind==='object'?(!record(proposal.objectRef)||!text(proposal.objectRef.label)||!text(proposal.objectRef.kind))
      :proposal.proposalKind==='relationship'?(!text(proposal.relationshipType)||!endpoint(proposal.sourceObjectRef)||!endpoint(proposal.targetObjectRef))
      :true))throw new Error('Saved proposal fields are invalid. The request is retained; no request was sent.');
  const selection=proposal.selection;
  if(!selection||selection.sourceArtifactId!==scope.artifactId||selection.sourceArtifactSha256!==scope.hash
    ||typeof selection.sourceSpanRefId!=='string'||!selection.sourceSpanRefId
    ||typeof selection.selectedText!=='string'||!normalizeKnowledgeText(selection.selectedText))throw new Error('Saved source selection is unavailable. The request is retained.');
  return value;
}
