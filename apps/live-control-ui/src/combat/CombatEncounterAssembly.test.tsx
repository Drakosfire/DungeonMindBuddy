import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act, cleanup } from '@testing-library/react';
import * as mechanicsApi from './combatApi';
import type { WorldMechanicsAssociation } from '../api/worldMechanicsTypes';
import type { AssociatedCombatMechanicsSnapshot as CombatMechanicsSnapshot } from './combatTypes';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import * as api from '../api/liveApi';
import { CombatEncounterAssembly } from './CombatEncounterAssembly';
import type { ManagedWorldGraphProjectionResponse } from '../api/types';
const world = {managedWorldId:'elderwyld', nativeWorldId:'native-world', bindingVersion:2,
  projection:{snapshot:{worldId:'native-world',revisionId:'revision-a',scopeMode:'world'},nodes:[
    {nodeId:'npc-a',label:'World Scout',kind:'npc',role:'npc',aliases:['Scout']},
    {nodeId:'location-a',label:'Scout Camp',kind:'location',role:'location',aliases:[]},
  ]}} as ManagedWorldGraphProjectionResponse;
beforeEach(() => {vi.spyOn(api, 'listWorldMechanicsAssociations').mockResolvedValue([]);});
afterEach(() => {cleanup();vi.restoreAllMocks();});
function mount(disabled = false, remainingSlots = 100) {
  const onAdd = vi.fn();
  const view = render(<CombatEncounterAssembly worldId="elderwyld" disabled={disabled} remainingSlots={remainingSlots} onAdd={onAdd} />);
  fireEvent.click(screen.getByText('Add combatants'));
  return {...view,onAdd};
}
it('adds independent grouped manual actors to the draft without fetching or inventing mechanics', async () => {
  const read=vi.spyOn(api,'postManagedWorldGraphProjection');const {onAdd}=mount();
  await userEvent.type(screen.getByLabelText('Combatant name'),'Scout');
  fireEvent.change(screen.getByLabelText('Combatant copies'),{target:{value:'2'}});
  await userEvent.selectOptions(screen.getByLabelText('Combatant team'),'ally');
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  const [actors,group]=onAdd.mock.calls[0];
  expect(actors).toHaveLength(2);expect(actors[0].id).not.toBe(actors[1].id);
  expect(actors[0]).toMatchObject({name:'Scout 1',team:'ally',source:'manual',world_identity:null,ac:null,hp:null,max_hp:null,init:null});
  expect(group.member_ids).toEqual(actors.map((actor: {id:string})=>actor.id));expect(read).not.toHaveBeenCalled();
});
it('requires explicit World selection, searches locally and stores exact identity without inferred mechanics', async () => {
  const read=vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(world);const {onAdd}=mount();
  await userEvent.click(screen.getByRole('button',{name:'Find World creatures'}));
  await screen.findByRole('button',{name:'World Scout npc · World · npc-a'});
  expect(screen.queryByRole('button',{name:'Scout Camp location'})).not.toBeInTheDocument();
  expect(screen.getByLabelText('Combatant name')).toHaveValue('');
  await userEvent.type(screen.getByLabelText('Search World creatures'),'Scout');
  await userEvent.click(screen.getByRole('button',{name:'World Scout npc · World · npc-a'}));
  await userEvent.type(screen.getByLabelText('Combatant HP'),'18');
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  expect(read).toHaveBeenCalledTimes(1);
  expect(onAdd.mock.calls[0][0][0]).toMatchObject({hp:18,max_hp:18,ac:null,source:'manual',world_identity:{
    managed_world_id:'elderwyld',native_world_id:'native-world',binding_version:2,graph_revision_id:'revision-a',node_id:'npc-a',label:'World Scout'}});
});
it('ignores a pending discovery from an unmounted World/encounter', async () => {
  let resolve!: (value: ManagedWorldGraphProjectionResponse)=>void;
  vi.spyOn(api,'postManagedWorldGraphProjection').mockReturnValue(new Promise(r=>{resolve=r}));
  const {unmount}=mount();await userEvent.click(screen.getByRole('button',{name:'Find World creatures'}));unmount();
  mount();resolve(world);await waitFor(()=>expect(screen.queryByRole('button',{name:'World Scout npc · World · npc-a'})).not.toBeInTheDocument());
});
it('refuses a foreign projection and preserves manually entered name', async () => {
  vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue({...world,managedWorldId:'other-world'});
  mount();await userEvent.type(screen.getByLabelText('Combatant name'),'My PC');
  await userEvent.click(screen.getByRole('button',{name:'Find World creatures'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('World identity could not be verified');
  expect(screen.getByLabelText('Combatant name')).toHaveValue('My PC');
});
it('prevents assembly while the host is saving or replacing a draft', () => {
  mount(true);expect(screen.getByRole('button',{name:'Find World creatures'})).toBeDisabled();
  expect(screen.getByLabelText('Combatant name')).toBeDisabled();expect(screen.getByRole('button',{name:'Add to encounter draft'})).toBeDisabled();
});

it.each([
  ['Combatant initiative','1000','Initiative must be'], ['Combatant HP','1000000','HP must be'],
  ['Combatant AC','1000000','AC must be'], ['Combatant HP','-1','HP must be'],
  ['Combatant name','x'.repeat(160),'including any copy number'],
])('rejects inherited schema violations before draft append: %s', async (label,value,message) => {
  const {onAdd}=mount();fireEvent.change(screen.getByLabelText('Combatant name'),{target:{value:'Scout'}});
  if(label==='Combatant name') fireEvent.change(screen.getByLabelText('Combatant copies'),{target:{value:'2'}});
  fireEvent.change(screen.getByLabelText(label),{target:{value}});
  expect(screen.getByRole('button',{name:'Add to encounter draft'})).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent(message);expect(onAdd).not.toHaveBeenCalled();
});
it('keeps copies within the remaining owning draft capacity', () => {
  mount(false,1);fireEvent.change(screen.getByLabelText('Combatant name'),{target:{value:'Scout'}});
  fireEvent.change(screen.getByLabelText('Combatant copies'),{target:{value:'2'}});
  expect(screen.getByRole('button',{name:'Add to encounter draft'})).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent('between 1 and 1');
});
it('distinguishes same-name World identities by campaign and exact node', async () => {
  vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue({...world,projection:{...world.projection,nodes:[
    {...world.projection.nodes[0],campaignScope:'campaign-one'},
    {...world.projection.nodes[0],nodeId:'npc-b',campaignScope:'campaign-two'},
  ]}});
  const {onAdd}=mount();await userEvent.click(screen.getByRole('button',{name:'Find World creatures'}));
  await userEvent.click(await screen.findByRole('button',{name:'World Scout npc · campaign-two · npc-b'}));
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  expect(onAdd.mock.calls[0][0][0].world_identity).toMatchObject({node_id:'npc-b',campaign_scope:'campaign-two'});
});


const associated = {association_id:'association-one',version:1,request:{target:{node_id:'npc-a',managed_world_id:'elderwyld'}}} as WorldMechanicsAssociation;
const mechanics = {association_id:'association-one',association_version:1,
  target:{managed_world_id:'elderwyld',native_world_id:'native-world',binding_version:2,graph_revision_id:'revision-a',node_id:'npc-a',label:'World Scout',kind:'npc',role:'npc',campaign_scope:null},
  resource:{definition:{identity:{name:'Saved Scout'}}},snapshot_digest:'sha256:verified'} as CombatMechanicsSnapshot;
async function selectAssociated() {
  vi.mocked(api.listWorldMechanicsAssociations).mockResolvedValue([associated]);
  vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(world);
  const mounted=mount();await userEvent.click(screen.getByRole('button',{name:'Find World creatures'}));
  await userEvent.click(await screen.findByRole('button',{name:'World Scout npc · World · npc-a'}));
  return mounted;
}
it('loads mechanics only explicitly and copies exact snapshots without inferring tracker stats',async()=>{
  const preview=vi.spyOn(mechanicsApi,'previewWorldCombatMechanics').mockResolvedValue(mechanics);
  const {onAdd}=await selectAssociated();expect(preview).not.toHaveBeenCalled();
  await userEvent.type(screen.getByLabelText('Search World creatures'),'Scout');
  await userEvent.click(screen.getByRole('button',{name:'Load associated mechanics'}));
  await screen.findByText('Exact saved mechanics loaded. Tracker AC and HP stay manual.');
  fireEvent.change(screen.getByLabelText('Combatant copies'),{target:{value:'2'}});
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  const actors=onAdd.mock.calls[0][0];expect(actors).toHaveLength(2);
  expect(actors[0].id).not.toEqual(actors[1].id);
  expect(actors[0].mechanics_snapshot).toEqual(mechanics);expect(actors[1].mechanics_snapshot).toEqual(mechanics);
  expect(actors[0]).toMatchObject({ac:null,hp:null,max_hp:null,init:null,source:'manual'});
  expect(preview).toHaveBeenCalledTimes(1);expect(api.postManagedWorldGraphProjection).toHaveBeenCalledTimes(1);
  expect(api.listWorldMechanicsAssociations).toHaveBeenCalledTimes(1);
});
it('removes loaded mechanics before adding a manual actor',async()=>{
  vi.spyOn(mechanicsApi,'previewWorldCombatMechanics').mockResolvedValue(mechanics);
  const {onAdd}=await selectAssociated();await userEvent.click(screen.getByRole('button',{name:'Load associated mechanics'}));
  await userEvent.click(await screen.findByRole('button',{name:'Remove loaded mechanics'}));
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  expect(onAdd.mock.calls[0][0][0].mechanics_snapshot).toBeNull();
});
it('discards a late mechanics preview after removing the selected identity',async()=>{
  let finish!:(snapshot:CombatMechanicsSnapshot)=>void;
  vi.spyOn(mechanicsApi,'previewWorldCombatMechanics').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  const {onAdd}=await selectAssociated();await userEvent.click(screen.getByRole('button',{name:'Load associated mechanics'}));
  expect(screen.getByRole('button',{name:'Add to encounter draft'})).toBeDisabled();
  await userEvent.click(screen.getByRole('button',{name:'Use name only'}));
  await act(async()=>finish(mechanics));expect(screen.queryByText('Exact saved mechanics loaded. Tracker AC and HP stay manual.')).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));expect(onAdd.mock.calls[0][0][0]).toMatchObject({world_identity:null,mechanics_snapshot:null});
});
it('discards a late preview on World or encounter unmount',async()=>{
  let finish!:(snapshot:CombatMechanicsSnapshot)=>void;
  vi.spyOn(mechanicsApi,'previewWorldCombatMechanics').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  const mounted=await selectAssociated();await userEvent.click(screen.getByRole('button',{name:'Load associated mechanics'}));
  mounted.unmount();mount();await act(async()=>finish(mechanics));
  expect(screen.queryByText('Exact saved mechanics loaded. Tracker AC and HP stay manual.')).toBeNull();
});

const acceptedChoice = {draft_id:'draft-accepted',draft_version:2,name:'Saved Wolf'};
const directMechanics = {origin:'world_accepted_mechanics_v1',managed_world_id:'elderwyld',...acceptedChoice,
  resource:{definition:{identity:{name:'Saved Wolf'}}},snapshot_digest:'sha256:verified'} as unknown as import('./combatTypes').AcceptedCombatMechanicsSnapshot;
it('selects accepted mechanics without World discovery and adds independent copies',async()=>{
  const graph=vi.spyOn(api,'postManagedWorldGraphProjection');
  vi.spyOn(mechanicsApi,'listAcceptedCombatMechanics').mockResolvedValue({choices:[acceptedChoice],nextOffset:null});
  const preview=vi.spyOn(mechanicsApi,'previewAcceptedCombatMechanics').mockResolvedValue(directMechanics);
  const {onAdd}=mount();expect(preview).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'Find saved mechanics'}));
  await userEvent.click(await screen.findByRole('button',{name:'Saved Wolf Saved mechanics · draft 2'}));
  await screen.findByText('Exact saved mechanics loaded. Tracker AC and HP stay manual.');
  fireEvent.change(screen.getByLabelText('Combatant copies'),{target:{value:'2'}});
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  const actors=onAdd.mock.calls[0][0];expect(actors).toHaveLength(2);
  expect(actors[0].id).not.toBe(actors[1].id);
  expect(actors[0]).toMatchObject({world_identity:null,mechanics_snapshot:directMechanics,hp:null,ac:null});
  expect(actors[1].mechanics_snapshot).toEqual(directMechanics);expect(graph).not.toHaveBeenCalled();
  expect(preview).toHaveBeenCalledWith('elderwyld',{draft_id:'draft-accepted',draft_version:2});
});
it('rejects foreign or stale direct previews without changing entered name',async()=>{
  vi.spyOn(mechanicsApi,'listAcceptedCombatMechanics').mockResolvedValue({choices:[acceptedChoice],nextOffset:null});
  vi.spyOn(mechanicsApi,'previewAcceptedCombatMechanics').mockResolvedValue({...directMechanics,draft_version:3});
  const {onAdd}=mount();fireEvent.change(screen.getByLabelText('Combatant name'),{target:{value:'My PC'}});
  await userEvent.click(screen.getByRole('button',{name:'Find saved mechanics'}));
  await userEvent.click(await screen.findByRole('button',{name:'Saved Wolf Saved mechanics · draft 2'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('did not match');
  expect(screen.getByLabelText('Combatant name')).toHaveValue('My PC');
  await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
  expect(onAdd.mock.calls[0][0][0].mechanics_snapshot).toBeNull();
});
it('ignores direct preview after unmount and pages saved drafts only on request',async()=>{
  const list=vi.spyOn(mechanicsApi,'listAcceptedCombatMechanics').mockResolvedValueOnce({choices:[],nextOffset:20})
    .mockResolvedValueOnce({choices:[acceptedChoice],nextOffset:null});
  let finish!:(snapshot:import('./combatTypes').AcceptedCombatMechanicsSnapshot)=>void;
  vi.spyOn(mechanicsApi,'previewAcceptedCombatMechanics').mockReturnValue(new Promise(resolve=>{finish=resolve}));
  const mounted=mount();await userEvent.click(screen.getByRole('button',{name:'Find saved mechanics'}));
  await userEvent.click(await screen.findByRole('button',{name:'More saved drafts'}));
  expect(list).toHaveBeenLastCalledWith('elderwyld',20);
  await userEvent.click(await screen.findByRole('button',{name:'Saved Wolf Saved mechanics · draft 2'}));
  expect(screen.getByRole('button',{name:'Add to encounter draft'})).toBeDisabled();
  mounted.unmount();mount();await act(async()=>finish(directMechanics));
  expect(screen.queryByText('Exact saved mechanics loaded. Tracker AC and HP stay manual.')).toBeNull();
});
