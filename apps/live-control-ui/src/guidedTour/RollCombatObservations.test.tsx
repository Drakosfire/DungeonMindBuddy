import {render} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import type {TourOwnerReading} from './GuidedTour';
import {RecordedRollTourObservation,type RecordedRollReceipt} from './RollObservations';
import {CombatTourObservation,type AcknowledgedCombatSave} from './CombatObservations';
import {TourRunProvider} from './RunScope';
import type {WorldPlayRunRecordV2} from '../api/types';
import type {CombatEncounterRecord} from '../combat/combatTypes';
import {runPins} from './ownerPins';
import {validObservation} from './protocol';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('./GuidedTour',()=>({useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)readings.set(reading.step,reading);}}));
const run={schema_version:'dmb_world_play_run_record_v2',world_id:'world',run_id:'run',run_revision:3,playable_artifact_id:'plan',playable_revision:2,playable_work_revision_id:'work-2',playable_content_sha256:'a'.repeat(64)} as WorldPlayRunRecordV2;
const receipt:RecordedRollReceipt={world_id:'world',run_id:'run',command_id:'command',source:{playable_artifact_id:'plan',playable_revision:2,playable_work_revision_id:'work-2',playable_content_sha256:'a'.repeat(64)},table_id:'table',table_sha256:'b'.repeat(64),die_sides:12,physical_value:9,row_id:'row',recorded_at:'2026-10-28T00:00:00Z',expected_run_revision:2,resulting_run_revision:3};
beforeEach(()=>readings.clear());
it('labels retained roll history as an example rather than a new physical roll',()=>{
 render(<RecordedRollTourObservation run={run} history={[receipt]} acknowledged={null} blocked={false} error={null}/>);
 expect(readings.get('roll')?.observation?.origin).toBe('existing');expect(validObservation(readings.get('roll')?.observation,'world')).toBe(true);
});
it('does not transfer a recovered roll onto another source version of the same Run',()=>{
 render(<RecordedRollTourObservation run={{...run,playable_work_revision_id:'different'}} history={[receipt]} acknowledged={{run,receipt}} blocked={false} error={null}/>);
 expect(readings.get('roll')?.observation).toBeUndefined();
});
it.each([{...receipt,physical_value:13},{...receipt,world_id:'other'},{...receipt,run_id:'other'}])('does not recognize invalid or foreign roll evidence',wrong=>{
 render(<RecordedRollTourObservation run={run} history={[wrong]} acknowledged={null} blocked={false} error={null}/>);
 expect(readings.get('roll')?.observation).toBeUndefined();
});
const before={world_id:'world',encounter_id:'encounter',revision:1,updated_at:'2026-10-28T00:00:00Z',draft:{round:1,active_turn_entity_id:'actor',entities:[{id:'actor',hp:10,temp_hp:0,conditions:[]}]}} as CombatEncounterRecord;
const saved={...before,revision:2,draft:{...before.draft,entities:[{...before.draft.entities[0],hp:7}]}};
const acknowledged:AcknowledgedCombatSave={scope:runPins(run),sceneId:'scene',before,saved};
function combat(ack:AcknowledgedCombatSave,blocked=false,sceneId='scene'){
 return <TourRunProvider run={run}><CombatTourObservation record={saved} runScope={{runId:'run',sceneId}} acknowledged={ack} blocked={blocked} error={null}/></TourRunProvider>;
}
it('recognizes saved tracker fields with exact encounter revision references',()=>{
 render(combat(acknowledged));const observation=readings.get('combat')?.observation;
 expect(validObservation(observation,'world')).toBe(true);expect(observation?.proof).toMatchObject({kind:'combat-tracker',baseRevision:1,savedRevision:2,actors:[{actorId:'actor',fields:['hp']}]});
});
it('does not mistake roster-only edits or pending tracker work for saved tracking',()=>{
 const mounted=render(combat({...acknowledged,before:{...before,draft:{...saved.draft,title:'Previous roster title'}}}));
 expect(readings.get('combat')?.observation).toBeUndefined();
 mounted.rerender(combat(acknowledged,true));expect(readings.get('combat')?.observation).toBeUndefined();
});
it('does not transfer a tracker acknowledgement to another scene',()=>{
 render(combat(acknowledged,false,'other-scene'));expect(readings.get('combat')?.observation).toBeUndefined();
});
