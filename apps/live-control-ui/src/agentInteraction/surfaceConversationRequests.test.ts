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
