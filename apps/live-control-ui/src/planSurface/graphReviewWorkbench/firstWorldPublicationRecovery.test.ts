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
it('retains the exact submitted request despite a request-local not-invoked proof',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);
  await saveFirstWorldRecovery(review,plan,true,()=>true);
  expect(firstWorldNonapplication(proofError(),plan)).toEqual(proof());
  await expect(releaseFirstWorldRecovery(review,plan,proof(),()=>true)).rejects.toThrow('retained');
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
});
it('refuses to release a foreign retained request',async()=>{
  await saveFirstWorldRecovery(review,{...plan,planId:'foreign'},false,()=>true);
  const before=localStorage.getItem(firstWorldRecoveryKey(review));
  await expect(releaseFirstWorldRecovery(review,plan,proof(),()=>true)).rejects.toThrow('retained');
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(before);
});
it('retains recovery if source changes while waiting for release ownership',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  let release!:()=>void,current=true;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>new Promise((resolve,reject)=>{
    release=()=>{try{resolve(action());}catch(error){reject(error);}};
  })}});
  const pending=releaseFirstWorldRecovery(review,plan,proof(),()=>current);current=false;
  expect(release).toBeUndefined();
  await expect(pending).rejects.toThrow('retained');expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
});
it('retains recovery when storage refuses removal',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  vi.spyOn(Storage.prototype,'removeItem').mockImplementation(()=>{throw new Error('storage unavailable');});
  await expect(releaseFirstWorldRecovery(review,plan,proof(),()=>true)).rejects.toThrow('retained');
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
  expect(readFirstWorldRecovery(review)?.plan).toEqual(saved.plan);
  expect(() => assertFirstWorldPlan(saved.plan,review)).toThrow('reviewed structured meaning');
  expect(localStorage.getItem(key)).toBe(raw);
});

it('discovers submitted native requests by World/run after the source and candidates change',async()=>{
  const {withNativeFirstWorldPlan}=await import('./firstWorldPublicationRecovery.testSupport');
  const {retainFirstWorldRetry}=await import('./firstWorldPublicationRecovery');
  const native=withNativeFirstWorldPlan(plan,review);
  await saveFirstWorldRecovery(review,native,false,()=>true);await saveFirstWorldRecovery(review,native,true,()=>true);
  const changed={...review,sourceRevisionId:'sha256:'+'f'.repeat(64),inspectionStatus:'missing',assertions:[]};
  expect(readFirstWorldRecovery(changed)?.plan).toEqual(native);
  expect(readFirstWorldRecovery({...changed,worldId:'foreign'})).toBeNull();
  expect(readFirstWorldRecovery({...changed,runId:'foreign'})).toBeNull();
  expect(await retainFirstWorldRetry(changed,native,()=>true)).toEqual({schema:'dmb_native_first_world_confirm_request_v1',plan:native});
});

it('discovers the original v3 classic request under its original source key without upgrading it',async()=>{
  const {retainFirstWorldRetry}=await import('./firstWorldPublicationRecovery');
  const key='dmb.firstWorldPublication.v1:'+firstWorldScope(review);
  const value={schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),submitted:true,plan};
  localStorage.setItem(key,JSON.stringify(value));
  expect(readFirstWorldRecovery({worldId:review.worldId,runId:review.runId})?.plan).toEqual(plan);
  expect(await retainFirstWorldRetry(review,plan,()=>true)).toEqual({schema:'dmb_first_world_graph_confirm_request_v1',plan});
  expect(JSON.parse(localStorage.getItem(key)!)).toEqual(value);
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBeNull();
});

it('refuses inconsistent native request envelopes and preserves their exact bytes',async()=>{
  const {withNativeFirstWorldPlan}=await import('./firstWorldPublicationRecovery.testSupport');
  const native=withNativeFirstWorldPlan(plan,review);
  await saveFirstWorldRecovery(review,native,false,()=>true);
  const key=firstWorldRecoveryKey(review),value=JSON.parse(localStorage.getItem(key)!);
  value.request.plan.publicationId='foreign'; // Shared JSON values are distinct after parsing.
  const raw=JSON.stringify(value);localStorage.setItem(key,raw);
  expect(()=>readFirstWorldRecovery(review)).toThrow();expect(localStorage.getItem(key)).toBe(raw);
});

it('retains expired native plans for server-governed receipt-first recovery',async()=>{
  const {withNativeFirstWorldPlan}=await import('./firstWorldPublicationRecovery.testSupport');
  const {retainFirstWorldRetry}=await import('./firstWorldPublicationRecovery');
  const native={...withNativeFirstWorldPlan(plan,review),createdAt:'2020-01-01T00:00:00Z',expiresAt:'2020-01-01T01:00:00Z'};
  await saveFirstWorldRecovery(review,native,false,()=>true);
  expect((await retainFirstWorldRetry(review,native,()=>true)).plan).toEqual(native);
  expect(readFirstWorldRecovery(review)?.plan).toMatchObject({createdAt:'2020-01-01T00:00:00Z'});
});

it('refuses multiple retained requests for a selected World/run without choosing a winner',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);
  const legacyKey='dmb.firstWorldPublication.v1:'+firstWorldScope(review);
  const raw=JSON.stringify({schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),submitted:true,plan});
  localStorage.setItem(legacyKey,raw);
  expect(()=>readFirstWorldRecovery(review)).toThrow('Multiple');expect(localStorage.getItem(legacyKey)).toBe(raw);
});

it('uses authenticated native URLs with exact versioned bodies and preserves errors',async()=>{
  const {prepareNativeFirstWorld,confirmNativeFirstWorld}=await import('../../api/nativeFirstWorldPublicationApi');
  const live=await import('../../api/liveApi');
  const {withNativeFirstWorldPlan,nativeFirstWorldReceipt}=await import('./firstWorldPublicationRecovery.testSupport');
  const native=withNativeFirstWorldPlan(plan,review),receipt=nativeFirstWorldReceipt(native);
  const transport=vi.spyOn(live,'authenticatedApiFetch');
  transport.mockResolvedValueOnce({response:new Response(JSON.stringify(native),{status:200}),csrf:null,requestEpoch:1});
  const decisions=[{assertionId:'keeper',decision:'create_new' as const}];
  expect(await prepareNativeFirstWorld({runId:review.runId,decisions})).toEqual(native);
  expect(transport).toHaveBeenLastCalledWith('/api/live/extract-promote/worldbuilding/first-world/prepare',{
    method:'POST',body:JSON.stringify({schema:'dmb_native_first_world_prepare_request_v1',runId:review.runId,decisions})});
  const request={schema:'dmb_native_first_world_confirm_request_v1' as const,plan:native};
  transport.mockResolvedValueOnce({response:new Response(JSON.stringify(receipt),{status:200}),csrf:null,requestEpoch:1});
  expect(await confirmNativeFirstWorld(request)).toEqual(receipt);
  expect(transport).toHaveBeenLastCalledWith('/api/live/extract-promote/worldbuilding/first-world/confirm',{method:'POST',body:JSON.stringify(request)});
  transport.mockResolvedValueOnce({response:new Response(JSON.stringify({schema:'dmb_extract_promote_error_v1',code:'forbidden',message:'Owner changed'}),{status:403}),csrf:null,requestEpoch:1});
  await expect(confirmNativeFirstWorld(request)).rejects.toMatchObject({status:403,code:'forbidden',message:'Owner changed'});
});

it('retains existing context proofs, original proof epochs and unknown host metadata without relabeling',async()=>{
  const {withNativeFirstWorldPlan}=await import('./firstWorldPublicationRecovery.testSupport');
  const {retainFirstWorldRetry}=await import('./firstWorldPublicationRecovery');
  const native=withNativeFirstWorldPlan(plan,review);
  native.sourceStage={...native.sourceStage,admissionState:'admitted',admissionReceiptSha256:'d'.repeat(64),
    nativeSourceArtifactId:'artifact:native',nativeSourceRevisionId:'revision:native',wholeDocumentEvidenceRefId:'evidence:document',
    headRevisionId:'rev:admitted',headProfileRef:native.targetProfileRef,sourceAuthorityEpoch:7,
    existingBindings:[{reviewedEvidenceRefId:'evidence:reviewed',evidenceRole:'context',proofAuthorityEpoch:2,
      originKind:'extension',originOperationId:'extension:original',originReceiptSha256:'e'.repeat(64),introducedRevisionId:'rev:original',
      proof:{schema_version:'dm_native_utf8_span_v1',span_id:'span:native',source_revision_id:'revision:native',
        evidence_ref_id:'evidence:native',start_byte:0,end_byte:8,slice_sha256:'f'.repeat(64)},
      sourceRevision:{schema_version:'dm_source_revision_v2',source_revision_id:'revision:native',source_artifact_id:'artifact:native',
        content_sha256:native.sourceStage.bodySha256,body_storage:'dm_native_utf8_body_v1',locator:null,created_at:'2026-11-19T12:00:00Z'}}]};
  Object.assign(native.sourceStage,{futureHostMetadata:{opaque:'retained exactly'}});
  await saveFirstWorldRecovery(review,native,false,()=>true);
  const request=await retainFirstWorldRetry(review,native,()=>true);
  expect(request).toEqual({schema:'dmb_native_first_world_confirm_request_v1',plan:native});
  expect(request.plan).toMatchObject({sourceStage:{sourceAuthorityEpoch:7,existingBindings:[{evidenceRole:'context',proofAuthorityEpoch:2}],
    futureHostMetadata:{opaque:'retained exactly'}}});
  expect(readFirstWorldRecovery(review)?.request).toEqual(request);
});
