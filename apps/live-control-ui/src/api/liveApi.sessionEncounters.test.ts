import {afterEach,expect,it,vi} from 'vitest';
import {authenticatedApiFetch,setNativeGraphAccessToken} from './liveApi';
import {assertSessionOutcome} from '../combat/runEncountersApi';
afterEach(()=>{vi.restoreAllMocks();setNativeGraphAccessToken(null);});
it.each([
 ['/api/live/world-play-runs/v2/preparation','POST'],
 ['/api/live/world-play-runs/v2/run-a','PUT'],
 ['/api/live/world-play-runs/v2/run-a/creation','GET'],
 ['/api/live/world-play-runs/v2/run-a/creation:cancel','POST'],
 ['/api/live/combat/run-encounters/run-a/scenes/scene%3Agate','POST'],
 ['/api/live/combat/run-encounters/run-a/scenes/scene%3Agate/inspect','POST'],
 ['/api/live/combat/run-encounters/run-a/scenes/scene%3Agate/encounters/fight-a','PUT'],
 ['/api/live/combat/run-encounters/run-a/scenes/scene%3Agate/encounters/fight-a/mechanics-adoptions:cancel','POST'],
])('authenticates current session/encounter transport %s',async(path,method)=>{
 setNativeGraphAccessToken('test-only-local-operator-credential-value');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 await authenticatedApiFetch(path+'?world_id=elderwyld',{method,...(method==='GET'?{}:{body:JSON.stringify(method==='PUT'&&path.startsWith('/api/live/world-play-runs/')?{schema_version:'dmb_world_session_create_v1'}:{intent:'fixed'})})});
 expect(fetch).toHaveBeenCalledTimes(1);expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer test-only-local-operator-credential-value');
 expect(fetch.mock.calls[0][1]).toMatchObject({redirect:'error',credentials:'same-origin',method});
});
it('does not accept a cancellation of a different entry choice',()=>{
 const request={schema_version:'dmb_world_session_create_v1' as const,playable_artifact_id:'source',expected_playable_revision:1,expected_playable_work_revision_id:'revision',expected_playable_content_sha256:'a'.repeat(64),entry_scene_id:'scene:gate',encounters:[{scene_id:'scene:gate',template:null}]};
 expect(()=>assertSessionOutcome({state:'canceled',world_id:'elderwyld',run_id:'run-a',request_digest:'sha256:a',request:{...request,entry_scene_id:'scene:other'}},'elderwyld','run-a',request)).toThrow('another session');
});
