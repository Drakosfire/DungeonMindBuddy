import { act, fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../../api/worldbuildingPublicationApi";
import * as live from "../../api/liveApi";
import type { ExactRunReviewPackage, ManagedWorldGraphProjectionResponse } from "../../api/types";
import type { WorldbuildingPlan } from "../../api/worldbuildingPublicationApi";
import { GraphReviewWorldbuildingPublication } from "./GraphReviewWorldbuildingPublication";
const selection = vi.hoisted(() => ({kind: "managed", worldId: "world-a", name: "A", documentId: null}));
vi.mock("../../selectedWorld/SelectedWorldContext", () => ({useSelectedWorld: () => selection}));
vi.mock("./GraphReviewFirstWorldPublishSheet", () => ({GraphReviewFirstWorldPublishSheet: () => <p>First World review</p>}));
const review: ExactRunReviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1", runId: "run-a", sourceDomain: "worldbuilding",
  sourceArtifactId: "source-a", sourceRevisionId: "source-r1", worldId: "world-a", sourceProse: "Draft lore",
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
  sourceRevisionId: "source-r1", prepareBinding: "sealed", publicationBinding: {managedWorldId: "world-a", nativeWorldId: "native-a",
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
    const refresh = vi.fn(); render(<GraphReviewWorldbuildingPublication review={review} onCatalogRefresh={refresh} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"}));
    await screen.findByRole("button", {name: "Confirm publication"});
    expect(api.prepareWorldbuilding).toHaveBeenCalledExactlyOnceWith({runId: "run-a", expectedParentRevisionId: "rev:1",
      dispositions: choices.map(({candidateKind: _, ...d}) => d)});
    expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    await screen.findByText(/Publication recorded/);
    expect(api.confirmWorldbuilding).toHaveBeenCalledExactlyOnceWith(plan); expect(refresh).toHaveBeenCalledOnce();
  });
  it("requires a binding target and invalidates a prepared plan when choices change", async () => {
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.change(screen.getByLabelText("Existing identity for Edge"), {target: {value: ""}});
    expect(screen.queryByRole("button", {name: "Confirm publication"})).toBeNull();
    expect(screen.getByRole("button", {name: "Prepare proposed changes"})).toBeDisabled();
  });
  it("allows first-World flow only on an explicit missing native binding plus exact eligibility", async () => {
    vi.mocked(live.postManagedWorldGraphProjection).mockRejectedValue(new live.LiveApiError("missing", 409, {code: "native_graph_binding_missing"}));
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
  it("rejects stale head without automatically preparing or confirming again", async () => {
    vi.mocked(api.prepareWorldbuilding).mockRejectedValue(new Error("stale_parent_revision"));
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("alert");
    expect(api.prepareWorldbuilding).toHaveBeenCalledOnce(); expect(api.confirmWorldbuilding).not.toHaveBeenCalled();
  });
  it("retains uncertain confirmation as an error and disables another POST", async () => {
    vi.mocked(api.confirmWorldbuilding).mockRejectedValue(new Error("network interrupted"));
    render(<GraphReviewWorldbuildingPublication review={review} />); await ready(); choose();
    fireEvent.click(screen.getByRole("button", {name: "Prepare proposed changes"})); await screen.findByRole("button", {name: "Confirm publication"});
    fireEvent.click(screen.getByRole("button", {name: "Confirm publication"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("outcome is unverified");
    expect(screen.getByRole("button", {name: "Confirm publication"})).toBeDisabled(); expect(api.confirmWorldbuilding).toHaveBeenCalledOnce();
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
