import {worldCreatureChoiceKey} from '../api/worldMechanicsTypes';
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api/liveApi";
import type { ThreatDraftV2 } from "../api/types";
import type { AssociateWorldMechanicsRequest, AssociateWorldMechanicsResponse, WorldCreatureCatalog } from "../api/worldMechanicsTypes";
import { WorldMechanicsAssociationPanel } from "./WorldMechanicsAssociationPanel";

const locator = { provider:"dungeonmind",statblock_id:"sb_one",revision_id:"rev_one",
  contract:"dungeonmind.dungeonbuddy-statblocks",contract_version:"1.0.0",definition_digest:`sha256:${"a".repeat(64)}` } as const;
const draft = {schema:"dmb_threat_draft_v2",world_id:"elderwyld",draft_id:"9e02566a-c840-402b-8d22-61f6bee780c4",version:3,
  workflow_state:"mechanics_saved",accepted_mechanics_ref:{...locator,accepted_from_draft_version:2,accepted_from_candidate_id:"cand_one",accepted_at:"2026-10-22T00:00:00Z"}} as ThreatDraftV2;
const view:WorldCreatureCatalog = {schema:'dmb_native_world_creatures_v1',managed_world_id:'elderwyld',native_world_id:'world:opaque',binding_version:2,revision_id:'rev:head',completeness:'complete',targets:[
  {managed_world_id:'elderwyld',native_world_id:'world:opaque',binding_version:2,graph_revision_id:'rev:head',node_id:'node:one',label:'Keeper',kind:'npc',role:'',campaign_scope:null},
  {managed_world_id:'elderwyld',native_world_id:'world:opaque',binding_version:2,graph_revision_id:'rev:head',node_id:'node:two',label:'Keeper',kind:'npc',role:'',campaign_scope:null},
]};
function result(request:AssociateWorldMechanicsRequest):AssociateWorldMechanicsResponse {
  return {replayed:false,association:{association_id:"association-one",request,request_digest:"b".repeat(64),version:request.expected_version+1,
    previous_association_id:request.expected_version ? "previous" : null,
    proof:{locator:request.locator,origin_locator:locator,origin_acceptance_operation_id:"accept-one",revision_operation_id:request.locator.revision_id===locator.revision_id?null:"revision-one"},actor:"gm",created_at:"2026-10-22T00:00:00Z"}};
}
const key=`dmb.worldMechanics.pending:${draft.world_id}:${draft.draft_id}`;
async function choose() {
  const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"Load creatures"}));
  await user.selectOptions(await screen.findByRole("combobox",{name:"World creature"}),worldCreatureChoiceKey(view.targets[1]));return user;
}
beforeEach(()=>{
  localStorage.clear();
  Object.defineProperty(navigator, "locks", {configurable: true, value: {
    request: vi.fn(async (_key: string, action: () => unknown) => action()),
  }});
  vi.spyOn(api,"getThreatDraft").mockResolvedValue(draft);
  vi.spyOn(api,"listWorldCreatures").mockResolvedValue(view);
  vi.spyOn(api,"listWorldMechanicsAssociations").mockResolvedValue([]);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

describe("World mechanics explicit association",()=>{
  it("does not read on mount and submits the selected exact node with accepted draft CAS",async()=>{
    const save=vi.spyOn(api,"associateWorldMechanics").mockImplementation(async(_,request)=>result(request));
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);
    expect(api.listWorldCreatures).not.toHaveBeenCalled();
    const user=await choose();expect(screen.queryByRole("option",{name:/Ferry/})).toBeNull();
    await user.click(screen.getByRole("button",{name:"Associate creature mechanics"}));
    await screen.findByText(/Mechanics associated with Keeper/);
    expect(save).toHaveBeenCalledTimes(1);
    expect(save.mock.calls[0][1]).toMatchObject({draft_id:draft.draft_id,expected_draft_version:3,expected_version:0,
      target:{node_id:"node:two",native_world_id:"world:opaque",binding_version:2,graph_revision_id:"rev:head"}});
    expect(api.listWorldCreatures).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(key)).toBeNull();
  });
  it("retains the exact request across lost acknowledgement and component reload",async()=>{
    const save=vi.spyOn(api,"associateWorldMechanics").mockRejectedValueOnce(new Error("Connection lost"))
      .mockImplementation(async(_,request)=>({...result(request),replayed:true}));
    const mounted=render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);const user=await choose();
    await user.click(screen.getByRole("button",{name:"Associate creature mechanics"}));
    await screen.findByRole("alert");const original=JSON.parse(localStorage.getItem(key)!);
    mounted.unmount();render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);
    await user.click(screen.getByRole("button",{name:"Resume same association"}));
    await screen.findByText(/Association receipt recovered for Keeper/);
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(save.mock.calls[1][1]).toEqual(original);
    expect(save.mock.calls[0][1]).toEqual(original);
    expect(api.listWorldCreatures).toHaveBeenCalledTimes(1);
  });
  it("requires refresh after a definitive stale conflict",async()=>{
    vi.spyOn(api,"associateWorldMechanics").mockRejectedValue(new api.LiveApiError("World changed",409));
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);const user=await choose();
    await user.click(screen.getByRole("button",{name:"Associate creature mechanics"}));
    await user.click(await screen.findByRole("button",{name:"Refresh after conflict"}));
    await waitFor(() => expect(screen.queryByRole("combobox")).toBeNull());expect(localStorage.getItem(key)).toBeNull();
    expect(api.associateWorldMechanics).toHaveBeenCalledTimes(1);
  });
  it("does not claim success for a mismatched response",async()=>{
    vi.spyOn(api,"associateWorldMechanics").mockImplementation(async(_,request)=>{
      const response=result(request);response.association.proof.locator={...locator,revision_id:"rev_wrong"};return response;
    });
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);const user=await choose();
    await user.click(screen.getByRole("button",{name:"Associate creature mechanics"}));
    await screen.findByRole("alert");expect(screen.queryByRole("status")).toBeNull();
    expect(localStorage.getItem(key)).not.toBeNull();
  });
  it("ignores a late success after changing World",async()=>{
    let finish!:(value:AssociateWorldMechanicsResponse)=>void;
    const save=vi.spyOn(api,"associateWorldMechanics").mockReturnValue(new Promise(resolve=>{finish=resolve;}));
    const mounted=render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);const user=await choose();
    await user.click(screen.getByRole("button",{name:"Associate creature mechanics"}));
    mounted.unmount();render(<WorldMechanicsAssociationPanel worldId="other-world" draftId={draft.draft_id} locator={locator}/>);
    await act(async()=>finish(result(save.mock.calls[0][1])));
    expect(screen.queryByRole("status")).toBeNull();expect(localStorage.getItem(key)).not.toBeNull();
  });
  it("refuses cross-World projection contents before selection",async()=>{
    vi.mocked(api.listWorldCreatures).mockRejectedValue(new TypeError("Native creature selection did not match the selected World."));
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);
    await userEvent.click(screen.getByRole("button",{name:"Load creatures"}));
    await screen.findByRole("alert");expect(screen.queryByRole("combobox")).toBeNull();
  });
  it("does not overwrite a competing reservation before POST", async () => {
    const save = vi.spyOn(api, "associateWorldMechanics");
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>); const user = await choose();
    const other = JSON.stringify({request_id: "other-view", draft_id: draft.draft_id});
    localStorage.setItem(key, other);
    await user.click(screen.getByRole("button", {name: "Associate creature mechanics"}));
    await screen.findByText(/Another view retained/);
    expect(save).not.toHaveBeenCalled(); expect(localStorage.getItem(key)).toBe(other);
  });
  it("preserves another pending request when an earlier POST succeeds", async () => {
    let finish!: (value: AssociateWorldMechanicsResponse) => void;
    const save = vi.spyOn(api, "associateWorldMechanics").mockReturnValue(new Promise(resolve => {finish = resolve;}));
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>); const user = await choose();
    await user.click(screen.getByRole("button", {name: "Associate creature mechanics"}));
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    const other = JSON.stringify({...save.mock.calls[0][1], request_id: "other-view"});
    localStorage.setItem(key, other);
    await act(async () => finish(result(save.mock.calls[0][1])));
    await screen.findByText(/Another view retained/);
    expect(localStorage.getItem(key)).toBe(other); expect(screen.queryByRole("status")).toBeNull();
  });
  it("does not clear a foreign request on stale conflict refresh", async () => {
    const save = vi.spyOn(api, "associateWorldMechanics").mockRejectedValue(new api.LiveApiError("World changed",409));
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>); const user = await choose();
    await user.click(screen.getByRole("button", {name: "Associate creature mechanics"}));
    const refresh = await screen.findByRole("button", {name: "Refresh after conflict"});
    const other = JSON.stringify({...save.mock.calls[0][1], request_id: "other-view"});
    localStorage.setItem(key, other); await user.click(refresh);
    await screen.findByText(/Another view retained/); expect(localStorage.getItem(key)).toBe(other);
  });
  it("does not reserve or POST after unmount while waiting for the lock", async () => {
    let acquire!: () => unknown;
    vi.mocked(navigator.locks.request).mockImplementation(((_key: string, action: () => unknown) =>
      new Promise((resolve, reject) => {acquire = () => {try {resolve(action());} catch (error) {reject(error);}};})) as typeof navigator.locks.request);
    const save = vi.spyOn(api, "associateWorldMechanics");
    const mounted = render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>); const user = await choose();
    await user.click(screen.getByRole("button", {name: "Associate creature mechanics"}));
    mounted.unmount(); await act(async () => {acquire();});
    expect(localStorage.getItem(key)).toBeNull(); expect(save).not.toHaveBeenCalled();
  });
  it("fails closed when browser locking is unavailable", async () => {
    Object.defineProperty(navigator, "locks", {configurable: true, value: undefined});
    const save = vi.spyOn(api, "associateWorldMechanics");
    render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>); const user = await choose();
    await user.click(screen.getByRole("button", {name: "Associate creature mechanics"}));
    await screen.findByText(/cannot safely retain/);
    expect(save).not.toHaveBeenCalled(); expect(localStorage.getItem(key)).toBeNull();
  });

});

it('ignores an old native read after the same host switches World in place',async()=>{
  let finish!:(value:WorldCreatureCatalog)=>void;
  vi.mocked(api.listWorldCreatures).mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  const mounted=render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);
  await userEvent.click(screen.getByRole('button',{name:'Load creatures'}));
  mounted.rerender(<WorldMechanicsAssociationPanel worldId="other-world" draftId={draft.draft_id} locator={locator}/>);
  await act(async()=>finish(view));
  expect(screen.queryByRole('combobox',{name:'World creature'})).toBeNull();
  expect(screen.getByRole('button',{name:'Load creatures'})).toBeEnabled();
});

it('preserves separate campaign choices for one actor instead of broadening scope',async()=>{
  vi.mocked(api.listWorldCreatures).mockResolvedValue({...view,targets:[
    {...view.targets[0],campaign_scope:'c1'}, {...view.targets[0],campaign_scope:'c2'},
  ]});
  const save=vi.spyOn(api,'associateWorldMechanics').mockImplementation(async(_,request)=>result(request));
  render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);
  await userEvent.click(screen.getByRole('button',{name:'Load creatures'}));
  await userEvent.selectOptions(await screen.findByRole('combobox',{name:'World creature'}),worldCreatureChoiceKey({...view.targets[0],campaign_scope:'c2'}));
  await userEvent.click(screen.getByRole('button',{name:'Associate creature mechanics'}));
  await waitFor(()=>expect(save).toHaveBeenCalledTimes(1));
  expect(save.mock.calls[0][1].target).toMatchObject({node_id:'node:one',campaign_scope:'c2'});
});


it('binds the displayed successor rather than the original accepted revision',async()=>{
  const selected={...locator,revision_id:'rev_portrait'};
  const save=vi.spyOn(api,'associateWorldMechanics').mockImplementation(async(_,request)=>result(request));
  render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={selected}/>);
  const user=await choose();await user.click(screen.getByRole('button',{name:'Associate creature mechanics'}));
  await screen.findByText(/Mechanics associated/);
  expect(save.mock.calls[0][1].locator).toEqual(selected);
});

it('looks up an old pending acknowledgement without posting or silently adding a locator',async()=>{
  const old={request_id:crypto.randomUUID(),draft_id:draft.draft_id,expected_draft_version:2,expected_version:0,target:view.targets[0]};
  const raw=JSON.stringify(old);localStorage.setItem(key,raw);
  const lookup=vi.spyOn(api,'findWorldMechanicsAssociationRequest').mockResolvedValue(null);
  const save=vi.spyOn(api,'associateWorldMechanics');
  render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator}/>);
  await userEvent.click(screen.getByRole('button',{name:'Check earlier association'}));
  await screen.findByText(/No saved acknowledgement/);
  expect(localStorage.getItem(key)).toBe(raw);expect(save).not.toHaveBeenCalled();expect(lookup).toHaveBeenCalledWith(draft.world_id,old.request_id);
  await userEvent.click(screen.getByRole('button',{name:'Release earlier request'}));
  expect(localStorage.getItem(key)).toBeNull();expect(save).not.toHaveBeenCalled();
});

it('keeps association unavailable while saved editor work is dirty',()=>{
  render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={locator} disabledReason="Save or revert edits first."/>);
  expect(screen.getByRole('button',{name:'Load creatures'})).toBeDisabled();
  expect(api.getThreatDraft).not.toHaveBeenCalled();
});


it('recovers an existing historical acknowledgement and never resubmits the obsolete request',async()=>{
  const old={request_id:crypto.randomUUID(),draft_id:draft.draft_id,expected_draft_version:2,expected_version:0,target:view.targets[0]};
  localStorage.setItem(key,JSON.stringify(old));
  const receipt={...result({...old,locator}).association,request:old,proof:{locator,acceptance_operation_id:'old-accept',accepted_from_draft_version:1,accepted_from_candidate_id:null,acceptance_request_digest:'sha256:'+'c'.repeat(64)}};
  vi.spyOn(api,'findWorldMechanicsAssociationRequest').mockResolvedValue(receipt);
  const save=vi.spyOn(api,'associateWorldMechanics');
  render(<WorldMechanicsAssociationPanel worldId={draft.world_id} draftId={draft.draft_id} locator={{...locator,revision_id:'rev_other'}}/>);
  await userEvent.click(screen.getByRole('button',{name:'Check earlier association'}));
  await screen.findByText(/Association receipt recovered for Keeper/);
  expect(localStorage.getItem(key)).toBeNull();expect(save).not.toHaveBeenCalled();
  expect(api.listWorldCreatures).not.toHaveBeenCalled();
});
