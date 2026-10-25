import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {render,cleanup} from '@testing-library/react';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/MarkdownCanvasSession';
import type {BuildComposeBridge} from './buildComposeBridge';
import type {WorkPlan} from '../api/conversationWorkPlanApi';
import {BuildWorkPlanHost} from './BuildWorkPlanHost';
import {useWorkPlanHost,type WorkPlanHost} from '../surface/workPlans/WorkPlanHost';
import {queueSurfaceConversationRequest} from '../agentInteraction/surfaceConversationRequests';
const state=vi.hoisted(()=>({registry:{history:{conversation_id:'conversation',active_conversation_id:'conversation',pointer_revision:1},pendingTurn:null},open:vi.fn()}));
vi.mock('../agentInteraction/WorldAgentConversation',()=>({useWorldAgentConversationState:()=>state.registry}));
vi.mock('../agentInteraction/useAgentInteraction',()=>({useAgentInteraction:()=>({setPaneOpen:state.open})}));
vi.mock('../agentInteraction/surfaceConversationRequests',()=>({queueSurfaceConversationRequest:vi.fn()}));
let host:WorkPlanHost;const child=()=>{host=useWorkPlanHost()!;return null;};
const bridge={} as BuildComposeBridge;
const plan={world_id:'world',document_id:'page',conversation_id:'conversation'} as WorkPlan;
function session(documentId='page',clean=true){return {documentId,record:{world_id:'world'},editor:{},snapshot:{},activeCommand:null,phase:'ready',lookupAdmission:()=>({ok:clean})} as unknown as MarkdownCanvasSessionValue;}
function view(s:MarkdownCanvasSessionValue){const Child=child;return <BuildWorkPlanHost session={s} bridge={bridge}><Child/></BuildWorkPlanHost>;}
beforeEach(()=>vi.clearAllMocks());afterEach(cleanup);
it('captures the host before await and rejects leaving/returning to the identical clean context',()=>{
 const original=session(),mounted=render(view(original)),admitted=host.beginContinuation!(plan);
 expect(admitted()).toBe(true);mounted.rerender(view(session('other')));mounted.rerender(view(original));expect(admitted()).toBe(false);
});
it('blocks a dirty page before reservation and opens chat for a valid explicitly queued continuation',()=>{
 const original=session(),mounted=render(view(session('page',false)));
 expect(()=>host.beginContinuation!(plan)).toThrow(/Save and open/);expect(queueSurfaceConversationRequest).not.toHaveBeenCalled();
 mounted.rerender(view(original));host.onContinue(plan,{command_id:'command',step_id:'step',client_thread_id:'thread',client_turn_id:'turn',message:'Reviewed text'},null);
 expect(state.open).toHaveBeenCalledWith(true);expect(queueSurfaceConversationRequest).toHaveBeenCalledTimes(1);
 const request=vi.mocked(queueSurfaceConversationRequest).mock.calls[0][0];expect(request.isCurrent()).toBe(true);
 mounted.rerender(view(session('other')));mounted.rerender(view(original));expect(request.isCurrent()).toBe(false);
});
