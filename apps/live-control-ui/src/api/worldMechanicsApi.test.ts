import { afterEach, expect, it, vi } from "vitest";
import { associateWorldMechanics, listWorldMechanicsAssociations, listWorldCreatures, setNativeGraphAccessToken } from "./liveApi";
import type { AssociateWorldMechanicsRequest } from "./worldMechanicsTypes";
afterEach(()=>{vi.restoreAllMocks();setNativeGraphAccessToken("");});
it("authenticates exact association reads and writes without altering the request",async()=>{
  setNativeGraphAccessToken("association-test-token");
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(async()=>Response.json({fixture:true}));
  const request={request_id:"fixed-key",draft_id:"draft-one",expected_draft_version:3,expected_version:0,
    target:{managed_world_id:"elderwyld"}} as AssociateWorldMechanicsRequest;
  await listWorldMechanicsAssociations("elderwyld");await associateWorldMechanics("elderwyld",request);
  expect(fetch).toHaveBeenCalledTimes(2);
  for(const [url,init] of fetch.mock.calls){
    expect(String(url)).toBe("/api/live/world-mechanics/associations?world_id=elderwyld");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer association-test-token");
    expect(init?.credentials).toBe("same-origin");expect(init?.redirect).toBe("error");
  }
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual(request);
});

const native = {schema:'dmb_native_world_creatures_v1',managed_world_id:'elderwyld',native_world_id:'native',binding_version:2,revision_id:'rev:one',completeness:'complete',targets:[
  {managed_world_id:'elderwyld',native_world_id:'native',binding_version:2,graph_revision_id:'rev:one',node_id:'entity:one',label:'Keeper',kind:'npc',role:'',campaign_scope:'c1'},
]};
it.each(['npc','character','creature'])('uses authenticated native %s reads without a classic projection request',async kind=>{
  setNativeGraphAccessToken('native-test-token');
  const packet=structuredClone(native);packet.targets[0].kind=kind;
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(packet));
  expect(await listWorldCreatures('elderwyld')).toEqual(packet);
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url,init]=fetch.mock.calls[0];
  expect(url).toBe('/api/live/world-mechanics/associations/creatures?world_id=elderwyld');
  expect(init?.method??'GET').toBe('GET');
  expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer native-test-token');
});
it.each(['world','revision','binding','kind','duplicate','coverage'])('refuses a malformed native %s selection',async change=>{
  setNativeGraphAccessToken('native-test-token');
  const view=structuredClone(native);
  if(change==='world')view.targets[0].managed_world_id='foreign';
  if(change==='revision')view.targets[0].graph_revision_id='rev:other';
  if(change==='binding')view.targets[0].binding_version++;
  if(change==='kind')view.targets[0].kind='location';
  if(change==='duplicate')view.targets.push({...view.targets[0]});
  if(change==='coverage')view.completeness='unknown';
  vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(view));
  await expect(listWorldCreatures('elderwyld')).rejects.toThrow('Native creature selection did not match');
});
