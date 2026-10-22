import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import type {ExactRunReviewPackage,FirstWorldGraphPlan} from '../../api/types';
import {withFirstWorldEffect} from './firstWorldPublicationRecovery.testSupport';
import {ExtractPromoteApiError} from '../../api/extractPromoteApi';
import {obsoleteUnsubmittedRecovery,archiveObsoleteUnsubmittedRecovery,firstWorldScope,firstWorldNonapplication,releaseFirstWorldRecovery,assertFirstWorldPlan,firstWorldRecoveryKey,readFirstWorldRecovery,saveFirstWorldRecovery} from './firstWorldPublicationRecovery';
const review:ExactRunReviewPackage={schema:'dmb_extract_promote_exact_run_review_v1',sourceDomain:'worldbuilding',inspectionStatus:'ready',
  runId:'run-a',sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+'a'.repeat(64),worldId:'world-a',sourceProse:'A keeper.',diagnostics:[],
  assertions:[{assertionId:'keeper',kind:'object', nodeType: "npc", contributionKind: "npc",label:'Keeper',summary:'A keeper',evidence:[{sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'A keeper.',anchorQuotes:['keeper']}]}]};
const plan:FirstWorldGraphPlan=withFirstWorldEffect({schema:'dmb_first_world_graph_plan_v3',sourceEvidenceSha256:'sha256:'+'d'.repeat(64),nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},planId:'plan-a',planDigest:'sha256:'+'b'.repeat(64),decisionDigest:'sha256:'+'c'.repeat(64),
  worldId:'world-a',runId:'run-a',sourceArtifactId:'source-a',sourceRevisionId:review.sourceRevisionId,workspaceDocumentId:'doc-a',workspaceDocumentRevision:'1',
  extractionProfile:'worldbuilding_shepherds_flock_v0@0.1',acceptedAssertionIds:['assertion:keeper'],rejectedAssertionIds:[],contributionId:'contribution-a',
  contributionPayloadSha256:'d'.repeat(64),reviewedEffect:{decision_snapshot:[{assertion_id:'keeper',candidate_kind:'node',decision:'create_new',target_node_id:null}]},
  summary:{createNewNodeCount:1,acceptedEdgeCount:0,rejectedCandidateCount:0,acceptedAssertionCount:1},confirmable:true,diagnostics:[]},review);
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>Promise.resolve(action())}});});
afterEach(()=>vi.restoreAllMocks());
it('retains exact plan bytes and advances submission without replacing its request',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  expect(readFirstWorldRecovery(review)).toMatchObject({plan,submitted:true});
  await expect(saveFirstWorldRecovery(review,plan,false,()=>true)).rejects.toThrow('Another creation');
  await expect(saveFirstWorldRecovery(review,{...plan,planId:'another-plan'},true,()=>true)).rejects.toThrow('Another creation');
  expect(readFirstWorldRecovery(review)?.plan).toEqual(plan);
});
it('never overwrites another view that retained a different plan first',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);
  await expect(saveFirstWorldRecovery(review,{...plan,planId:'another-plan'},false,()=>true)).rejects.toThrow('Another creation');
  expect(readFirstWorldRecovery(review)?.plan).toEqual(plan);
});
it('requires the original prepared request before marking it submitted',async()=>{
  await expect(saveFirstWorldRecovery(review,plan,true,()=>true)).rejects.toThrow('Another creation');expect(localStorage.length).toBe(0);
});
it.each(['worldId','runId','sourceArtifactId','sourceRevisionId'] as const)('refuses a foreign prepared %s',field=>{
  expect(()=>assertFirstWorldPlan({...plan,[field]:'other'},review)).toThrow('does not match');
});
it('refuses changed or duplicate reviewed decisions',()=>{
  expect(()=>assertFirstWorldPlan(plan,review,[{assertionId:'keeper',decision:'reject'}])).toThrow('does not match');
  const other=structuredClone(plan);other.reviewedEffect.decision_snapshot=[{assertion_id:'unknown',candidate_kind:'node',decision:'create_new'}];
  expect(()=>assertFirstWorldPlan(other,review)).toThrow('does not match');
});
it('does not write after scope changes while waiting for its browser lock',async()=>{
  let release!:()=>void,current=true;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>new Promise((resolve,reject)=>{
    release=()=>{try{resolve(action());}catch(error){reject(error);}};
  })}});
  const pending=saveFirstWorldRecovery(review,plan,false,()=>current);current=false;release();
  await expect(pending).rejects.toThrow('selected source');expect(localStorage.length).toBe(0);
});
it('refuses malformed recovery without manufacturing a fresh plan',()=>{
  localStorage.setItem(firstWorldRecoveryKey(review),'bad json');expect(()=>readFirstWorldRecovery(review)).toThrow();
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe('bad json');
});
it('fails closed when cross-tab serialization is unavailable',async()=>{
  Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});
  await expect(saveFirstWorldRecovery(review,plan,false,()=>true)).rejects.toThrow('across tabs');expect(localStorage.length).toBe(0);
});

it.each(['campaign','session','artifact','revision','profile','nested_campaign','proposal_source','effect_map'] as const)('refuses foreign nested scope %s',field=>{
  const altered=structuredClone(plan),meta=altered.reviewedEffect.contribution_meta as Record<string,unknown>;
  if(field==='campaign')altered.campaignScope='foreign';
  if(field==='session')Object.assign(altered,{sessionScope:'foreign'});
  if(field==='artifact')meta.source_artifact_id='foreign';
  if(field==='revision')meta.source_revision_id='sha256:'+'e'.repeat(64);
  if(field==='profile')meta.extraction_profile='foreign';
  if(field==='nested_campaign')meta.campaign_scope='foreign';
  if(field==='proposal_source')(altered.reviewedEffect.accepted_proposals as Record<string,unknown>[])[0].source_artifact_id='foreign';
  if(field==='effect_map')altered.reviewedEffect.candidate_effect_map={keeper:['foreign']};
  expect(()=>assertFirstWorldPlan(altered,review)).toThrow('foreign scope');
});

it('rejects an obsolete v1 carried creation plan without upgrading it',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);
  await saveFirstWorldRecovery(review,plan,true,()=>true);
  const key=firstWorldRecoveryKey(review);
  const stored=JSON.parse(localStorage.getItem(key)!);
  stored.plan.schema='dmb_first_world_graph_plan_v1';
  delete stored.plan.nativeTarget;
  localStorage.setItem(key,JSON.stringify(stored));
  expect(()=>readFirstWorldRecovery(review)).toThrow();
  expect(JSON.parse(localStorage.getItem(key)!).plan.schema).toBe('dmb_first_world_graph_plan_v1');
});

const proof=()=>({schema:'dmb_first_world_confirm_not_invoked_v1' as const,worldId:plan.worldId,
  nativeWorldId:plan.nativeTarget.nativeWorldId,initializationId:plan.nativeTarget.provisioningId,
  planId:plan.planId,planDigest:plan.planDigest,initializationInvoked:false as const,
  validationMessage:'Invalid endpoint pair',failure:{reason:'invalid_endpoint_kinds'}});
const proofError=(value:unknown=proof())=>new ExtractPromoteApiError('Not invoked',409,'first_world_confirm_not_invoked',{
  schema:'dmb_extract_promote_error_v1',failureResult:value as Record<string,unknown>});
it.each(['worldId','nativeWorldId','initializationId','planId','planDigest','schema','initializationInvoked','validationMessage','failure'])(
  'refuses a wrong or malformed nonapplication proof %s',field=>{
    const value={...proof(),[field]:field==='initializationInvoked'?true:field==='failure'?[]:field==='validationMessage'?'':'foreign'};
    expect(firstWorldNonapplication(proofError(value),plan)).toBeNull();
  });
it('never treats a timeout or a generic conflict as nonapplication',()=>{
  expect(firstWorldNonapplication(new Error('timeout'),plan)).toBeNull();
  expect(firstWorldNonapplication(new ExtractPromoteApiError('conflict',409),plan)).toBeNull();
});
it('explicitly releases only the exact submitted request on verified proof',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);
  await saveFirstWorldRecovery(review,plan,true,()=>true);
  expect(firstWorldNonapplication(proofError(),plan)).toEqual(proof());
  await releaseFirstWorldRecovery(review,plan,proof(),()=>true);
  expect(readFirstWorldRecovery(review)).toBeNull();
});
it('refuses to release a foreign retained request',async()=>{
  await saveFirstWorldRecovery(review,{...plan,planId:'foreign'},false,()=>true);
  const before=localStorage.getItem(firstWorldRecoveryKey(review));
  await expect(releaseFirstWorldRecovery(review,plan,proof(),()=>true)).rejects.toThrow('Another creation');
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(before);
});
it('retains recovery if source changes while waiting for release ownership',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  let release!:()=>void,current=true;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>new Promise((resolve,reject)=>{
    release=()=>{try{resolve(action());}catch(error){reject(error);}};
  })}});
  const pending=releaseFirstWorldRecovery(review,plan,proof(),()=>current);current=false;release();
  await expect(pending).rejects.toThrow('selected source');expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
});
it('retains recovery when storage refuses removal',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  vi.spyOn(Storage.prototype,'removeItem').mockImplementation(()=>{throw new Error('storage unavailable');});
  await expect(releaseFirstWorldRecovery(review,plan,proof(),()=>true)).rejects.toThrow('storage unavailable');
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
});

it('preserves an old submitted plan and requires explicit fresh review without reposting',()=>{
  const raw=JSON.stringify({schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),submitted:true,plan:{...plan,schema:'dmb_first_world_graph_plan_v2'}});
  // Use the actual current scope, retaining the old plan bytes verbatim.
  localStorage.setItem(firstWorldRecoveryKey(review),raw);
  expect(()=>readFirstWorldRecovery(review)).toThrow('out of date');
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(raw);
});

function obsoleteRecovery(submitted=false) {
  const raw=JSON.stringify({schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),
    plan:{...plan,schema:'dmb_first_world_graph_plan_v2'},submitted});
  localStorage.setItem(firstWorldRecoveryKey(review),raw);return raw;
}
it('archives exact obsolete unsubmitted bytes before freeing fresh review',async()=>{
  const raw=obsoleteRecovery();expect(obsoleteUnsubmittedRecovery(review)).toBe(raw);
  await archiveObsoleteUnsubmittedRecovery(review,raw,()=>true);
  expect(readFirstWorldRecovery(review)).toBeNull();
  expect(localStorage.length).toBe(1);expect(localStorage.getItem(localStorage.key(0)!)).toBe(raw);
  await saveFirstWorldRecovery(review,plan,false,()=>true);
  expect(readFirstWorldRecovery(review)?.plan).toEqual(plan);
});
it('never archives a submitted obsolete request',async()=>{
  const raw=obsoleteRecovery(true);expect(obsoleteUnsubmittedRecovery(review)).toBeNull();
  await expect(archiveObsoleteUnsubmittedRecovery(review,raw,()=>true)).rejects.toThrow('Another creation');
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(raw);
});
it('rechecks submission and source after waiting for archive ownership',async()=>{
  const raw=obsoleteRecovery();let release!:()=>void;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>new Promise((resolve,reject)=>{
    release=()=>{try{resolve(action());}catch(error){reject(error);}};
  })}});
  const pending=archiveObsoleteUnsubmittedRecovery(review,raw,()=>true);
  const changed=JSON.stringify({...JSON.parse(raw),submitted:true});localStorage.setItem(firstWorldRecoveryKey(review),changed);release();
  await expect(pending).rejects.toThrow('Another creation');
  expect(localStorage.length).toBe(1);expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(changed);
});
it('preserves the active request when archive storage fails',async()=>{
  const raw=obsoleteRecovery();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('quota');});
  await expect(archiveObsoleteUnsubmittedRecovery(review,raw,()=>true)).rejects.toThrow('quota');
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(raw);
});
it('does not archive a foreign obsolete envelope or changed scope',async()=>{
  const raw=obsoleteRecovery();
  expect(obsoleteUnsubmittedRecovery({...review,worldId:'foreign'})).toBeNull();
  await expect(archiveObsoleteUnsubmittedRecovery(review,raw,()=>false)).rejects.toThrow('selected source');
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(raw);
});

it('retains but refuses recovery whose stored kind no longer matches reviewed semantics', async () => {
  await saveFirstWorldRecovery(review, plan, false, () => true);
  const key = firstWorldRecoveryKey(review), saved = JSON.parse(localStorage.getItem(key)!);
  saved.plan.reviewedEffect.accepted_proposals[0].value.kind = 'faction';
  const raw = JSON.stringify(saved); localStorage.setItem(key, raw);
  expect(() => readFirstWorldRecovery(review)).toThrow('reviewed structured meaning');
  expect(localStorage.getItem(key)).toBe(raw);
});
