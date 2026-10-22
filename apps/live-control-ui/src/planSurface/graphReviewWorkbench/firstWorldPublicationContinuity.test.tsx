import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {useState} from 'react';
import * as live from '../../api/liveApi';
import * as first from '../../api/extractPromoteApi';
import type {ExactRunReviewPackage, FirstWorldGraphPlan, FirstWorldGraphConfirmReceipt} from '../../api/types';
import {GraphReviewWorldbuildingPublication} from './GraphReviewWorldbuildingPublication';
import {withFirstWorldEffect} from './firstWorldPublicationRecovery.testSupport';
import {readFirstWorldRecovery} from './firstWorldPublicationRecovery';

vi.mock('../../selectedWorld/SelectedWorldContext',()=>({useSelectedWorld:()=>({kind:'managed',worldId:'world-a',name:'A'})}));
const review:ExactRunReviewPackage={schema:'dmb_extract_promote_exact_run_review_v1',runId:'run-a',sourceDomain:'worldbuilding',
  inspectionStatus:'ready',worldId:'world-a',sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+'c'.repeat(64),
  sourceProse:'The guardian watches.',diagnostics:[],promotable:false,worldState:'uninitialized',firstWorldPublishEligible:true,
  assertions:[{assertionId:'guardian',kind:'object', nodeType: "npc", contributionKind: "npc",label:'Guardian',summary:'The guardian watches.',evidence:[{
    sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'The guardian watches.',anchorQuotes:['guardian']}]}]};
const plan:FirstWorldGraphPlan=withFirstWorldEffect({schema:'dmb_first_world_graph_plan_v3',sourceEvidenceSha256:'sha256:'+'d'.repeat(64),
  nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},
  planId:'plan-a',planDigest:'sha256:'+'a'.repeat(64),decisionDigest:'sha256:'+'b'.repeat(64),worldId:'world-a',runId:'run-a',
  sourceArtifactId:review.sourceArtifactId,sourceRevisionId:review.sourceRevisionId,workspaceDocumentId:'doc-a',workspaceDocumentRevision:'2',
  extractionProfile:'worldbuilding_shepherds_flock_v0@0.1',acceptedAssertionIds:['assertion-a'],rejectedAssertionIds:[],
  contributionId:'contribution-a',contributionPayloadSha256:'d'.repeat(64),
  reviewedEffect:{decision_snapshot:[{assertion_id:'guardian',candidate_kind:'node',decision:'create_new',target_node_id:null}]},
  summary:{createNewNodeCount:1,acceptedEdgeCount:0,rejectedCandidateCount:0,acceptedAssertionCount:1},confirmable:true,diagnostics:[]},review);
const receipt:FirstWorldGraphConfirmReceipt={schema:'dmb_first_world_graph_confirm_v1',outcome:'initialized',worldId:'world-a',
  planId:plan.planId,planDigest:plan.planDigest,decisionDigest:plan.decisionDigest,sourceArtifactId:plan.sourceArtifactId,
  sourceRevisionId:plan.sourceRevisionId,contributionId:plan.contributionId,baselineRevisionId:null,committedRevisionId:'rev:1',
  appliedAssertionCount:1,acceptedAssertionIds:plan.acceptedAssertionIds,rejectedAssertionIds:[],auditStatus:'ok',warnings:[]};
function Parent({selected=review}:{selected?:ExactRunReviewPackage}){
  const [busy,setBusy]=useState(false),[renders,setRenders]=useState(0);
  return <><output data-testid="busy">{String(busy)}</output><button onClick={()=>setRenders(n=>n+1)}>Parent update {renders}</button>
    <GraphReviewWorldbuildingPublication review={selected} onConfirmInFlightChange={setBusy}/></>;
}
beforeEach(()=>{
  localStorage.clear();
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,callback:()=>unknown)=>Promise.resolve(callback())}});
  vi.spyOn(live,'postManagedWorldGraphProjection').mockRejectedValue(new live.LiveApiError('Pending',409,{code:'native_graph_provisioning_pending'}));
  vi.spyOn(first,'prepareFirstWorldGraph').mockResolvedValue(plan);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('retains the actual first receipt across parent busy and cosmetic rerenders without recovery',async()=>{
  let complete!:(value:FirstWorldGraphConfirmReceipt)=>void;
  vi.spyOn(first,'confirmFirstWorldGraph').mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
  render(<Parent/>);
  fireEvent.click(await screen.findByRole('button',{name:'Create World Graph with 1 change'}));
  await waitFor(()=>expect(first.confirmFirstWorldGraph).toHaveBeenCalledExactlyOnceWith({plan}));
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:/Parent update/}));
  expect(screen.queryByRole('button',{name:/Recover saved creation result/})).toBeNull();
  await act(async()=>complete(receipt));
  await waitFor(()=>expect(screen.getByTestId('busy')).toHaveTextContent('false'));
  expect(screen.getByTestId('graph-review-first-world-receipt')).toHaveTextContent('World Graph created');
  fireEvent.click(screen.getByRole('button',{name:/Parent update/}));
  expect(screen.getByTestId('graph-review-first-world-receipt')).toHaveTextContent('rev:1');
  expect(first.prepareFirstWorldGraph).toHaveBeenCalledTimes(1);
  expect(first.confirmFirstWorldGraph).toHaveBeenCalledTimes(1);
});

it('keeps durable recovery but never delivers a previous source receipt into another scope',async()=>{
  let complete!:(value:FirstWorldGraphConfirmReceipt)=>void;
  vi.spyOn(first,'confirmFirstWorldGraph').mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
  const mounted=render(<Parent/>);
  fireEvent.click(await screen.findByRole('button',{name:'Create World Graph with 1 change'}));
  await waitFor(()=>expect(first.confirmFirstWorldGraph).toHaveBeenCalledTimes(1));
  mounted.rerender(<Parent selected={{...review,runId:'run-b',sourceArtifactId:'source-b'}}/>);
  await screen.findByRole('button',{name:'Create World Graph with 1 change'});
  await act(async()=>complete(receipt));
  expect(screen.queryByTestId('graph-review-first-world-receipt')).toBeNull();
  expect(readFirstWorldRecovery(review)?.plan).toEqual(plan);
  mounted.rerender(<Parent/>);
  await screen.findByRole('button',{name:'Recover saved creation result'});
  expect(first.confirmFirstWorldGraph).toHaveBeenCalledTimes(1);
});


it('returns to retained choices only after an exact nonapplication proof and explicit action',async()=>{
  const proof={schema:'dmb_first_world_confirm_not_invoked_v1',worldId:plan.worldId,
    nativeWorldId:plan.nativeTarget.nativeWorldId,initializationId:plan.nativeTarget.provisioningId,
    planId:plan.planId,planDigest:plan.planDigest,initializationInvoked:false,
    validationMessage:'Invalid endpoint pair',failure:{candidate_assertion_ids:['guardian'],reason:'invalid_endpoint_kinds'}};
  vi.spyOn(first,'confirmFirstWorldGraph').mockRejectedValue(new first.ExtractPromoteApiError('Not invoked',409,
    'first_world_confirm_not_invoked',{schema:'dmb_extract_promote_error_v1',failureResult:proof}));
  render(<Parent/>);
  fireEvent.click(await screen.findByRole('button',{name:'Create World Graph with 1 change'}));
  const back=await screen.findByRole('button',{name:'Return to review'});
  expect(screen.getByRole('checkbox',{name:'Keep Guardian'})).toBeDisabled();
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
  expect(screen.getByRole('checkbox',{name:'Keep Guardian'}).closest('li')).toHaveAttribute('aria-invalid','true');
  fireEvent.click(back);
  await waitFor(()=>expect(screen.getByRole('checkbox',{name:'Keep Guardian'})).toBeEnabled());
  expect(screen.getByRole('checkbox',{name:'Keep Guardian'})).toBeChecked();
  expect(readFirstWorldRecovery(review)).toBeNull();
  expect(first.prepareFirstWorldGraph).toHaveBeenCalledTimes(1);
  expect(first.confirmFirstWorldGraph).toHaveBeenCalledTimes(1);
});
