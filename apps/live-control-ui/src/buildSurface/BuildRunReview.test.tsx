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
  source_domain:'worldbuilding',status:'reviewable',revision:7,components:{candidate_graph:{kind:'candidate_graph',uri:'candidate.json',exists:true,sha256:candidate},source_span_index:{kind:'source_span_index',uri:'spans.json',exists:true,sha256:'e'.repeat(64)}}} as ExtractionRunRecord;
const handoff={href:'/build?documentId=doc-a&revision=2&sourceArtifactId=source-a&extractionRunId=run-a',
  extraction_run_id:'run-a',source_artifact_id:'source-a',document_id:'doc-a',document_revision:2};
const review:ExactRunReviewPackage={schema:'dmb_extract_promote_exact_run_review_v1',runId:'run-a',sourceDomain:'worldbuilding',
  sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+hash,worldId:'world-a',sourceProse:'Full source prose must not become a second surface',
  inspectionStatus:'ready',diagnostics:[],assertions:[{assertionId:'keeper',kind:'object',label:'Keeper',summary:'A keeper',
    evidence:[{sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'The keeper watches the gate.',anchorQuotes:['keeper']}]}]};
const catalog={schema:'dmb_worldbuilding_frozen_span_catalog_v1' as const,parentRunId:'run-a',parentRevision:7,parentStatus:'reviewable' as const,
  worldId:'world-a',sourceArtifactId:'source-a',sourceSha256:hash,spanIndexSha256:'e'.repeat(64),parentCandidateSha256:candidate,
  spans:[{sourceSpanRefId:'span-a',startLine:1,endLine:1,paragraphText:'The keeper watches the gate.'}],
  evidenceRefs:[{assertionId:'keeper',evidenceIndex:0,refSha256:'f'.repeat(64)}]};
function submitCorrection(){
  const preview=screen.queryByRole('button',{name:'Preview evidence corrections'});
  if(preview)fireEvent.click(preview);
  fireEvent.click(screen.getByRole('button',{name:'Create reviewed child candidate'}));
}
function props(){return {document,currentRevision:3,run,handoff,sourceContentSha256:hash,onClose:vi.fn(),onDerivedRun:vi.fn().mockResolvedValue(()=>undefined),onBusyChange:vi.fn(),onSemanticDecision:vi.fn().mockResolvedValue(()=>undefined)};}
beforeEach(()=>{
  selection.worldId='world-a';localStorage.clear();
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>Promise.resolve(action())}});
  vi.spyOn(extract,'getExactRunReviewPackage').mockResolvedValue(structuredClone(review));
  vi.spyOn(extract,'getWorldbuildingFrozenSpans').mockResolvedValue(structuredClone(catalog));
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
  submitCorrection();
  expect(await screen.findByRole('alert')).toHaveTextContent('lost response');
  expect(p.onDerivedRun).not.toHaveBeenCalled();
  const request=vi.mocked(extract.correctExactRunEvidence).mock.calls[0][0];
  expect(localStorage.length).toBe(1);
  fireEvent.click(screen.getByRole('button',{name:/Retry saved (?:quote|evidence) corrections/}));
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
  submitCorrection();
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
  submitCorrection();
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
  submitCorrection();
  expect(await screen.findByRole('alert')).toHaveTextContent('run mapping storage failed');
  expect(localStorage.getItem('dmb.buildEvidenceCorrection.v2:'+JSON.stringify(['world-a','doc-a','run-a',candidate]))).not.toBeNull();
  expect(screen.getByRole('button',{name:/Retry saved (?:quote|evidence) corrections/})).toBeEnabled();
});

function correctionCase(domain:'worldbuilding'|'recap') {
  const p=props();
  const invalid=structuredClone(review);invalid.inspectionStatus='invalid_evidence';
  invalid.assertions[0].evidence[0].anchorQuotes=['bad quote'];
  invalid.assertions[0].evidence[0].invalidAnchorQuotes=['bad quote'];
  if(domain==='recap') {
    p.run={...run,source_domain:'recap',profile_id:'recap_category_v1@1.0',campaign_id:'longmont-c2',session_id:'session-30',
      components:{...run.components,source_artifact:{kind:'source_artifact',uri:'source.md',exists:true,sha256:hash},
        source_span_index:{kind:'source_span_index',uri:'spans.json',exists:true,sha256:'e'.repeat(64)}},
      lineage:{world_campaign_ingest_context:{managed_world_id:'world-a',native_world_id:'native-a',campaign_id:'longmont-c2'}}};
    Object.assign(invalid,{sourceDomain:'recap',campaignId:'longmont-c2',sessionId:'session-30',worldId:'native-a'});
  }
  vi.mocked(extract.getExactRunReviewPackage).mockResolvedValue(invalid);
  const api=domain==='recap'?vi.spyOn(extract,'correctRecapRunEvidence'):vi.mocked(extract.correctExactRunEvidence);
  const key=(domain==='recap'?'dmb.buildRecapEvidenceCorrection.v1:':'dmb.buildEvidenceCorrection.v2:')
    +JSON.stringify(['world-a','doc-a','run-a',candidate]);
  return {p,key,api};
}

it.each(['worldbuilding','recap'] as const)('refuses a competing %s request persisted by another review before dispatch',async domain=>{
  const {p,key,api}=correctionCase(domain);
  render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  const original=JSON.stringify({parentRunId:'run-a',parentCandidateSha256:candidate,corrections:[{
    assertionId:'keeper',evidenceIndex:0,quoteIndex:0,sourceSpanRefId:'span-a',originalQuote:'bad quote',replacementQuote:'gate'}]});
  localStorage.setItem(key,original);
  submitCorrection();
  expect(await screen.findByRole('alert')).toHaveTextContent('Another correction is retained');
  expect(localStorage.getItem(key)).toBe(original);expect(api).not.toHaveBeenCalled();
});

it.each(['worldbuilding','recap'] as const)('serializes two %s review views before either can overwrite the request',async domain=>{
  const {p,key,api}=correctionCase(domain);
  const queue:Array<()=>void>=[];
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>
    new Promise((resolve,reject)=>queue.push(()=>{try{resolve(action());}catch(reason){reject(reason);}}))}});
  api.mockImplementation(()=>new Promise(()=>{}));
  render(<><BuildRunReview {...p}/><BuildRunReview {...p}/></>);
  const inputs=await screen.findAllByLabelText('Literal replacement for Keeper quote 1');
  fireEvent.change(inputs[0],{target:{value:'keeper'}});fireEvent.change(inputs[1],{target:{value:'gate'}});
  screen.queryAllByRole('button',{name:'Preview evidence corrections'}).forEach(b=>fireEvent.click(b));
  const buttons=screen.getAllByRole('button',{name:'Create reviewed child candidate'});
  fireEvent.click(buttons[0]);fireEvent.click(buttons[1]);expect(queue).toHaveLength(2);
  expect(api).not.toHaveBeenCalled();
  await act(async()=>queue.shift()!());await waitFor(()=>expect(api).toHaveBeenCalledOnce());
  const original=localStorage.getItem(key);expect(original).toContain('keeper');
  await act(async()=>queue.shift()!());
  expect(await screen.findByRole('alert')).toHaveTextContent('Another correction is retained');
  expect(api).toHaveBeenCalledOnce();expect(localStorage.getItem(key)).toBe(original);
});

it.each(['worldbuilding','recap'] as const)('blocks %s correction dispatch without cross-tab locking',async domain=>{
  const {p,api}=correctionCase(domain);
  Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});
  render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  submitCorrection();
  expect(await screen.findByRole('alert')).toHaveTextContent('cannot safely retain evidence corrections across tabs');
  expect(api).not.toHaveBeenCalled();expect(localStorage.length).toBe(0);
});

it.each(['world change','unmount'])('preserves Worldbuilding recovery after queued abandonment and %s',async transition=>{
  const {p,key,api}=correctionCase('worldbuilding');
  localStorage.setItem(key,'original malformed request');
  const view=render(<BuildRunReview {...p}/>);
  const button=await screen.findByRole('button',{name:'Abandon saved request'});
  let release!:()=>void;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>
    new Promise((resolve,reject)=>{release=()=>{try{resolve(action());}catch(reason){reject(reason);}};})}});
  fireEvent.click(button);
  if(transition==='unmount')view.unmount();else{selection.worldId='other';view.rerender(<BuildRunReview {...p}/>);}
  await act(async()=>release());
  expect(localStorage.getItem(key)).toBe('original malformed request');expect(localStorage.length).toBe(1);
  expect(api).not.toHaveBeenCalled();
});

it('retains abandoned Worldbuilding request bytes before clearing the active key',async()=>{
  const {p,key,api}=correctionCase('worldbuilding');
  localStorage.setItem(key,'original malformed request');render(<BuildRunReview {...p}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Abandon saved request'}));
  await waitFor(()=>expect(localStorage.getItem(key)).toBeNull());
  const retained=Object.keys(localStorage).filter(name=>name.startsWith(key+':retained:'));
  expect(retained).toHaveLength(1);expect(localStorage.getItem(retained[0])).toBe('original malformed request');
  expect(api).not.toHaveBeenCalled();
});

it('recovers the exact Worldbuilding correction after remount without automatic dispatch',async()=>{
  const {p,key,api}=correctionCase('worldbuilding');api.mockRejectedValueOnce(new Error('lost response'));
  const view=render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  submitCorrection();
  expect(await screen.findByRole('alert')).toHaveTextContent('lost response');
  const request=api.mock.calls[0][0],retained=localStorage.getItem(key);
  expect(retained).not.toBeNull();view.unmount();render(<BuildRunReview {...p}/>);
  const retry=await screen.findByRole('button',{name:/Retry saved (?:quote|evidence) corrections/});
  expect(api).toHaveBeenCalledOnce();expect(localStorage.getItem(key)).toBe(retained);
  fireEvent.click(retry);await waitFor(()=>expect(p.onDerivedRun).toHaveBeenCalledOnce());
  expect(api).toHaveBeenNthCalledWith(2,request);await waitFor(()=>expect(localStorage.getItem(key)).toBeNull());
});

it.each(['world change','unmount'])('does not persist or dispatch queued Worldbuilding correction after %s',async transition=>{
  const {p,key,api}=correctionCase('worldbuilding');let release!:()=>void;
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>
    new Promise((resolve,reject)=>{release=()=>{try{resolve(action());}catch(reason){reject(reason);}};})}});
  const view=render(<BuildRunReview {...p}/>);
  fireEvent.change(await screen.findByLabelText('Literal replacement for Keeper quote 1'),{target:{value:'keeper'}});
  submitCorrection();
  if(transition==='unmount')view.unmount();else{selection.worldId='other';view.rerender(<BuildRunReview {...p}/>);}
  await act(async()=>release());expect(localStorage.getItem(key)).toBeNull();expect(api).not.toHaveBeenCalled();
});

it('keeps Worldbuilding recovery when abandonment retention fails',async()=>{
  const {p,key,api}=correctionCase('worldbuilding');localStorage.setItem(key,'original malformed request');
  render(<BuildRunReview {...p}/>);const button=await screen.findByRole('button',{name:'Abandon saved request'});
  const setItem=Storage.prototype.setItem;
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(name,value){
    if(name.startsWith(key+':retained:'))throw new Error('storage quota');
    return setItem.call(this,name,value);
  });
  fireEvent.click(button);
  await waitFor(()=>expect(screen.getAllByRole('alert').some(el=>el.textContent?.includes('could not be retained'))).toBe(true));
  expect(localStorage.getItem(key)).toBe('original malformed request');expect(api).not.toHaveBeenCalled();
});
