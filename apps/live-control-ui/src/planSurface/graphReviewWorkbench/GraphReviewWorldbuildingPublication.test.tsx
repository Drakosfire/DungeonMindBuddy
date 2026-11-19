import * as native from "../../api/nativeWorldbuildingPublicationApi";
import {retainNativeWorldbuildingConfirmation} from "./worldbuildingPublicationRecovery";
import { act, fireEvent, render, screen, waitFor, cleanup, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {ExtractPromoteApiError} from "../../api/extractPromoteApi";
import * as api from "../../api/worldbuildingPublicationApi";
import * as live from "../../api/liveApi";
import type { ExactRunReviewPackage, ManagedWorldGraphProjectionResponse } from "../../api/types";
import type { WorldbuildingPlan } from "../../api/worldbuildingPublicationApi";
import {readWorldbuildingPublicationRecovery, worldbuildingPublicationRecoveryKey, worldbuildingPublicationScope} from './worldbuildingPublicationRecovery';
import {withFirstWorldEffect,withNativeFirstWorldPlan} from './firstWorldPublicationRecovery.testSupport';
import {firstWorldRecoveryKey,firstWorldScope,saveFirstWorldRecovery} from './firstWorldPublicationRecovery';
import { GraphReviewWorldbuildingPublication } from "./GraphReviewWorldbuildingPublication";
const firstWorldReview = vi.hoisted(() => vi.fn());
const selection = vi.hoisted(() => ({kind: "managed", worldId: "world-a", name: "A", documentId: null}));
vi.mock("../../selectedWorld/SelectedWorldContext", () => ({useSelectedWorld: () => selection}));
vi.mock("./GraphReviewFirstWorldPublishSheet", () => ({GraphReviewFirstWorldPublishSheet: ({review}: {review: ExactRunReviewPackage}) => {firstWorldReview(review); return <p>First World review</p>;}, GraphReviewFirstWorldRecovery: () => <p>Saved first-World recovery</p>}));
const review: ExactRunReviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1", runId: "run-a", sourceDomain: "worldbuilding",
  sourceArtifactId: "source-a", sourceRevisionId: "sha256:" + "c".repeat(64), worldId: "world-a", sourceProse: "Draft lore",
  inspectionStatus: "ready", promotable: false, worldState: "uninitialized", firstWorldPublishEligible: true,
  diagnostics: [], assertions: [
    {assertionId: "location:edge", kind: "object", nodeType: "npc", contributionKind: "npc", label: "Edge", summary: "A proposed town", evidence: []},
    {assertionId: "npc:a", kind: "object", nodeType: "npc", contributionKind: "npc", label: "Mara", summary: "A proposed soldier", evidence: []},
    {assertionId: "edge:a", kind: "relationship", relationshipType: "located_in", fromCandidateNodeId: "npc:a", toCandidateNodeId: "location:edge", label: "In town", summary: "npc:a → location:edge", evidence: []},
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
async function choose() {
  fireEvent.change(screen.getByLabelText("Decision for Edge"), {target: {value: "bind_existing"}});
  await waitFor(() => expect(screen.getByLabelText("Decision for Edge")).toHaveValue("bind_existing"));
  fireEvent.change(screen.getByLabelText("Existing identity for Edge"), {target: {value: "loc_3"}});
  fireEvent.change(screen.getByLabelText("Decision for Mara"), {target: {value: "create_new"}});
  fireEvent.change(screen.getByLabelText("Decision for In town"), {target: {value: "reject"}});
}
async function ready() { await waitFor(() => expect(screen.getByRole("group", {name: "Publication choices"})).not.toBeDisabled()); }
function deferred<T>() {let resolve!: (v: T) => void; const promise = new Promise<T>(r => {resolve=r;}); return {promise, resolve};}
beforeEach(() => {
  localStorage.clear();
  firstWorldReview.mockClear();
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
// These retained-protocol tests deliberately start with a saved, unsubmitted
// classic packet. Fresh reviews now use native publication and cannot create it.
function seedRetainedClassic(value = review) {
  const scope = worldbuildingPublicationScope(value, "world-a");
  const key = worldbuildingPublicationRecoveryKey(scope);
  if (localStorage.getItem(key) !== null) return;
  const deferredPlan: WorldbuildingPlan = {...plan, runId: value.runId,
    effect: {decisionSnapshot: value.assertions.map(row => ({assertionId: row.assertionId,
      candidateKind: row.kind === "object" ? "node" : "edge", decision: "defer"})), acceptedProposals: []},
    summary: {createNewNodeCount: 0, bindExistingNodeCount: 0, acceptedEdgeCount: 0,
      rejectedCandidateCount: 0, deferredCandidateCount: value.assertions.length, acceptedAssertionCount: 0}};
  localStorage.setItem(key, JSON.stringify({schema: "dmb_worldbuilding_publication_recovery_v1", scope,
    plan: deferredPlan, submitted: false, staleParent: false}));
}
function renderRetainedClassic() {
  seedRetainedClassic();
  return render(<GraphReviewWorldbuildingPublication review={review}/>);
}
describe("retained classic Worldbuilding publication", () => {
  it("reads only, with all assertions deferred, despite generic false and stale first-World eligibility", async () => {
    renderRetainedClassic(); await ready();
    expect(screen.queryByText("First World review")).toBeNull();
    expect(screen.getByLabelText("Decision for Edge")).toHaveValue("defer");
    expect(screen.getByRole("button", {name: "Confirm publication"})).toBeDisabled();
    expect(api.prepareWorldbuilding).not.toHaveBeenCalled(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("posts exact explicit identities/omissions once, then separately confirms the unchanged sealed plan", async () => {
    renderRetainedClassic(); await ready(); await choose();
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
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    await waitFor(() => expect(screen.getByLabelText("Decision for Edge")).toHaveValue("bind_existing"));
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
    renderRetainedClassic(); await screen.findByRole("alert");
    expect(screen.getByRole("button", {name: "Confirm publication"})).toBeDisabled();
  });
  it.each(["worldId", "sourceArtifactId", "sourceRevisionId", "runId", "parentRevisionId"] as const)("rejects mismatched prepared %s", async key => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, [key]: "foreign"});
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("rejects a plan that changed a reviewed choice or repeats an assertion", async () => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, effect: {...plan.effect,
      decisionSnapshot: [choices[0], choices[0], choices[2]]}});
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull();
  });
  it("rejects a changed managed/native publication binding", async () => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, publicationBinding: {...plan.publicationBinding!, bindingVersion: 2}});
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("does not treat a foreign publication receipt as success or retry it", async () => {
    vi.mocked(api.confirmWorldbuilding).mockResolvedValue({...await api.confirmWorldbuilding(plan), planDigest: "foreign"});
    vi.mocked(api.confirmWorldbuilding).mockClear();
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("receipt could not be verified");
    expect(screen.queryByText(/Publication recorded/)).toBeNull(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
  });
  it.each(["d".repeat(64), "malformed", ""])("rejects contradictory or malformed nested source digest %s", async sourceSha256 => {
    vi.mocked(api.prepareWorldbuilding).mockResolvedValue({...plan, publicationBinding: {...plan.publicationBinding!, sourceSha256}});
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("rejects stale head without automatically preparing or confirming again", async () => {
    vi.mocked(api.prepareWorldbuilding).mockRejectedValue(new Error("stale_parent_revision"));
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(api.prepareWorldbuilding).toHaveBeenCalledOnce(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("retains uncertain confirmation for an explicit exact retry", async () => {
    vi.mocked(api.confirmWorldbuilding).mockRejectedValue(new Error("network interrupted"));
    renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("outcome is unverified");
    expect(screen.getByRole("button", {name: "Recover publication result"})).toBeEnabled(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
    expect(screen.getByRole("group", {name: "Publication choices"})).toBeDisabled();
  });
  it("discards an old run's late prepared result on selection change", async () => {
    const pending = deferred<WorldbuildingPlan>(); vi.mocked(api.prepareWorldbuilding).mockReturnValue(pending.promise);
    const ui = renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"}));
    seedRetainedClassic({...review, runId: "run-b"});
    ui.rerender(<GraphReviewWorldbuildingPublication review={{...review, runId: "run-b"}} />); await ready();
    await act(async () => {pending.resolve(plan); await pending.promise;});
    expect(screen.getByRole("button", {name: "Confirm publication"})).toBeDisabled(); expect(screen.getByLabelText("Decision for Edge")).toHaveValue("defer");
  });
  it("ignores a late projection after unmount", async () => {
    const pending = deferred<ManagedWorldGraphProjectionResponse>(); vi.mocked(live.postManagedWorldGraphProjection).mockReturnValue(pending.promise);
    const ui = render(<GraphReviewWorldbuildingPublication review={review} />); ui.unmount();
    await act(async () => {pending.resolve(projection); await pending.promise;});
    expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled(); expect(api.prepareWorldbuilding).not.toHaveBeenCalled();
  });
  it("does not request another World's private projection", () => {
    selection.worldId = "world-b";
    renderRetainedClassic();
    expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled(); expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled();
  });
});


describe("durable exact Worldbuilding recovery", () => {
  async function prepared() {
    const ui = renderRetainedClassic(); await ready(); await choose();
    fireEvent.click(screen.getByRole("button", {name:"Prepare proposed changes"}));
    await screen.findByRole("button", {name:"Confirm publication"});
    return ui;
  }
  it("persists before confirmation and restores exact choices after closing review without a POST", async () => {
    const ui = await prepared();
    expect(readWorldbuildingPublicationRecovery(review, 'world-a')).toMatchObject({plan, submitted:false});
    ui.unmount(); renderRetainedClassic(); await ready();
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
    renderRetainedClassic();
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
    renderRetainedClassic();
    await waitFor(()=>expect(screen.getByRole('button',{name:'Recover publication result'})).toBeEnabled());
    expect(screen.queryByText(/Publication recorded/)).toBeNull(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
  });
  it("never exposes confirmation if retaining the prepared plan fails", async () => {
    const ui=renderRetainedClassic(); await ready(); await choose();
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('storage full');});
    expect(ui.container).not.toBeEmptyDOMElement();
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
    seedRetainedClassic({...review,runId:'run-b'});
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
    const context=vi.spyOn(native,'getNativeWorldbuildingContext').mockRejectedValue(new Error('fresh native context'));
    fireEvent.click(screen.getByRole('button',{name:'Set aside rejected plan and refresh World'}));
    await screen.findByText('fresh native context'); expect(context).toHaveBeenCalledOnce();
    expect(localStorage.getItem(key)).toBeNull();
    expect(JSON.parse(localStorage.getItem(key+':retained:'+plan.planId)!)).toMatchObject({plan,submitted:true,staleParent:true});
    expect(screen.queryByLabelText('Decision for Edge')).toBeNull();
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
    const mounted: ReturnType<typeof within>[]=[];
    for(let tab=0;tab<2;tab++){
      // Each tab enters from a retained unsubmitted packet, then explicitly
      // invalidates it before its concurrent prepare response is delivered.
      seedRetainedClassic();
      const ui=render(<GraphReviewWorldbuildingPublication review={review}/>);
      const q=within(ui.container);mounted.push(q);
      await waitFor(()=>expect(q.getByRole('group',{name:'Publication choices'})).toBeEnabled());
      fireEvent.change(q.getByLabelText('Decision for Edge'),{target:{value:'bind_existing'}});
      await waitFor(()=>expect(q.getByLabelText('Decision for Edge')).toHaveValue('bind_existing'));
      fireEvent.change(q.getByLabelText('Existing identity for Edge'),{target:{value:'loc_3'}});
      fireEvent.change(q.getByLabelText('Decision for Mara'),{target:{value:'create_new'}});
      fireEvent.change(q.getByLabelText('Decision for In town'),{target:{value:'reject'}});
      fireEvent.click(q.getByRole('button',{name:'Prepare proposed changes'}));
    }
    const [qa,qb]=mounted;
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
    renderRetainedClassic();await ready();
    fireEvent.change(screen.getByLabelText('Decision for Edge'),{target:{value:'bind_existing'}});
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


it.each(["none","classic","native"])("retained creation versus existing-World packet %s refuses ambiguity without rewriting",async family=>{
  const bound={...review,assertions:review.assertions.map(row=>({...row,evidence:[{sourceArtifactId:review.sourceArtifactId,
    sourceSpanRefId:'span-a',paragraphText:'A source-backed claim.',anchorQuotes:['source-backed']}]}))};
  await saveFirstWorldRecovery(bound,withFirstWorldEffect({schema:'dmb_first_world_graph_plan_v3',sourceEvidenceSha256:'sha256:'+'d'.repeat(64),nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},planId:'first-plan',planDigest:'sha256:'+'a'.repeat(64),
    decisionDigest:'sha256:'+'b'.repeat(64),worldId:'world-a',runId:review.runId,sourceArtifactId:review.sourceArtifactId,sourceRevisionId:review.sourceRevisionId,
    workspaceDocumentId:'doc-a',workspaceDocumentRevision:'1',extractionProfile:'worldbuilding_shepherds_flock_v0@0.1',acceptedAssertionIds:['assertion-a','assertion-b','assertion-c'],
    rejectedAssertionIds:[],contributionId:'contribution-a',contributionPayloadSha256:'c'.repeat(64),
    reviewedEffect:{decision_snapshot:bound.assertions.map(row=>({assertion_id:row.assertionId,candidate_kind:row.kind==='object'?'node':'edge',
      decision:row.kind==='object'?'create_new':'accept',target_node_id:null}))},summary:{createNewNodeCount:2,acceptedEdgeCount:1,rejectedCandidateCount:0,acceptedAssertionCount:3},
    confirmable:true,diagnostics:[]},bound),false,()=>true);
  if(family==="classic")seedRetainedClassic(bound);
  if(family==="native")await retainNativeWorldbuildingConfirmation(bound,"world-a",{
    envelope:{purpose:"dmb_native_worldbuilding_confirm_v1",prepared_change_id:"change:retained",
      review:{managed_world_id:"world-a",run_id:"run-a"}},prepared:{operations:[]},token:"signed-retained"});
  const retained={...localStorage};
  render(<GraphReviewWorldbuildingPublication review={{...bound,worldState:'initialized',firstWorldPublishEligible:false}}/>);
  if(family==="none")expect(await screen.findByText('First World review')).toBeInTheDocument();
  else {expect(await screen.findByRole("alert")).toHaveTextContent("Multiple publication requests");
    expect(screen.queryByText("First World review")).toBeNull();}
  expect({...localStorage}).toEqual(retained);
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

it("replays a retained native publication when Graph Review reopens", async () => {
  const packet = {
    envelope: {
      purpose: "dmb_native_worldbuilding_confirm_v1",
      prepared_change_id: "change:a",
      review: { managed_world_id: "world-a", run_id: "run-a" },
    },
    prepared: { operations: [] },
    token: "signed-fixture",
  };
  await retainNativeWorldbuildingConfirmation(review, "world-a", packet);
  const confirm = vi.spyOn(native, "confirmNativeWorldbuilding")
    .mockResolvedValue({ recovered: true, result: { child_revision_id: "rev:child" } });
  render(<GraphReviewWorldbuildingPublication review={review} />);
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Retry saved publication" }));
  await screen.findByText("Worldbuilding publication confirmed.");
  expect(confirm).toHaveBeenCalledExactlyOnceWith(packet);
  expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
});

it.each([undefined, "stale-world", "world-a"].flatMap(selector => [false,true].map(bindExisting => ({selector,bindExisting}))))("fresh native packet: $selector, bind existing $bindExisting", async ({selector,bindExisting}) => {
  if (selector !== undefined) vi.stubEnv("VITE_NATIVE_WORLDBUILDING_WORLD", selector);
  try {
    const coordinates = {
      managed_world_id: "world-a", run_id: "run-a", expected_run_revision: 1,
      candidate_sha256: "a".repeat(64), expected_parent_revision_id: "rev:1",
      expected_source_authority_epoch: 1, workspace_document_id: "doc-a",
      workspace_document_revision: 1,
    };
    const packet = {
      envelope: {
        purpose: "dmb_native_worldbuilding_confirm_v1", prepared_change_id: "change:a",
        review: { managed_world_id: "world-a", run_id: "run-a" },
      },
      prepared: { operations: [] }, token: "signed-fixture",
    };
    vi.spyOn(native, "getNativeWorldbuildingContext").mockResolvedValue({
      prepareCoordinates: coordinates, nativeWorldId: "native-a",
      records: [{ kind: "node", record_id: "npc:a", label: "Mara", fields: { label: "Mara", node_type: "npc" } },
        {kind: "node", record_id: "town:a", label: "Town", fields: {label: "Town"}},
        {kind: "edge", record_id: "edge:a", from_record_id: "npc:a", to_record_id: "town:a",
          relationship_type: "located_in", fields: {}}],

      sourceSupport: [{ evidence_ref_id: "support:a", text: "Mara arrived.", start_byte: 0, end_byte: 13 }],
    });
    const prepare = vi.spyOn(native, "prepareNativeWorldbuilding")
      .mockResolvedValue({ status: "prepared", confirmation: packet, records: [] });
    const response=deferred<Awaited<ReturnType<typeof native.confirmNativeWorldbuilding>>>();
    const confirm = vi.spyOn(native, "confirmNativeWorldbuilding").mockReturnValue(response.promise);
    const ui = render(<GraphReviewWorldbuildingPublication review={{...review,worldState:"initialized",firstWorldPublishEligible:false}} />);
    fireEvent.change(await screen.findByLabelText("Candidate object"), { target: { value: "npc:a" } });
    if (bindExisting) {
      fireEvent.change(screen.getByLabelText("Object action"), { target: { value: "existing" } });
      fireEvent.change(screen.getByLabelText("Existing object ID"), { target: { value: "ent:mara" } });
    }
    const facts = screen.getByLabelText("Facts") as HTMLSelectElement;
    for (const option of facts.options) option.selected = true;
    fireEvent.change(facts);
    fireEvent.change(screen.getByLabelText("Supporting excerpt"), { target: { value: "support:a" } });
    fireEvent.change(screen.getByLabelText("Candidate object"), {target: {value: "town:a"}});
    fireEvent.change(screen.getByLabelText("Supporting excerpt"), {target: {value: "support:a"}});
    expect(screen.getByRole("button", {name: "Prepare selected facts"})).toBeDisabled();
    fireEvent.click(screen.getByRole("button", {name: "Clear choices for this object"}));
    expect(screen.getByRole("button", {name: "Prepare selected facts"})).toBeEnabled();
    expect(screen.queryByLabelText("Relationships")).not.toBeInTheDocument();
    if (bindExisting) {
      fireEvent.change(screen.getByLabelText("Candidate object"), {target: {value: "town:a"}});
      const townFacts = screen.getByLabelText("Facts") as HTMLSelectElement;
      townFacts.options[0].selected = true;
      fireEvent.change(townFacts);
      fireEvent.change(screen.getByLabelText("Supporting excerpt"), {target: {value: "support:a"}});
      const edges = screen.getByLabelText("Relationships") as HTMLSelectElement;
      for (const option of edges.options) option.selected = true;
      fireEvent.change(edges);
      fireEvent.change(screen.getByLabelText("Relationship excerpt for edge:a"), {target: {value: "support:a"}});
    }
    fireEvent.click(screen.getByRole("button", { name: "Prepare selected facts" }));
    const submit = await screen.findByRole("button", { name: "Confirm native publication" });
    const input = prepare.mock.calls[0][0];
    expect({...input, selections: input.selections.slice(0, 1)}).toEqual({
      ...coordinates,
      selections: [{ kind: "node", record_id: "npc:a", action: bindExisting ? "use_existing" : "create",
        ...(bindExisting ? {entity_id: "ent:mara"} : {}), facts: ["label", "node_type"].map(field => ({
        field, metadata: {
          evidence_ref_ids: ["support:a"],
          visibility: { kind: "labels_any", labels: ["dungeonbuddy.visibility:gm"] },
          epistemic_basis: "asserted", claim_mode: "dungeonbuddy.claim:fact",
          standing: "provisional", temporal_scope: { kind: "timeless" },
        },
      })) }],
    });
    expect(input.selections.slice(1)).toEqual(bindExisting ? [
      {kind: "node", record_id: "town:a", action: "create",
        facts: [expect.objectContaining({field: "label"})]},
      {kind: "edge", record_id: "edge:a", action: "create",
        metadata: expect.objectContaining({evidence_ref_ids: ["support:a"]})},
    ] : []);
    expect(confirm).not.toHaveBeenCalled();
    fireEvent.click(submit);
    await waitFor(()=>expect(confirm).toHaveBeenCalledOnce());
    ui.rerender(<GraphReviewWorldbuildingPublication review={review}/>);
    expect(screen.getByRole("button",{name:"Confirm native publication"})).toBeDisabled();
    expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();
    await act(async()=>{response.resolve({recovered:false,result:{child_revision_id:"rev:2"}});await response.promise;});
    await screen.findByText("Worldbuilding publication confirmed.");
    ui.rerender(<GraphReviewWorldbuildingPublication review={{...review}} />);
    expect(screen.getByText("Worldbuilding publication confirmed.")).toBeInTheDocument();
    expect(confirm).toHaveBeenCalledExactlyOnceWith(packet);
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  } finally {
    vi.unstubAllEnvs();
  }
});


it('selects retained native creation before existing-World publication despite changed current source',async()=>{
  const bound={...review,assertions:review.assertions.map(row=>({...row,evidence:[{sourceArtifactId:review.sourceArtifactId,
    sourceSpanRefId:'span-a',paragraphText:'A source-backed claim.',anchorQuotes:['source-backed']}]}))};
  const nativePlan=withNativeFirstWorldPlan({schema:'dmb_first_world_graph_plan_v3',sourceEvidenceSha256:'sha256:'+'d'.repeat(64),
    nativeTarget:{nativeWorldId:'world:'+'1'.repeat(32),provisioningId:'provision:'+'2'.repeat(32),bindingVersion:1},
    planId:'native-first',planDigest:'sha256:'+'a'.repeat(64),decisionDigest:'sha256:'+'b'.repeat(64),worldId:'world-a',runId:review.runId,
    sourceArtifactId:review.sourceArtifactId,sourceRevisionId:review.sourceRevisionId,workspaceDocumentId:'doc-a',workspaceDocumentRevision:'1',
    extractionProfile:'worldbuilding_shepherds_flock_v0@0.1',acceptedAssertionIds:['a','b','c'],rejectedAssertionIds:[],
    contributionId:'reviewed-correlation',contributionPayloadSha256:'c'.repeat(64),reviewedEffect:{decision_snapshot:bound.assertions.map(row=>({
      assertion_id:row.assertionId,candidate_kind:row.kind==='object'?'node':'edge',decision:row.kind==='object'?'create_new':'accept',target_node_id:null}))},
    summary:{createNewNodeCount:2,acceptedEdgeCount:1,rejectedCandidateCount:0,acceptedAssertionCount:3},confirmable:true,diagnostics:[]},bound);
  await saveFirstWorldRecovery(bound,nativePlan,false,()=>true);await saveFirstWorldRecovery(bound,nativePlan,true,()=>true);
  render(<GraphReviewWorldbuildingPublication review={{...bound,sourceRevisionId:'sha256:'+'f'.repeat(64),assertions:[],worldState:'initialized',firstWorldPublishEligible:false}}/>);
  expect(await screen.findByText('First World review')).toBeInTheDocument();
  expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();expect(api.prepareWorldbuilding).not.toHaveBeenCalled();
  expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
});


it('selects native first-World review for an eligible source-only empty head',async()=>{
  vi.mocked(live.postManagedWorldGraphProjection).mockResolvedValue({...projection,projection:{...projection.projection,nodes:[]}});
  render(<GraphReviewWorldbuildingPublication review={review}/>);
  expect(await screen.findByText('First World review')).toBeInTheDocument();
  expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled();
  expect(api.prepareWorldbuilding).not.toHaveBeenCalled();expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
});


describe("fresh native routing guards", () => {
  it.each([undefined, "stale-world", "world-a"])("skips projection for an initialized review with selector %s and never falls back", async selector => {
    if (selector !== undefined) vi.stubEnv("VITE_NATIVE_WORLDBUILDING_WORLD", selector);
    try {
      const context=vi.spyOn(native,"getNativeWorldbuildingContext").mockRejectedValue(new Error("native context unavailable"));
      render(<GraphReviewWorldbuildingPublication review={{...review,worldState:"initialized",firstWorldPublishEligible:false}}/>);
      await screen.findByText("native context unavailable");
      expect(context).toHaveBeenCalledExactlyOnceWith({managed_world_id:"world-a",run_id:"run-a",
        source_artifact_id:"source-a",source_sha256:"c".repeat(64)});
      expect(live.postManagedWorldGraphProjection).not.toHaveBeenCalled();
      expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled();
      expect(api.prepareWorldbuilding).not.toHaveBeenCalled();expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
    } finally {vi.unstubAllEnvs();}
  });
  it.each(["managedWorldId","nativeWorldId","historical","head"])("refuses contradictory first-World probe %s before any prepare",async damage=>{
    const bad={...projection,projection:{...projection.projection,snapshot:{...projection.projection.snapshot}}};
    if(damage==="managedWorldId")bad.managedWorldId="foreign";
    if(damage==="nativeWorldId")bad.nativeWorldId="foreign";
    if(damage==="historical")bad.projection.snapshot.isHead=false;
    if(damage==="head")bad.projection.snapshot.headRevisionId="rev:other";
    vi.mocked(live.postManagedWorldGraphProjection).mockResolvedValue(bad);
    const context=vi.spyOn(native,"getNativeWorldbuildingContext");
    render(<GraphReviewWorldbuildingPublication review={review}/>);
    expect(await screen.findByRole("alert")).toHaveTextContent("binding could not be verified");
    expect(context).not.toHaveBeenCalled();expect(api.prepareWorldbuilding).not.toHaveBeenCalled();
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();expect(screen.queryByText("First World review")).toBeNull();
  });
});


it("keeps the entry classification while same-source first-World hints change during a pending probe",async()=>{
  const probe=deferred<ManagedWorldGraphProjectionResponse>();
  vi.mocked(live.postManagedWorldGraphProjection).mockReturnValue(probe.promise);
  const context=vi.spyOn(native,"getNativeWorldbuildingContext");
  const ui=render(<GraphReviewWorldbuildingPublication review={review}/>);
  ui.rerender(<GraphReviewWorldbuildingPublication review={{...review,worldState:"initialized",firstWorldPublishEligible:false}}/>);
  await act(async()=>{probe.resolve({...projection,projection:{...projection.projection,nodes:[]}});await probe.promise;});
  expect(await screen.findByText("First World review")).toBeInTheDocument();
  expect(live.postManagedWorldGraphProjection).toHaveBeenCalledOnce();expect(context).not.toHaveBeenCalled();
  expect(firstWorldReview).toHaveBeenLastCalledWith(expect.objectContaining({worldState:"uninitialized",firstWorldPublishEligible:true}));
});

it("routes stale first-World eligibility on a populated head to native, not classic",async()=>{
  const context=vi.spyOn(native,"getNativeWorldbuildingContext").mockRejectedValue(new Error("native-only context"));
  render(<GraphReviewWorldbuildingPublication review={review}/>);
  await screen.findByText("native-only context");expect(context).toHaveBeenCalledOnce();
  expect(screen.queryByText("First World review")).toBeNull();expect(api.getWorldbuildingCapabilities).not.toHaveBeenCalled();
});
