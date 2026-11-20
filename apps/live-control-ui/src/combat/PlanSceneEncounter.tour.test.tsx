import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,beforeEach,it,expect,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {testCombatLocks} from './combatRecovery.testSupport';
import * as api from './sceneTemplatesApi';
import * as combatApi from './combatApi';
import * as selectedWorld from '../selectedWorld/SelectedWorldContext';
import {PlanSceneEncounter} from './PlanSceneEncounter';
import type {CombatEncounterRecord} from './combatTypes';
import type {TourOwnerReading} from '../guidedTour/GuidedTour';
const tourReadings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
const dispatch={worldId:'elderwyld',walkthroughId:'walk',epoch:1};
vi.mock('../guidedTour/GuidedTour',()=>({useGuidedTour:()=>({tracking:true,captureScope:()=>dispatch}),useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)tourReadings.set(reading.step,reading);}}));
const entity = {
  id: "drake-1",
  name: "Geomantic Drake",
  team: "enemy" as const,
  order: 1,
  init: 14,
  ac: 15,
  hp: 76,
  max_hp: 76,
  temp_hp: 0,
  defeated: false,
  notes: "Guards the pass",
  conditions: [],
  tags: [],
  statblock_path: null,
  statblock_artifact_id: null,
  statblock_title: null,
  corpus_fingerprint: null,
  source: "manual" as const,
  provenance: [], world_identity:null, mechanics_snapshot:null,
};

function record(overrides: Partial<CombatEncounterRecord> = {}): CombatEncounterRecord {
  return {
    encounter_id: "3f620410-21cb-4d18-88d4-5ea5e60b0b14",
    world_id: "elderwyld",
    campaign_id: "longmont-c2",
    session: 29,
    revision: 1,
    ruleset: {
      schema: "dmb_combat_ruleset_v1",
      config_id: "generic.manual-tracking",
      system_id: "generic",
      edition_id: "manual",
      revision: "1",
      mode: "manual_tracking",
      fields: [],
      manual_defaults: {},
    },
    ruleset_digest: "a".repeat(64),
    draft: {
      schema: "dmb_combat_encounter_draft_v1",
      title: "Mireward Gate",
      round: 1,
      active_turn_entity_id: "drake-1",
      round_start_entity_id: "drake-1",
      queue_model: "circular_barrel_v1",
      entities: [entity],
      groups: [],
      provenance: [],
    },
    created_at: "2026-10-17T12:00:00Z",
    updated_at: "2026-10-17T12:00:00Z",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}


const pin={revisionN:22,workRevisionId:'current-plan-22',contentSha256:'b'.repeat(64)};
const context:api.PlanEncounterContext={worldId:'elderwyld',documentId:'plan',sceneId:'scene:gate',sceneTitle:'Gate',canCreate:true,objectRevision:24,contentSha256:pin.contentSha256,verifiedPlan:pin};
function view(encounter=record(),scene_present=true):api.SceneTemplateView{return {binding:{schema_version:'dmb_scene_template_binding_v1',world_id:'elderwyld',encounter_id:encounter.encounter_id,origin:{document_id:'plan',scene_id:'scene:gate',revision_n:1,work_revision_id:'old-plan-1',content_sha256:'a'.repeat(64)},operation_id:'creation-original',request_digest:'sha256:'+'c'.repeat(64),created_at:encounter.created_at},encounter,versions:[{revision:encounter.revision,digest:'sha256:'+'d'.repeat(64),saved_at:encounter.updated_at}],scene_present};}
beforeEach(()=>{tourReadings.clear();localStorage.clear();sessionStorage.clear();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});vi.spyOn(selectedWorld,'useSelectedWorld').mockReturnValue({kind:'managed',worldId:'elderwyld',name:'Elderwyld',documentId:null});vi.spyOn(api,'getSceneTemplate').mockResolvedValue(view());});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function open(){const mounted=render(<PlanSceneEncounter context={context}/>);await screen.findByRole('textbox',{name:'Encounter title'});await waitFor(()=>expect(tourReadings.get('encounter')?.status).toBe('ready'));return mounted;}
function savedResponse(){return vi.spyOn(combatApi,'saveWorldCombatEncounter').mockImplementation(async(_world,_id,revision,draft)=>{const saved=record({revision:revision+1,draft,updated_at:'2026-10-28T19:00:00Z'});vi.mocked(api.getSceneTemplate).mockResolvedValue(view(saved));return saved;});}
it('admits the actual older-origin encounter as an existing example under the verified current Plan',async()=>{await open();expect(tourReadings.get('encounter')?.observation).toMatchObject({origin:'existing',target:{revision:22,revisionId:pin.workRevisionId,digest:pin.contentSha256},proof:{revision:1,operationId:'creation-original'}});});
it('credits an ordinary roster Save only after pairing its exact admitted record with the server version digest',async()=>{const save=savedResponse();await open();fireEvent.change(screen.getByRole('textbox',{name:'Notes for Geomantic Drake'}),{target:{value:'Warn before escalating; unresolved rehearsal.'}});await userEvent.click(screen.getByRole('button',{name:'Save',exact:true}));await waitFor(()=>expect(tourReadings.get('encounter')?.observation?.origin).toBe('acknowledged'));expect(save).toHaveBeenCalledTimes(1);expect(api.getSceneTemplate).toHaveBeenCalledTimes(2);expect(tourReadings.get('encounter')).toMatchObject({dispatchScope:dispatch,observation:{target:{revisionId:pin.workRevisionId},proof:{revision:2,digest:'sha256:'+'d'.repeat(64)}}});});
it('reloaded prepared records remain existing examples',async()=>{savedResponse();const mounted=await open();fireEvent.change(screen.getByRole('textbox',{name:'Encounter title'}),{target:{value:'Rehearsal title'}});await userEvent.click(screen.getByRole('button',{name:'Save',exact:true}));await waitFor(()=>expect(tourReadings.get('encounter')?.observation?.origin).toBe('acknowledged'));mounted.unmount();await open();expect(tourReadings.get('encounter')?.observation?.origin).toBe('existing');});
it('does not credit a newer draft arriving during Save',async()=>{const pending=deferred<CombatEncounterRecord>();vi.spyOn(combatApi,'saveWorldCombatEncounter').mockReturnValue(pending.promise);await open();fireEvent.change(screen.getByRole('textbox',{name:'Encounter title'}),{target:{value:'Submitted title'}});await userEvent.click(screen.getByRole('button',{name:'Save',exact:true}));fireEvent.change(screen.getByRole('textbox',{name:'Notes for Geomantic Drake'}),{target:{value:'Later local draft'}});const submitted=vi.mocked(combatApi.saveWorldCombatEncounter).mock.calls[0][3];await act(async()=>pending.resolve(record({revision:2,draft:submitted})));expect(screen.getByRole('textbox',{name:'Notes for Geomantic Drake'})).toHaveValue('Later local draft');expect(tourReadings.get('encounter')?.observation).toBeUndefined();expect(api.getSceneTemplate).toHaveBeenCalledTimes(1);});
it('re-admits membership on a changed Plan and refuses an absent scene instead of reusing the prior view',async()=>{const mounted=await open();const pending=deferred<api.SceneTemplateView|null>();vi.mocked(api.getSceneTemplate).mockReturnValueOnce(pending.promise);mounted.rerender(<PlanSceneEncounter context={{...context,objectRevision:25,contentSha256:'e'.repeat(64),verifiedPlan:{...pin,revisionN:23,workRevisionId:'work-23',contentSha256:'e'.repeat(64)}}}/>);expect(tourReadings.get('encounter')?.observation).toBeUndefined();await act(async()=>pending.resolve(view(record(),false)));expect(tourReadings.get('encounter')?.observation).toBeUndefined();});
it('cannot credit an earlier Plan save after its exact pin changes during the request',async()=>{const mounted=await open();const pending=deferred<CombatEncounterRecord>();vi.spyOn(combatApi,'saveWorldCombatEncounter').mockReturnValue(pending.promise);fireEvent.change(screen.getByRole('textbox',{name:'Encounter title'}),{target:{value:'Submitted title'}});await userEvent.click(screen.getByRole('button',{name:'Save',exact:true}));mounted.rerender(<PlanSceneEncounter context={{...context,objectRevision:25,contentSha256:'e'.repeat(64),verifiedPlan:{...pin,revisionN:23,workRevisionId:'work-23',contentSha256:'e'.repeat(64)}}}/>);await act(async()=>pending.resolve(record({revision:2,draft:vi.mocked(combatApi.saveWorldCombatEncounter).mock.calls[0][3]})));expect(tourReadings.get('encounter')?.observation?.origin).not.toBe('acknowledged');});
it('refuses a server version read that does not match the acknowledged record',async()=>{vi.spyOn(combatApi,'saveWorldCombatEncounter').mockImplementation(async(_w,_id,rev,draft)=>record({revision:rev+1,draft}));await open();fireEvent.change(screen.getByRole('textbox',{name:'Encounter title'}),{target:{value:'Saved title'}});await userEvent.click(screen.getByRole('button',{name:'Save',exact:true}));await screen.findByRole('alert');expect(tourReadings.get('encounter')?.status).toBe('failed');expect(tourReadings.get('encounter')?.observation).toBeUndefined();});
it.each(['world','scene','encounter'])('refuses a foreign %s view',async kind=>{const foreign=view();if(kind==='world')foreign.binding.world_id='other';if(kind==='scene')foreign.binding.origin.scene_id='scene:other';if(kind==='encounter')foreign.encounter={...foreign.encounter,encounter_id:'other'};vi.mocked(api.getSceneTemplate).mockResolvedValue(foreign);render(<PlanSceneEncounter context={context}/>);await screen.findByRole('alert');expect(tourReadings.get('encounter')?.observation).toBeUndefined();});
it('requires the complete current verified Plan pin',async()=>{render(<PlanSceneEncounter context={{...context,verifiedPlan:null}}/>);await screen.findByRole('textbox',{name:'Encounter title'});expect(tourReadings.get('encounter')?.observation).toBeUndefined();});
