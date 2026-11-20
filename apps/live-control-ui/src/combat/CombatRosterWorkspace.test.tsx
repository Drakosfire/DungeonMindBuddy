import {useState} from 'react';
import {cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, expect, it, vi} from 'vitest';
import fixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {CombatEncounterDraft, CombatEntity, CombatMechanicsSnapshot} from './combatTypes';
import {CombatRosterWorkspace, type CombatProjectionControl} from './CombatRosterWorkspace';
import * as combatApi from './combatApi';

afterEach(() => {cleanup(); vi.restoreAllMocks();});
function draft(): CombatEncounterDraft {
  return {schema:'dmb_combat_encounter_draft_v1',title:'Bridge',round:1,
    active_turn_entity_id:null,round_start_entity_id:null,queue_model:'circular_barrel_v1',groups:[],provenance:[],
    entities:[{id:'brute',name:'Bridge brute',defeated:false,mechanics_snapshot:{resource:structuredClone(fixture)} as unknown as CombatMechanicsSnapshot}] as CombatEntity[]};
}
function Row({entity, hidden, projection}: {entity:CombatEntity;hidden:boolean;projection:CombatProjectionControl}) {
  const [damage,setDamage] = useState('1');
  return <tr hidden={hidden}><td colSpan={8}>
    <input aria-label="Staged damage" value={damage} onChange={event=>setDamage(event.target.value)}/>
    <button type="button" aria-pressed={projection.selected} onClick={event=>projection.open(event.currentTarget)}>Project {entity.name}</button>
  </td></tr>;
}
const row=(entity:CombatEntity,hidden:boolean,projection:CombatProjectionControl)=><Row key={entity.id} entity={entity} hidden={hidden} projection={projection}/>;
function board(value:CombatEncounterDraft,key='world:prepared') {
  return <CombatRosterWorkspace key={key} draft={value} disabled={false} onToggleGroup={vi.fn()} renderRow={row}/>;
}

it('keeps the exact source beside stable editable rows without fetching latest mechanics', async()=>{
  const fetch=vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('No provider'));
  render(board(draft()));
  const input=screen.getByRole('textbox',{name:'Staged damage'});
  await userEvent.clear(input);await userEvent.type(input,'7');
  const trigger=screen.getByRole('button',{name:'Project Bridge brute'});
  await userEvent.click(trigger);
  const panel=screen.getByRole('complementary',{name:'Projected statblock for Bridge brute'});
  expect(panel).toHaveFocus();
  expect(await within(panel).findByRole('heading',{name:'Ironhide Brute'})).toBeInTheDocument();
  expect(within(panel).getByText('68 (8d10+24)')).toBeInTheDocument();
  expect(input).toBe(screen.getByRole('textbox',{name:'Staged damage'}));
  await userEvent.clear(input);await userEvent.type(input,'9');
  await userEvent.click(within(panel).getByRole('button',{name:'Close projected statblock'}));
  expect(trigger).toHaveFocus();expect(input).toHaveValue('9');
  expect(screen.queryByRole('complementary')).toBeNull();expect(fetch).not.toHaveBeenCalled();
});

it('resolves explicit source replacement from the selected actor rather than a stale copied snapshot',async()=>{
  const initial=draft();const view=render(board(initial));
  await userEvent.click(screen.getByRole('button',{name:'Project Bridge brute'}));
  expect(await screen.findByRole('heading',{name:'Ironhide Brute'})).toBeInTheDocument();
  const replacement=structuredClone(initial);replacement.entities[0].mechanics_snapshot!.resource.definition.identity.name='Accepted replacement';
  view.rerender(board(replacement));
  expect(await screen.findByRole('heading',{name:'Accepted replacement'})).toBeInTheDocument();
  expect(screen.queryByRole('heading',{name:'Ironhide Brute'})).toBeNull();
});

it('keeps roster focus when Save returns an equivalent statblock snapshot', async () => {
  const initial = draft();
  const view = render(board(initial));
  await userEvent.click(screen.getByRole('button', {name: 'Project Bridge brute'}));
  const input = screen.getByRole('textbox', {name: 'Staged damage'});
  await userEvent.click(input);
  view.rerender(board(structuredClone(initial)));
  expect(input).toHaveFocus();
  expect(screen.getByRole('complementary')).toBeVisible();
});

it('projects the exact registered corpus text independently of turn and tracker edits', async () => {
  const value = draft();
  const sourceId = 'artifact:worldbuilding:the-registered-source';
  const sha = 'a'.repeat(64);
  Object.assign(value.entities[0], {
    source: 'imported', mechanics_snapshot: null,
    statblock_artifact_id: sourceId, corpus_fingerprint: sha,
  });
  const request = vi.spyOn(combatApi, 'getWorldCombatCorpusSheet').mockResolvedValue('# Original sheet\n\nRecorded abilities');
  const props = {disabled: false, onToggleGroup: vi.fn(), renderRow: row, corpusScope: {worldId: 'elderwyld', encounterId: 'bridge'}};
  const view = render(<CombatRosterWorkspace draft={value} {...props}/>);
  const trigger = screen.getByRole('button', {name: 'Project Bridge brute'});
  await userEvent.click(trigger);
  const panel = screen.getByRole('complementary');
  expect(await within(panel).findByRole('heading', {name: 'Original sheet'})).toBeVisible();
  expect(request).toHaveBeenCalledWith('elderwyld', 'bridge', 'brute', sourceId, sha, expect.any(AbortSignal));

  view.rerender(<CombatRosterWorkspace draft={{...value, round: 2}} {...props}/>);
  expect(within(panel).getByText('Recorded abilities')).toBeVisible();
  expect(request).toHaveBeenCalledTimes(1);
  await userEvent.click(within(panel).getByRole('button', {name: 'Close projected statblock'}));
  expect(trigger).toHaveFocus();
});

it('retires a removed or sourceless selection and does not revive it when an ID returns',async()=>{
  const initial=draft();const view=render(board(initial));
  await userEvent.click(screen.getByRole('button',{name:'Project Bridge brute'}));
  view.rerender(board({...initial,entities:[]}));expect(screen.queryByRole('complementary')).toBeNull();
  view.rerender(board(initial));expect(screen.queryByRole('complementary')).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Project Bridge brute'}));
  view.rerender(board({...initial,entities:[{...initial.entities[0],mechanics_snapshot:null}]}));
  expect(screen.queryByRole('complementary')).toBeNull();
  view.rerender(board(initial));expect(screen.queryByRole('complementary')).toBeNull();
});

it('keeps defeated source access but clears selection when the full encounter scope changes',async()=>{
  const initial=draft();initial.entities[0].defeated=true;const view=render(board(initial));
  await userEvent.click(screen.getByRole('button',{name:'Project Bridge brute'}));
  expect(screen.getByRole('complementary')).toBeInTheDocument();
  view.rerender(board(initial,'other-world:run:scene'));
  expect(screen.queryByRole('complementary')).toBeNull();
  expect(screen.getByRole('button',{name:'Project Bridge brute'})).toHaveAttribute('aria-pressed','false');
});

it('keeps selection through group collapse and returns close focus outside hidden rows',async()=>{
  const initial=draft();initial.groups=[{group_key:'guards',label:'Guards',statblock_path:null,member_ids:['brute'],collapsed:false}];
  const view=render(board(initial));await userEvent.click(screen.getByRole('button',{name:'Project Bridge brute'}));
  view.rerender(board({...initial,groups:[{...initial.groups[0],collapsed:true}]}));
  expect(screen.getByRole('complementary')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Project Bridge brute'})).toBeNull();
  await userEvent.click(screen.getByRole('button',{name:'Close projected statblock'}));
  expect(screen.getByRole('region',{name:'Combat roster and statblock'})).toHaveFocus();
});

it('moves the selected source into a modal and restores roster focus on cancel', async () => {
  const nativeDialog = HTMLDialogElement.prototype;
  const showModal = Object.getOwnPropertyDescriptor(nativeDialog, 'showModal');
  const close = Object.getOwnPropertyDescriptor(nativeDialog, 'close');
  Object.defineProperties(nativeDialog, {
    showModal: {configurable: true, value(this: HTMLDialogElement) { this.open = true; }},
    close: {configurable: true, value(this: HTMLDialogElement) { this.open = false; }},
  });
  try {
    render(board(draft()));
    const trigger = screen.getByRole('button', {name: 'Project Bridge brute'});
    await userEvent.click(trigger);
    await userEvent.click(screen.getByRole('button', {name: 'Open as modal'}));
    const modal = screen.getByRole('dialog', {name: 'Projected statblock for Bridge brute'});
    expect(await within(modal).findByRole('heading', {name: 'Ironhide Brute'})).toBeVisible();
    await userEvent.click(within(modal).getByRole('button', {name: 'Dock statblock'}));
    expect(screen.getByRole('complementary')).toHaveFocus();
    await userEvent.click(screen.getByRole('button', {name: 'Open as modal'}));
    const reopened = screen.getByRole('dialog');
    fireEvent(reopened, new Event('cancel', {cancelable: true}));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(trigger).toHaveFocus();
  } finally {
    if (showModal) Object.defineProperty(nativeDialog, 'showModal', showModal);
    else Reflect.deleteProperty(nativeDialog, 'showModal');
    if (close) Object.defineProperty(nativeDialog, 'close', close);
    else Reflect.deleteProperty(nativeDialog, 'close');
  }
});
