import {act,renderHook,waitFor} from '@testing-library/react';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import * as api from '../api/buildRecapApi';
import * as live from '../api/liveApi';
import type {ExtractionRunStatusResponse,WorkspaceDocumentSnapshot} from '../api/types';
import {buildInitialWorkspaceDocumentLocalState,writeWorkspaceDocumentLocalState} from '../tiptap/state/tiptapLocalState';
import {BuildCanvasTestProvider} from './buildCanvasTestProvider';
import {useBuildExtraction} from './useBuildExtraction';
const doc='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',runId='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',hash='a'.repeat(64);
const settings={worldId:'managed-a',campaignId:'longmont-c2',session:30,evidence:[]};
const key=api.recapRecoveryKey('managed-a',doc);
function status(request:api.BuildRecapLaunchRequest):ExtractionRunStatusResponse{
  return {schema_version:'dmb_extraction_run_status_v1',run:{schema_version:'dmb_extraction_run_v1',version:'1.0',
    run_id:runId,source_artifact_id:'artifact:recap:build',source_domain:'recap',status:'reviewable',campaign_id:request.campaign_id,
    session_id:`session-${request.session}`,profile_id:'recap_category_v1@1.0',lineage:{build_launch:{schema:'dmb_build_recap_launch_v1',request},
      world_campaign_ingest_context:{managed_world_id:'managed-a',native_world_id:'native-a'}}},
    document_id:doc,document_revision:2,source_artifact_id:'artifact:recap:build',source_content_sha256:hash,
    graph_review_handoff:{href:`/build?documentId=${doc}&revision=2&extractionRunId=${runId}&sourceArtifactId=artifact:recap:build`,
      document_id:doc,document_revision:2,extraction_run_id:runId,source_artifact_id:'artifact:recap:build'}};
}
function wrapper({children}:{children:React.ReactNode}){return <BuildCanvasTestProvider documentId={doc}>{children}</BuildCanvasTestProvider>;}
function mount(){return renderHook(({worldId,recap})=>useBuildExtraction({documentId:doc,worldId,recap}),
  {initialProps:{worldId:'managed-a',recap:settings},wrapper});}
beforeEach(()=>{
  localStorage.clear();history.replaceState({},'',`/build?documentId=${doc}`);
  writeWorkspaceDocumentLocalState(localStorage,buildInitialWorkspaceDocumentLocalState({documentId:doc,title:'External recap',campaignId:'workspace-campaign',
    kind:'worldbuilding_source',targetSession:null,surface:'build',baseRevision:2,baseContentSha256:hash,starterContent:{type:'doc',content:[]}}));
  vi.spyOn(live,'getWorkspaceDocumentSnapshot').mockResolvedValue({schema_version:'dmb_workspace_document_snapshot_v1',record:{schema_version:'dmb_workspace_document_record_v1',
    document_id:doc,title:'External recap',campaign_id:'workspace-campaign',world_id:'managed-a',kind:'worldbuilding_source',status:'active',content_status:'committed',revision:2,
    target_relpath:'corpus/managed-a-markdown/recap.md',source_domain:'worldbuilding'},loaded_revision:2,content_sha256:hash,markdown:'# External recap\n',file_exists:true} as WorkspaceDocumentSnapshot);
  vi.spyOn(live,'getExtractionRunStatus').mockRejectedValue(new Error('unexpected additional status read'));
  vi.spyOn(api,'launchBuildRecap').mockImplementation(async request=>{
    expect(JSON.parse(localStorage.getItem(key)!)).toEqual(request);return status(request);
  });
  vi.spyOn(api,'recoverBuildRecap').mockImplementation(async request=>status(request));
});
afterEach(()=>vi.restoreAllMocks());
it('saves the exact admitted request before POST and adopts its frozen run',async()=>{
  const {result}=mount();await waitFor(()=>expect(result.current.canLaunch).toBe(true));
  await act(async()=>result.current.launch());
  expect(api.launchBuildRecap).toHaveBeenCalledOnce();const request=vi.mocked(api.launchBuildRecap).mock.calls[0][0];
  expect(request).toMatchObject({document_id:doc,expected_revision:2,expected_content_sha256:hash,campaign_id:'longmont-c2',session:30,managed_world_id:'managed-a'});
  expect(result.current.run?.run_id).toBe(runId);expect(result.current.pendingRecap).toBe(false);expect(localStorage.getItem(key)).toBeNull();
});
it('recovers a lost response using the original request after next-run settings change',async()=>{
  vi.mocked(api.launchBuildRecap).mockRejectedValueOnce(new Error('lost response'));
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));
  await act(async()=>view.result.current.launch());const saved=JSON.parse(localStorage.getItem(key)!);
  view.rerender({worldId:'managed-a',recap:{...settings,campaignId:'other',session:31}});
  await act(async()=>view.result.current.recoverRecap());
  expect(api.recoverBuildRecap).toHaveBeenCalledExactlyOnceWith(saved);expect(api.launchBuildRecap).toHaveBeenCalledOnce();
  expect(view.result.current.run?.campaign_id).toBe('longmont-c2');expect(view.result.current.run?.session_id).toBe('session-30');
});
it('reload retains the saved request and explicit retry sends the same identity',async()=>{
  vi.mocked(api.launchBuildRecap).mockRejectedValueOnce(new Error('lost response'));
  const first=mount();await waitFor(()=>expect(first.result.current.canLaunch).toBe(true));await act(async()=>first.result.current.launch());
  const saved=JSON.parse(localStorage.getItem(key)!);first.unmount();const next=mount();
  await waitFor(()=>expect(next.result.current.pendingRecap).toBe(true));
  await act(async()=>next.result.current.recoverRecap(true));
  expect(api.launchBuildRecap).toHaveBeenNthCalledWith(2,saved);expect(next.result.current.run?.run_id).toBe(runId);
});
it('does not dispatch if the exact recovery request cannot be saved',async()=>{
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));
  const original=Storage.prototype.setItem;vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(k,v){if(k===key)throw new Error('storage unavailable');original.call(this,k,v);});
  await act(async()=>view.result.current.launch());expect(api.launchBuildRecap).not.toHaveBeenCalled();
});
it('retains original World recovery and discards late launch adoption on a World change',async()=>{
  let resolve!:(value:ExtractionRunStatusResponse)=>void;vi.mocked(api.launchBuildRecap).mockImplementation(()=>new Promise(r=>{resolve=r;}));
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));let operation!:Promise<void>;
  await act(async()=>{operation=view.result.current.launch();});await waitFor(()=>expect(api.launchBuildRecap).toHaveBeenCalledOnce());
  const saved=JSON.parse(localStorage.getItem(key)!);view.rerender({worldId:'managed-b',recap:{...settings,worldId:'managed-b'}});
  await act(async()=>{resolve(status(saved));await operation;});expect(view.result.current.run).toBeNull();expect(localStorage.getItem(key)).not.toBeNull();
});
it.each(['world','request','digest','revision'])('refuses a foreign %s response and retains exact recovery',async field=>{
  vi.mocked(api.launchBuildRecap).mockImplementation(async request=>{
    const response=status(request);
    if(field==='world')(response.run.lineage!.world_campaign_ingest_context as any).managed_world_id='other';
    if(field==='request')(response.run.lineage!.build_launch as any).request={...request,session:31};
    if(field==='digest')response.source_content_sha256='b'.repeat(64);
    if(field==='revision')response.document_revision=3;
    return response;
  });
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));await act(async()=>view.result.current.launch());
  expect(view.result.current.handoff).toBeNull();expect(view.result.current.pendingRecap).toBe(true);expect(localStorage.getItem(key)).not.toBeNull();
});
it('keeps an unfinished request for manual status checks without automatic replay',async()=>{
  vi.mocked(api.launchBuildRecap).mockImplementation(async request=>{const response=status(request);response.run.status='draft';return response;});
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));await act(async()=>view.result.current.launch());
  expect(view.result.current.pendingRecap).toBe(true);expect(view.result.current.canLaunch).toBe(false);expect(api.launchBuildRecap).toHaveBeenCalledOnce();
});
it('retains a rejected request after missing status, then permits a corrected separate launch and original recovery',async()=>{
  vi.mocked(api.launchBuildRecap).mockRejectedValueOnce(new live.LiveApiError('stale source',409));
  vi.mocked(api.recoverBuildRecap).mockRejectedValueOnce(new live.LiveApiError('not found',404));
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));
  await act(async()=>view.result.current.launch());const saved=JSON.parse(localStorage.getItem(key)!);
  await act(async()=>view.result.current.recoverRecap());
  expect(view.result.current.canLaunch).toBe(false);expect(localStorage.getItem(key)).not.toBeNull();
  act(()=>view.result.current.setAsideRecap());
  expect(view.result.current.canLaunch).toBe(true);
  expect(JSON.parse(localStorage.getItem(api.recapHistoryKey('managed-a',doc))!)).toEqual([saved]);
  view.rerender({worldId:'managed-a',recap:{...settings,session:31}});
  await act(async()=>view.result.current.launch());
  const corrected=vi.mocked(api.launchBuildRecap).mock.calls[1][0];
  expect(corrected.request_id).not.toBe(saved.request_id);expect(corrected.session).toBe(31);
  view.unmount();const restored=mount();
  await waitFor(()=>expect(restored.result.current.savedRecapRequests).toHaveLength(1));
  act(()=>restored.result.current.restoreRecap(0));
  expect(restored.result.current.canLaunch).toBe(false);
  await act(async()=>restored.result.current.recoverRecap());
  expect(api.recoverBuildRecap).toHaveBeenLastCalledWith(saved);
  expect(restored.result.current.run?.session_id).toBe('session-30');
});
it('keeps uncertain requests pending if retaining their history fails',async()=>{
  vi.mocked(api.launchBuildRecap).mockRejectedValueOnce(new Error('lost response'));
  const view=mount();await waitFor(()=>expect(view.result.current.canLaunch).toBe(true));
  await act(async()=>view.result.current.launch());const raw=localStorage.getItem(key);
  const original=Storage.prototype.setItem;
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(k,v){
    if(k===api.recapHistoryKey('managed-a',doc))throw new Error('storage full');original.call(this,k,v);
  });
  act(()=>view.result.current.setAsideRecap());
  expect(view.result.current.pendingRecap).toBe(true);expect(view.result.current.canLaunch).toBe(false);
  expect(localStorage.getItem(key)).toBe(raw);expect(view.result.current.error).toBe('storage full');
});
it('refuses malformed saved pins without throwing and retains them until explicitly set aside',async()=>{
  const malformed={request_id:runId,document_id:doc,expected_revision:2,expected_content_sha256:hash,
    managed_world_id:'managed-a',campaign_id:'longmont-c2',session:30,session_evidence:[null]};
  localStorage.setItem(key,JSON.stringify(malformed));const view=mount();
  await act(async()=>view.result.current.recoverRecap());
  expect(view.result.current.error).toContain('unavailable');expect(api.recoverBuildRecap).not.toHaveBeenCalled();
  expect(view.result.current.pendingRecap).toBe(true);
  act(()=>view.result.current.setAsideRecap());
  expect(JSON.parse(localStorage.getItem(api.recapHistoryKey('managed-a',doc))!)).toEqual([malformed]);
});
