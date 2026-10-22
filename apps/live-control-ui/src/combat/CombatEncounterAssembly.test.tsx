import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '../api/liveApi';
import { CombatEncounterAssembly } from './CombatEncounterAssembly';
import type { ManagedWorldGraphProjectionResponse } from '../api/types';
const world = {managedWorldId:'elderwyld', nativeWorldId:'native-world', bindingVersion:2,
  projection:{snapshot:{worldId:'native-world',revisionId:'revision-a',scopeMode:'world'},nodes:[
    {nodeId:'npc-a',label:'World Scout',kind:'npc',role:'npc',aliases:['Scout']},
    {nodeId:'location-a',label:'Scout Camp',kind:'location',role:'location',aliases:[]},
  ]}} as ManagedWorldGraphProjectionResponse;
afterEach(() => vi.restoreAllMocks());
function mount(disabled = false) {
  const onAdd = vi.fn();
  const view = render(<CombatEncounterAssembly worldId="elderwyld" disabled={disabled} onAdd={onAdd} />);
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
  await screen.findByRole('button',{name:'World Scout npc'});
  expect(screen.queryByRole('button',{name:'Scout Camp location'})).not.toBeInTheDocument();
  expect(screen.getByLabelText('Combatant name')).toHaveValue('');
  await userEvent.type(screen.getByLabelText('Search World creatures'),'Scout');
  await userEvent.click(screen.getByRole('button',{name:'World Scout npc'}));
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
  mount();resolve(world);await waitFor(()=>expect(screen.queryByRole('button',{name:'World Scout npc'})).not.toBeInTheDocument());
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
