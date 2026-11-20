import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/extractPromoteApi';
import * as native from '../api/nativeRecapPublicationApi';
import * as live from '../api/liveApi';
import type {ExactRunReviewPackage,ExtractionRunRecord,ExtractPromotePrepareResponse} from '../api/types';
import {assertRecapPrepared,recapPublicationRecoveryKey,recapPublicationScope} from './buildRecapPublicationRecovery';
import {BuildRecapPublication,RetainedRecapPublication} from './BuildRecapPublication';
const run={run_id:'run-a',source_artifact_id:'source-a',source_domain:'recap',campaign_id:'longmont-c2',session_id:'session-30',
  components:{candidate_graph:{kind:'candidate_graph',uri:'repo://runs/run-a/candidate_graph.json',sha256:'b'.repeat(64)}},
  lineage:{world_campaign_ingest_context:{managed_world_id:'managed-a',native_world_id:'native-a'}}} as ExtractionRunRecord;
const review={runId:'run-a',worldId:'native-a',sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+ 'a'.repeat(64),inspectionStatus:'ready',promotable:true} as ExactRunReviewPackage;
const prepared:ExtractPromotePrepareResponse={schema:'dmb_extract_promote_prepare_v1',proposalId:'proposal-a',proposalDigest:'digest-a',parentRevisionId:'rev:1',
  worldId:'native-a',runId:'run-a',campaignId:'longmont-c2',sessionId:'session-30',acceptedProposalsCount:1,unresolvedMentionsCount:0,rejectedAssertionsCount:0,
  reviewPackage:{schema:'dmb_extract_promote_proposal_v1',proposal_version:3,proposal_id:'proposal-a',proposal_digest:'digest-a',effect:{
    world_id:'native-a',parent_revision_id:'rev:1',source_artifact_id:'source-a',source_revision_id:review.sourceRevisionId,
    contribution_meta:{source_artifact_id:'source-a',source_revision_id:review.sourceRevisionId,campaign_scope:'longmont-c2'},
    managed_world_publication_target:{schema:'dmb_managed_world_publication_target_v1',managed_world_id:'managed-a',native_world_id:'native-a'},
    world_campaign_ingest_context:{managed_world_id:'managed-a',native_world_id:'native-a',campaign_id:'longmont-c2'},
    candidate_admission:{schema:'dmb_candidate_graph_admission_v1',world_id:'native-a',parent_revision_id:'rev:1',source_artifact_id:'source-a',
      source_revision_id:review.sourceRevisionId,candidate_locator:'/private/artifact-root/runs/run-a/candidate_graph.json'}
  }},reviewSummary:{newObjectCount:1,connectExistingCount:0,relationshipCount:0,unresolvedMentionCount:0,rejectedAssertionCount:0},
  reviewItems:[{assertionId:'keeper',sliceQualifiedId:'0:source_extraction::keeper',kind:'object',label:'Keeper',action:'create',identityOutcome:'created_new',
    summary:'Create keeper',warnings:[],selectable:true,selectedByDefault:true,dependsOnAssertionIds:[],dependsOnSliceQualifiedIds:[]}]};
it.each([true,false])('verifies the sealed database candidate (matching digest: %s)', matches => {
  const databaseRun = {...run, revision: 2, components: {...run.components,
    candidate_graph: {...run.components.candidate_graph, uri: 'urn:dmb:ingest-output:run-a:candidate_graph'}}};
  const response = structuredClone(prepared);
  const effect = response.reviewPackage.effect as Record<string, unknown>;
  (effect.candidate_admission as Record<string, unknown>).candidate_locator = null;
  effect.extraction_run = {run_id: 'run-a', run_revision: 2, components: {
    candidate_graph: 'sha256:' + (matches ? 'b' : 'c').repeat(64),
  }};
  const verify = () => assertRecapPrepared(response, databaseRun, review, 'managed-a');
  if (matches) expect(verify).not.toThrow();
  else expect(verify).toThrow('The sealed publication does not match');
});
it.each(['prefixed URN','wrong URN run','missing revision','zero revision','fractional revision',
  'unsafe revision','wrong bound revision','wrong bound run','filesystem locator','empty digest',
  'malformed digest','missing bound digest'])('rejects a database candidate with %s', failure => {
  const component={...run.components!.candidate_graph!,uri:'urn:dmb:ingest-output:run-a:candidate_graph'};
  const databaseRun:ExtractionRunRecord={...run,revision:2,components:{...run.components,candidate_graph:component}};
  const response=structuredClone(prepared);
  const effect=response.reviewPackage.effect as Record<string,unknown>;
  const admission=effect.candidate_admission as Record<string,unknown>;
  admission.candidate_locator=null;
  const binding:{run_id:string;run_revision?:number;components:{candidate_graph?:string}}={
    run_id:'run-a',run_revision:2,components:{candidate_graph:'sha256:'+'b'.repeat(64)},
  };
  effect.extraction_run=binding;
  if(failure==='prefixed URN')component.uri='repo://'+component.uri;
  if(failure==='wrong URN run')component.uri='urn:dmb:ingest-output:other-run:candidate_graph';
  if(failure==='missing revision')delete databaseRun.revision;
  if(failure==='zero revision')databaseRun.revision=0;
  if(failure==='fractional revision')databaseRun.revision=1.5;
  if(failure==='unsafe revision')databaseRun.revision=Number.MAX_SAFE_INTEGER+1;
  if(failure==='wrong bound revision')binding.run_revision=3;
  if(failure==='wrong bound run')binding.run_id='other-run';
  if(failure==='filesystem locator')admission.candidate_locator='/tmp/candidate_graph.json';
  if(failure==='empty digest')component.sha256='';
  if(failure==='malformed digest')component.sha256='not-a-digest';
  if(failure==='missing bound digest')delete binding.components.candidate_graph;
  expect(()=>assertRecapPrepared(response,databaseRun,review,'managed-a')).toThrow('The sealed publication does not match');
});
beforeEach(()=>{
  localStorage.clear();
  vi.spyOn(api,'prepareExtractPromote').mockResolvedValue(structuredClone(prepared));
  vi.spyOn(api,'confirmExtractPromote').mockRejectedValue(new Error('simulated unknown confirmation outcome'));
  vi.spyOn(live,'postWorldGraphProjection').mockRejectedValue(new Error('not confirming in this test'));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('uses existing explicit prepare/confirm owner without loading a catalog',async()=>{
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(api.prepareExtractPromote).not.toHaveBeenCalled();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  const merge=await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  expect(api.prepareExtractPromote).toHaveBeenCalledExactlyOnceWith({runId:'run-a',managedWorldId:'managed-a'});
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();
  fireEvent.click(merge);await waitFor(()=>expect(api.confirmExtractPromote).toHaveBeenCalledExactlyOnceWith({reviewPackage:prepared.reviewPackage,assertionIds:['0:source_extraction::keeper']}));
});
it.each(['world','run','campaign','session'])('rejects prepared foreign %s before exposing confirmation',async field=>{
  const value=structuredClone(prepared);if(field==='world')value.worldId='other';if(field==='run')value.runId='other';if(field==='campaign')value.campaignId='other';if(field==='session')value.sessionId='session-31';
  vi.mocked(api.prepareExtractPromote).mockResolvedValue(value);
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));expect(await screen.findByRole('alert')).toHaveTextContent('do not match');
  expect(screen.queryByRole('button',{name:/Merge .*change/})).not.toBeInTheDocument();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});
it('drops a late prepared response after source scope unmounts',async()=>{
  let resolve!:(p:ExtractPromotePrepareResponse)=>void;vi.mocked(api.prepareExtractPromote).mockReturnValue(new Promise(r=>{resolve=r;}));
  const view=render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));view.unmount();await act(async()=>resolve(prepared));
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});

it('retains and replays the exact successful receipt without a classic projection',async()=>{
  vi.mocked(api.confirmExtractPromote).mockResolvedValue({schema:'dmb_extract_promote_confirm_v2',outcome:'committed',worldId:'native-a',proposalId:'proposal-a',proposalDigest:'digest-a',
    parentRevisionId:'rev:1',committedRevisionId:'rev:2',headAdvanced:true,selectedAssertionIds:['0:source_extraction::keeper'],acceptedAssertionIds:['0:source_extraction::keeper'],
    affectedObjectIds:[],appliedAssertionCount:1,auditStatus:'ok',warnings:[]});
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  expect(await screen.findByText('These changes are committed to campaign memory.')).toBeInTheDocument();
  expect(api.confirmExtractPromote).toHaveBeenCalledOnce();
  cleanup();render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  const recover=await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(api.confirmExtractPromote).toHaveBeenCalledOnce();
  expect(screen.queryByText('These changes are committed to campaign memory.')).not.toBeInTheDocument();
  vi.mocked(api.confirmExtractPromote).mockResolvedValue({...vi.mocked(api.confirmExtractPromote).mock.settledResults[0].value,outcome:'already_applied'});
  fireEvent.click(recover);
  await screen.findByText('These changes are committed to campaign memory.');
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api.confirmExtractPromote).mock.calls[1]).toEqual(vi.mocked(api.confirmExtractPromote).mock.calls[0]);
  expect(screen.getByTestId("graph-review-extract-promote-receipt")).toHaveTextContent("rev:1 → rev:2");
  expect(live.postWorldGraphProjection).not.toHaveBeenCalled();
});

it('persists exact selected choices before dispatch, restores them after reload and retries only explicitly',async()=>{
  const key=recapPublicationRecoveryKey(recapPublicationScope(review,run,'managed-a'));
  vi.mocked(api.confirmExtractPromote).mockImplementation(async request=>{
    const stored=JSON.parse(localStorage.getItem(key)!);
    expect(stored.prepared.reviewPackage).toEqual(request.reviewPackage);expect(stored.assertionIds).toEqual(request.assertionIds);
    throw new Error('lost response');
  });
  const first=render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  await screen.findByRole('button',{name:'Retry exact confirm'});first.unmount();
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  const retry=await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).toHaveBeenCalledOnce();
  expect(screen.getByRole('checkbox',{name:'Select Keeper'})).toBeDisabled();
  fireEvent.click(retry);await waitFor(()=>expect(api.confirmExtractPromote).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.confirmExtractPromote).mock.calls[1]).toEqual(vi.mocked(api.confirmExtractPromote).mock.calls[0]);
});
it('does not confirm if exact request storage fails',async()=>{
  const view=render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  const merge=await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});
  fireEvent.click(merge);expect(await screen.findByRole('alert')).toHaveTextContent('storage full');
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();view.unmount();
});
it('keeps the same prepared proposal across close/reopen and a full remount',async()=>{
  const first=render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  fireEvent.click(screen.getByRole('button',{name:'Close'}));
  fireEvent.click(screen.getByRole('button',{name:'Reopen saved publication review'}));
  expect(screen.getByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
  first.unmount();render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});
it.each(['scope','proposal','choices','null item'])('fails closed on malformed or cross-bound saved %s',async field=>{
  const scope=recapPublicationScope(review,run,'managed-a');
  const value:any={schema:'dmb_build_recap_publication_recovery_v1',scope,prepared:structuredClone(prepared),assertionIds:['0:source_extraction::keeper'],canReprepare:false,selectionIds:null};
  if(field==='scope')value.scope='another source';if(field==='proposal')value.prepared.worldId='other';
  if(field==='choices')value.assertionIds=['foreign assertion'];if(field==='null item')value.prepared.reviewItems=[null];
  localStorage.setItem(recapPublicationRecoveryKey(scope),JSON.stringify(value));
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(screen.getByRole('alert')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Prepare changes for review'})).toBeDisabled();
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();expect(api.prepareExtractPromote).not.toHaveBeenCalled();
});

it.each(['proposal id','world','source','source revision','candidate','managed World','campaign'])('refuses foreign nested sealed %s even when outer recovery metadata matches',async field=>{
  const scope=recapPublicationScope(review,run,'managed-a'), foreign=structuredClone(prepared);
  const pkg=foreign.reviewPackage as any;
  if(field==='proposal id')pkg.proposal_id='foreign';if(field==='world')pkg.effect.world_id='foreign';
  if(field==='source')pkg.effect.source_artifact_id='foreign';if(field==='source revision')pkg.effect.source_revision_id='sha256:'+ 'f'.repeat(64);
  if(field==='candidate')pkg.effect.candidate_admission.candidate_locator='/private/artifact-root/runs/foreign/candidate_graph.json';
  if(field==='managed World')pkg.effect.managed_world_publication_target.managed_world_id='foreign';
  if(field==='campaign')pkg.effect.world_campaign_ingest_context.campaign_id='foreign';
  localStorage.setItem(recapPublicationRecoveryKey(scope),JSON.stringify({schema:'dmb_build_recap_publication_recovery_v1',scope,prepared:foreign,
    assertionIds:['0:source_extraction::keeper'],canReprepare:false,selectionIds:null}));
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('sealed publication');expect(api.confirmExtractPromote).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:'Retry exact confirm'})).not.toBeInTheDocument();
});
it('retains an unsubmitted or stale-parent rejected proposal and allows preparing against the current World',async()=>{
  const scope=recapPublicationScope(review,run,'managed-a'), key=recapPublicationRecoveryKey(scope);
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  fireEvent.click(screen.getByRole('button',{name:'Set aside proposal and prepare again'}));
  expect(localStorage.getItem(key)).toBeNull();expect(JSON.parse(localStorage.getItem(key+':retained')!)).toHaveLength(1);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  vi.mocked(api.confirmExtractPromote).mockRejectedValue(new api.ExtractPromoteApiError('head advanced',409,'governed_write_stale_parent'));
  fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('head advanced');
  const reprepare=await screen.findByRole('button',{name:'Set aside proposal and prepare again'});
  await waitFor(()=>expect(reprepare).toBeEnabled());fireEvent.click(reprepare);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  expect(api.prepareExtractPromote).toHaveBeenCalledTimes(3);
});
it('never offers a fresh proposal when an original confirmation is uncertain, including after reload',async()=>{
  const first=render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(screen.queryByRole('button',{name:'Set aside proposal and prepare again'})).not.toBeInTheDocument();
  first.unmount();render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(screen.queryByRole('button',{name:'Set aside proposal and prepare again'})).not.toBeInTheDocument();
});

it('accepts the current single-source flat package emitted by the existing prepare owner',async()=>{
  const current=structuredClone(prepared);current.reviewPackage.proposal_version=2;
  vi.mocked(api.prepareExtractPromote).mockResolvedValue(current);
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  expect(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
});
it('preserves the active rejected proposal if retaining it fails',async()=>{
  const key=recapPublicationRecoveryKey(recapPublicationScope(review,run,'managed-a'));
  render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  const raw=localStorage.getItem(key), original=Storage.prototype.setItem;
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(k,v){if(k===key+':retained')throw new Error('retention storage full');original.call(this,k,v);});
  fireEvent.click(screen.getByRole('button',{name:'Set aside proposal and prepare again'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('retention storage full');
  expect(localStorage.getItem(key)).toBe(raw);expect(screen.getByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});

it('retains unsubmitted review selections through a full remount without confirming',async()=>{
  const first=render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  fireEvent.click(await screen.findByRole('checkbox',{name:'Select Keeper'}));
  expect(screen.getByRole('checkbox',{name:'Select Keeper'})).not.toBeChecked();
  first.unmount();render(<RetainedRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(await screen.findByRole('checkbox',{name:'Select Keeper'})).not.toBeChecked();
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});


it('the public entry preserves a retained unsubmitted classic packet without preparing again',async()=>{
  const scope=recapPublicationScope(review,run,'managed-a');
  localStorage.setItem(recapPublicationRecoveryKey(scope),JSON.stringify({schema:'dmb_build_recap_publication_recovery_v1',scope,prepared,assertionIds:null,selectionIds:null,canReprepare:true}));
  const nativeRead=vi.spyOn(native,'loadRecapSnapshot');
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
  expect(api.prepareExtractPromote).not.toHaveBeenCalled();expect(api.confirmExtractPromote).not.toHaveBeenCalled();expect(nativeRead).not.toHaveBeenCalled();
});
it('the public fresh entry uses native without a selector or classic error fallback',async()=>{
  const fresh={...run,revision:2};
  const nativeRead=vi.spyOn(native,'loadRecapSnapshot').mockRejectedValue(new Error('exact native source unavailable'));
  render(<BuildRecapPublication review={review} run={fresh} worldId="managed-a" onBusy={vi.fn()}/>);
  await screen.findByText('exact native source unavailable');expect(nativeRead).toHaveBeenCalledOnce();
  expect(api.prepareExtractPromote).not.toHaveBeenCalled();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});
it('the public entry refuses an earlier classic snapshot rather than bypassing or converting it',()=>{
  const scope=recapPublicationScope(review,run,'managed-a'),key=recapPublicationRecoveryKey(scope),raw=JSON.stringify({schema:'dmb_build_recap_publication_recovery_v1',scope,prepared,assertionIds:null,selectionIds:null,canReprepare:true});
  localStorage.setItem(key,raw);
  render(<BuildRecapPublication review={review} run={{...run,components:{...run.components,candidate_graph:{...run.components.candidate_graph,sha256:'f'.repeat(64)}}}} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('earlier snapshot');expect(localStorage.getItem(key)).toBe(raw);expect(api.prepareExtractPromote).not.toHaveBeenCalled();
});
