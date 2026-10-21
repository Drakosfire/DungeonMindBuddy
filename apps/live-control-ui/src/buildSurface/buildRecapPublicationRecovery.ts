import type {ExactRunReviewPackage, ExtractionRunRecord, ExtractPromotePrepareResponse} from '../api/types';

export interface RecapPublicationRecovery {
  schema: 'dmb_build_recap_publication_recovery_v1';
  scope: string;
  prepared: ExtractPromotePrepareResponse;
  assertionIds: string[] | null;
  canReprepare: boolean;
  selectionIds: string[] | null;
}
export function recapPublicationScope(review: ExactRunReviewPackage, run: ExtractionRunRecord, worldId: string): string {
  return JSON.stringify([worldId, review.worldId, run.run_id, run.source_artifact_id,
    review.sourceRevisionId, run.components?.candidate_graph?.sha256 ?? null, run.campaign_id, run.session_id]);
}
export const recapPublicationRecoveryKey=(scope:string)=>'dmb.buildRecapPublication.v1:'+scope;
export function assertRecapPrepared(prepared: ExtractPromotePrepareResponse, run: ExtractionRunRecord, review: ExactRunReviewPackage, worldId: string) {
  const context=run.lineage?.world_campaign_ingest_context as Record<string,unknown>|undefined;
  if(!prepared || prepared.schema!=='dmb_extract_promote_prepare_v1'||prepared.runId!==run.run_id
    ||prepared.worldId!==context?.native_world_id||prepared.campaignId!==run.campaign_id||prepared.sessionId!==run.session_id
    ||typeof prepared.proposalId!=='string'||!prepared.proposalId||typeof prepared.proposalDigest!=='string'||!prepared.proposalDigest
    ||typeof prepared.parentRevisionId!=='string'||!prepared.parentRevisionId
    ||!prepared.reviewPackage||typeof prepared.reviewPackage!=='object'||Array.isArray(prepared.reviewPackage)
    ||!Array.isArray(prepared.reviewItems)||!prepared.reviewSummary
    ||!['newObjectCount','connectExistingCount','relationshipCount','unresolvedMentionCount','rejectedAssertionCount'].every(key=>{
      const count=(prepared.reviewSummary as unknown as Record<string,unknown>)[key];return typeof count==='number'&&Number.isInteger(count)&&count>=0;})
    ||prepared.reviewItems.some(item=>!item||typeof item!=='object'||typeof item.sliceQualifiedId!=='string'
      ||typeof item.selectable!=='boolean'||typeof item.selectedByDefault!=='boolean'
      ||!['label','summary','action','kind'].every(key=>typeof (item as unknown as Record<string,unknown>)[key]==='string')
      ||!Array.isArray(item.warnings)||item.warnings.some(w=>typeof w!=='string')
      ||(item.dependsOnSliceQualifiedIds!==undefined&&(!Array.isArray(item.dependsOnSliceQualifiedIds)||item.dependsOnSliceQualifiedIds.some(id=>typeof id!=='string'))))) {
    throw new Error('The proposed changes do not match this exact Recap and World.');
  }
  const pkg=prepared.reviewPackage as Record<string,any>, effect=pkg.effect;
  const admission=effect?.candidate_admission, target=effect?.managed_world_publication_target;
  const membership=effect?.world_campaign_ingest_context;
  // Registry components are repo-relative (optionally repo://); prepare seals
  // their resolved absolute locator. Match the full relative path at its boundary.
  const relative=run.components?.candidate_graph?.uri?.replace(/^repo:\/\//,'');
  const segments=relative?.split('/').filter(segment=>segment!=='.');
  const candidatePath=segments?.join('/');
  if(pkg.schema!=='dmb_extract_promote_proposal_v1'||![2,3].includes(pkg.proposal_version)
    ||pkg.proposal_id!==prepared.proposalId||pkg.proposal_digest!==prepared.proposalDigest
    ||!effect||effect.world_id!==prepared.worldId||effect.parent_revision_id!==prepared.parentRevisionId
    ||effect.source_artifact_id!==run.source_artifact_id||effect.source_revision_id!==review.sourceRevisionId
    ||effect.contribution_meta?.source_artifact_id!==run.source_artifact_id
    ||effect.contribution_meta?.source_revision_id!==review.sourceRevisionId
    ||effect.contribution_meta?.campaign_scope!==run.campaign_id
    ||target?.schema!=='dmb_managed_world_publication_target_v1'||target.managed_world_id!==worldId||target.native_world_id!==prepared.worldId
    ||membership?.managed_world_id!==worldId||membership.native_world_id!==prepared.worldId||membership.campaign_id!==run.campaign_id
    ||admission?.schema!=='dmb_candidate_graph_admission_v1'||admission.source_artifact_id!==run.source_artifact_id
    ||admission.source_revision_id!==review.sourceRevisionId||admission.world_id!==prepared.worldId||admission.parent_revision_id!==prepared.parentRevisionId
    ||!candidatePath||relative?.startsWith('/')||segments?.includes('..')||relative?.includes('\\')
    ||typeof admission.candidate_locator!=='string'||!admission.candidate_locator.endsWith('/'+candidatePath)) {
    throw new Error('The sealed publication does not match the reviewed source, candidate and World.');
  }
}
export function readRecapPublicationRecovery(scope:string,run:ExtractionRunRecord,review:ExactRunReviewPackage,worldId:string):RecapPublicationRecovery|null {
  const raw=localStorage.getItem(recapPublicationRecoveryKey(scope));
  if(raw===null)return null;
  const value=JSON.parse(raw) as RecapPublicationRecovery;
  if(!value||value.schema!=='dmb_build_recap_publication_recovery_v1'||value.scope!==scope)throw new Error('Saved publication belongs to another source or World.');
  assertRecapPrepared(value.prepared,run,review,worldId);
  if(typeof value.canReprepare!=="boolean")throw new Error("Saved publication recovery state is unavailable.");
  if(value.selectionIds!==null&&(!Array.isArray(value.selectionIds)||new Set(value.selectionIds).size!==value.selectionIds.length
    ||value.selectionIds.some(id=>typeof id!=='string'||!value.prepared.reviewItems.some(item=>item.selectable&&item.sliceQualifiedId===id))))
    throw new Error('Saved review selections are unavailable.');
  if(value.assertionIds!==null&&(!Array.isArray(value.assertionIds)||!value.assertionIds.length
    ||new Set(value.assertionIds).size!==value.assertionIds.length||value.assertionIds.some(id=>typeof id!=='string'
      ||!value.prepared.reviewItems.some(item=>item.selectable&&item.sliceQualifiedId===id)))) {
    throw new Error('Saved publication choices are unavailable.');
  }
  return value;
}
export function saveRecapPublicationRecovery(value:RecapPublicationRecovery){
  localStorage.setItem(recapPublicationRecoveryKey(value.scope),JSON.stringify(value));
}

export function setAsideRecapPublication(value:RecapPublicationRecovery){
  if(value.selectionIds!==null&&(!Array.isArray(value.selectionIds)||new Set(value.selectionIds).size!==value.selectionIds.length
    ||value.selectionIds.some(id=>typeof id!=='string'||!value.prepared.reviewItems.some(item=>item.selectable&&item.sliceQualifiedId===id))))
    throw new Error('Saved review selections are unavailable.');
  if(value.assertionIds!==null&&!value.canReprepare)throw new Error('Recover the original confirmation before preparing another publication.');
  const key=recapPublicationRecoveryKey(value.scope), archiveKey=key+':retained';
  const archive=JSON.parse(localStorage.getItem(archiveKey)??'[]');
  if(!Array.isArray(archive))throw new Error('Retained publication history is unavailable.');
  if(!archive.some(item=>JSON.stringify(item)===JSON.stringify(value)))archive.push(value);
  localStorage.setItem(archiveKey,JSON.stringify(archive));
  localStorage.removeItem(key);
}
