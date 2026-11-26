import * as hostedAuth from "../../auth/HostedAuthGate";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { RecapArtifactRecord } from "../../api/types";
import { RecapGraphModule } from "./RecapGraphModule";
import { SelectedWorldProvider } from "../../selectedWorld/SelectedWorldContext";
import { session23WorldGraphRecapFixture } from "../../test/worldGraphRecapFixture";

const context = {
  campaignId: "longmont-c2",
  ingestSession: 22,
  liveSession: 22,
  target: { target_type: "session", target_id: "session-22" },
} as const;

function artifactRecord(session: number): RecapArtifactRecord {
  return {
    schema_version: "dmb_recap_artifact_record_v1",
    artifact_id: `longmont-c2/session-${session}`,
    campaign_id: "longmont-c2",
    session_id: `session-${session}`,
    source_artifact_id: null,
    source_recap_path: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session ${session} - Dogfood.md`,
    breadcrumb_seed_path: null,
    session_memory_records_path: null,
    run_bundle_uri: "",
    run_manifest_uri: "",
    source_span_index_uri: "",
    provenance_index_uri: null,
    graph_run_refs: [],
    default_graph_run_uri: null,
    default_projection_mode: "recap_graph",
    source_sha256: `sha256:session-${session}`,
    registered_at: "2026-06-28T00:00:00Z",
    updated_at: "2026-06-28T00:00:00Z",
    registry_source: "scan",
  };
}

function mockArtifacts() {
  vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
    records: [artifactRecord(24)],
  });
}

type NativeRecap = Awaited<ReturnType<typeof liveApi.readPublishedNativeRecap>>;
function nativeRecap(campaign: string, session: string): NativeRecap {
  return { schema: "dmb_native_published_recap_v1",
    scope: { managed_world_id: "elderwyld", native_world_id: "elderwyld", binding_version: 3,
      revision_id: "rev:recap", scope_mode: "world", campaign_id: null },
    campaign_id: campaign, session_id: session, evidence_ref_ids: ["ev:recap"],
    source: { status: "available", source_artifact_id: "source:recap", source_revision_id: "srev:recap",
      body_text: `Admitted ${campaign} ${session}.`, body_sha256: "digest", evidence_ref_id: "ev:recap", source_authority_epoch: 1 } };
}
function mockManagedRecap() {
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({ schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: "elderwyld", name: "Elderwyld", source_root_relpath: "", created_at: "" }] });
  vi.spyOn(liveApi, "getNativeGraphCatalog").mockImplementation(async pin => ({
    schema: "dmb_native_graph_catalog_v1", scope: pin,
    catalogue: { identity: { space_id: pin.native_world_id, revision_id: pin.revision_id }, entities: [], admitted_assertion_ids: [],
      completeness: { status: "complete", reason: null }, request_sha256: "digest", result_digest: "digest" }, assertions: [] }));
  return vi.spyOn(liveApi, "readPublishedNativeRecap").mockImplementation(async (_world, campaign, session) => nativeRecap(campaign, session));
}
function renderManagedRecap() {
  const url = new URL(window.location.href);
  url.searchParams.set("world", "elderwyld");
  window.history.replaceState({}, "", url);
  return render(<SelectedWorldProvider locationSnapshot={window.location.href}><RecapGraphModule context={context} /></SelectedWorldProvider>);
}
function mockAuthoringWrites() {
  vi.spyOn(liveApi, "postWorldGraphCompleteObject");
  vi.spyOn(liveApi, "prepareGraphObjectAuthoringWrite");
  vi.spyOn(liveApi, "commitGraphObjectAuthoringWrite");
}
function expectNoClassicWork() {
  expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();
  expect(liveApi.postWorldGraphCompleteObject).not.toHaveBeenCalled();
  expect(liveApi.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  expect(liveApi.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  expect(screen.queryByTestId("published-recap-local-authoring")).not.toBeInTheDocument();
}

describe("RecapGraphModule", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
    mockAuthoringWrites();
  });

  it("keeps the session picker available without fetching a legacy graph", async () => {
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection");

    render(<RecapGraphModule context={context} />);

    expect(await screen.findByText("Recap graph visualization requires a managed World.")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Focus session" })).toBeInTheDocument();
    expect(postRecap).not.toHaveBeenCalled();
  });

  it("defaults to the latest ingested recap artifact when no URL session is provided", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(23), artifactRecord(24)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection");

    const native = mockManagedRecap();
    renderManagedRecap();

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Focus session" })).toHaveValue("session-24"));
    expect(await screen.findByText("Admitted longmont-c2 session-24.")).toBeInTheDocument();
    expect(native).toHaveBeenCalledWith("elderwyld", "longmont-c2", "session-24");
    expect(postRecap).not.toHaveBeenCalled();
  });

  it("reads admitted native recap without a preview union or classic authoring", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    mockManagedRecap(); renderManagedRecap();
    expect(await screen.findByText("Admitted longmont-c2 session-24.")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Focus session" })).toBeInTheDocument();
    expectNoClassicWork();
  });

  it("shows native recap unavailability without classic fallback", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    mockManagedRecap().mockRejectedValue(new liveApi.LiveApiError("missing", 404, { code: "recap_markdown_unavailable" }));
    renderManagedRecap();
    expect(await screen.findByRole("alert")).toHaveTextContent("Canonical normalized recap is unavailable for session-24 in longmont-c2.");
    expectNoClassicWork();
  });

  it("uses campaign-specific session selection without a legacy graph request", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-1&campaign=longmont-c1");
    vi.spyOn(liveApi, "getRecapArtifacts").mockImplementation(async (campaignId) => {
      if (campaignId === "longmont-c1") {
        return { records: [{ ...artifactRecord(1), campaign_id: "longmont-c1", session_id: "session-1" }] };
      }
      return { records: [] };
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection");

    render(<RecapGraphModule context={context} />);

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Focus session" })).toHaveValue("session-1"));
    expect(postRecap).not.toHaveBeenCalled();
  });

  it("keeps World lens URL state when recap selection is synchronized on Ingest", async () => {
    window.history.replaceState(
      {},
      "",
      "/ingest?campaign=longmont-c1&scopeMode=campaign&session=session-1&campaigns=longmont-c1,longmont-c2&graphFocus=longmont-c2:23",
    );
    const recapRecord = {
      ...artifactRecord(1),
      campaign_id: "longmont-c1",
      session_id: "session-1",
    };
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({ records: [recapRecord] });
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    mockManagedRecap();

    renderManagedRecap();

    await screen.findByRole("combobox", { name: "Focus session" });
    expect(await screen.findByText("Admitted longmont-c1 session-1.")).toBeInTheDocument();
    expectNoClassicWork();
    expect(window.location.search).toContain("campaign=longmont-c1");
    expect(window.location.search).toContain("session=session-1");
    expect(window.location.search).toContain("campaigns=longmont-c1%2Clongmont-c2");
    expect(window.location.search).toContain("graphFocus=longmont-c2%3A23");
    expect(window.location.search).not.toContain("scopeMode");
  });

  it("does not synthesize local authoring from a legacy artifact identity", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    render(<RecapGraphModule context={context} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Recap graph visualization requires a managed World.");
    expectNoClassicWork();
  });

});

describe("RecapGraphModule PR380B World Graph authority", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-24");
    mockArtifacts();
    mockAuthoringWrites();
  });

  it("does not call legacy projection or object readers when visualization is retired", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    render(<RecapGraphModule context={context} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Recap graph visualization requires a managed World.");
    expectNoClassicWork();
  });

  it("does not expose retired classic Peek or authoring controls", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    render(<RecapGraphModule context={context} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Recap graph visualization requires a managed World.");
    expect(screen.queryByRole("link", { name: /Continue in Build/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    expectNoClassicWork();
  });

  it("does not render preview-candidate or recap-lens metadata copy", async () => {
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    mockManagedRecap();
    renderManagedRecap();
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Focus session" })).toBeInTheDocument());
    expect(await screen.findByText("Admitted longmont-c2 session-24.")).toBeInTheDocument();
    expectNoClassicWork();
    expect(screen.queryByText(/Session focus lens/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Published World Graph · session recap/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/graph mentions projected/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/preview memory candidates/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/evidence highlights/i)).not.toBeInTheDocument();
  });

  it("preserves an explicit URL session even when it is absent from the artifact listing", async () => {
    window.history.replaceState({}, "", "/plan?tool=recap&session=session-99");
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    const read = mockManagedRecap().mockRejectedValue(new liveApi.LiveApiError("missing", 404, { code: "recap_markdown_unavailable" }));
    renderManagedRecap();
    expect(await screen.findByRole("alert")).toHaveTextContent("Canonical normalized recap is unavailable for session-99 in longmont-c2.");
    expect(read).toHaveBeenCalledWith("elderwyld", "longmont-c2", "session-99");
    expect(screen.getByLabelText("Focus session")).toHaveValue("session-99");
    expectNoClassicWork();
  });

  it("keeps Ingest recap session-27 identity instead of Plan-qualified lens syntax", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-27");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(26), artifactRecord(27)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection");

    render(<RecapGraphModule context={context} />);

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Focus session" })).toHaveValue("session-27"));
    expect(postRecap).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/ingest");
    expect(window.location.search).toContain("session=session-27");
    expect(window.location.search).not.toMatch(/longmont-c2:27/);
  });

  it("recovers Ingest recap identity if the URL was already rewritten to qualified lens syntax", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=longmont-c2:27");
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      records: [artifactRecord(27)],
    });
    const postRecap = vi.spyOn(liveApi, "postWorldGraphRecapProjection");

    render(<RecapGraphModule context={context} />);

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Focus session" })).toHaveValue("session-27"));
    expect(postRecap).not.toHaveBeenCalled();
    expect(window.location.search).toContain("session=session-27");
    expect(window.location.search).not.toMatch(/longmont-c2:27/);
  });

  it("chooses a valid C1 recap session when switching from C2 session-26", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-26");
    vi.mocked(liveApi.getRecapArtifacts).mockImplementation(async campaign => ({ records: campaign === "longmont-c1"
      ? [15, 16].map(n => ({ ...artifactRecord(n), campaign_id: "longmont-c1" })) : [artifactRecord(26)] }));
    const read = mockManagedRecap(); renderManagedRecap();
    expect(await screen.findByText("Admitted longmont-c2 session-26.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Campaign"), { target: { value: "longmont-c1" } });
    await waitFor(() => expect(screen.getByLabelText("Focus session")).toHaveValue("session-16"));
    expect(read.mock.calls.some(call => call[1] === "longmont-c1")).toBe(false);
    fireEvent.click(await screen.findByRole("button", { name: "Load", exact: true }));
    expect(await screen.findByText("Admitted longmont-c1 session-16.")).toBeInTheDocument();
    expect(read).toHaveBeenCalledWith("elderwyld", "longmont-c1", "session-16");
    expect(read.mock.calls.some(call => call[1] === "longmont-c1" && call[2] === "session-26")).toBe(false);
    expect(window.location.search).toContain("campaign=longmont-c1");
    expect(window.location.search).toContain("session=session-16");
  });

  it("never exposes previous recap authoring during a campaign switch", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-26");
    vi.mocked(liveApi.getRecapArtifacts).mockImplementation(async campaign => ({ records: campaign === "longmont-c1"
      ? [{ ...artifactRecord(16), campaign_id: "longmont-c1" }] : [artifactRecord(26)] }));
    vi.spyOn(liveApi, "postWorldGraphRecapProjection");
    mockManagedRecap(); renderManagedRecap();
    expect(await screen.findByText("Admitted longmont-c2 session-26.")).toBeInTheDocument();
    expectNoClassicWork();
    fireEvent.change(screen.getByLabelText("Campaign"), { target: { value: "longmont-c1" } });
    expectNoClassicWork();
    await waitFor(() => expect(screen.getByLabelText("Focus session")).toHaveValue("session-16"));
    fireEvent.click(screen.getByRole("button", { name: "Load", exact: true }));
    expect(await screen.findByText("Admitted longmont-c1 session-16.")).toBeInTheDocument();
    expect(screen.queryByText("Admitted longmont-c2 session-26.")).not.toBeInTheDocument();
    expectNoClassicWork();
  });

  it("keeps the loaded native recap stable until an explicit session Load", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-26");
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({ records: [artifactRecord(26), artifactRecord(27)] });
    let resolveSecond!: (value: NativeRecap) => void;
    const second = new Promise<NativeRecap>(resolve => { resolveSecond = resolve; });
    const read = mockManagedRecap().mockResolvedValueOnce(nativeRecap("longmont-c2", "session-26")).mockReturnValueOnce(second);
    renderManagedRecap();
    expect(await screen.findByText("Admitted longmont-c2 session-26.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Focus session"), { target: { value: "session-27" } });
    expect(screen.getByText("Admitted longmont-c2 session-26.")).toBeInTheDocument();
    expect(read).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Load", exact: true }));
    await waitFor(() => expect(read).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("Admitted longmont-c2 session-26.")).not.toBeInTheDocument();
    resolveSecond(nativeRecap("longmont-c2", "session-27"));
    expect(await screen.findByText("Admitted longmont-c2 session-27.")).toBeInTheDocument();
    expect(screen.queryByTestId("published-recap-local-authoring")).not.toBeInTheDocument();
  });

});

it.each([false, true])("drills into a native recap object and renders only its matching excerpt (hosted=%s)", async hosted => {
  vi.restoreAllMocks();
  if (hosted) vi.spyOn(hostedAuth, "useHostedAuthStatus").mockReturnValue({
    status: "authenticated", subject: "owner", displayName: "Owner", refreshWarning: false,
  });
  window.history.replaceState({}, "", "/plan?world=elderwyld&session=session-24");
  const scope = {
    managed_world_id: "elderwyld", native_world_id: "elderwyld",
    binding_version: 3, revision_id: "rev:recap", scope_mode: "world" as const, campaign_id: null,
  };
  const pin = { ...scope, scope_mode: "campaign" as const, campaign_id: "longmont-c2" };
  mockArtifacts();
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: "elderwyld",
      name: "Elderwyld", source_root_relpath: "", created_at: "" }],
  });
  vi.spyOn(liveApi, "getHostedWorldContainer").mockResolvedValue({
    schema_version: "dmb_world_container_record_v1", world_id: "elderwyld",
    name: "Elderwyld", source_root_relpath: "", created_at: "",
  });
  vi.spyOn(liveApi, "readPublishedNativeRecap").mockResolvedValue({
    schema: "dmb_native_published_recap_v1", scope, campaign_id: "longmont-c2", session_id: "session-24",
    evidence_ref_ids: ["ev:recap"],
    source: { status: "available", source_artifact_id: "source:recap", source_revision_id: "srev:recap",
      body_text: "Admitted recap body.", body_sha256: "digest", evidence_ref_id: "ev:recap", source_authority_epoch: 1 },
  });
  const catalog = vi.spyOn(liveApi, "getNativeGraphCatalog").mockResolvedValue({
    schema: "dmb_native_graph_catalog_v1", scope: pin,
    catalogue: { identity: { space_id: "elderwyld", revision_id: pin.revision_id },
      entities: [{ entity_id: "ent:recap" }], admitted_assertion_ids: ["asrt:recap"],
      completeness: { status: "complete", reason: null }, request_sha256: "digest", result_digest: "digest" },
    assertions: [{ assertion_id: "asrt:recap", subject_entity_id: "ent:recap", predicate: "dnd5e:name",
      value: { kind: "literal", value: "Recap Object" }, metadata: { evidence_ref_ids: ["ev:recap"],
        scope: [], visibility: null, epistemic_basis: "", claim_mode: "", standing: "",
        temporal_scope: null, domain_metadata: [] } }],
  });
  const read = vi.spyOn(liveApi, "postNativeWorldGraphCompleteObject").mockResolvedValue({
    schema: "dmb_world_graph_object_projection_v1", found: true,
    completeness: { status: "complete", truncatedFields: [] },
    snapshot: { ...session23WorldGraphRecapFixture.snapshot, revisionId: pin.revision_id },
    requestedNodeId: "ent:recap", resolvedNodeId: "ent:recap",
    node: null, relatedNodes: [], semanticFingerprint: "digest",
    sourceBindings: [{ evidenceRefId: "ev:recap", excerpt: "Exact admitted excerpt." },
      { evidenceRefId: "ev:other", excerpt: "Unrelated excerpt." }],
  });
  const scoped = vi.spyOn(liveApi, "readPublishedRecapObjects");
  if (hosted) {
    scoped.mockResolvedValueOnce({ scope: pin, objects: [{ id: "ent:recap", label: "Recap Object", ambiguous: false }], partial: false });
    const result = await read.getMockImplementation()!({} as never, pin);
    scoped.mockResolvedValueOnce({ kind: "complete", detail: result });
  }
  const classic = vi.spyOn(liveApi, "postWorldGraphRecapProjection");
  const classicPrepare = vi.spyOn(liveApi, "prepareGraphObjectAuthoringWrite").mockRejectedValue(new Error("Classic preparation forbidden"));
  const classicCommit = vi.spyOn(liveApi, "commitGraphObjectAuthoringWrite").mockRejectedValue(new Error("Classic publication forbidden"));
  render(<SelectedWorldProvider locationSnapshot={window.location.href}>
    <RecapGraphModule context={context} />
  </SelectedWorldProvider>);
  expect(await screen.findByText("Admitted recap body.")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Recap Object" }));
  expect(await screen.findByText("Exact admitted excerpt.")).toBeInTheDocument();
  expect(screen.queryByText("Unrelated excerpt.")).not.toBeInTheDocument();
  if (hosted) {
    expect(catalog).not.toHaveBeenCalled();
    expect(read).not.toHaveBeenCalled();
    expect(scoped).toHaveBeenLastCalledWith(expect.objectContaining({ scope, campaign_id: "longmont-c2" }), "ent:recap");
  } else {
    expect(catalog).toHaveBeenCalledWith(pin, expect.any(AbortSignal));
    expect(read).toHaveBeenCalledWith(expect.objectContaining({ revisionPin: pin.revision_id, nodeId: "ent:recap" }), pin);
    expect(scoped).not.toHaveBeenCalled();
  }
  expect(classic).not.toHaveBeenCalled();
  expect(classicPrepare).not.toHaveBeenCalled();
  expect(classicCommit).not.toHaveBeenCalled();
  expect(screen.queryByTestId("published-recap-local-authoring")).not.toBeInTheDocument();
});
