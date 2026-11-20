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

it('pages the existing World draft list and keeps only saved World mechanics without provider reads',async()=>{
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({drafts:[
    {schema:'dmb_threat_draft_summary_v2',draft_id:'saved',version:2,world_id:'elderwyld',name:'Wolf',workflow_state:'mechanics_saved'},
    {schema:'dmb_threat_draft_summary_v2',draft_id:'unsaved',version:1,world_id:'elderwyld',name:'Draft',workflow_state:'draft'},
    {schema:'dmb_threat_draft_summary_v1',draft_id:'campaign',version:2,world_id:'elderwyld',name:'Campaign',workflow_state:'mechanics_saved'},
  ],offset:20,limit:20,total:50}));
  const {listAcceptedCombatMechanics}=await import('./combatApi');
  expect(await listAcceptedCombatMechanics('elderwyld',20)).toEqual({choices:[{draft_id:'saved',draft_version:2,name:'Wolf'}],nextOffset:40});
  expect(fetch).toHaveBeenCalledTimes(1);expect(fetch.mock.calls[0][0]).toContain('world_id=elderwyld&limit=20&offset=20');
});
it('refuses a foreign draft catalog and sends exact direct preview selection once',async()=>{
  setNativeGraphAccessToken('synthetic-combat-test-credential');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({drafts:[{world_id:'foreign'}],offset:0,limit:20,total:1}))
    .mockResolvedValueOnce(Response.json({detail:'Saved draft changed'},{status:409}));
  const {listAcceptedCombatMechanics,previewAcceptedCombatMechanics}=await import('./combatApi');
  await expect(listAcceptedCombatMechanics('elderwyld')).rejects.toThrow('another World');
  const selection={draft_id:'exact-draft',draft_version:2};
  await expect(previewAcceptedCombatMechanics('elderwyld',selection)).rejects.toThrow('Saved draft changed');
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual(selection);
  expect(fetch.mock.calls[1][1]?.headers).toMatchObject({Authorization:'Bearer synthetic-combat-test-credential'});
});
