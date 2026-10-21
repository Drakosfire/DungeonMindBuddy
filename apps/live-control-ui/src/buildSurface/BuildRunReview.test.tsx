import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import * as extract from '../api/extractPromoteApi';
import * as live from '../api/liveApi';
import * as publication from '../api/worldbuildingPublicationApi';
import type { ExactRunReviewPackage, WorkspaceDocumentRecord, ExtractionRunRecord } from '../api/types';
import { BuildRunReview } from './BuildRunReview';
const selection=vi.hoisted(()=>({kind:'managed',worldId:'world-a'}));
vi.mock('../selectedWorld/SelectedWorldContext',()=>({useSelectedWorld:()=>selection}));
const hash='b'.repeat(64), candidate='a'.repeat(64);
const document={document_id:'doc-a',title:'Edge',world_id:'world-a'} as WorkspaceDocumentRecord;
const run={schema_version:'dmb_extraction_run_v1',version:'1.0',run_id:'run-a',source_artifact_id:'source-a',
  source_domain:'worldbuilding',status:'reviewable',components:{candidate_graph:{kind:'candidate_graph',uri:'candidate.json',exists:true,sha256:candidate}}} as ExtractionRunRecord;
const handoff={href:'/build?documentId=doc-a&revision=2&sourceArtifactId=source-a&extractionRunId=run-a',
  extraction_run_id:'run-a',source_artifact_id:'source-a',document_id:'doc-a',document_revision:2};
const review:ExactRunReviewPackage={schema:'dmb_extract_promote_exact_run_review_v1',runId:'run-a',sourceDomain:'worldbuilding',
  sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+hash,worldId:'world-a',sourceProse:'Full source prose must not become a second surface',
  inspectionStatus:'ready',diagnostics:[],assertions:[{assertionId:'keeper',kind:'object',label:'Keeper',summary:'A keeper',
    evidence:[{sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'The keeper watches the gate.',anchorQuotes:['keeper']}]}]};
function props(){return {document,currentRevision:3,run,handoff,sourceContentSha256:hash,onClose:vi.fn(),onDerivedRun:vi.fn().mockResolvedValue(()=>undefined),onBusyChange:vi.fn(),onSemanticDecision:vi.fn().mockResolvedValue(()=>undefined)};}
beforeEach(()=>{
  selection.worldId='world-a';localStorage.clear();
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>Promise.resolve(action())}});
  vi.spyOn(extract,'getExactRunReviewPackage').mockResolvedValue(structuredClone(review));
  vi.spyOn(extract,'correctExactRunEvidence').mockResolvedValue({schema:'dmb_exact_run_evidence_correction_response_v1',runId:'run-b',
    parentRunId:'run-a',parentCandidateSha256:candidate,candidateSha256:'c'.repeat(64),correctionDigest:'d'.repeat(64),status:'reviewable'});
  vi.spyOn(live,'postManagedWorldGraphProjection').mockResolvedValue({schema:'dmb_managed_world_graph_projection_v1',managedWorldId:'world-a',nativeWorldId:'native-a',bindingVersion:1,
    projection:{snapshot:{worldId:'native-a',revisionId:'rev:1',headRevisionId:'rev:1',isHead:true},nodes:[]}} as any);
  vi.spyOn(publication,'getWorldbuildingCapabilities').mockResolvedValue({schema:'dmb_worldbuilding_publication_capabilities_v1',configured:true,confirmationSupported:true,unavailabilityReasons:[]});
  vi.spyOn(publication,'prepareWorldbuilding').mockRejectedValue(new Error('Prepared operation deliberately stopped in test'));
  vi.spyOn(publication,'confirmWorldbuilding').mockRejectedValue(new Error('No confirmation authorized in test'));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('reads one exact run, shows frozen revision, and reuses owner decisions without another source surface',async()=>{
  render(<BuildRunReview {...props()}/>);
  await waitFor(()=>expect(screen.getByRole('group',{name:'Publication choices'})).not.toBeDisabled());
  expect(extract.getExactRunReviewPackage).toHaveBeenCalledExactlyOnceWith('run-a');
  expect(screen.getByText(/editor has newer changes/)).toHaveTextContent('Edge');
  expect(screen.queryByText(review.sourceProse)).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Canonical source prose')).not.toBeInTheDocument();
  expect(publication.prepareWorldbuilding).not.toHaveBeenCalled();expect(publication.confirmWorldbuilding).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Decision for Keeper'),{target:{value:'create_new'}});
  fireEvent.click(screen.getByRole('button',{name:'Prepare proposed changes'}));
  await waitFor(()=>expect(publication.prepareWorldbuilding).toHaveBeenCalledWith({runId:'run-a',expectedParentRevisionId:'rev:1',dispositions:[{assertionId:'keeper',decision:'create_new'}]}));
  expect(publication.confirmWorldbuilding).not.toHaveBeenCalled();
});
it.each(['world','digest','artifact','run'])('rejects mismatched review %s before publication',async field=>{
  const changed=structuredClone(review);
  if(field==='world')changed.worldId='other';if(field==='digest')changed.sourceRevisionId='c'.repeat(64);
  if(field==='artifact')changed.sourceArtifactId='other';if(field==='run')changed.runId='other';
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(changed);
  render(<BuildRunReview {...props()}/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('does not match');
  expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();
});
it('discards a late review when the selected World changes',async()=>{
  let resolve!:(v:ExactRunReviewPackage)=>void;
  vi.mocked(extract.getExactRunReviewPackage).mockReturnValue(new Promise(r=>{resolve=r;}));
  const p=props(),view=render(<BuildRunReview {...p}/>);
  selection.worldId='other';view.rerender(<BuildRunReview {...p}/>);
  await act(async()=>resolve(review));
  expect(screen.getByRole('status')).toHaveTextContent('verified World');
  expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();
});
it('retains the exact failed correction and retries deliberately with the same request',async()=>{
  const invalid=structuredClone(review);invalid.inspectionStatus='invalid_evidence';
  invalid.assertions[0].evidence[0].anchorQuotes=['bad quote'];invalid.assertions[0].evidence[0].invalidAnchorQuotes=['bad quote'];
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(invalid);
  vi.mocked(extract.correctExactRunEvidence).mockRejectedValueOnce(new Error('lost response'));
  const p=props();render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  fireEvent.click(screen.getByRole('button',{name:'Create reviewed child candidate'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('lost response');
  expect(p.onDerivedRun).not.toHaveBeenCalled();
  const request=vi.mocked(extract.correctExactRunEvidence).mock.calls[0][0];
  expect(localStorage.length).toBe(1);
  fireEvent.click(screen.getByRole('button',{name:'Retry saved quote corrections'}));
  await waitFor(()=>expect(p.onDerivedRun).toHaveBeenCalledOnce());
  expect(extract.correctExactRunEvidence).toHaveBeenNthCalledWith(2,request);
  expect(localStorage.length).toBe(0);
});

it('keeps original recovery when World changes during awaited child adoption',async()=>{
  const invalid=structuredClone(review);invalid.inspectionStatus='invalid_evidence';
  invalid.assertions[0].evidence[0].anchorQuotes=['bad quote'];invalid.assertions[0].evidence[0].invalidAnchorQuotes=['bad quote'];
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(invalid);
  let finish!:()=>void;const p=props();p.onDerivedRun.mockImplementation(()=>new Promise<()=>void>(r=>{finish=()=>r(()=>undefined);}));
  const view=render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  fireEvent.click(screen.getByRole('button',{name:'Create reviewed child candidate'}));
  await waitFor(()=>expect(p.onDerivedRun).toHaveBeenCalledOnce());
  const guard=p.onDerivedRun.mock.calls[0][2] as ()=>boolean;
  expect(guard()).toBe(true);selection.worldId='other';view.rerender(<BuildRunReview {...p}/>);
  expect(guard()).toBe(false);
  await act(async()=>finish());expect(localStorage.length).toBe(1);
});

it('reviews a Recap against native World and frozen source session without Worldbuilding publication',async()=>{
  const p=props();p.run={...run,source_domain:'recap',campaign_id:'longmont-c2',session_id:'session-30',lineage:{world_campaign_ingest_context:{managed_world_id:'world-a',native_world_id:'native-a'}}};
  const recap={...review,sourceDomain:'recap',campaignId:'longmont-c2',sessionId:'session-30',worldId:'native-a'};
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(recap);
  render(<BuildRunReview {...p}/>);
  expect(await screen.findByRole('button',{name:'Prepare changes for review'})).toBeEnabled();
  expect(publication.prepareWorldbuilding).not.toHaveBeenCalled();expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();
  expect(screen.queryByLabelText('Canonical source prose')).not.toBeInTheDocument();
});

it('repairs Recap quotes through the Recap owner and retains the semantic hold for explicit review',async()=>{
  const p=props();p.run={...run,source_domain:'recap',profile_id:'recap_category_v1@1.0',campaign_id:'longmont-c2',session_id:'session-30',
    components:{...run.components,source_artifact:{kind:'source_artifact',uri:'source.md',exists:true,sha256:hash},
      source_span_index:{kind:'source_span_index',uri:'spans.json',exists:true,sha256:'e'.repeat(64)}},
    lineage:{world_campaign_ingest_context:{managed_world_id:'world-a',native_world_id:'native-a',campaign_id:'longmont-c2'}}};
  const invalid={...structuredClone(review),sourceDomain:'recap',campaignId:'longmont-c2',sessionId:'session-30',worldId:'native-a',inspectionStatus:'invalid_evidence' as const};
  invalid.assertions[0].evidence[0].anchorQuotes=['bad quote'];invalid.assertions[0].evidence[0].invalidAnchorQuotes=['bad quote'];
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(invalid);
  const corrected=vi.spyOn(extract,'correctRecapRunEvidence').mockImplementation(async request=>{
    const {exactRunCorrectionDigest}=await import('../api/exactRunCorrectionIdentity');
    expect(localStorage.getItem('dmb.buildRecapEvidenceCorrection.v1:'+JSON.stringify(['world-a','doc-a','run-a',candidate]))).not.toBeNull();
    return {schema:'dmb_recap_evidence_correction_response_v1',runId:'run-b',parentRunId:'run-a',parentCandidateSha256:candidate,
      candidateSha256:'c'.repeat(64),correctionDigest:await exactRunCorrectionDigest(request),status:'reviewable',semanticState:'held',semanticBasisSha256:'f'.repeat(64)};
  });
  render(<BuildRunReview {...p}/>);fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  fireEvent.click(screen.getByRole('button',{name:'Create reviewed child candidate'}));
  await waitFor(()=>expect(p.onDerivedRun).toHaveBeenCalledOnce());
  expect(corrected).toHaveBeenCalledOnce();expect(extract.correctExactRunEvidence).not.toHaveBeenCalled();
  expect(p.onDerivedRun.mock.calls[0][0]).toMatchObject({semanticState:'held'});await waitFor(()=>expect(localStorage.length).toBe(0));
  expect(publication.prepareWorldbuilding).not.toHaveBeenCalled();expect(publication.confirmWorldbuilding).not.toHaveBeenCalled();
});


it.each(['world change','unmount'])('preserves queued Recap abandonment recovery after %s',async transition=>{
  const p=props();p.run={...run,source_domain:'recap',campaign_id:'longmont-c2',session_id:'session-30',
    lineage:{world_campaign_ingest_context:{managed_world_id:'world-a',native_world_id:'native-a'}}};
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue({...review,sourceDomain:'recap',
    campaignId:'longmont-c2',sessionId:'session-30',worldId:'native-a'});
  const key='dmb.buildRecapEvidenceCorrection.v1:'+JSON.stringify(['world-a','doc-a','run-a',candidate]);
  localStorage.setItem(key,'malformed original request');
  const view=render(<BuildRunReview {...p}/>);
  const button=await screen.findByRole('button',{name:'Abandon saved request'});
  let release!:()=>void;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>
    new Promise((resolve,reject)=>{release=()=>{try{resolve(action());}catch(reason){reject(reason);}};})}});
  fireEvent.click(button);
  if(transition==='unmount')view.unmount();
  else {selection.worldId='other';view.rerender(<BuildRunReview {...p}/>);}
  await act(async()=>release());
  expect(localStorage.getItem(key)).toBe('malformed original request');
  expect(localStorage.length).toBe(1);
  expect(extract.correctExactRunEvidence).not.toHaveBeenCalled();expect(p.onDerivedRun).not.toHaveBeenCalled();
});

it('retains the correction request when staged child persistence fails',async()=>{
  const invalid=structuredClone(review);invalid.inspectionStatus='invalid_evidence';
  invalid.assertions[0].evidence[0].anchorQuotes=['bad quote'];invalid.assertions[0].evidence[0].invalidAnchorQuotes=['bad quote'];
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(invalid);
  const p=props();p.onDerivedRun.mockResolvedValue(()=>{throw new Error('run mapping storage failed');});
  render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  fireEvent.click(screen.getByRole('button',{name:'Create reviewed child candidate'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('run mapping storage failed');
  expect(localStorage.getItem('dmb.buildEvidenceCorrection.v1:'+JSON.stringify(['world-a','doc-a','run-a',candidate]))).not.toBeNull();
  expect(screen.getByRole('button',{name:'Retry saved quote corrections'})).toBeEnabled();
});
