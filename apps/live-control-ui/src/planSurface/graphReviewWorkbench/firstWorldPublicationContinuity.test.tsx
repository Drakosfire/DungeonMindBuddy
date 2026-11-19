import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {useState,type ReactNode} from 'react';
import * as live from '../../api/liveApi';
import * as first from '../../api/nativeFirstWorldPublicationApi';
import {ExtractPromoteApiError} from '../../api/extractPromoteApi';
import type {ExactRunReviewPackage} from '../../api/types';
import type {NativeFirstWorldPlan as FirstWorldGraphPlan, NativeFirstWorldReceipt as FirstWorldGraphConfirmReceipt} from '../../api/nativeFirstWorldPublicationTypes';
import {GraphReviewWorldbuildingPublication} from './GraphReviewWorldbuildingPublication';
import {withNativeFirstWorldPlan,nativeFirstWorldReceipt,legacyFirstWorldPlan} from './firstWorldPublicationRecovery.testSupport';
import {readFirstWorldRecovery,saveFirstWorldRecovery} from './firstWorldPublicationRecovery';
import {GraphReviewWorkbenchModule} from './GraphReviewWorkbenchModule';
import {GraphReviewFirstWorldRecovery} from './GraphReviewFirstWorldPublishSheet';

const selectedWorld=vi.hoisted(()=>({kind:'managed',worldId:'world-a',name:'A'}));
vi.mock('../../selectedWorld/SelectedWorldContext',()=>({useSelectedWorld:()=>selectedWorld}));
vi.mock('../../agentInteraction/AgentInteractionProvider',()=>({useAgentInteraction:()=>({
  publishProjectionSurface:()=>()=>{},updateProjectionSurfaceConfig:()=>{},
})}));
vi.mock('./GraphReviewWorkbenchHeader',()=>({GraphReviewWorkbenchHeader:()=>null}));
vi.mock('./GraphReviewDiagnosticsProjectionBinding',()=>({GraphReviewDiagnosticsProjectionBinding:()=>null}));
vi.mock('./GraphReviewCommittedProjectionPanel',()=>({GraphReviewCommittedProjectionPanel:()=>null}));
vi.mock('./GraphReviewLiveStateContext',()=>({
  GraphReviewLiveStateProvider:({children}:{children:ReactNode})=><>{children}</>,
  useGraphReviewLiveState:()=>({committedPhase:'candidate',committedReceipt:null}),
}));
const review:ExactRunReviewPackage={schema:'dmb_extract_promote_exact_run_review_v1',runId:'run-a',sourceDomain:'worldbuilding',
  inspectionStatus:'ready',worldId:'world-a',sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+'c'.repeat(64),
  sourceProse:'The guardian watches.',diagnostics:[],promotable:false,worldState:'uninitialized',firstWorldPublishEligible:true,
  assertions:[{assertionId:'guardian',kind:'object', nodeType: "npc", contributionKind: "npc",label:'Guardian',summary:'The guardian watches.',evidence:[{
    sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'The guardian watches.',anchorQuotes:['guardian']}]}]};
const plan:FirstWorldGraphPlan=withNativeFirstWorldPlan({schema:'dmb_first_world_graph_plan_v3',sourceEvidenceSha256:'sha256:'+'d'.repeat(64),
  nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},
  planId:'plan-a',planDigest:'sha256:'+'a'.repeat(64),decisionDigest:'sha256:'+'b'.repeat(64),worldId:'world-a',runId:'run-a',
  sourceArtifactId:review.sourceArtifactId,sourceRevisionId:review.sourceRevisionId,workspaceDocumentId:'doc-a',workspaceDocumentRevision:'2',
  extractionProfile:'worldbuilding_shepherds_flock_v0@0.1',acceptedAssertionIds:['assertion-a'],rejectedAssertionIds:[],
  contributionId:'contribution-a',contributionPayloadSha256:'d'.repeat(64),
  reviewedEffect:{decision_snapshot:[{assertion_id:'guardian',candidate_kind:'node',decision:'create_new',target_node_id:null}]},
  summary:{createNewNodeCount:1,acceptedEdgeCount:0,rejectedCandidateCount:0,acceptedAssertionCount:1},confirmable:true,diagnostics:[]},review);
const receipt:FirstWorldGraphConfirmReceipt=nativeFirstWorldReceipt(plan);
function Parent({selected=review}:{selected?:ExactRunReviewPackage}){
  const [busy,setBusy]=useState(false),[renders,setRenders]=useState(0);
  return <><output data-testid="busy">{String(busy)}</output><button onClick={()=>setRenders(n=>n+1)}>Parent update {renders}</button>
    <GraphReviewWorldbuildingPublication review={selected} onConfirmInFlightChange={setBusy}/></>;
}
beforeEach(()=>{
  localStorage.clear();selectedWorld.worldId='world-a';
  vi.spyOn(live,'getManualReviewBeds').mockRejectedValue(new Error('No manual fixture'));
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,callback:()=>unknown)=>Promise.resolve(callback())}});
  vi.spyOn(live,'postManagedWorldGraphProjection').mockRejectedValue(new live.LiveApiError('Pending',409,{code:'native_graph_provisioning_pending'}));
  vi.spyOn(first,'prepareNativeFirstWorld').mockResolvedValue(plan);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('retains the actual first receipt across parent busy and cosmetic rerenders without recovery',async()=>{
  let complete!:(value:FirstWorldGraphConfirmReceipt)=>void;
  vi.spyOn(first,'confirmNativeFirstWorld').mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
  render(<Parent/>);
  fireEvent.click(await screen.findByRole('button',{name:'Review World Graph with 1 change'}));
  fireEvent.click(await screen.findByRole('button',{name:'Confirm native World creation'}));
  await waitFor(()=>expect(first.confirmNativeFirstWorld).toHaveBeenCalledExactlyOnceWith({schema:'dmb_native_first_world_confirm_request_v1',plan}));
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:/Parent update/}));
  expect(screen.queryByRole('button',{name:/Recover saved creation result/})).toBeNull();
  await act(async()=>complete(receipt));
  await waitFor(()=>expect(screen.getByTestId('busy')).toHaveTextContent('false'));
  expect(screen.getByTestId('graph-review-first-world-receipt')).toHaveTextContent('World Graph created');
  fireEvent.click(screen.getByRole('button',{name:/Parent update/}));
  expect(screen.getByTestId('graph-review-first-world-receipt')).toHaveTextContent('rev:1');
  expect(first.prepareNativeFirstWorld).toHaveBeenCalledTimes(1);
  expect(first.confirmNativeFirstWorld).toHaveBeenCalledTimes(1);
});

it('keeps durable recovery but never delivers a previous source receipt into another scope',async()=>{
  let complete!:(value:FirstWorldGraphConfirmReceipt)=>void;
  vi.spyOn(first,'confirmNativeFirstWorld').mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
  const mounted=render(<Parent/>);
  fireEvent.click(await screen.findByRole('button',{name:'Review World Graph with 1 change'}));
  fireEvent.click(await screen.findByRole('button',{name:'Confirm native World creation'}));
  await waitFor(()=>expect(first.confirmNativeFirstWorld).toHaveBeenCalledTimes(1));
  mounted.rerender(<Parent selected={{...review,runId:'run-b',sourceArtifactId:'source-b'}}/>);
  await screen.findByRole('button',{name:'Review World Graph with 1 change'});
  await act(async()=>complete(receipt));
  expect(screen.queryByTestId('graph-review-first-world-receipt')).toBeNull();
  expect(readFirstWorldRecovery(review)?.plan).toEqual(plan);
  mounted.rerender(<Parent/>);
  await screen.findByRole('button',{name:'Recover saved creation result'});
  expect(first.confirmNativeFirstWorld).toHaveBeenCalledTimes(1);
});


it('retains submitted native recovery after a request-local nonapplication result',async()=>{
  const proof={schema:'dmb_first_world_confirm_not_invoked_v1',worldId:plan.worldId,
    nativeWorldId:plan.nativeTarget.nativeWorldId,initializationId:plan.nativeTarget.provisioningId,
    planId:plan.planId,planDigest:plan.planDigest,initializationInvoked:false,
    validationMessage:'Invalid endpoint pair',failure:{candidate_assertion_ids:['guardian'],reason:'invalid_endpoint_kinds'}};
  vi.spyOn(first,'confirmNativeFirstWorld').mockRejectedValue(new ExtractPromoteApiError('Not invoked',409,
    'first_world_confirm_not_invoked',{schema:'dmb_extract_promote_error_v1',failureResult:proof}));
  render(<Parent/>);
  fireEvent.click(await screen.findByRole('button',{name:'Review World Graph with 1 change'}));
  fireEvent.click(await screen.findByRole('button',{name:'Confirm native World creation'}));
  await screen.findByRole('button',{name:'Recover saved creation result'});
  expect(screen.getByRole('checkbox',{name:'Keep Guardian'})).toBeDisabled();
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
  expect(screen.getByRole('checkbox',{name:'Keep Guardian'}).closest('li')).toHaveAttribute('aria-invalid','true');
  expect(screen.queryByRole('button',{name:'Return to review'})).toBeNull();
  expect(first.prepareNativeFirstWorld).toHaveBeenCalledTimes(1);
  expect(first.confirmNativeFirstWorld).toHaveBeenCalledTimes(1);
});


function MissingReviewWorkbench({sourceReviewOnly=false,runId='run-a'}:{sourceReviewOnly?:boolean;runId?:string}){
  const search='?extractionRunId='+runId;
  return <GraphReviewWorkbenchModule context={{campaignId:'campaign',liveSession:1,ingestSession:1,headerLabel:'Ingest'}}
    locationSearch={search} sourceReviewOnly={sourceReviewOnly}
    initialRunObservation={{status:'error',message:'The current run/source is unavailable',
      owner:{worldId:selectedWorld.worldId,search,generation:1,accessGeneration:1}}}/>;
}

it('mounts deliberate exact-request recovery in the real Workbench with no current review',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  vi.spyOn(first,'confirmNativeFirstWorld').mockResolvedValue(receipt);
  render(<MissingReviewWorkbench/>);
  const retry=await screen.findByRole('button',{name:'Recover saved creation result'});
  expect(first.confirmNativeFirstWorld).not.toHaveBeenCalled();
  fireEvent.click(retry);
  await screen.findByTestId('graph-review-first-world-receipt');
  expect(first.confirmNativeFirstWorld).toHaveBeenCalledExactlyOnceWith({schema:'dmb_native_first_world_confirm_request_v1',plan});
  expect(first.prepareNativeFirstWorld).not.toHaveBeenCalled();
});

it.each(['sourceReviewOnly','otherWorld','otherRun'] as const)('fences Workbench saved recovery by %s',async boundary=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  const confirm=vi.spyOn(first,'confirmNativeFirstWorld');
  if(boundary==='otherWorld')selectedWorld.worldId='world-b';
  render(<MissingReviewWorkbench sourceReviewOnly={boundary==='sourceReviewOnly'} runId={boundary==='otherRun'?'run-b':'run-a'}/>);
  await screen.findByTestId('graph-review-workbench');
  expect(screen.queryByRole('button',{name:'Recover saved creation result'})).toBeNull();
  expect(confirm).not.toHaveBeenCalled();expect(first.prepareNativeFirstWorld).not.toHaveBeenCalled();
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
});

it('retains activation-pending and unavailable-source outcomes and retries only the saved request',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  vi.spyOn(first,'confirmNativeFirstWorld').mockResolvedValueOnce({...receipt,outcome:'activation_pending',activationStatus:'pending',sourceStatus:'unavailable'})
    .mockResolvedValueOnce({...receipt,outcome:'already_initialized',recovered:true});
  render(<GraphReviewFirstWorldRecovery worldId={review.worldId} runId={review.runId}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Recover saved creation result'}));
  expect(await screen.findByText('Native graph committed; World activation pending')).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('Citation access remains denied');
  expect(readFirstWorldRecovery(review)?.submitted).toBe(true);
  fireEvent.click(await screen.findByRole('button',{name:'Recover saved creation result'}));
  await screen.findByText('World Graph already exists');
  expect(first.confirmNativeFirstWorld).toHaveBeenNthCalledWith(1,{schema:'dmb_native_first_world_confirm_request_v1',plan});
  expect(first.confirmNativeFirstWorld).toHaveBeenNthCalledWith(2,{schema:'dmb_native_first_world_confirm_request_v1',plan});
  expect(first.prepareNativeFirstWorld).not.toHaveBeenCalled();
});

it('recovers a submitted v3 classic request as explicit historical-only receipt',async()=>{
  const legacy=legacyFirstWorldPlan(plan);
  await saveFirstWorldRecovery(review,legacy,false,()=>true);await saveFirstWorldRecovery(review,legacy,true,()=>true);
  vi.spyOn(first,'confirmNativeFirstWorld').mockResolvedValue({schema:'dmb_historical_first_world_receipt_v1',
    worldId:legacy.worldId,nativeWorldId:legacy.nativeTarget.nativeWorldId,planId:legacy.planId,planDigest:legacy.planDigest,
    activationStatus:'historical_only',historicalReceipt:{world_id:legacy.nativeTarget.nativeWorldId,
      source_plan_id:legacy.planId,source_plan_sha256:legacy.planDigest.slice(7)}});
  render(<GraphReviewFirstWorldRecovery worldId={review.worldId} runId={review.runId}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Recover saved creation result'}));
  await screen.findByText('Historical classic World creation receipt recovered.');
  expect(screen.getByText('This is read-only history, not native activation.')).toBeInTheDocument();
  expect(first.confirmNativeFirstWorld).toHaveBeenCalledExactlyOnceWith({schema:'dmb_first_world_graph_confirm_request_v1',plan:legacy});
  expect(first.prepareNativeFirstWorld).not.toHaveBeenCalled();
});

it('recovers the original native request after today’s source revision and candidate list change',async()=>{
  await saveFirstWorldRecovery(review,plan,false,()=>true);await saveFirstWorldRecovery(review,plan,true,()=>true);
  vi.spyOn(first,'confirmNativeFirstWorld').mockResolvedValue(receipt);
  render(<Parent selected={{...review,sourceRevisionId:'sha256:'+'f'.repeat(64),assertions:[],inspectionStatus:'invalid_evidence'}}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Recover saved creation result'}));
  await screen.findByTestId('graph-review-first-world-receipt');
  expect(first.confirmNativeFirstWorld).toHaveBeenCalledExactlyOnceWith({schema:'dmb_native_first_world_confirm_request_v1',plan});
  expect(first.prepareNativeFirstWorld).not.toHaveBeenCalled();
});
