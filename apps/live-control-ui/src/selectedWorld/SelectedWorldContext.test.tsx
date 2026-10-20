import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getExtractionRun, getPlayRun, getWorkspaceDocument, getWorkspaceDocumentAny, listWorldContainers } from "../api/liveApi";
import type { WorkspaceDocumentRecord, WorldContainerRecord, WorldOwnedPlanRecordV2 } from "../api/types";
import { getWorldIdForCampaign } from "../worldGraph/worldGraphSurfaceContext";
import {
  SelectedWorldProvider,
  requestedWorldSelection,
  useRetrySelectedWorld,
  useSelectedWorldAdmission,
  useSelectedWorld,
  verifyManagedWorldSelection,
} from "./SelectedWorldContext";

vi.mock("../api/liveApi", () => ({
  getExtractionRun: vi.fn(),
  getPlayRun: vi.fn(),
  getWorkspaceDocument: vi.fn(),
  getWorkspaceDocumentAny: vi.fn(),
  listWorldContainers: vi.fn(),
}));

const world: WorldContainerRecord = {
  schema_version: "dmb_world_container_record_v1",
  world_id: "of-conks-cons-demo",
  name: "Of Conks",
  source_root_relpath: "corpus/of-conks-cons-demo-markdown",
  created_at: "2026-01-01T00:00:00Z",
};

const document: WorkspaceDocumentRecord = {
  schema_version: "dmb_workspace_document_record_v1",
  document_id: "c03fbfcb-79fc-46ae-9124-3f1f7c384c1b",
  title: "Source",
  campaign_id: world.world_id,
  world_id: world.world_id,
  target_session: null,
  kind: "worldbuilding_source",
  target_relpath: null,
  status: "active",
  content_status: "committed",
  revision: 2,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function Probe() {
  const selection = useSelectedWorld();
  return <div>{selection.kind}:{selection.kind === "managed" ? getWorldIdForCampaign(selection.worldId) : "none"}</div>;
}

function RecoveryProbe() {
  const selection = useSelectedWorld();
  const retry = useRetrySelectedWorld();
  return <div><span>{selection.kind}</span><button type="button" onClick={retry}>Retry</button></div>;
}

afterEach(() => vi.clearAllMocks());

describe("selected managed World", () => {
  it("keeps explicit empty selection fail closed", () => {
    expect(requestedWorldSelection("/plan?world=").explicit).toBe(true);
  });

  it("rejects unknown and mismatched document scopes", () => {
    expect(verifyManagedWorldSelection({ requestedWorldId: "unknown", document: null, worlds: [world] }).kind).toBe("error");
    expect(verifyManagedWorldSelection({
      requestedWorldId: world.world_id,
      document: { ...document, campaign_id: "longmont-c2" },
      worlds: [world],
    }).kind).toBe("error");
  });

  it("verifies a managed source before Build graph mapping becomes available", async () => {
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [world] });
    vi.mocked(getWorkspaceDocument).mockResolvedValue(document);
    vi.mocked(getWorkspaceDocumentAny).mockResolvedValue(document);
    const view = render(
      <SelectedWorldProvider locationSnapshot={`/build?documentId=${document.document_id}`}>
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText(`managed:${world.world_id}`)).toBeTruthy());
    expect(getWorldIdForCampaign("longmont-c2")).toBe("eldyrwild");
    view.unmount();
    expect(getWorldIdForCampaign(world.world_id)).toBeNull();
  });

  it("keeps an exact Graph Review extraction run bound to its source World", async () => {
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [world] });
    vi.mocked(getWorkspaceDocument).mockResolvedValue(document);
    vi.mocked(getWorkspaceDocumentAny).mockResolvedValue(document);
    const runId = "07a33f99-7520-4c59-bee2-b38514cb61b8";
    const view = render(
      <SelectedWorldProvider locationSnapshot={`/ingest?extractionRunId=${runId}&sourceArtifactId=artifact%3Aworldbuilding%3Asource&documentId=${document.document_id}&revision=2`}>
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText(`managed:${world.world_id}`)).toBeTruthy());
    expect(getWorkspaceDocumentAny).toHaveBeenCalledWith(document.document_id);
    view.unmount();
  });

  it("accepts a true World-owned Plan only under its exact World identity", () => {
    const worldPlan: WorldOwnedPlanRecordV2 = {
      schema_version: "dmb_world_owned_plan_record_v2",
      scope_mode: "world",
      document_id: "e514b109-c83a-4630-904f-6fe12fe5a20e",
      title: "Plan",
      campaign_id: null,
      world_id: world.world_id,
      target_session: null,
      kind: "plan",
      target_relpath: "out/workspace/plan/e514b109-c83a-4630-904f-6fe12fe5a20e.md",
      status: "active",
      content_status: "draft",
      revision: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(verifyManagedWorldSelection({ requestedWorldId: world.world_id, document: worldPlan, worlds: [world] }).kind).toBe("managed");
    expect(verifyManagedWorldSelection({ requestedWorldId: "other-world", document: worldPlan, worlds: [world] }).kind).toBe("error");
  });

  it("derives a managed World from a bare exact Play Run before Play mounts", async () => {
    const runId = "07a33f99-7520-4c59-bee2-b38514cb61b8";
    vi.mocked(getPlayRun).mockResolvedValue({
      run_id: runId,
      campaign_id: world.world_id,
    } as Awaited<ReturnType<typeof getPlayRun>>);
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [world] });
    expect(requestedWorldSelection(`/play?run=${runId}`).runId).toBe(runId);
    window.history.replaceState({}, "", `/play?run=${runId}`);
    render(
      <SelectedWorldProvider locationSnapshot={`/play?run=${runId}`}>
        <Probe />
      </SelectedWorldProvider>,
    );
    expect(screen.getByText("loading:none")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(`managed:${world.world_id}`)).toBeInTheDocument());
    expect(getPlayRun).toHaveBeenCalledExactlyOnceWith(runId);
    expect(new URLSearchParams(window.location.search).get("world")).toBe(world.world_id);
    expect(new URLSearchParams(window.location.search).get("run")).toBe(runId);
  });

  it("keeps a bare exact C2 Play Run on the legacy route", async () => {
    const runId = "07a33f99-7520-4c59-bee2-b38514cb61b8";
    vi.mocked(getPlayRun).mockResolvedValue({
      run_id: runId,
      campaign_id: "longmont-c2",
    } as Awaited<ReturnType<typeof getPlayRun>>);
    render(
      <SelectedWorldProvider locationSnapshot={`/play?run=${runId}`}>
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText("legacy:none")).toBeInTheDocument());
    expect(listWorldContainers).not.toHaveBeenCalled();
  });

  it("does not fall back to legacy when an exact Run cannot be verified", async () => {
    vi.mocked(getPlayRun).mockRejectedValue(new Error("Run not found"));
    render(
      <SelectedWorldProvider locationSnapshot="/play?run=unknown">
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText("error:none")).toBeInTheDocument());
    expect(listWorldContainers).not.toHaveBeenCalled();
  });

  it("derives a managed World from an exact Ingest extraction Run without a document query", async () => {
    const extractionRunId = "extraction-run-b";
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: extractionRunId,
      campaign_id: world.world_id,
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [world] });
    expect(requestedWorldSelection(`/ingest?extractionRunId=${extractionRunId}`).extractionRunId).toBe(extractionRunId);
    window.history.replaceState({}, "", `/ingest?extractionRunId=${extractionRunId}`);
    render(
      <SelectedWorldProvider locationSnapshot={`/ingest?extractionRunId=${extractionRunId}`}>
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText(`managed:${world.world_id}`)).toBeInTheDocument());
    expect(getExtractionRun).toHaveBeenCalledExactlyOnceWith(extractionRunId);
    expect(new URLSearchParams(window.location.search).get("world")).toBe(world.world_id);
    expect(new URLSearchParams(window.location.search).get("extractionRunId")).toBe(extractionRunId);
  });

  it("keeps exact C1/C2 extraction Run links on the legacy review route", async () => {
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: "legacy-run",
      campaign_id: "longmont-c1",
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    render(
      <SelectedWorldProvider locationSnapshot="/ingest?extractionRunId=legacy-run">
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText("legacy:none")).toBeInTheDocument());
    expect(listWorldContainers).not.toHaveBeenCalled();
  });

  it("does not treat an unbound extraction Run as legacy or a managed World", async () => {
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: "unbound-run",
      campaign_id: null,
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    render(
      <SelectedWorldProvider locationSnapshot="/ingest?extractionRunId=unbound-run">
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText("error:none")).toBeInTheDocument());
    expect(listWorldContainers).not.toHaveBeenCalled();
  });

  it("retries a registry failure without accepting stale content", async () => {
    vi.mocked(listWorldContainers)
      .mockRejectedValueOnce(new Error("registry offline"))
      .mockResolvedValueOnce({ schema_version: "dmb_world_container_registry_v1", records: [world] });
    render(
      <SelectedWorldProvider locationSnapshot={`/plan?world=${world.world_id}`}>
        <RecoveryProbe />
      </SelectedWorldProvider>,
    );
    expect(await screen.findByText("error")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("managed")).toBeInTheDocument();
    expect(listWorldContainers).toHaveBeenCalledTimes(2);
  });

  it("keeps C1/C2 exact documents legacy even with their Eldyrwild mapping", async () => {
    vi.mocked(getWorkspaceDocumentAny).mockResolvedValue({
      ...document,
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    render(
      <SelectedWorldProvider locationSnapshot={`/build?documentId=${document.document_id}`}>
        <RecoveryProbe />
      </SelectedWorldProvider>,
    );
    expect(await screen.findByText("legacy")).toBeInTheDocument();
    expect(listWorldContainers).not.toHaveBeenCalled();
  });
});

function AdmissionProbe() {
  const world = useSelectedWorld();
  const admission = useSelectedWorldAdmission();
  const retry = useRetrySelectedWorld();
  return <><output data-testid="identity">{world.kind}:{world.kind === 'managed' ? world.worldId : ''}:{world.kind === 'managed' ? world.documentId ?? '' : ''}</output>
    <output data-testid="admission">{admission.kind}</output><button onClick={retry}>Retry admission</button></>;
}
function deferred<T>() { let resolve!:(value:T)=>void; const promise=new Promise<T>(r=>{resolve=r}); return {promise,resolve}; }

describe('World lifetime and incoming page admission',()=>{
 it('retains only same verified World identity while a new document is pending, then rejects a mismatch',async()=>{
  vi.mocked(listWorldContainers).mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[world]});
  const view=render(<SelectedWorldProvider locationSnapshot={`/plan?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
  await waitFor(()=>expect(screen.getByTestId('admission')).toHaveTextContent('managed'));
  const gate=deferred<WorkspaceDocumentRecord>();vi.mocked(getWorkspaceDocumentAny).mockReturnValue(gate.promise);
  view.rerender(<SelectedWorldProvider locationSnapshot={`/plan?world=${world.world_id}&documentId=new-doc`}><AdmissionProbe/></SelectedWorldProvider>);
  expect(screen.getByTestId('identity')).toHaveTextContent(`managed:${world.world_id}:`);
  expect(screen.getByTestId('admission')).toHaveTextContent('loading');
  await act(async()=>gate.resolve({...document,document_id:'new-doc',world_id:'other',campaign_id:'other'}));
  await waitFor(()=>expect(screen.getByTestId('identity')).toHaveTextContent('error'));
  expect(screen.getByTestId('admission')).toHaveTextContent('error');expect(getWorldIdForCampaign(world.world_id)).toBeNull();
 });
 it('does not reacquire a verified World when navbar navigation drops a document or changes view/hash',async()=>{
  vi.mocked(listWorldContainers).mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[world]});vi.mocked(getWorkspaceDocumentAny).mockResolvedValue(document);
  const view=render(<SelectedWorldProvider locationSnapshot={`/build?world=${world.world_id}&documentId=${document.document_id}`}><AdmissionProbe/></SelectedWorldProvider>);
  await waitFor(()=>expect(screen.getByTestId('admission')).toHaveTextContent('managed'));
  view.rerender(<SelectedWorldProvider locationSnapshot={`/build?world=${world.world_id}&documentId=${document.document_id}&view=cards#scene`}><AdmissionProbe/></SelectedWorldProvider>);
  view.rerender(<SelectedWorldProvider locationSnapshot={`/play?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
  expect(screen.getByTestId('admission')).toHaveTextContent('managed');expect(screen.getByTestId('identity').textContent).toBe(`managed:${world.world_id}:`);
  expect(getWorkspaceDocumentAny).toHaveBeenCalledTimes(1);expect(listWorldContainers).toHaveBeenCalledTimes(1);
 });
 it('does not retire a pending read when only view/hash changes and canonicalizes the current URL',async()=>{
  const run=deferred<Awaited<ReturnType<typeof getPlayRun>>>();vi.mocked(getPlayRun).mockReturnValue(run.promise);
  vi.mocked(listWorldContainers).mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[world]});
  window.history.replaceState({},'', '/play?run=run-one');
  const view=render(<SelectedWorldProvider locationSnapshot="/play?run=run-one"><AdmissionProbe/></SelectedWorldProvider>);
  window.history.replaceState({},'', '/play?run=run-one&view=cards#second');
  view.rerender(<SelectedWorldProvider locationSnapshot="/play?run=run-one&view=cards#second"><AdmissionProbe/></SelectedWorldProvider>);
  await act(async()=>run.resolve({run_id:'run-one',campaign_id:world.world_id} as never));
  await waitFor(()=>expect(screen.getByTestId('admission')).toHaveTextContent('managed'));
  expect(getPlayRun).toHaveBeenCalledTimes(1);expect(window.location.hash).toBe('#second');
  expect(new URLSearchParams(window.location.search).get('view')).toBe('cards');expect(new URLSearchParams(window.location.search).get('world')).toBe(world.world_id);
 });
 it('retires private World identity synchronously for a different World and explicit retry',async()=>{
  vi.mocked(listWorldContainers).mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[world]});
  const view=render(<SelectedWorldProvider locationSnapshot={`/plan?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
  await waitFor(()=>expect(screen.getByTestId('admission')).toHaveTextContent('managed'));
  const gate=deferred<Awaited<ReturnType<typeof listWorldContainers>>>();vi.mocked(listWorldContainers).mockReturnValue(gate.promise);
  fireEvent.click(screen.getByRole('button',{name:'Retry admission'}));expect(screen.getByTestId('identity')).toHaveTextContent('loading');expect(getWorldIdForCampaign(world.world_id)).toBeNull();
  await act(async()=>gate.resolve({schema_version:'dmb_world_container_registry_v1',records:[world]}));await waitFor(()=>expect(screen.getByTestId('admission')).toHaveTextContent('managed'));
  vi.mocked(listWorldContainers).mockReturnValue(new Promise(()=>{}));
  view.rerender(<SelectedWorldProvider locationSnapshot="/plan?world=other"><AdmissionProbe/></SelectedWorldProvider>);
  expect(screen.getByTestId('identity')).toHaveTextContent('loading');expect(getWorldIdForCampaign(world.world_id)).toBeNull();
 });
});

it('rejects late inferred A→B→A responses and canonicalizes only the current admitted generation',async()=>{
 const first=deferred<Awaited<ReturnType<typeof getPlayRun>>>(),middle=deferred<Awaited<ReturnType<typeof getPlayRun>>>(),current=deferred<Awaited<ReturnType<typeof getPlayRun>>>();
 vi.mocked(getPlayRun).mockReturnValueOnce(first.promise).mockReturnValueOnce(middle.promise).mockReturnValueOnce(current.promise);
 vi.mocked(listWorldContainers).mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[world]});
 window.history.replaceState({},'','/play?run=A');const view=render(<SelectedWorldProvider locationSnapshot="/play?run=A"><AdmissionProbe/></SelectedWorldProvider>);
 window.history.replaceState({},'','/play?run=B');view.rerender(<SelectedWorldProvider locationSnapshot="/play?run=B"><AdmissionProbe/></SelectedWorldProvider>);
 window.history.replaceState({},'','/play?run=A&view=cards#current');view.rerender(<SelectedWorldProvider locationSnapshot="/play?run=A&view=cards#current"><AdmissionProbe/></SelectedWorldProvider>);
 await act(async()=>{first.resolve({run_id:'A',campaign_id:'wrong'} as never);middle.resolve({run_id:'B',campaign_id:'wrong'} as never)});
 expect(new URLSearchParams(window.location.search).has('world')).toBe(false);expect(listWorldContainers).not.toHaveBeenCalled();expect(screen.getByTestId('admission')).toHaveTextContent('loading');
 await act(async()=>current.resolve({run_id:'A',campaign_id:world.world_id} as never));
 await waitFor(()=>expect(screen.getByTestId('admission')).toHaveTextContent('managed'));
 expect(new URLSearchParams(window.location.search).get('world')).toBe(world.world_id);expect(window.location.hash).toBe('#current');expect(getPlayRun).toHaveBeenCalledTimes(3);expect(listWorldContainers).toHaveBeenCalledTimes(1);
});

it('retires an old World receipt at A→B-pending→A and requires the changed registry',async()=>{
 const middle=deferred<Awaited<ReturnType<typeof listWorldContainers>>>();
 vi.mocked(listWorldContainers).mockResolvedValueOnce({schema_version:'dmb_world_container_registry_v1',records:[world]}).mockReturnValueOnce(middle.promise).mockResolvedValueOnce({schema_version:'dmb_world_container_registry_v1',records:[]});
 const view=render(<SelectedWorldProvider locationSnapshot={`/play?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
 await waitFor(()=>expect(screen.getByTestId('identity')).toHaveTextContent('managed'));
 view.rerender(<SelectedWorldProvider locationSnapshot="/play?world=B"><AdmissionProbe/></SelectedWorldProvider>);
 expect(screen.getByTestId('identity')).toHaveTextContent('loading');
 view.rerender(<SelectedWorldProvider locationSnapshot={`/play?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
 expect(screen.getByTestId('identity')).toHaveTextContent('loading');
 await waitFor(()=>expect(screen.getByTestId('identity')).toHaveTextContent('error'));
 expect(listWorldContainers).toHaveBeenCalledTimes(3);
 await act(async()=>middle.resolve({schema_version:'dmb_world_container_registry_v1',records:[world]}));
 expect(screen.getByTestId('identity')).toHaveTextContent('error');expect(getWorldIdForCampaign(world.world_id)).toBeNull();
});
it.each(['clear','inference'] as const)('retires a receipt when leaving its explicit World for %s',async boundary=>{
 vi.mocked(listWorldContainers).mockResolvedValueOnce({schema_version:'dmb_world_container_registry_v1',records:[world]}).mockResolvedValueOnce({schema_version:'dmb_world_container_registry_v1',records:[]});
 const pending=deferred<Awaited<ReturnType<typeof getPlayRun>>>();vi.mocked(getPlayRun).mockReturnValueOnce(pending.promise);
 const view=render(<SelectedWorldProvider locationSnapshot={`/play?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
 await waitFor(()=>expect(screen.getByTestId('identity')).toHaveTextContent('managed'));
 view.rerender(<SelectedWorldProvider locationSnapshot={boundary==='clear'?'/':'/play?run=unverified'}><AdmissionProbe/></SelectedWorldProvider>);
 expect(screen.getByTestId('identity')).not.toHaveTextContent('managed');
 view.rerender(<SelectedWorldProvider locationSnapshot={`/play?world=${world.world_id}`}><AdmissionProbe/></SelectedWorldProvider>);
 expect(screen.getByTestId('identity')).toHaveTextContent('loading');
 await waitFor(()=>expect(screen.getByTestId('identity')).toHaveTextContent('error'));
 expect(listWorldContainers).toHaveBeenCalledTimes(2);
 await act(async()=>pending.resolve({run_id:'unverified',campaign_id:world.world_id} as never));
 expect(screen.getByTestId('identity')).toHaveTextContent('error');
});
