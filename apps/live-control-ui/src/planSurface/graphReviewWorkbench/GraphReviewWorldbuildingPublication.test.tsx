import { act, fireEvent, render, screen, waitFor, cleanup, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {ExtractPromoteApiError} from "../../api/extractPromoteApi";
import * as api from "../../api/worldbuildingPublicationApi";
import * as live from "../../api/liveApi";
import type { ExactRunReviewPackage, ManagedWorldGraphProjectionResponse } from "../../api/types";
import type { WorldbuildingPlan } from "../../api/worldbuildingPublicationApi";
import {readWorldbuildingPublicationRecovery, worldbuildingPublicationRecoveryKey, worldbuildingPublicationScope} from './worldbuildingPublicationRecovery';
import {withFirstWorldEffect} from './firstWorldPublicationRecovery.testSupport';
import {firstWorldRecoveryKey,firstWorldScope,saveFirstWorldRecovery} from './firstWorldPublicationRecovery';
import { GraphReviewWorldbuildingPublication } from "./GraphReviewWorldbuildingPublication";
const selection = vi.hoisted(() => ({kind: "managed", worldId: "world-a", name: "A", documentId: null}));
vi.mock("../../selectedWorld/SelectedWorldContext", () => ({useSelectedWorld: () => selection}));
vi.mock("./GraphReviewFirstWorldPublishSheet", () => ({GraphReviewFirstWorldPublishSheet: () => <p>First World review</p>}));
const review: ExactRunReviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1", runId: "run-a", sourceDomain: "worldbuilding",
  sourceArtifactId: "source-a", sourceRevisionId: "sha256:" + "c".repeat(64), worldId: "world-a", sourceProse: "Draft lore",
  inspectionStatus: "ready", promotable: false, worldState: "uninitialized", firstWorldPublishEligible: true,
  diagnostics: [], assertions: [
    {assertionId: "location:edge", kind: "object", label: "Edge", summary: "A proposed town", evidence: []},
    {assertionId: "npc:a", kind: "object", label: "Mara", summary: "A proposed soldier", evidence: []},
    {assertionId: "edge:a", kind: "relationship", label: "In town", summary: "npc:a → location:edge", evidence: []},
  ],
};
const projection = {schema: "dmb_managed_world_graph_projection_v1", managedWorldId: "world-a", nativeWorldId: "native-a", bindingVersion: 1,
  projection: {snapshot: {worldId: "native-a", revisionId: "rev:1", headRevisionId: "rev:1", isHead: true},
    nodes: [{nodeId: "loc_3", label: "Edge", kind: "location"}]}} as ManagedWorldGraphProjectionResponse;
const choices = [
  {assertionId: "location:edge", decision: "bind_existing", targetNodeId: "loc_3", candidateKind: "node"},
  {assertionId: "npc:a", decision: "create_new", candidateKind: "node"},
  {assertionId: "edge:a", decision: "reject", candidateKind: "edge"},
] as WorldbuildingPlan["effect"]["decisionSnapshot"];
const plan: WorldbuildingPlan = {schema: "dmb_worldbuilding_write_plan_v2", version: 2, planId: "plan-a", planDigest: "sha256:" + "a".repeat(64),
  decisionDigest: "sha256:" + "b".repeat(64), worldId: "native-a", parentRevisionId: "rev:1", runId: "run-a", sourceArtifactId: "source-a",
  sourceRevisionId: "sha256:" + "c".repeat(64), prepareBinding: "sealed", publicationBinding: {managedWorldId: "world-a", nativeWorldId: "native-a",
    bindingVersion: 1, sourceArtifactId: "source-a", documentId: "doc-a", documentRevision: 1, sourceSha256: "c".repeat(64)},
  effect: {decisionSnapshot: choices, acceptedProposals: [{kind: "node"}]}, summary: {createNewNodeCount: 1, bindExistingNodeCount: 1,
    acceptedEdgeCount: 0, rejectedCandidateCount: 1, deferredCandidateCount: 0, acceptedAssertionCount: 2}, diagnostics: []};
function choose() {
  fireEvent.change(screen.getByLabelText("Decision for Edge"), {target: {value: "bind_existing"}});
  fireEvent.change(screen.getByLabelText("Existing identity for Edge"), {target: {value: "loc_3"}});
  fireEvent.change(screen.getByLabelText("Decision for Mara"), {target: {value: "create_new"}});
  fireEvent.change(screen.getByLabelText("Decision for In town"), {target: {value: "reject"}});
}
async function ready() { await waitFor(() => expect(screen.getByRole("group", {name: "Publication choices"})).not.toBeDisabled()); }
function deferred<T>() {let resolve!: (v: T) => void; const promise = new Promise<T>(r => {resolve=r;}); return {promise, resolve};}
beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,callback:()=>unknown)=>Promise.resolve(callback())}});
  selection.worldId = "world-a";
  vi.spyOn(live, "postManagedWorldGraphProjection").mockResolvedValue(projection);
  vi.spyOn(api, "getWorldbuildingCapabilities").mockResolvedValue({schema: "dmb_worldbuilding_publication_capabilities_v1", configured: true,
    confirmationSupported: true, unavailabilityReasons: []});
  vi.spyOn(api, "prepareWorldbuilding").mockResolvedValue(plan);
  vi.spyOn(api, "confirmWorldbuilding").mockResolvedValue({schema: "dmb_worldbuilding_write_plan_confirm_v1", outcome: "committed",
    worldId: "native-a", planId: plan.planId, planDigest: plan.planDigest, decisionDigest: plan.decisionDigest, parentRevisionId: "rev:1",
    committedRevisionId: "rev:2", appliedAssertionCount: 2, auditStatus: "ok", warnings: []});
});
afterEach(() => {cleanup(); vi.restoreAllMocks();});
describe("existing World worldbuilding publication", () => {
  it("reads only, with all assertions deferred, despite generic false and stale first-World eligibility", async () => {
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready();
    expect(screen.queryByText("First World review")).toBeNull();
    expect(screen.getByLabelText("Decision for Edge")).toHaveValue("defer");
    expect(screen.getByRole("button", {name: "Prepare proposed changes"})).toBeDisabled();
    expect(api.prepareWorldbuilding).not.toHaveBeenCalled(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("posts exact explicit identities/omissions once, then separately confirms the unchanged sealed plan", async () => {
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"}));
    await screen.findByRole("button", {name: "Confirm publication"});
    expect(api.prepareWorldbuilding).toHaveBeenCalledExactlyOnceWith({runId: "run-a", expectedParentRevisionId: "rev:1",
      dispositions: choices.map(({candidateKind: _, ...d}) => d)});
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    await screen.findByText(/Publication recorded/);
    expect(api.confirmWorldbuilding).toHaveBeenCalledExactlyOnceWith(plan);
  });
  it("requires a binding target and invalidates a prepared plan when choices change", async () => {
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.change(screen.getByLabelText("Existing identity for Edge"), {target: {value: ""}});
    await waitFor(()=>expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull());
    expect(screen.getByRole("button", {name: "Prepare proposed changes"})).toBeDisabled();
  });
  it("allows first-World flow only on an explicit missing native binding plus exact eligibility", async () => {
    vi.mocked(live.postManagedWorldGraphProjection).mockRejectedValue(new live.LiveApiError("missing", 409, {code: "native_graph_provisioning_pending"}));
    render(<GraphReviewWorldbuildingPublication review={review} />);
    await screen.findByText("First World review"); expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled();
  });
  it("does not bootstrap on an unavailable or inactive existing World", async () => {
    vi.mocked(live.postManagedWorldGraphProjection).mockRejectedValue(new live.LiveApiError("World unavailable", 503, {code: "native_graph_binding_inactive"}));
    render(<GraphReviewWorldbuildingPublication review={review} />); await screen.findByRole("alert");
    expect(screen.queryByText("First World review")).toBeNull(); expect(api.prepareWorldbuilding).not.toHaveBeenCalled();
  });
  it("does not admit sources when configuration is unavailable", async () => {
    vi.mocked(api.getWorldbuildingCapabilities).mockResolvedValue({schema: "dmb_worldbuilding_publication_capabilities_v1", configured: false,
      confirmationSupported: true, unavailabilityReasons: ["native_database_unconfigured"]});
    render(<GraphReviewWorldbuildingPublication review={review} />); await screen.findByRole("alert");
    expect(screen.getByRole("button", {name: "Prepare proposed changes"})).toBeDisabled();
  });
  it.each(["worldId", "sourceArtifactId", "sourceRevisionId", "runId", "parentRevisionId"] as const)("rejects mismatched prepared %s", async key => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, [key]: "foreign"});
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("rejects a plan that changed a reviewed choice or repeats an assertion", async () => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, effect: {...plan.effect,
      decisionSnapshot: [choices[0], choices[0], choices[2]]}});
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull();
  });
  it("rejects a changed managed/native publication binding", async () => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, publicationBinding: {...plan.publicationBinding!, bindingVersion: 2}});
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("does not treat a foreign publication receipt as success or retry it", async () => {
    vi.mocked(api.confirmWorldbuilding).mockResolvedValue({...await api.confirmWorldbuilding(plan), planDigest: "foreign"});
    vi.mocked(api.confirmWorldbuilding).mockClear();
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("receipt could not be verified");
    expect(screen.queryByText(/Publication recorded/)).toBeNull(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
  });
  it.each(["d".repeat(64), "malformed", ""])("rejects contradictory or malformed nested source digest %s", async sourceSha256 => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, publicationBinding: {...plan.publicationBinding!, sourceSha256}});
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("rejects stale head without automatically preparing or confirming again", async () => {
    vi.mocked(api.prepareWorldbuilding).mockRejectedValue(new Error("stale_parent_revision"));
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(api.prepareWorldbuilding).toHaveBeenCalledOnce(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("retains uncertain confirmation for an explicit exact retry", async () => {
    vi.mocked(api.confirmWorldbuilding).mockRejectedValue(new Error("network interrupted"));
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("outcome is unverified");
    expect(screen.getByRole("button", {name: "Recover publication result"})).toBeEnabled(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
    expect(screen.getByRole("group", {name: "Publication choices"})).toBeDisabled();
  });
  it("discards an old run's late prepared result on selection change", async () => {
    const pending = deferred<WorldbuildingPlan>(); vi.mocked(api.prepareWorldbuilding).mockReturnValue(pending.promise);
    const ui = render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"}));
    ui.rerender(<GraphReviewWorldbuildingPublication review={{...review, runId: "run-b"}} />); await ready();
    await act(async () => {pending.resolve(plan); await pending.promise;});
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull(); expect(screen.getByLabelText("Decision for Edge")).toHaveValue("defer");
  });
  it("ignores a late projection after unmount", async () => {
    const pending = deferred<ManagedWorldGraphProjectionResponse>(); vi.mocked(live.postManagedWorldGraphProjection).mockReturnValue(pending.promise);
    const ui = render(<GraphReviewWorldbuildingPublication review={review} />); ui.unmount();
    await act(async () => {pending.resolve(projection); await pending.promise;});
    expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled(); expect(api.prepareWorldbuilding).not.toHaveBeenCalled();
  });
  it("does not request another World's private projection", () => {
    selection.worldId = "world-b";
    render(<GraphReviewWorldbuildingPublication review={review} />);
    expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled(); expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled();
  });
});


describe("durable exact Worldbuilding recovery", () => {
  async function prepared() {
    const ui = render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name:"Prepare proposed changes"}));
    await screen.findByRole("button", {name:"Confirm publication"});
    return ui;
  }
  it("persists before confirmation and restores exact choices after closing review without a POST", async () => {
    const ui = await prepared();
    expect(readWorldbuildingPublicationRecovery(review, 'world-a')).toMatchObject({plan, submitted:false});
    ui.unmount(); render(<GraphReviewWorldbuildingPublication review={review} />); await ready();
    expect(screen.getByLabelText('Decision for Edge')).toHaveValue('bind_existing');
    expect(screen.getByLabelText('Existing identity for Edge')).toHaveValue('loc_3');
    expect(screen.getByLabelText('Decision for Mara')).toHaveValue('create_new');
    expect(api.prepareWorldbuilding).toHaveBeenCalledOnce(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    await screen.findByText(/Publication recorded/);
    expect(api.confirmWorldbuilding).toHaveBeenCalledExactlyOnceWith(plan);
  });
  it("persists submitted state before POST, then recovers a lost response after reload and advanced World head", async () => {
    vi.mocked(api.confirmWorldbuilding).mockImplementationOnce(async actual => {
      expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({plan:actual,submitted:true});
      throw new Error('response lost');
    });
    const ui = await prepared(); fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    await screen.findByRole('alert'); ui.unmount();
    vi.mocked(live.postManagedWorldGraphProjection).mockResolvedValue({...projection,projection:{...projection.projection,
      snapshot:{...projection.projection.snapshot,revisionId:'rev:9',headRevisionId:'rev:9'}}});
    render(<GraphReviewWorldbuildingPublication review={review} />);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Recover publication result'})).toBeEnabled());
    expect(api.confirmWorldbuilding).toHaveBeenCalledOnce(); expect(api.prepareWorldbuilding).toHaveBeenCalledOnce();
    expect(screen.getByRole('group',{name:'Publication choices'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Recover publication result'}));
    await screen.findByText(/Publication recorded/);
    expect(vi.mocked(api.confirmWorldbuilding).mock.calls).toEqual([[plan],[plan]]);
  });
  it("does not treat a saved successful request as a verified receipt after reload", async () => {
    const ui=await prepared(); fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    await screen.findByText(/Publication recorded/); ui.unmount();
    render(<GraphReviewWorldbuildingPublication review={review} />);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Recover publication result'})).toBeEnabled());
    expect(screen.queryByText(/Publication recorded/)).toBeNull(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
  });
  it("never exposes confirmation if retaining the prepared plan fails", async () => {
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole('button',{name:'Prepare proposed changes'})); await screen.findByRole('alert');
    expect(screen.queryByRole('button',{name:'Confirm publication'})).toBeNull(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("blocks POST if submitted-state persistence fails and retains the unsubmitted plan", async () => {
    await prepared(); vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});
    fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('No request was sent');
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({submitted:false,plan});
  });
  it("retains the original choices and plan if storage invalidation fails", async () => {
    await prepared(); vi.spyOn(Storage.prototype,'removeItem').mockImplementation(()=>{throw new Error('storage unavailable');});
    fireEvent.change(screen.getByLabelText('Decision for Mara'),{target:{value:'defer'}});
    await screen.findByRole('alert');
    expect(screen.getByLabelText('Decision for Mara')).toHaveValue('create_new');
    expect(screen.getByRole('button',{name:'Confirm publication'})).toBeEnabled();
    expect(readWorldbuildingPublicationRecovery(review,'world-a')?.plan).toEqual(plan);
  });
  it.each(['world','run','source','revision','binding','snapshot','duplicate','submitted','schema','malformed'])(
    'refuses malformed or cross-scope saved %s before any write',async mutation=>{
      const ui=await prepared();ui.unmount();
      const key=worldbuildingPublicationRecoveryKey(worldbuildingPublicationScope(review,'world-a'));
      const value=JSON.parse(localStorage.getItem(key)!);
      if(mutation==='world')value.plan.worldId='foreign';
      else if(mutation==='run')value.plan.runId='other';
      else if(mutation==='source')value.plan.publicationBinding.sourceArtifactId='other';
      else if(mutation==='revision')value.plan.sourceRevisionId='sha256:'+'d'.repeat(64);
      else if(mutation==='binding')value.plan.publicationBinding.bindingVersion=2;
      else if(mutation==='snapshot')value.plan.effect.decisionSnapshot[0].assertionId='foreign';
      else if(mutation==='duplicate')value.plan.effect.decisionSnapshot[1]=value.plan.effect.decisionSnapshot[0];
      else if(mutation==='submitted')value.submitted='true';
      else if(mutation==='schema')value.schema='old';
      localStorage.setItem(key,mutation==='malformed'?'{':JSON.stringify(value));
      render(<GraphReviewWorldbuildingPublication review={review}/>);await screen.findByRole('alert');
      const confirm=screen.queryByRole('button',{name:'Confirm publication'}); if(confirm)expect(confirm).toBeDisabled();
      expect(api.confirmWorldbuilding).not.toHaveBeenCalled(); expect(api.prepareWorldbuilding).toHaveBeenCalledOnce();
    });
  it("ignores a late confirmation after another exact run is selected, retaining the original request",async()=>{
    const pending=deferred<api.WorldbuildingReceipt>();vi.mocked(api.confirmWorldbuilding).mockReturnValue(pending.promise);
    const ui=await prepared();fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    ui.rerender(<GraphReviewWorldbuildingPublication review={{...review,runId:'run-b'}}/>);await ready();
    await act(async()=>{pending.resolve({schema:'dmb_worldbuilding_write_plan_confirm_v1',outcome:'committed',
      worldId:'native-a',planId:plan.planId,planDigest:plan.planDigest,decisionDigest:plan.decisionDigest,
      parentRevisionId:'rev:1',committedRevisionId:'rev:2',appliedAssertionCount:2,auditStatus:'ok',warnings:[]});await pending.promise;});
    expect(screen.queryByText(/Publication recorded/)).toBeNull();
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({submitted:true,plan});
  });
  it('allows explicit replacement only after retaining a typed stale-parent rejection',async()=>{
    vi.mocked(api.confirmWorldbuilding).mockRejectedValueOnce(new ExtractPromoteApiError('Outdated parent',409,'stale_parent_revision'));
    await prepared();fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    await screen.findByRole('button',{name:'Set aside rejected plan and refresh World'});
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({submitted:true,staleParent:true,plan});
    const key=worldbuildingPublicationRecoveryKey(worldbuildingPublicationScope(review,'world-a'));
    fireEvent.click(screen.getByRole('button',{name:'Set aside rejected plan and refresh World'}));await ready();
    expect(localStorage.getItem(key)).toBeNull();
    expect(JSON.parse(localStorage.getItem(key+':retained:'+plan.planId)!)).toMatchObject({plan,submitted:true,staleParent:true});
    expect(screen.getByLabelText('Decision for Edge')).toHaveValue('defer');
    expect(api.prepareWorldbuilding).toHaveBeenCalledOnce();expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
  });
  it('does not replace a rejected plan when archive storage fails',async()=>{
    vi.mocked(api.confirmWorldbuilding).mockRejectedValueOnce(new ExtractPromoteApiError('Outdated parent',409,'stale_parent_revision'));
    await prepared();fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    await screen.findByRole('button',{name:'Set aside rejected plan and refresh World'});
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('archive unavailable');});
    fireEvent.click(screen.getByRole('button',{name:'Set aside rejected plan and refresh World'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('archive unavailable');
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({submitted:true,staleParent:true,plan});
    expect(screen.getByRole('group',{name:'Publication choices'})).toBeDisabled();
  });
  it('never offers to replace an unknown confirmation',async()=>{
    vi.mocked(api.confirmWorldbuilding).mockRejectedValueOnce(new Error('unknown delivery'));
    await prepared();fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));await screen.findByRole('alert');
    expect(screen.queryByRole('button',{name:'Set aside rejected plan and refresh World'})).toBeNull();
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({submitted:true,staleParent:false});
  });

  it('preserves current server null target fields in the sealed confirmation',async()=>{
    const actual=JSON.parse(JSON.stringify(plan));
    actual.effect.decisionSnapshot[1].targetNodeId=null;actual.effect.decisionSnapshot[2].targetNodeId=null;
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue(actual);
    await prepared();fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    await screen.findByText(/Publication recorded/);
    expect(api.confirmWorldbuilding).toHaveBeenCalledExactlyOnceWith(actual);
  });

  it('preserves an unknown request when another mounted review finishes preparing a different plan',async()=>{
    const first=deferred<WorldbuildingPlan>(),second=deferred<WorldbuildingPlan>();
    vi.mocked(api.prepareWorldbuilding).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    vi.mocked(api.confirmWorldbuilding).mockRejectedValueOnce(new Error('response lost'));
    const a=render(<GraphReviewWorldbuildingPublication review={review}/>);
    const b=render(<GraphReviewWorldbuildingPublication review={review}/>);
    const qa=within(a.container),qb=within(b.container);
    for(const q of [qa,qb]){
      await waitFor(()=>expect(q.getByRole('group',{name:'Publication choices'})).toBeEnabled());
      fireEvent.change(q.getByLabelText('Decision for Edge'),{target:{value:'bind_existing'}});
      fireEvent.change(q.getByLabelText('Existing identity for Edge'),{target:{value:'loc_3'}});
      fireEvent.change(q.getByLabelText('Decision for Mara'),{target:{value:'create_new'}});
      fireEvent.change(q.getByLabelText('Decision for In town'),{target:{value:'reject'}});
      fireEvent.click(q.getByRole('button',{name:'Prepare proposed changes'}));
    }
    await act(async()=>{first.resolve(plan);await first.promise;});
    fireEvent.click(await qa.findByRole('button',{name:'Confirm publication'}));await qa.findByRole('alert');
    const other={...plan,planId:'other-plan',planDigest:'sha256:'+'e'.repeat(64)};
    await act(async()=>{second.resolve(other);await second.promise;});
    expect(await qb.findByRole('alert')).toHaveTextContent('Another publication request was retained');
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({plan,submitted:true});
    expect(api.confirmWorldbuilding).toHaveBeenCalledExactlyOnceWith(plan);
    expect(qb.queryByRole('button',{name:'Confirm publication'})).toBeNull();
  });
  it('fails closed when cross-tab locking is unavailable',async()=>{
    Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});
    render(<GraphReviewWorldbuildingPublication review={review}/>);await ready();choose();
    fireEvent.click(screen.getByRole('button',{name:'Prepare proposed changes'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('cannot safely retain publication recovery across tabs');
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });

  it('does not dispatch if review closes while waiting for the browser storage lock',async()=>{
    const ui=await prepared();let release!:()=>void;
    Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,callback:()=>unknown)=>
      new Promise(resolve=>{release=()=>resolve(callback());})}});
    fireEvent.click(screen.getByRole('button',{name:'Confirm publication'}));
    ui.unmount();await act(async()=>{release();await Promise.resolve();});
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
    expect(readWorldbuildingPublicationRecovery(review,'world-a')).toMatchObject({submitted:true,plan});
  });

});


it('routes retained creation to recovery after initialization instead of existing-World publication',async()=>{
  const bound={...review,assertions:review.assertions.map(row=>({...row,evidence:[{sourceArtifactId:review.sourceArtifactId,
    sourceSpanRefId:'span-a',paragraphText:'A source-backed claim.',anchorQuotes:['source-backed']}]}))};
  await saveFirstWorldRecovery(bound,withFirstWorldEffect({schema:'dmb_first_world_graph_plan_v3',sourceEvidenceSha256:'sha256:'+'d'.repeat(64),nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},planId:'first-plan',planDigest:'sha256:'+'a'.repeat(64),
    decisionDigest:'sha256:'+'b'.repeat(64),worldId:'world-a',runId:review.runId,sourceArtifactId:review.sourceArtifactId,sourceRevisionId:review.sourceRevisionId,
    workspaceDocumentId:'doc-a',workspaceDocumentRevision:'1',extractionProfile:'worldbuilding_shepherds_flock_v0@0.1',acceptedAssertionIds:['assertion-a','assertion-b','assertion-c'],
    rejectedAssertionIds:[],contributionId:'contribution-a',contributionPayloadSha256:'c'.repeat(64),
    reviewedEffect:{decision_snapshot:bound.assertions.map(row=>({assertion_id:row.assertionId,candidate_kind:row.kind==='object'?'node':'edge',
      decision:row.kind==='object'?'create_new':'accept',target_node_id:null}))},summary:{createNewNodeCount:2,acceptedEdgeCount:1,rejectedCandidateCount:0,acceptedAssertionCount:3},
    confirmable:true,diagnostics:[]},bound),false,()=>true);
  render(<GraphReviewWorldbuildingPublication review={{...bound,worldState:'initialized',firstWorldPublishEligible:false}}/>);
  expect(await screen.findByText('First World review')).toBeInTheDocument();
  expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();expect(api.prepareWorldbuilding).not.toHaveBeenCalled();
});

it('routes obsolete unsubmitted creation recovery to its explicit archive UI',()=>{
  const raw=JSON.stringify({schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),submitted:false,
    plan:{schema:'dmb_first_world_graph_plan_v2',worldId:review.worldId,runId:review.runId,
      sourceArtifactId:review.sourceArtifactId,sourceRevisionId:review.sourceRevisionId,planId:'old-plan',planDigest:'sha256:'+'a'.repeat(64)}});
  localStorage.setItem(firstWorldRecoveryKey(review),raw);
  render(<GraphReviewWorldbuildingPublication review={review}/>);
  expect(screen.getByText('First World review')).toBeInTheDocument();
  expect(api.prepareWorldbuilding).not.toHaveBeenCalled();expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  expect(localStorage.getItem(firstWorldRecoveryKey(review))).toBe(raw);
});

it('holds publication safely when browser recovery storage is unreadable',()=>{
  vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw new Error('storage denied');});
  expect(()=>render(<GraphReviewWorldbuildingPublication review={review}/>)).not.toThrow();
  expect(screen.getByRole('alert')).toHaveTextContent('storage denied');
  expect(api.prepareWorldbuilding).not.toHaveBeenCalled();expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
});
