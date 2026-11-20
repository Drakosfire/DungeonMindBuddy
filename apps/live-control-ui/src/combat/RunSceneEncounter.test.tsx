import {testCombatLocks} from './combatRecovery.testSupport';
import {fireEvent,render,screen,waitFor,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {RunSceneEncounter} from './RunSceneEncounter';
const api=vi.hoisted(()=>({read:vi.fn(),preview:vi.fn(),create:vi.fn()}));
vi.mock('./runEncountersApi',()=>({readRunEncounter:api.read,previewRunEncounter:api.preview,materializeRunEncounter:api.create}));
vi.mock('../surface/modules/CombatRosterModule',()=>({CombatRosterModule:({scope}:{scope:{runScope:{runId:string;sceneId:string};initialRecord:{draft:{title:string}}}})=><p>Scoped fight {scope.initialRecord.draft.title} · {scope.runScope.sceneId}</p>}));
const context={worldId:'elderwyld',runId:'run-a',sceneId:'scene:gate',sceneTitle:'Gate'};
const preview={world_id:'elderwyld',run_id:'run-a',scene_id:'scene:gate',title:'Gate guardians',preparation_digest:'sha256:a',template:{encounter_id:'template-a',revision:2,digest:'sha256:b'},initialization_policy:'dmb_fresh_scene_encounter_v1',preview_digest:'sha256:c',actors:[{actor_id:'guard',name:'Gate guard',hp_before:2,hp_after:20,typed_maximum:true,temp_hp_before:7,conditions_before:['Prone'],defeated_before:true}]};
beforeEach(()=>{Object.defineProperty(navigator,"locks",{configurable:true,value:testCombatLocks()});localStorage.clear();vi.resetAllMocks();api.read.mockResolvedValue(null);api.preview.mockResolvedValue(preview);});
afterEach(cleanup);
it('requires an explicit start and retains the exact request before dispatch',async()=>{
 api.create.mockImplementation(async(_world,scope,request)=>{expect(localStorage.getItem('dmb.scene.encounter.creation:'+JSON.stringify(['elderwyld','run-a','scene:gate']))).toContain(request.operation_id);return {state:'applied',encounter:{world_id:'elderwyld',encounter_id:'fight-a',draft:{title:'Gate guardians'}},receipt:{encounter_id:'fight-a',intent:{world_id:'elderwyld',run_id:scope.runId,scene_id:scope.sceneId,request}}};});
 render(<RunSceneEncounter context={context}/>);await screen.findByRole('button',{name:'Start this encounter'});expect(api.create).not.toHaveBeenCalled();
 expect(screen.getByText(/HP 2 → 20/)).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Start this encounter'}));
 await screen.findByText('Scoped fight Gate guardians · scene:gate');expect(api.read).toHaveBeenCalledTimes(1);expect(api.create).toHaveBeenCalledTimes(1);
});
it('recovers an unknown creation across unmount without auto-reposting',async()=>{
 api.create.mockRejectedValue(new Error('response lost'));const first=render(<RunSceneEncounter context={context}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Start this encounter'}));await screen.findByText(/response lost/);first.unmount();
 render(<RunSceneEncounter context={context}/>);await screen.findByRole('button',{name:'Check creation'});expect(api.create).toHaveBeenCalledTimes(1);expect(api.read).toHaveBeenCalledTimes(1);
 api.create.mockResolvedValue(null);fireEvent.click(screen.getByRole('button',{name:'Check creation'}));await waitFor(()=>expect(api.create).toHaveBeenLastCalledWith('elderwyld',context,expect.objectContaining({template:preview.template}),'/inspect'));
 expect(localStorage.length).toBe(1);
});
it('does not consult current preparation when a bound fight exists',async()=>{
 api.read.mockResolvedValue({state:'applied',encounter:{encounter_id:'fight-a',world_id:'elderwyld',draft:{title:'Progressed fight'}},receipt:{encounter_id:'fight-a',intent:{world_id:'elderwyld',run_id:'run-a',scene_id:'scene:gate'}}});
 render(<RunSceneEncounter context={context}/>);await screen.findByText('Scoped fight Progressed fight · scene:gate');expect(api.preview).not.toHaveBeenCalled();
});
