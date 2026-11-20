import {render,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import type {WorldPlayRunRecordV2} from '../api/types';
import type {TourOwnerReading} from './GuidedTour';
import {RunStateTourObservations} from './RunObservations';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
const mode=vi.hoisted(()=>({tracking:true}));
vi.mock('./GuidedTour',()=>({useGuidedTour:()=>mode,useTourOwnerReading:(reading:TourOwnerReading)=>readings.set(reading.step,reading)}));
const run={schema_version:'dmb_world_play_run_record_v2',world_id:'world',run_id:'run',run_revision:7,playable_artifact_id:'plan',playable_revision:3,playable_work_revision_id:'work-3',playable_content_sha256:'a'.repeat(64),updated_at:'2026-10-28T00:00:00Z',progress:{current_scene_id:'scene',current_beat_id:'beat',resolved_beat_ids:[],selections:{choice:'option'},notes_by_element_id:{scene:'Secret saved scene note'}}} as WorldPlayRunRecordV2;
const content={edition_revision:0,edition_revision_id:null,content_sha256:'a'.repeat(64)};
beforeEach(()=>{mode.tracking=true;readings.clear();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});});
it('compares exact saved state across page instances without storing note bodies',async()=>{
 const mounted=render(<RunStateTourObservations run={run} content={content} blocked={false} acknowledgedRun={null} pageInstanceId='page-1'/>);
 await waitFor(()=>expect(readings.get('recovery')?.observation?.proof?.kind).toBe('run-state'));
 const old=readings.get('recovery')!.observation!.proof!;
 expect(JSON.stringify(old)).not.toContain('Secret saved scene note');
 mounted.rerender(<RunStateTourObservations run={{...run}} content={{...content}} blocked={false} acknowledgedRun={null} pageInstanceId='page-2'/>);
 await waitFor(()=>expect(readings.get('recovery')?.observation?.proof).toMatchObject({pageInstanceId:'page-2'}));
 expect(readings.get('recovery')?.observation?.proof).toMatchObject({...old,pageInstanceId:'page-2'});
 expect(readings.get('progress')?.observation?.origin).toBe('existing');
});
it('credits progress only from an acknowledged current Run with choices and saved notes',async()=>{
 const acknowledgedRun={worldId:'world',runId:'run',revision:7};
 const mounted=render(<RunStateTourObservations run={run} content={content} blocked={false} acknowledgedRun={acknowledgedRun}/>);
 await waitFor(()=>expect(readings.get('progress')?.observation?.origin).toBe('acknowledged'));
 mounted.rerender(<RunStateTourObservations run={run} content={content} blocked={true} acknowledgedRun={acknowledgedRun}/>);
 expect(readings.get('progress')?.observation).toBeUndefined();expect(readings.get('recovery')?.observation).toBeUndefined();
 mounted.rerender(<RunStateTourObservations run={{...run,progress:{...run.progress,notes_by_element_id:{}}}} content={content} blocked={false} acknowledgedRun={acknowledgedRun}/>);
 await waitFor(()=>expect(readings.get('recovery')?.status).toBe('ready'));
 expect(readings.get('progress')?.observation).toBeUndefined();expect(readings.get('progress')?.status).toBe('pending');
});

afterEach(()=>vi.restoreAllMocks());
it('does no saved-state fingerprinting when no walkthrough is running',()=>{
 mode.tracking=false;const digest=vi.spyOn(crypto.subtle,'digest');
 render(<RunStateTourObservations run={run} content={content} blocked={false} acknowledgedRun={null}/>);
 expect(digest).not.toHaveBeenCalled();expect(readings.get('recovery')?.observation).toBeUndefined();
});

it('keeps blocked admission unavailable and actual fingerprint failure failed',async()=>{
 const mounted=render(<RunStateTourObservations run={run} content={content} blocked={true} acknowledgedRun={null}/>);
 expect(readings.get('progress')?.status).toBe('unavailable');expect(readings.get('progress')?.observation).toBeUndefined();
 vi.spyOn(crypto.subtle,'digest').mockRejectedValue(new Error('Digest unavailable'));
 mounted.rerender(<RunStateTourObservations run={run} content={content} blocked={false} acknowledgedRun={null}/>);
 await waitFor(()=>expect(readings.get('progress')?.status).toBe('failed'));expect(readings.get('recovery')?.status).toBe('failed');expect(readings.get('progress')?.observation).toBeUndefined();
});
