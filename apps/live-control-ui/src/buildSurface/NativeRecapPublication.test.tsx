import {webcrypto} from 'node:crypto';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import * as api from '../api/nativeRecapPublicationApi';
import * as sourceApi from '../api/nativeRecapSourceApi';
import {LiveApiError} from '../api/liveApi';
import type {ExactRunReviewPackage,ExtractionRunRecord} from '../api/types';
import type {ExactRunCandidateProjection} from '../api/exactRunCandidateProjectionApi';
import type {SavedRecapSource} from '../api/savedRecapRunsApi';
import {NativeRecapPublication} from './NativeRecapPublication';
import {readNativeRecovery,recoveryKey} from './nativeRecapPublicationRecovery';
let snapshot:api.Snapshot,context:api.Context,projection:ExactRunCandidateProjection,packet:api.Confirmation;
let admitted:boolean,supported:boolean;
const review={runId:'run',worldId:'native',sourceDomain:'recap',sourceArtifactId:'app-source',inspectionStatus:'ready'} as ExactRunReviewPackage;
const run={run_id:'run',revision:2,source_artifact_id:'app-source',source_domain:'recap',campaign_id:'campaign',session_id:'session-8',components:{candidate_graph:{sha256:'a'.repeat(64)}}} as ExtractionRunRecord;
const onBusy=vi.fn();
function mount(){return render(<NativeRecapPublication review={{...review,sourceRevisionId:'sha256:'+snapshot.sourceSha256}} run={run} worldId="world" onBusy={onBusy}/>);}
function status():sourceApi.NativeRecapSourceStatus{return {schema_version:'dmb_native_recap_source_status_v2',state:'admitted',run_id:'00000000-0000-4000-8000-000000000002',run_revision:3,managed_world_id:'world',native_world_id:'native',binding_version:1,campaign_id:'campaign',session_id:'session-8',app_source_artifact_id:'app-source',app_source_revision_id:snapshot.sourceRevisionId,app_body_sha256:snapshot.sourceSha256,admission_id:'actual-source-admission',admission_committed:true,command_sha256:'d'.repeat(64),published_revision_id:'rev:admitted',evidence_ref_id:'context-evidence',failure_code:null,opening:{state:'verified'}};}
beforeEach(async()=>{
 vi.stubGlobal('crypto',webcrypto);localStorage.clear();Object.defineProperty(navigator,'locks',{value:{request:(_k:string,fn:()=>unknown)=>Promise.resolve(fn())},configurable:true});admitted=false;supported=false;onBusy.mockClear();
 snapshot={worldId:'world',nativeWorldId:'native',bindingVersion:1,runId:'run',runRevision:2,campaignId:'campaign',sessionId:'session-8',artifactId:'app-source',sourceRevisionId:'00000000-0000-4000-8000-000000000001',sourceSha256:await api.sha256('Ari arrived.'),candidateSha256:'a'.repeat(64),spanIndexSha256:'b'.repeat(64),sourceMarkdown:'Ari arrived.'};
 context={schema:'dmb_native_recap_review_context_v1',publication:'not_performed',binding:{managed_world_id:'world',native_world_id:'native',binding_version:1},campaign_id:'campaign',session_id:'session-8',source_artifact_id:snapshot.artifactId,source_revision_id:snapshot.sourceRevisionId,source_sha256:snapshot.sourceSha256,native_source:{admission_id:'actual-source-admission',source_artifact_id:'native-source',source_revision_id:'native-revision',body_sha256:snapshot.sourceSha256},source_support:[],records:[{kind:'node',record_id:'ari',candidate:{label:'Ari',aliases:['Arin']},fields:{label:'Ari',session_actions:['arrived']},selectable_facts:[{field:'label',value:'Ari'},{field:'session_actions',index:0,value:'arrived'}]},{kind:'beat',record_id:'arrival',candidate:{title:'Arrival',order:1},selectable_facts:[{field:'title',value:'Arrival'}]},{kind:'edge',record_id:'edge',candidate:{},from_record_id:'ari',to_record_id:'ari',relationship_type:'knows'},{kind:'placement',record_id:'ari',candidate:{}}],held_records:[{kind:'deferred',candidate:{label:'Uncertain'}}],candidate_inventory:{},source_order:{beat_order_is_narrative_only:true},prepare_coordinates:{managed_world_id:'world',campaign_id:'campaign',run_id:'run',expected_run_revision:2,candidate_sha256:snapshot.candidateSha256,source_admission_run_id:'00000000-0000-4000-8000-000000000002',expected_parent_revision_id:'rev:admitted',expected_source_authority_epoch:4}};
 projection={sourceSpans:[{span_id:'span',kind:'paragraph',ordinal:0,text_excerpt:'Ari arrived.',line_start:1,line_end:1}]} as ExactRunCandidateProjection;
 vi.spyOn(api,'loadRecapSnapshot').mockResolvedValue({snapshot,projection,source:{} as SavedRecapSource});
 vi.spyOn(api,'readContext').mockImplementation(async()=>{if(!admitted)throw new LiveApiError('admit exact source',409,{code:'candidate_source_not_admitted'});return {...context,source_support:supported?[{evidence_ref_id:'support',start_byte:0,end_byte:3,text:'Ari'}]:[]};});
 vi.spyOn(sourceApi,'admitRecapSource').mockImplementation(async target=>{expect(target.sourceRevisionId).toBe(snapshot.sourceRevisionId);expect(readNativeRecovery('world','run')?.value.operation.stage).toBe('admission');admitted=true;return status();});
 vi.spyOn(sourceApi,'inspectRecapSource').mockResolvedValue(status());vi.spyOn(sourceApi,'resumeRecapSource').mockResolvedValue(status());
 vi.spyOn(api,'extendEvidence').mockImplementation(async(s,request)=>{expect(s).toEqual(snapshot);expect(readNativeRecovery('world','run')?.value.operation).toEqual({stage:'extension',request});supported=true;return {status:'committed'};});
 vi.spyOn(api,'prepareRecap').mockImplementation(async(s,c,selections)=>{packet={envelope:{purpose:'dmb_native_recap_confirm_v1',producer:'dungeonbuddy:reviewed-recap',prepared_change_id:'prepared-change',prepared_digest:'d'.repeat(64),expires_at:'2026-12-01T00:00:00Z',binding:{managed_world_id:'world',native_world_id:'native',binding_version:1},parent_context:{revision_id:c.prepare_coordinates.expected_parent_revision_id,source_epoch:c.prepare_coordinates.expected_source_authority_epoch},review:{...c.prepare_coordinates,selections:JSON.parse(JSON.stringify(selections))}},prepared:{opaque:'unchanged'},token:'signed'};return {status:'prepared',packet,records:[]};});
 vi.spyOn(api,'confirmRecap').mockImplementation(async(s,p)=>{expect(s).toEqual(snapshot);expect(readNativeRecovery('world','run')?.value.operation).toEqual({stage:'confirmation',packet:p});return {status:'committed',recovered:false};});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});
async function admitAndExtend(expectExtensionFailure=false){fireEvent.click(await screen.findByRole('button',{name:'Admit or recover exact Recap source'}));await screen.findByRole('button',{name:'Extend exact support evidence'});fireEvent.change(screen.getByLabelText('Frozen witness paragraph'),{target:{value:'0'}});fireEvent.change(screen.getByLabelText('Exact witness text'),{target:{value:'Ari'}});fireEvent.click(screen.getByRole('button',{name:'Extend exact support evidence'}));await waitFor(()=>expect(api.extendEvidence).toHaveBeenCalledOnce());if(!expectExtensionFailure)await screen.findByLabelText('Action for node:ari');}
async function choose(existing=false,indexed=false){fireEvent.change(screen.getByLabelText('Action for node:ari'),{target:{value:existing?'use_existing':'create'}});if(existing)fireEvent.change(screen.getByLabelText('Entity ID for node:ari'),{target:{value:'ent:ari'}});fireEvent.click(screen.getByLabelText(indexed?'Fact node:ari session_actions:0':'Fact node:ari label'));fireEvent.change(screen.getByLabelText('Support for node:ari'),{target:{value:'support'}});fireEvent.change(screen.getByLabelText('Epistemic basis for node:ari'),{target:{value:'inferred'}});fireEvent.change(screen.getByLabelText('Claim mode for node:ari'),{target:{value:'dungeonbuddy.claim:belief'}});fireEvent.change(screen.getByLabelText('Standing for node:ari'),{target:{value:'provisional'}});fireEvent.change(screen.getByLabelText('Temporal scope for node:ari'),{target:{value:'unknown'}});fireEvent.click(screen.getByRole('button',{name:'Prepare selected Recap facts'}));await screen.findByRole('button',{name:'Confirm native Recap publication'});}
it('completes an ordinary unadmitted one-line source with explicit proper witness and facts, never writes on load',async()=>{mount();await screen.findByRole('button',{name:'Admit or recover exact Recap source'});expect(sourceApi.admitRecapSource).not.toHaveBeenCalled();expect(api.extendEvidence).not.toHaveBeenCalled();expect(api.prepareRecap).not.toHaveBeenCalled();await admitAndExtend();await choose();expect(api.confirmRecap).not.toHaveBeenCalled();const selections=vi.mocked(api.prepareRecap).mock.calls[0][2];expect(selections[0]).toMatchObject({kind:'node',record_id:'ari',action:'create',facts:[{field:'label',metadata:{epistemic_basis:'inferred',claim_mode:'dungeonbuddy.claim:belief',temporal_scope:{kind:'unknown'}}}]});expect(selections.slice(1).every(s=>s.action==='defer')).toBe(true);fireEvent.click(screen.getByRole('button',{name:'Confirm native Recap publication'}));await screen.findByText('Native Recap publication confirmed.');expect(api.confirmRecap).toHaveBeenCalledExactlyOnceWith(snapshot,packet);});
it('recovers admission loss before a run ID using the exact retained target without fresh reads',async()=>{vi.mocked(sourceApi.admitRecapSource).mockRejectedValueOnce(new Error('response lost before ID'));const ui=mount();fireEvent.click(await screen.findByRole('button',{name:'Admit or recover exact Recap source'}));await screen.findByText('response lost before ID');const raw=localStorage.getItem(recoveryKey('world','run'));ui.unmount();vi.mocked(api.loadRecapSnapshot).mockClear().mockRejectedValue(new Error('today unavailable'));vi.mocked(api.readContext).mockClear();mount();expect(api.loadRecapSnapshot).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Retry exact saved admission'}));await waitFor(()=>expect(sourceApi.admitRecapSource).toHaveBeenCalledTimes(2));expect(vi.mocked(sourceApi.admitRecapSource).mock.calls[1]).toEqual(vi.mocked(sourceApi.admitRecapSource).mock.calls[0]);expect(raw).toContain(snapshot.sourceRevisionId);});
it.each(['extension','confirmation'] as const)('recovers unknown %s before unavailable context or changed candidate',async stage=>{const ui=mount();if(stage==='extension')vi.mocked(api.extendEvidence).mockRejectedValueOnce(new Error('extension response lost'));await admitAndExtend(stage==='extension');if(stage==='confirmation'){await choose();vi.mocked(api.confirmRecap).mockRejectedValueOnce(new Error('confirmation response lost'));fireEvent.click(screen.getByRole('button',{name:'Confirm native Recap publication'}));}await screen.findByText(stage+' response lost');const raw=localStorage.getItem(recoveryKey('world','run'))!;ui.unmount();vi.mocked(api.loadRecapSnapshot).mockClear().mockRejectedValue(new Error('new candidate unavailable'));vi.mocked(api.readContext).mockClear().mockRejectedValue(new Error('head advanced'));mount();expect(api.loadRecapSnapshot).not.toHaveBeenCalled();expect(api.readContext).not.toHaveBeenCalled();if(stage==='extension')vi.mocked(api.extendEvidence).mockRejectedValueOnce(new Error('still unknown'));fireEvent.click(screen.getByRole('button',{name:'Retry exact saved '+stage}));await waitFor(()=>expect(stage==='extension'?api.extendEvidence:api.confirmRecap).toHaveBeenCalledTimes(2));const calls=stage==='extension'?vi.mocked(api.extendEvidence).mock.calls:vi.mocked(api.confirmRecap).mock.calls;expect(calls[1]).toEqual(calls[0]);if(stage==='extension')expect(localStorage.getItem(recoveryKey('world','run'))).toBe(raw);});
it('does not dispatch an admission if storage fails and does not remove submitted bytes on an arbitrary error',async()=>{mount();await screen.findByRole('button',{name:'Admit or recover exact Recap source'});vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});fireEvent.click(screen.getByRole('button',{name:'Admit or recover exact Recap source'}));await screen.findByText('storage full');expect(sourceApi.admitRecapSource).not.toHaveBeenCalled();});
it('does not publish beat order, aliases, placement, or indexed actions unless explicitly selected',async()=>{admitted=true;supported=true;mount();await screen.findByLabelText('Action for node:ari');expect(screen.getByText(/Held aliases/)).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Prepare selected Recap facts'}));await screen.findByText(/All records are held/);expect(api.prepareRecap).not.toHaveBeenCalled();});


it('uses explicit existing identities and indexed action fields without predicting entity allocation',async()=>{
  admitted=true;supported=true;mount();await screen.findByLabelText('Action for node:ari');
  await choose(true,true);
  expect(vi.mocked(api.prepareRecap).mock.calls[0][2][0]).toMatchObject({kind:'node',record_id:'ari',action:'use_existing',entity_id:'ent:ari',facts:[{field:'session_actions',index:0}]});
  expect(vi.mocked(api.prepareRecap).mock.calls[0][2].slice(1).every(r=>r.action==='defer')).toBe(true);
});
it('keeps beat identity reuse explicit instead of deriving it from narrative order',async()=>{
  admitted=true;supported=true;mount();await screen.findByLabelText('Action for beat:arrival');
  fireEvent.change(screen.getByLabelText('Action for beat:arrival'),{target:{value:'use_existing'}});
  fireEvent.change(screen.getByLabelText('Entity ID for beat:arrival'),{target:{value:'ent:existing-beat'}});
  fireEvent.click(screen.getByRole('button',{name:'Prepare selected Recap facts'}));
  await screen.findByRole('button',{name:'Confirm native Recap publication'});
  expect(vi.mocked(api.prepareRecap).mock.calls[0][2].find(r=>r.kind==='beat')).toEqual({kind:'beat',record_id:'arrival',action:'use_existing',entity_id:'ent:existing-beat',facts:[]});
  expect(vi.mocked(api.prepareRecap).mock.calls[0][2].find(r=>r.kind==='placement')?.action).toBe('defer');
});


it('resumes an actual saved admission with no command yet without inventing a command or auto-resuming',async()=>{
  const saved={...status(),state:'conflict' as const,admission_committed:false,command_sha256:null,opening:{state:'not_checked' as const}};
  vi.mocked(sourceApi.admitRecapSource).mockResolvedValueOnce(saved);
  vi.mocked(sourceApi.resumeRecapSource).mockImplementation(async(target,previous)=>{
    expect(readNativeRecovery('world','run')?.value.operation).toEqual({stage:'admission',mode:'resume',target,previous:saved});
    admitted=true;return status();
  });
  mount();fireEvent.click(await screen.findByRole('button',{name:'Admit or recover exact Recap source'}));
  const button=await screen.findByRole('button',{name:'Resume exact source admission'});
  expect(sourceApi.resumeRecapSource).not.toHaveBeenCalled();fireEvent.click(button);
  await screen.findByRole('button',{name:'Extend exact support evidence'});
  expect(sourceApi.resumeRecapSource).toHaveBeenCalledExactlyOnceWith(api.targetFor(snapshot),saved);
});

async function rejectStage(stage:'confirmation'|'extension',error:Error){
  admitted=true;supported=stage==='confirmation';
  const ui=mount();
  if(stage==='confirmation'){
    await screen.findByLabelText('Action for node:ari');await choose();
    vi.mocked(api.confirmRecap).mockRejectedValueOnce(error);
    fireEvent.click(screen.getByRole('button',{name:'Confirm native Recap publication'}));
  }else{
    vi.mocked(api.extendEvidence).mockRejectedValueOnce(error);
    await screen.findByRole('button',{name:'Extend exact support evidence'});
    fireEvent.change(screen.getByLabelText('Frozen witness paragraph'),{target:{value:'0'}});
    fireEvent.change(screen.getByLabelText('Exact witness text'),{target:{value:'Ari'}});
    fireEvent.click(screen.getByRole('button',{name:'Extend exact support evidence'}));
  }
  await screen.findByRole('alert');
  return {ui,raw:localStorage.getItem(recoveryKey('world','run'))!};
}
it.each(['candidate_parent_stale','candidate_source_authority_stale','candidate_review_expired','native_recap_commit_stale'])(
  'explicitly archives verified precommit confirmation %s before fresh review, never automatically prepares',async code=>{
    const {raw}=await rejectStage('confirmation',new LiveApiError('Verified precommit refusal',409,{code}));
    const beforeReads=vi.mocked(api.readContext).mock.calls.length;
    expect(localStorage.getItem(recoveryKey('world','run'))).toBe(raw);
    expect(api.confirmRecap).toHaveBeenCalledOnce();expect(api.prepareRecap).toHaveBeenCalledOnce();
    context.prepare_coordinates={...context.prepare_coordinates,expected_parent_revision_id:'rev:fresh',expected_source_authority_epoch:9};
    fireEvent.click(screen.getByRole('button',{name:'Archive rejected confirmation and review again'}));
    await waitFor(()=>expect(api.readContext).toHaveBeenCalledTimes(beforeReads+1));
    await screen.findByRole('button',{name:'Prepare selected Recap facts'});
    expect(localStorage.getItem(recoveryKey('world','run'))).toBeNull();
    expect(Object.keys(localStorage).filter(k=>k.includes(':retained:confirmation:')).map(k=>localStorage.getItem(k))).toContain(raw);
    expect(api.prepareRecap).toHaveBeenCalledOnce();expect(api.confirmRecap).toHaveBeenCalledOnce();
    await choose();expect(api.prepareRecap).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.prepareRecap).mock.calls[1][1].prepare_coordinates.expected_parent_revision_id).toBe('rev:fresh');
  });
it('explicitly archives typed extension parent-CAS rejection; only a new user action creates a fresh request',async()=>{
  const {raw}=await rejectStage('extension',new LiveApiError('Verified extension precommit refusal',409,{code:'knowledge_stale_parent_revision'}));
  const oldRequest=vi.mocked(api.extendEvidence).mock.calls[0][1];
  context.prepare_coordinates={...context.prepare_coordinates,expected_parent_revision_id:'rev:extension-fresh',expected_source_authority_epoch:9};
  fireEvent.click(screen.getByRole('button',{name:'Archive rejected extension and review again'}));
  await screen.findByRole('button',{name:'Extend exact support evidence'});
  expect(localStorage.getItem(recoveryKey('world','run'))).toBeNull();
  expect(Object.keys(localStorage).filter(k=>k.includes(':retained:extension:')).map(k=>localStorage.getItem(k))).toContain(raw);
  expect(api.extendEvidence).toHaveBeenCalledOnce();expect(api.prepareRecap).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Frozen witness paragraph'),{target:{value:'0'}});
  fireEvent.change(screen.getByLabelText('Exact witness text'),{target:{value:'Ari'}});
  fireEvent.click(screen.getByRole('button',{name:'Extend exact support evidence'}));
  await waitFor(()=>expect(api.extendEvidence).toHaveBeenCalledTimes(2));
  const next=vi.mocked(api.extendEvidence).mock.calls[1][1];
  expect(next.expected_parent_revision_id).toBe('rev:extension-fresh');expect(next.expected_source_authority_epoch).toBe(9);
  expect(next.extension_id).not.toBe(oldRequest.extension_id);
  expect(JSON.parse(raw).operation.request).toEqual(oldRequest);
});
it.each([
  ['confirmation',409,'arbitrary_conflict'],['confirmation',401,'candidate_parent_stale'],
  ['confirmation',403,'candidate_review_expired'],['confirmation',503,'candidate_source_authority_stale'],
  ['confirmation',409,'knowledge_stale_parent_revision'],['confirmation',503,'native_recap_commit_outcome_unknown'],
  ['extension',409,'candidate_parent_stale'],['extension',401,'knowledge_stale_parent_revision'],
  ['extension',403,'knowledge_stale_parent_revision'],['extension',503,'knowledge_stale_parent_revision'],
  ['extension',409,'native_text_source_admission_integrity_error'],['extension',409,'arbitrary_conflict'],
] as const)('retains exact %s on status %s/code %s; no generic message parsing or automatic refresh',async(stage,statusCode,code)=>{
  const {ui,raw}=await rejectStage(stage,new LiveApiError('extension_source_epoch_stale candidate_parent_stale',statusCode,{code}));
  expect(screen.queryByRole('button',{name:/Archive rejected/})).toBeNull();
  expect(localStorage.getItem(recoveryKey('world','run'))).toBe(raw);
  expect(Object.keys(localStorage).some(k=>k.includes(':retained:'))).toBe(false);
  ui.unmount();vi.mocked(api.loadRecapSnapshot).mockClear().mockRejectedValue(new Error('mutable source is unavailable'));
  vi.mocked(api.readContext).mockClear().mockRejectedValue(new Error('fresh context unavailable'));
  mount();expect(api.loadRecapSnapshot).not.toHaveBeenCalled();expect(api.readContext).not.toHaveBeenCalled();
  if(stage==='extension')vi.mocked(api.extendEvidence).mockRejectedValueOnce(new Error('still unknown'));
  else vi.mocked(api.confirmRecap).mockRejectedValueOnce(new Error('still unknown'));
  fireEvent.click(screen.getByRole('button',{name:'Retry exact saved '+stage}));
  await screen.findByText('still unknown');
  const calls=stage==='extension'?vi.mocked(api.extendEvidence).mock.calls:vi.mocked(api.confirmRecap).mock.calls;
  expect(calls[1]).toEqual(calls[0]);expect(localStorage.getItem(recoveryKey('world','run'))).toBe(raw);
});
