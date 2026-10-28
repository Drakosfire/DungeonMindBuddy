import {render,screen,waitFor,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import * as api from '../../api/liveApi';
import {SavedMechanicsRevisionEditor} from './SavedMechanicsRevisionEditor';
import {TourEncounterProvider,type TourEncounterScope} from '../../guidedTour/EncounterScope';
import type {TourOwnerReading} from '../../guidedTour/GuidedTour';
const tourReadings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('../../guidedTour/GuidedTour',()=>({useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)tourReadings.set(reading.step,reading);}}));
import {baseCandidateDefinition} from '../editor/editorFixtures';
import type {OpenSavedMechanicsVersion,RevisionSaveOutcome,SavedMechanicsVersionList} from './savedMechanicsRevisionTypes';
vi.mock('../../api/liveApi',()=>({listSavedMechanicsVersions:vi.fn(),openSavedMechanicsVersion:vi.fn(),saveMechanicsRevision:vi.fn(),recoverMechanicsRevision:vi.fn(),inspectMechanicsRevision:vi.fn(),validateStatblockDefinition:vi.fn()}));
const world='test-world',draft='11111111-1111-4111-8111-111111111111';
const base={provider:'dungeonmind' as const,statblock_id:'sb_one',revision_id:'rev_original',contract:'dungeonmind.dungeonbuddy-statblocks',contract_version:'1.0.0',definition_digest:'sha256:'+'a'.repeat(64)};
const next={...base,revision_id:'rev_next',definition_digest:'sha256:'+'b'.repeat(64)};
const tourScope:TourEncounterScope={plan:{kind:'plan',worldId:world,objectId:'plan',revision:2,revisionId:'work-2',digest:'d'.repeat(64)},sceneId:'scene',encounterId:'encounter'};
let outcome:RevisionSaveOutcome;
function page():SavedMechanicsVersionList{return {world_id:world,draft_id:draft,name:'Keeper',original:base,operations:[],pending:null,next_offset:null};}
function opened(revision=base.revision_id):OpenSavedMechanicsVersion{
  const definition=baseCandidateDefinition();if(revision===next.revision_id)definition.identity.name='Stronger keeper';
  return {world_id:world,draft_id:draft,locator:revision===next.revision_id?next:base,
    resource:{statblock_id:base.statblock_id,revision_id:revision,definition} as OpenSavedMechanicsVersion['resource']};
}
beforeEach(()=>{
  vi.resetAllMocks();tourReadings.clear();localStorage.clear();
  outcome={operation_id:'22222222-2222-4222-8222-222222222222',state:'committed',base,result:next,refusal_code:null,change_summary:'Stronger',created_at:'2026-10-22T00:00:00Z'};
  vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue(page());
  vi.mocked(api.openSavedMechanicsVersion).mockImplementation(async(_d,_w,rev)=>opened(rev));
  vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'success',definition_digest:next.definition_digest,validation_receipt:{status:'valid',issues:[],definition_digest:next.definition_digest}} as Awaited<ReturnType<typeof api.validateStatblockDefinition>>);
});
afterEach(cleanup);
async function load(){await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));await screen.findByLabelText('Creature name');}
async function edit(){const name=screen.getByLabelText('Creature name');await userEvent.clear(name);await userEvent.type(name,'Stronger keeper');}
async function validate(){await userEvent.click(screen.getByRole('button',{name:'Validate new version'}));await waitFor(()=>expect((screen.getByRole('button',{name:'Save new version'}) as HTMLButtonElement).disabled).toBe(false));}

it('validates edited exact source and saves a successor without an encounter mutation',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
  render(<TourEncounterProvider scope={tourScope}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></TourEncounterProvider>);await load();await edit();
  expect((screen.getByRole('button',{name:'Save new version'}) as HTMLButtonElement).disabled).toBe(true);
  await validate();await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
  const [owner,body]=vi.mocked(api.saveMechanicsRevision).mock.calls[0]!;
  expect(owner).toBe(draft);expect(body.base).toEqual(base);expect(body.definition.identity.name).toBe('Stronger keeper');
  expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();
  expect(tourReadings.get('mechanics')?.observation).toMatchObject({origin:'acknowledged',observedAt:outcome.created_at,target:tourScope.plan,proof:{kind:'mechanics',sceneId:'scene',encounterId:'encounter',draftId:draft,operationId:body.operation_id,locator:next}});
});

it('recovers local edits for the same exact source after remount',async()=>{
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();first.unmount();
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('retains an unknown Save across remount and explicitly recovers the original key',async()=>{
  let id='';vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>{id=body.operation_id;throw new Error('lost acknowledgement');});
  vi.mocked(api.inspectMechanicsRevision).mockImplementation(async()=>({operation:{...outcome,operation_id:id,state:'outcome_unknown',result:null}}));
  vi.mocked(api.recoverMechanicsRevision).mockImplementation(async()=>({...outcome,operation_id:id}));
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText(/Save outcome is unknown/);first.unmount();
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(true);
  await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
  expect(api.recoverMechanicsRevision).toHaveBeenCalledWith(draft,world,id);expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);
});

it('does not treat an unrelated outcome as this Save acknowledgement',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockResolvedValue({...outcome,operation_id:'other'});
  vi.mocked(api.inspectMechanicsRevision).mockRejectedValue(new Error('unavailable'));
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText(/Save outcome could not be checked/);expect(screen.queryByText(/New mechanics version saved/)).toBeNull();
  expect((screen.getByRole('button',{name:'Save new version'}) as HTMLButtonElement).disabled).toBe(true);
});


it('pages history metadata without rereading mechanics or replacing dirty edits',async()=>{
  vi.mocked(api.listSavedMechanicsVersions).mockResolvedValueOnce({...page(),next_offset:50}).mockResolvedValue(page());
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();
  await userEvent.click(screen.getByRole('button',{name:'More saved versions'}));
  await waitFor(()=>expect(api.listSavedMechanicsVersions).toHaveBeenCalledWith(draft,world,50));
  expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
});

it('keeps independent browser writers from overwriting each other’s recovered edits',async()=>{
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();
  const firstWriter=sessionStorage.getItem('dmb-manual-mechanics-writer')!;first.unmount();sessionStorage.removeItem('dmb-manual-mechanics-writer');
  const second=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).not.toBe('Stronger keeper');
  second.unmount();sessionStorage.setItem('dmb-manual-mechanics-writer',firstWriter);
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
});

it('does not unlock an absent Save until explicit recovery fences the original request',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockRejectedValue(new Error('request interrupted'));
  vi.mocked(api.inspectMechanicsRevision).mockResolvedValue({operation:null});
  vi.mocked(api.recoverMechanicsRevision).mockResolvedValue(null);
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText(/Save has no durable result yet/);
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(true);
  await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));
  await screen.findByText(/Save was safely canceled before dispatch/);
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(false);
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
});

it('reports unavailable validation without blaming or discarding edited mechanics',async()=>{
  vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'failure',failure_category:'downstream_timeout',failure_message:'timeout'});
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();
  await userEvent.click(screen.getByRole('button',{name:'Validate new version'}));
  await screen.findByText('Mechanics validation is unavailable. Your edits are retained; try again when it is available.');
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(false);
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});


it('shows actionable producer issues and clears them when mechanics change',async()=>{
  vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'success',validation_receipt:{status:'invalid',issues:[{code:'HP_DISPLAYED_AVERAGE_MISMATCH',severity:'error',field_path:'vitality.hit_points.displayed_average',message:'Displayed HP average does not match the typed dice formula.'}]}} as Awaited<ReturnType<typeof api.validateStatblockDefinition>>);
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  await userEvent.click(screen.getByRole('button',{name:'Validate new version'}));
  expect((await screen.findByRole('list',{name:'Mechanics validation issues'})).textContent).toContain('Displayed HP average does not match the typed dice formula.');
  expect(screen.getByRole('list',{name:'Mechanics validation issues'}).textContent).toContain('vitality.hit_points.displayed_average');
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();await edit();
  expect(screen.queryByRole('list',{name:'Mechanics validation issues'})).toBeNull();
});
