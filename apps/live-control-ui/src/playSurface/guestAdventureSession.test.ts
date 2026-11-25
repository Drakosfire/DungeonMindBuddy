import {beforeEach,describe,expect,it,vi} from 'vitest';
import {guestAdventureSession} from './guestAdventureSession';
import * as api from '../api/liveApi';
import * as session from '../combat/runEncountersApi';
vi.mock('../api/liveApi',()=>({listWorldOwnedPlans:vi.fn(),getWorldOwnedPlanCommittedRevision:vi.fn(),putWorldPlayRun:vi.fn()}));
vi.mock('../combat/runEncountersApi',()=>({previewSession:vi.fn(),assertSessionOutcome:vi.fn()}));
const world='guest-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', id='11111111-1111-4111-8111-111111111111';
const source={playable_artifact_id:id,expected_playable_revision:1,expected_playable_work_revision_id:'rev',expected_playable_content_sha256:'hash'};
const request={...source,schema_version:'dmb_world_session_create_v1',entry_scene_id:'scene:contract',encounters:[]};
describe('guest adventure session',()=>{
 beforeEach(()=>{vi.resetAllMocks();
  vi.mocked(api.listWorldOwnedPlans).mockResolvedValue({world_id:world,records:[{world_id:world,campaign_id:null,kind:'plan',status:'active',title:"Sizzek's Apprentice",document_id:id}]} as never);
  vi.mocked(api.getWorldOwnedPlanCommittedRevision).mockResolvedValue({world_id:world,campaign_id:null,kind:'plan',status:'active',document_id:id,revision_n:1,work_revision_id:'rev',content_sha256:'hash',has_divergent_working_copy:false} as never);
  vi.mocked(session.previewSession).mockResolvedValue({request,scenes:[],excluded_orphan_count:0} as never);
  vi.mocked(api.putWorldPlayRun).mockResolvedValue({state:'applied'} as never);
 });
 it('prepares and creates one deterministic session',async()=>{
  const result=await guestAdventureSession(world,[],()=>true);
  expect(result).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
  expect(session.previewSession).toHaveBeenCalledWith(world,source,'scene:contract');
  expect(api.putWorldPlayRun).toHaveBeenCalledWith(result,world,request);
  expect(session.assertSessionOutcome).toHaveBeenCalled();
 });
 it('reopens a matching session',async()=>{
  const run={schema_version:'dmb_world_play_run_record_v2',world_id:world,playable_artifact_id:id,run_id:'existing',updated_at:'2026-01-01'};
  expect(await guestAdventureSession(world,[run] as never,()=>true)).toBe('existing');
  expect(api.putWorldPlayRun).not.toHaveBeenCalled();
 });
 it('does not create after navigation or altered preparation',async()=>{
  expect(await guestAdventureSession(world,[],()=>false)).toBeNull();
  vi.mocked(session.previewSession).mockResolvedValue({request:{...request,entry_scene_id:'scene:other'}} as never);
  await expect(guestAdventureSession(world,[],()=>true)).rejects.toThrow('did not match');
  expect(api.putWorldPlayRun).not.toHaveBeenCalled();
 });
});
