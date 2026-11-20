import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {useMemo} from 'react';
import {afterEach,beforeEach,it,expect,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {testCombatLocks} from './combatRecovery.testSupport';
import * as api from './runEncountersApi';
import * as combatApi from './combatApi';
import * as selectedWorld from '../selectedWorld/SelectedWorldContext';
import type {CombatEncounterRecord} from './combatTypes';
import type {WorldPlayRunRecordV2} from '../api/types';
import type {TourOwnerReading} from '../guidedTour/GuidedTour';
import {TourRunProvider} from '../guidedTour/RunScope';
import {runPins} from '../guidedTour/ownerPins';
import {RunSceneEncounter,type RunEncounterContext} from './RunSceneEncounter';
import {AgentInteractionProvider,useAgentInteraction} from '../agentInteraction/AgentInteractionProvider';
import {usePublishSurfaceInteraction} from '../agentInteraction/usePublishSurfaceInteraction';
import {buildSurfaceInteractionIdentity} from '../surfaceInteraction/surfaceIdentity';
import {LegacyProjectionHostAdapter} from '../planSurface/projection/LegacyProjectionHostAdapter';
import {COMBAT_PROJECTION,COMBAT_TOOL,useCombatProjection} from './combatProjection';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
const dispatch={worldId:'elderwyld',walkthroughId:'walk',epoch:1};
vi.mock('../guidedTour/GuidedTour',()=>({useGuidedTour:()=>({tracking:true,captureScope:()=>dispatch}),useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)readings.set(reading.step,reading);}}));
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


const run={schema_version:'dmb_world_play_run_record_v2',world_id:'elderwyld',run_id:'run',run_revision:3,playable_artifact_id:'plan',playable_revision:22,playable_work_revision_id:'plan-22',playable_content_sha256:'b'.repeat(64)} as WorldPlayRunRecordV2;
const context:RunEncounterContext={worldId:'elderwyld',runId:'run',sceneId:'scene:gate',sceneTitle:'Gate',tourRun:runPins(run)};
function applied(encounter=record()):api.EncounterApplied{return {state:'applied',encounter,receipt:{encounter_id:encounter.encounter_id,intent:{world_id:'elderwyld',run_id:'run',scene_id:'scene:gate',request:{} as api.MaterializeRequest}}};}
function Publisher({current}:{current:RunEncounterContext}){
 const publication=useMemo(()=>({surfaceId:'play',label:'Play',identity:buildSurfaceInteractionIdentity({surfaceId:'play',instanceParts:['run']}),canvas:null,agentContext:null,tools:[COMBAT_TOOL],editCommands:[],projections:[COMBAT_PROJECTION],projectionBindings:[]}),[]);
 usePublishSurfaceInteraction(publication);useCombatProjection('play',true,current);
 const {activateProjectionTool}=useAgentInteraction();return <button onClick={()=>void activateProjectionTool('combat')}>Open encounter</button>;
}
// The real host is a sibling, outside the owning Play provider.
function fixture(current=context){return <AgentInteractionProvider><TourRunProvider run={run}><Publisher current={current}/></TourRunProvider><LegacyProjectionHostAdapter/></AgentInteractionProvider>;}
beforeEach(()=>{readings.clear();localStorage.clear();sessionStorage.clear();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});vi.spyOn(selectedWorld,'useSelectedWorld').mockReturnValue({kind:'managed',worldId:'elderwyld',name:'Elderwyld',documentId:null});vi.spyOn(api,'readRunEncounter').mockResolvedValue(applied());});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function open(current=context){const mounted=render(fixture(current));fireEvent.click(screen.getByText('Open encounter'));await screen.findByRole('textbox',{name:'Encounter title'});return mounted;}
function saveResponse(){return vi.spyOn(combatApi,'saveWorldCombatEncounter').mockImplementation(async(_world,_id,revision,draft)=>record({revision:revision+1,draft,updated_at:'2026-10-28T22:00:00Z'}));}
async function editAndSave(){fireEvent.change(screen.getByLabelText('HP for Geomantic Drake'),{target:{value:'65'}});await userEvent.click(screen.getByRole('button',{name:'Save',exact:true}));}
it('credits an actual tracker Save through the registered sibling host',async()=>{const save=saveResponse();await open();expect(readings.get('combat')?.observation).toBeUndefined();await editAndSave();await waitFor(()=>expect(readings.get('combat')?.observation?.origin).toBe('acknowledged'));expect(save).toHaveBeenCalledTimes(1);expect(readings.get('combat')).toMatchObject({dispatchScope:dispatch,observation:{target:runPins(run).target,parent:runPins(run).parent,proof:{kind:'combat-tracker',savedRevision:2,actors:[{actorId:entity.id,fields:['hp']}]}}});});
it.each([undefined,null,{...runPins(run),target:{...runPins(run).target,worldId:'foreign'}},{...runPins(run),target:{...runPins(run).target,objectId:'foreign'}},{...runPins(run),parent:{...runPins(run).parent,digest:'c'.repeat(64)}},{...runPins(run),parent:{...runPins(run).parent,kind:'source' as const}}])('refuses missing or foreign transported scope',async tourRun=>{saveResponse();await open({...context,tourRun});await editAndSave();await waitFor(()=>expect(screen.getByRole('button',{name:'Save',exact:true})).toBeDisabled());expect(readings.get('combat')?.observation).toBeUndefined();});
it.each(['run-revision','parent-revision'])('refuses acknowledgement after %s changes during Save',async change=>{const pending=deferred<CombatEncounterRecord>();vi.spyOn(combatApi,'saveWorldCombatEncounter').mockReturnValue(pending.promise);const mounted=await open();await editAndSave();const scope=runPins(run);mounted.rerender(fixture({...context,tourRun:change==='run-revision'?{...scope,target:{...scope.target,revision:4}}:{...scope,parent:{...scope.parent,revision:23,revisionId:'plan-23'}}}));await act(async()=>pending.resolve(record({revision:2,draft:{...record().draft,entities:[{...entity,hp:65}]}})));expect(readings.get('combat')?.observation).toBeUndefined();});
it('refuses newer edits made while Save is pending',async()=>{const pending=deferred<CombatEncounterRecord>();vi.spyOn(combatApi,'saveWorldCombatEncounter').mockReturnValue(pending.promise);await open();await editAndSave();fireEvent.change(screen.getByLabelText('HP for Geomantic Drake'),{target:{value:'64'}});await act(async()=>pending.resolve(record({revision:2,draft:{...record().draft,entities:[{...entity,hp:65}]}})));expect(readings.get('combat')?.observation).toBeUndefined();});
it('does not credit a reloaded record as a fresh action',async()=>{saveResponse();const mounted=await open();await editAndSave();await waitFor(()=>expect(readings.get('combat')?.observation?.origin).toBe('acknowledged'));mounted.unmount();readings.clear();vi.mocked(api.readRunEncounter).mockResolvedValue(applied(record({revision:2,draft:{...record().draft,entities:[{...entity,hp:65}]}})));await open();expect(readings.get('combat')?.observation).toBeUndefined();});

it('masks ambient Play scope when the projection has no transported scope',async()=>{saveResponse();render(<TourRunProvider run={run}><RunSceneEncounter context={{...context,tourRun:null}}/></TourRunProvider>);await screen.findByRole('textbox',{name:'Encounter title'});await editAndSave();await waitFor(()=>expect(screen.getByRole('button',{name:'Save',exact:true})).toBeDisabled());expect(readings.get('combat')?.observation).toBeUndefined();});
