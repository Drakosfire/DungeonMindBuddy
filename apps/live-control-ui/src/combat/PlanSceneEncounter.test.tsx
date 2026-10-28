import {useEffect} from 'react';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import * as api from './sceneTemplatesApi';
import * as liveApi from '../api/liveApi';
import {PlanSceneEncounter} from './PlanSceneEncounter';
import type {TourOwnerReading} from '../guidedTour/GuidedTour';
const tourReadings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('../guidedTour/GuidedTour',()=>({useGuidedTour:()=>({captureScope:()=>null}),useTourOwnerReading:(reading:TourOwnerReading)=>tourReadings.set(reading.step,reading)}));
vi.mock('../surface/modules/CombatRosterModule',()=>({CombatRosterModule:({scope}:any)=>{useEffect(()=>scope.onPreparedState?.({record:scope.initialRecord,blocked:false,error:null,acknowledged:null}),[scope.initialRecord,scope.onPreparedState]);return <div data-testid="scoped-combat">{scope.encounterId}</div>}}));
const context:api.PlanEncounterContext={worldId:'elderwyld',documentId:'11111111-1111-4111-8111-111111111111',sceneId:'scene:gate',sceneTitle:'Gate',canCreate:true,objectRevision:2,contentSha256:'a'.repeat(64),verifiedPlan:{revisionN:1,workRevisionId:'22222222-2222-4222-8222-222222222222',contentSha256:'a'.repeat(64)}};
const pin={document_id:context.documentId,scene_id:context.sceneId,revision_n:1,work_revision_id:'22222222-2222-4222-8222-222222222222',content_sha256:'a'.repeat(64)};
const committed={schema_version:'dmb_workspace_committed_revision_v2',scope_mode:'world',world_id:'elderwyld',document_id:context.documentId,kind:'plan',status:'active',has_divergent_working_copy:false,object_revision:2,revision_n:1,work_revision_id:pin.work_revision_id,content_sha256:pin.content_sha256};
async function result(intent:api.SceneTemplateIntent):Promise<api.SceneTemplateView>{return {binding:{schema_version:'dmb_scene_template_binding_v1',world_id:'elderwyld',encounter_id:'33333333-3333-4333-8333-333333333333',origin:intent.pin,operation_id:intent.operation_id,request_digest:await api.sceneCreationDigest('elderwyld',intent),created_at:'2026-10-22T00:00:00Z'},encounter:{world_id:'elderwyld',encounter_id:'33333333-3333-4333-8333-333333333333',revision:1,draft:{title:'Gate encounter',entities:[]}} as any,versions:[{revision:1,digest:'sha256:'+'a'.repeat(64),saved_at:'2026-10-22T00:00:00Z'}],scene_present:true};}
function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(r=>resolve=r);return {promise,resolve};}
beforeEach(()=>{tourReadings.clear();sessionStorage.clear();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});vi.spyOn(api,'getSceneTemplate').mockResolvedValue(null);vi.spyOn(liveApi,'getWorldOwnedPlanCommittedRevision').mockResolvedValue(committed as any);});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
describe('Plan scene encounter preparation',()=>{
 it('creates from a verified exact saved Plan then opens shared Combat directly',async()=>{
  const create=vi.spyOn(api,'createSceneTemplate').mockImplementation(async(_world,intent)=>result(intent));
  render(<PlanSceneEncounter context={context}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Prepare encounter'}));
  expect(await screen.findByTestId('scoped-combat')).toHaveTextContent('33333333');
  expect(create.mock.calls[0][1].pin).toEqual(pin);expect(sessionStorage.length).toBe(0);
  expect(tourReadings.get('encounter')?.observation).toMatchObject({origin:'acknowledged',target:{revision:1,revisionId:pin.work_revision_id,digest:pin.content_sha256},proof:{kind:'encounter',sceneId:context.sceneId,encounterId:'33333333-3333-4333-8333-333333333333',revision:1,digest:'sha256:'+'a'.repeat(64)}});
 });
 it('preserves an unknown creation across remount and retries the identical key and body',async()=>{
  const create=vi.spyOn(api,'createSceneTemplate').mockRejectedValueOnce(new Error('Response lost')).mockImplementation(async(_world,intent)=>result(intent));
  const view=render(<PlanSceneEncounter context={context}/>);await userEvent.click(await screen.findByRole('button',{name:'Prepare encounter'}));
  await screen.findByRole('button',{name:'Retry same creation'});await screen.findByText('Error: Response lost');
  const original=create.mock.calls[0][1];view.unmount();render(<PlanSceneEncounter context={context}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Retry same creation'}));await screen.findByTestId('scoped-combat');
  expect(create.mock.calls[1][1]).toEqual(original);expect(sessionStorage.length).toBe(0);
 });
 it('does not release unknown intent from an absent status read',async()=>{
  vi.spyOn(api,'createSceneTemplate').mockRejectedValue(new Error('Unknown'));vi.spyOn(api,'inspectSceneTemplateCreation').mockResolvedValue(null);
  render(<PlanSceneEncounter context={context}/>);await userEvent.click(await screen.findByRole('button',{name:'Prepare encounter'}));await screen.findByText('Error: Unknown');
  await userEvent.click(screen.getByRole('button',{name:'Check creation'}));await screen.findByText(/not acknowledged yet/);expect(sessionStorage.length).toBe(1);expect(screen.queryByTestId('scoped-combat')).not.toBeInTheDocument();
 });
 it('releases only a verified cancellation fence',async()=>{
  vi.spyOn(api,'createSceneTemplate').mockRejectedValue(new Error('Unknown'));
  vi.spyOn(api,'cancelSceneTemplateCreation').mockImplementation(async(world,intent)=>({state:'canceled',operation_id:intent.operation_id,world_id:world,request_digest:await api.sceneCreationDigest(world,intent)}));
  render(<PlanSceneEncounter context={context}/>);await userEvent.click(await screen.findByRole('button',{name:'Prepare encounter'}));await screen.findByText('Error: Unknown');await userEvent.click(screen.getByRole('button',{name:'Cancel creation'}));
  await waitFor(()=>expect(sessionStorage.length).toBe(0));expect(screen.getByRole('button',{name:'Prepare encounter'})).toBeEnabled();
 });
 it('retains recovery on a foreign or altered acknowledgement',async()=>{
  vi.spyOn(api,'createSceneTemplate').mockImplementation(async(_world,intent)=>({...await result(intent),binding:{...(await result(intent)).binding,request_digest:'sha256:'+'0'.repeat(64)}}));
  render(<PlanSceneEncounter context={context}/>);await userEvent.click(await screen.findByRole('button',{name:'Prepare encounter'}));await screen.findByText(/Creation acknowledgement differs/);expect(sessionStorage.length).toBe(1);expect(screen.queryByTestId('scoped-combat')).not.toBeInTheDocument();expect(tourReadings.get('encounter')?.observation).toBeUndefined();
 });
 it('ignores a late response after changing scenes',async()=>{
  const pending=deferred<api.SceneTemplateView|null>();vi.mocked(api.getSceneTemplate).mockReturnValueOnce(pending.promise);
  const view=render(<PlanSceneEncounter context={context}/>);view.rerender(<PlanSceneEncounter context={{...context,sceneId:'scene:other'}}/>);
  const intent:api.SceneTemplateIntent={schema_version:'dmb_scene_template_create_v1',operation_id:crypto.randomUUID(),pin,encounter:{title:'Gate encounter'}};
  pending.resolve(await result(intent));await screen.findByRole('button',{name:'Prepare encounter'});expect(screen.queryByTestId('scoped-combat')).not.toBeInTheDocument();
 });
 it('blocks creation from a dirty Plan without discarding text or making requests',async()=>{
  const create=vi.spyOn(api,'createSceneTemplate');render(<PlanSceneEncounter context={{...context,canCreate:false}}/>);
  expect(await screen.findByRole('button',{name:'Prepare encounter'})).toBeDisabled();expect(create).not.toHaveBeenCalled();
 });
 it('rechecks current Plan state after the committed-pin read',async()=>{
  const pending=deferred<any>();vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockReturnValueOnce(pending.promise);const create=vi.spyOn(api,'createSceneTemplate');
  const view=render(<PlanSceneEncounter context={context}/>);await userEvent.click(await screen.findByRole('button',{name:'Prepare encounter'}));view.rerender(<PlanSceneEncounter context={{...context,canCreate:false}}/>);pending.resolve(committed);
  await screen.findByText(/Save and reopen this Plan/);expect(create).not.toHaveBeenCalled();
 });
 it('uses a valid editable default for a long scene heading',async()=>{
  const create=vi.spyOn(api,'createSceneTemplate').mockImplementation(async(_world,intent)=>result(intent));
  render(<PlanSceneEncounter context={{...context,sceneTitle:'x'.repeat(160)}}/>);
  const name=await screen.findByLabelText('Prepared encounter name');expect((name as HTMLInputElement).value.length).toBe(160);
  await userEvent.click(screen.getByRole('button',{name:'Prepare encounter'}));await screen.findByTestId('scoped-combat');expect(create.mock.calls[0][1].encounter.title.length).toBe(160);
 });
 it('leaves an invalid name editable without retaining or dispatching intent',async()=>{
  const create=vi.spyOn(api,'createSceneTemplate');render(<PlanSceneEncounter context={context}/>);
  fireEvent.change(await screen.findByLabelText('Prepared encounter name'),{target:{value:'x'.repeat(170)}});
  await userEvent.click(screen.getByRole('button',{name:'Prepare encounter'}));await screen.findByText(/Enter an encounter name/);
  expect(sessionStorage.length).toBe(0);expect(create).not.toHaveBeenCalled();expect(screen.getByLabelText('Prepared encounter name')).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Prepared encounter name'),{target:{value:'Valid revised name'}});expect(screen.getByRole('button',{name:'Prepare encounter'})).toBeEnabled();
 });

});
