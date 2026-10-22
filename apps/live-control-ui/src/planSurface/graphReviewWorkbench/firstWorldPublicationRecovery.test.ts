import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import type {ExactRunReviewPackage,FirstWorldGraphPlan} from '../../api/types';
import {withFirstWorldEffect} from './firstWorldPublicationRecovery.testSupport';
import {assertFirstWorldPlan,firstWorldRecoveryKey,readFirstWorldRecovery,saveFirstWorldRecovery} from './firstWorldPublicationRecovery';
const review:ExactRunReviewPackage={schema:'dmb_extract_promote_exact_run_review_v1',sourceDomain:'worldbuilding',inspectionStatus:'ready',
  runId:'run-a',sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+'a'.repeat(64),worldId:'world-a',sourceProse:'A keeper.',diagnostics:[],
  assertions:[{assertionId:'keeper',kind:'object',label:'Keeper',summary:'A keeper',evidence:[{sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'A keeper.',anchorQuotes:['keeper']}]}]};
const plan:FirstWorldGraphPlan=withFirstWorldEffect({schema:'dmb_first_world_graph_plan_v2',nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},planId:'plan-a',planDigest:'sha256:'+'b'.repeat(64),decisionDigest:'sha256:'+'c'.repeat(64),
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
