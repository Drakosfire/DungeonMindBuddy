import {beforeEach,it,expect,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import type {WorldBuildAgentTurnRequestV1,WorldAgentConversationHistoryTurn} from '../../api/types';
import {captureWorkPlan} from './workPlanCapture';
import {getWorkPlan} from '../../api/conversationWorkPlanApi';
import {stagePlacement} from './workPlanPlacement';
vi.mock('../../api/conversationWorkPlanApi',()=>({getWorkPlan:vi.fn()}));
vi.mock('./workPlanPlacement',async original=>({...await original<typeof import('./workPlanPlacement')>(),stagePlacement:vi.fn()}));
const conversation='11111111-1111-4111-8111-111111111111',turnId='22222222-2222-4222-8222-222222222222';
const basis={world_id:'world',document_id:'page',registry_revision:3,content_sha256:'a'.repeat(64),draft_sha256:'b'.repeat(64),editor_sha256:'c'.repeat(64),visibility:'internal',caret:1,draft_generation:0,selection_generation:0};
const request={owner_scope:{world_id:'world'},primary_work:{kind:'build',object_id:'page',expected_revision:3,expected_content_sha256:basis.content_sha256},message:'Plan this.',build_write_capability:{conversation_id:conversation,expected_pointer_revision:2,basis}} as WorldBuildAgentTurnRequestV1;
const turn={turn_id:turnId,idempotency_key:'real-key',lifecycle_status:'completed',user_text:request.message,assistant_text:'A plan.',provenance:{world_id:'world',surface_id:'build',primary_work:{kind:'build',object_id:'page',revision:'3',content_sha256:basis.content_sha256}}} as WorldAgentConversationHistoryTurn;
const collaboration={kind:'plan' as const,steps:[{text:'Read the chart.',kind:'discuss' as const}]};
beforeEach(()=>{vi.clearAllMocks();vi.stubGlobal('crypto',webcrypto);vi.mocked(getWorkPlan).mockResolvedValue(null);});
it('transfers the actual request anchor to the durable history turn without copying execution state',async()=>{
 await captureWorkPlan(request,turn,conversation,2,'real-key','A plan.',collaboration,collaboration);
 expect(stagePlacement).toHaveBeenCalledWith(expect.objectContaining({source_turn_id:turnId,conversation_id:conversation,document_id:'page'}),basis,2,[expect.objectContaining({text:'Read the chart.',selected:true,kind:'discuss'})],0);
});
it.each(['key','pointer','answer','source','collaboration','selection'])('refuses a mismatched %s before any shared receipt write',async variant=>{
 const r=structuredClone(request),t=structuredClone(turn);let key='real-key',pointer=2,answer='A plan.',retained:unknown=collaboration;
 if(variant==='key')key='other';if(variant==='pointer')pointer=3;if(variant==='answer')answer='different';
 if(variant==='source')t.provenance.primary_work.object_id='other';if(variant==='collaboration')retained={kind:'questions',questions:[]};
 if(variant==='selection')r.build_write_capability!.basis.selection={end:2,text:'selected'};
 await expect(captureWorkPlan(r,t,conversation,pointer,key,answer,collaboration,retained)).rejects.toThrow(/explicit position/);
 expect(stagePlacement).not.toHaveBeenCalled();expect(getWorkPlan).not.toHaveBeenCalled();
});
it('adopts already reviewed stable step identities instead of minting a second review',async()=>{
 const rows=[{step_id:turnId,text:'Edited step.',selected:false,kind:'prepare_insertion' as const}];
 vi.mocked(getWorkPlan).mockResolvedValue({steps:rows,revision:4} as Awaited<ReturnType<typeof getWorkPlan>>);
 await captureWorkPlan(request,turn,conversation,2,'real-key','A plan.',collaboration,collaboration);
 expect(stagePlacement).toHaveBeenCalledWith(expect.anything(),basis,2,rows,4);
});
