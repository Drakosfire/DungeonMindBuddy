import {fireEvent,render,screen} from '@testing-library/react';
import {beforeEach,it,vi,expect} from 'vitest';
import {App} from '../App';
import * as liveApi from '../api/liveApi';
import {mockCatalog,mockLayout,mockPlanView,mockState} from '../test/fixtures';
import {createWalkthrough,reduceTour} from './protocol';
import {writeWalkthrough,readWalkthrough} from './storage';
vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getSurface: vi.fn(),
    getEvents: vi.fn(),
    getJobs: vi.fn(),
    getPlanView: vi.fn(),
    getGraphIngestRuns: vi.fn(),
    getGoldReviewSessions: vi.fn(),
    getManualReviewBeds: vi.fn(),
    getCapabilities: vi.fn(),
    listWorkspaceDocuments: vi.fn(),
    listWorldContainers: vi.fn(),
    listWorldOwnedPlans: vi.fn(),
    listWorldOwnedRunbooks: vi.fn(),
    listWorldPlayRuns: vi.fn(),
    putWorldPlayActiveRun: vi.fn(),
    getWorkspaceDocument: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    getPlayActiveRun: vi.fn(),
    putPlayActiveRun: vi.fn(),
    getCommittedWorkspaceRevision: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    listPlayRuns: vi.fn(),
    getPlayRun: vi.fn(),
    getPlayRunReferenceManifest: vi.fn(),
  };
});

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(liveApi.listWorldContainers).mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[]});
    window.history.pushState({}, "", "/");
    vi.mocked(liveApi.getSurface).mockResolvedValue({
      catalog: mockCatalog,
      layout: mockLayout,
      state: mockState,
    });
    vi.mocked(liveApi.getEvents).mockResolvedValue({ events: [] });
    vi.mocked(liveApi.getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(liveApi.getPlanView).mockResolvedValue(mockPlanView);
    vi.mocked(liveApi.getGraphIngestRuns).mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "test",
      runs: [],
    });
    vi.mocked(liveApi.getGoldReviewSessions).mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "test",
      sessions: [],
    });
    vi.mocked(liveApi.getManualReviewBeds).mockResolvedValue({
      schema_version: "dmb_graph_manual_review_beds_v1",
      version: "test",
      beds: [],
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [],
    });
    vi.mocked(liveApi.getPlayActiveRun).mockRejectedValue(
      new liveApi.LiveApiError("active selection unavailable", 503),
    );
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(
      new liveApi.LiveApiError("not found", 404),
    );
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [],
    });
  });

  it('keeps live guidance across actual Build and Play route transitions without selecting a latest Run',async()=>{
    localStorage.clear();const world='tour-route-world';
    vi.spyOn(liveApi,'listWorldContainers').mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[{schema_version:'dmb_world_container_record_v1',world_id:world,name:'Tour World',source_root_relpath:'corpus/tour-route-world',created_at:'2026-01-01T00:00:00Z'}]});
    vi.spyOn(liveApi,'listWorldOwnedPlans').mockResolvedValue({schema_version:'dmb_workspace_document_registry_v2',scope_mode:'world',world_id:world,records:[]});
    vi.spyOn(liveApi,'listWorldOwnedRunbooks').mockResolvedValue({schema_version:'dmb_workspace_document_registry_v2',scope_mode:'world',world_id:world,records:[]});
    vi.spyOn(liveApi,'listWorldPlayRuns').mockResolvedValue({schema_version:'dmb_world_play_runs_list_v2',world_id:world,records:[]});
    const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async(input)=>{
      const path=String(input);
      if(path.includes('/api/live/world-containers'))return new Response(JSON.stringify({schema_version:'dmb_world_container_registry_v1',records:[{schema_version:'dmb_world_container_record_v1',world_id:world,name:'Tour World',source_root_relpath:'corpus/tour-route-world',created_at:'2026-01-01T00:00:00Z'}]}),{status:200,headers:{'Content-Type':'application/json'}});
      return new Response(JSON.stringify({detail:'No fixture for '+path}),{status:404,headers:{'Content-Type':'application/json'}});
    });
    try{
    const active=vi.spyOn(liveApi,'putWorldPlayActiveRun');
    Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_:string,action:()=>unknown)=>action())}});
    let walk=createWalkthrough(world,'sheep','route-walk','2026-10-28T00:00:00Z');walk=reduceTour(walk,{kind:'move',index:13});writeWalkthrough(localStorage,walk,null);
    window.history.replaceState({},'',`/build?world=${world}`);render(<App/>);
    await screen.findByTestId('build-surface-empty');
    fireEvent.click(screen.getByRole('button',{name:'Open navigation'}));fireEvent.click(screen.getByRole('button',{name:'Guided journey'}));
    fireEvent.click(await screen.findByRole('button',{name:'Open Play',exact:true}));
    await screen.findByTestId('play-run-chooser');
    expect(window.location.search).toBe(`?world=${world}&choose=1`);
    expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeInTheDocument();
    expect(active).not.toHaveBeenCalled();expect(readWalkthrough(localStorage,world)?.record.bindings.run).toBeUndefined();
    fireEvent.click(screen.getByText('Steps and demonstrated results'));fireEvent.click(screen.getByRole('button',{name:'Open the source',exact:true}));
    fireEvent.click(await screen.findByRole('button',{name:'Open Build',exact:true}));
    await screen.findByTestId('build-surface-empty');expect(new URLSearchParams(window.location.search).get('world')).toBe(world);
    expect(readWalkthrough(localStorage,world)?.record.id).toBe('route-walk');expect(active).not.toHaveBeenCalled();
    }finally{fetch.mockRestore();}
  });

