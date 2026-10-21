import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/extractPromoteApi';
import * as live from '../api/liveApi';
import type {ExactRunReviewPackage,ExtractionRunRecord,ExtractPromotePrepareResponse} from '../api/types';
import {recapPublicationRecoveryKey,recapPublicationScope} from './buildRecapPublicationRecovery';
import {BuildRecapPublication} from './BuildRecapPublication';
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
beforeEach(()=>{
  localStorage.clear();
  vi.spyOn(api,'prepareExtractPromote').mockResolvedValue(structuredClone(prepared));
  vi.spyOn(api,'confirmExtractPromote').mockRejectedValue(new Error('simulated unknown confirmation outcome'));
  vi.spyOn(live,'getUnionSupergraphProjection').mockRejectedValue(new Error('catalog projection must not be read'));
  vi.spyOn(live,'postWorldGraphProjection').mockRejectedValue(new Error('not confirming in this test'));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('uses existing explicit prepare/confirm owner without loading a catalog',async()=>{
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(api.prepareExtractPromote).not.toHaveBeenCalled();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  const merge=await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  expect(api.prepareExtractPromote).toHaveBeenCalledExactlyOnceWith({runId:'run-a',managedWorldId:'managed-a'});
  expect(live.getUnionSupergraphProjection).not.toHaveBeenCalled();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
  fireEvent.click(merge);await waitFor(()=>expect(api.confirmExtractPromote).toHaveBeenCalledExactlyOnceWith({reviewPackage:prepared.reviewPackage,assertionIds:['0:source_extraction::keeper']}));
});
it.each(['world','run','campaign','session'])('rejects prepared foreign %s before exposing confirmation',async field=>{
  const value=structuredClone(prepared);if(field==='world')value.worldId='other';if(field==='run')value.runId='other';if(field==='campaign')value.campaignId='other';if(field==='session')value.sessionId='session-31';
  vi.mocked(api.prepareExtractPromote).mockResolvedValue(value);
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));expect(await screen.findByRole('alert')).toHaveTextContent('do not match');
  expect(screen.queryByRole('button',{name:/Merge .*change/})).not.toBeInTheDocument();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});
it('drops a late prepared response after source scope unmounts',async()=>{
  let resolve!:(p:ExtractPromotePrepareResponse)=>void;vi.mocked(api.prepareExtractPromote).mockReturnValue(new Promise(r=>{resolve=r;}));
  const view=render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));view.unmount();await act(async()=>resolve(prepared));
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});

it('retains successful receipt and reads its exact native World/revision without a campaign alias',async()=>{
  vi.mocked(api.confirmExtractPromote).mockResolvedValue({schema:'dmb_extract_promote_confirm_v2',outcome:'committed',worldId:'native-a',proposalId:'proposal-a',proposalDigest:'digest-a',
    parentRevisionId:'rev:1',committedRevisionId:'rev:2',headAdvanced:true,selectedAssertionIds:['0:source_extraction::keeper'],acceptedAssertionIds:['0:source_extraction::keeper'],
    affectedObjectIds:[],appliedAssertionCount:1,auditStatus:'ok',warnings:[]});
  vi.mocked(live.postWorldGraphProjection).mockResolvedValue({schema:'dmb_world_graph_projection_v1',snapshot:{worldId:'native-a',campaignId:'longmont-c2',revisionId:'rev:2',headRevisionId:'rev:2',
    isHead:true,admissibility:'gm',focus:{kind:'session',sessionId:'session-30',campaignId:'longmont-c2'}},nodes:[],relationships:[],summary:{}} as any);
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  await waitFor(()=>expect(live.postWorldGraphProjection).toHaveBeenCalledWith(expect.objectContaining({worldId:'native-a',campaignId:'longmont-c2',revisionPin:'rev:2'})));
  expect(await screen.findByText('These changes are committed to campaign memory.')).toBeInTheDocument();
  expect(api.confirmExtractPromote).toHaveBeenCalledOnce();
  cleanup();render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  const recover=await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(api.confirmExtractPromote).toHaveBeenCalledOnce();
  expect(screen.queryByText('These changes are committed to campaign memory.')).not.toBeInTheDocument();
  vi.mocked(api.confirmExtractPromote).mockResolvedValue({...vi.mocked(api.confirmExtractPromote).mock.settledResults[0].value,outcome:'already_applied'});
  fireEvent.click(recover);
  await screen.findByText('These changes are committed to campaign memory.');
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api.confirmExtractPromote).mock.calls[1]).toEqual(vi.mocked(api.confirmExtractPromote).mock.calls[0]);
  expect(live.postWorldGraphProjection).toHaveBeenLastCalledWith(expect.objectContaining({worldId:'native-a',revisionPin:'rev:2'}));
});

it('persists exact selected choices before dispatch, restores them after reload and retries only explicitly',async()=>{
  const key=recapPublicationRecoveryKey(recapPublicationScope(review,run,'managed-a'));
  vi.mocked(api.confirmExtractPromote).mockImplementation(async request=>{
    const stored=JSON.parse(localStorage.getItem(key)!);
    expect(stored.prepared.reviewPackage).toEqual(request.reviewPackage);expect(stored.assertionIds).toEqual(request.assertionIds);
    throw new Error('lost response');
  });
  const first=render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  await screen.findByRole('button',{name:'Retry exact confirm'});first.unmount();
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  const retry=await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).toHaveBeenCalledOnce();
  expect(screen.getByRole('checkbox',{name:'Select Keeper'})).toBeDisabled();
  fireEvent.click(retry);await waitFor(()=>expect(api.confirmExtractPromote).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.confirmExtractPromote).mock.calls[1]).toEqual(vi.mocked(api.confirmExtractPromote).mock.calls[0]);
});
it('does not confirm if exact request storage fails',async()=>{
  const view=render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  const merge=await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});
  fireEvent.click(merge);expect(await screen.findByRole('alert')).toHaveTextContent('storage full');
  expect(api.confirmExtractPromote).not.toHaveBeenCalled();view.unmount();
});
it('keeps the same prepared proposal across close/reopen and a full remount',async()=>{
  const first=render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  await screen.findByRole('button',{name:'Merge 1 change into campaign memory'});
  fireEvent.click(screen.getByRole('button',{name:'Close'}));
  fireEvent.click(screen.getByRole('button',{name:'Reopen saved publication review'}));
  expect(screen.getByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
  first.unmount();render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});
it.each(['scope','proposal','choices','null item'])('fails closed on malformed or cross-bound saved %s',async field=>{
  const scope=recapPublicationScope(review,run,'managed-a');
  const value:any={schema:'dmb_build_recap_publication_recovery_v1',scope,prepared:structuredClone(prepared),assertionIds:['0:source_extraction::keeper'],canReprepare:false,selectionIds:null};
  if(field==='scope')value.scope='another source';if(field==='proposal')value.prepared.worldId='other';
  if(field==='choices')value.assertionIds=['foreign assertion'];if(field==='null item')value.prepared.reviewItems=[null];
  localStorage.setItem(recapPublicationRecoveryKey(scope),JSON.stringify(value));
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
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
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('sealed publication');expect(api.confirmExtractPromote).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:'Retry exact confirm'})).not.toBeInTheDocument();
});
it('retains an unsubmitted or stale-parent rejected proposal and allows preparing against the current World',async()=>{
  const scope=recapPublicationScope(review,run,'managed-a'), key=recapPublicationRecoveryKey(scope);
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
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
  const first=render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  fireEvent.click(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'}));
  await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(screen.queryByRole('button',{name:'Set aside proposal and prepare again'})).not.toBeInTheDocument();
  first.unmount();render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  await screen.findByRole('button',{name:'Retry exact confirm'});
  expect(screen.queryByRole('button',{name:'Set aside proposal and prepare again'})).not.toBeInTheDocument();
});

it('accepts the current single-source flat package emitted by the existing prepare owner',async()=>{
  const current=structuredClone(prepared);current.reviewPackage.proposal_version=2;
  vi.mocked(api.prepareExtractPromote).mockResolvedValue(current);
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  expect(await screen.findByRole('button',{name:'Merge 1 change into campaign memory'})).toBeVisible();
});
it('preserves the active rejected proposal if retaining it fails',async()=>{
  const key=recapPublicationRecoveryKey(recapPublicationScope(review,run,'managed-a'));
  render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
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
  const first=render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Prepare changes for review'}));
  fireEvent.click(await screen.findByRole('checkbox',{name:'Select Keeper'}));
  expect(screen.getByRole('checkbox',{name:'Select Keeper'})).not.toBeChecked();
  first.unmount();render(<BuildRecapPublication review={review} run={run} worldId="managed-a" onBusy={vi.fn()}/>);
  expect(await screen.findByRole('checkbox',{name:'Select Keeper'})).not.toBeChecked();
  expect(api.prepareExtractPromote).toHaveBeenCalledOnce();expect(api.confirmExtractPromote).not.toHaveBeenCalled();
});
