import {afterEach,expect,it,vi} from 'vitest';
import {queueSurfaceConversationRequest,claimSurfaceConversationRequest,acceptSurfaceConversationRequest,failSurfaceConversationRequest,retrySurfaceConversationRequest,cancelSurfaceConversationRequest} from './surfaceConversationRequests';
const make=(id='test-gesture')=>({id,worldId:'world-a',surfaceId:'build',objectId:'page-a',message:'Build this',clientThreadId:'thread',turnId:'turn',isCurrent:()=>true});
afterEach(()=>{cancelSurfaceConversationRequest('test-gesture');});
it('claims a user gesture once and retires it only at accepted dispatch',()=>{
 queueSurfaceConversationRequest(make());expect(claimSurfaceConversationRequest('test-gesture')?.status).toBe('claimed');
 expect(claimSurfaceConversationRequest('test-gesture')).toBeNull();acceptSurfaceConversationRequest('test-gesture');
 expect(claimSurfaceConversationRequest('test-gesture')).toBeNull();
});
it('requires an explicit retry after failed preparation',()=>{
 queueSurfaceConversationRequest(make());claimSurfaceConversationRequest('test-gesture');failSurfaceConversationRequest('test-gesture');
 expect(claimSurfaceConversationRequest('test-gesture')).toBeNull();retrySurfaceConversationRequest('test-gesture');
 expect(claimSurfaceConversationRequest('test-gesture')?.status).toBe('claimed');
});
it('retires a gesture whose target changed before consumption',()=>{
 let current=true;queueSurfaceConversationRequest({...make(),isCurrent:()=>current});current=false;
 window.dispatchEvent(new PopStateEvent('popstate'));expect(claimSurfaceConversationRequest('test-gesture')).toBeNull();
});
it('rejects an already foreign target and does not execute its preparation',()=>{
 const prepare=vi.fn();expect(()=>queueSurfaceConversationRequest({...make(),isCurrent:()=>false,prepare})).toThrow('destination');
 expect(prepare).not.toHaveBeenCalled();
});

it('keeps frozen dispatch references and refuses deduplication with changed context',()=>{
 const refs={schema:'dmb_authored_graph_references_v1' as const,references:[{schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:'world-a',native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:'box',label:'Box'}]};
 queueSurfaceConversationRequest({...make(),authoredReferences:refs});
 expect(()=>queueSurfaceConversationRequest({...make(),authoredReferences:{...refs,references:[]}})).toThrow('different authoring request');
 expect(claimSurfaceConversationRequest('test-gesture')?.authoredReferences).toEqual(refs);
});
