import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/extractPromoteApi';
import * as live from '../api/liveApi';
import type {ExactRunReviewPackage,ExtractionRunRecord,ExtractPromotePrepareResponse} from '../api/types';
import {BuildRecapPublication} from './BuildRecapPublication';
const run={run_id:'run-a',source_artifact_id:'source-a',source_domain:'recap',campaign_id:'longmont-c2',session_id:'session-30',
  lineage:{world_campaign_ingest_context:{managed_world_id:'managed-a',native_world_id:'native-a'}}} as ExtractionRunRecord;
const review={runId:'run-a',inspectionStatus:'ready',promotable:true} as ExactRunReviewPackage;
const prepared:ExtractPromotePrepareResponse={schema:'dmb_extract_promote_prepare_v1',proposalId:'proposal-a',proposalDigest:'digest-a',parentRevisionId:'rev:1',
  worldId:'native-a',runId:'run-a',campaignId:'longmont-c2',sessionId:'session-30',acceptedProposalsCount:1,unresolvedMentionsCount:0,rejectedAssertionsCount:0,
  reviewPackage:{schema:'dmb_extract_promote_proposal_v1'},reviewSummary:{newObjectCount:1,connectExistingCount:0,relationshipCount:0,unresolvedMentionCount:0,rejectedAssertionCount:0},
  reviewItems:[{assertionId:'keeper',sliceQualifiedId:'0:source_extraction::keeper',kind:'object',label:'Keeper',action:'create',identityOutcome:'created_new',
    summary:'Create keeper',warnings:[],selectable:true,selectedByDefault:true,dependsOnAssertionIds:[],dependsOnSliceQualifiedIds:[]}]};
beforeEach(()=>{
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
});
