import { afterEach, expect, it, vi } from 'vitest';
import { listWorldCombatEncounters, saveWorldCombatEncounter } from './combatApi';
import { setNativeGraphAccessToken } from '../api/liveApi';
import type { CombatEncounterDraft } from './combatTypes';
afterEach(() => {vi.restoreAllMocks(); setNativeGraphAccessToken(null);});
it('uses native authorization for Combat reads and preserves exact Save/CAS intent without retries', async () => {
  setNativeGraphAccessToken('synthetic-combat-test-credential');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json([]));
  await listWorldCombatEncounters('elderwyld');
  expect(fetch.mock.calls[0][1]?.headers).toMatchObject({Authorization:'Bearer synthetic-combat-test-credential'});
  fetch.mockResolvedValueOnce(Response.json({detail:'changed since it was opened'},{status:409}));
  const draft={title:'Draft',entities:[]} as unknown as CombatEncounterDraft;
  await expect(saveWorldCombatEncounter('elderwyld','encounter-a',7,draft)).rejects.toThrow('changed since it was opened');
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual({expected_revision:7,draft});
  expect(fetch.mock.calls[1][1]?.headers).toMatchObject({Authorization:'Bearer synthetic-combat-test-credential'});
});

it('authenticates exact mechanics preview and sends selected identity unchanged without retry', async () => {
  setNativeGraphAccessToken('synthetic-combat-test-credential');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({detail:'Exact mechanics unavailable'},{status:503}));
  const {previewWorldCombatMechanics}=await import('./combatApi');
  const selection={association_id:'association-one',association_version:3,target:{managed_world_id:'elderwyld',node_id:'npc-one'}} as import('./combatTypes').CombatMechanicsSelection;
  await expect(previewWorldCombatMechanics('elderwyld',selection)).rejects.toThrow('Exact mechanics unavailable');
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toContain('/world-mechanics/preview?world_id=elderwyld');
  expect(fetch.mock.calls[0][1]?.headers).toMatchObject({Authorization:'Bearer synthetic-combat-test-credential'});
  expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(selection);
});
