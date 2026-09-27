import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getExtractionRun, getPlayRun, getWorkspaceDocument, listWorldContainers } from "../api/liveApi";
import type { WorkspaceDocumentRecord, WorldContainerRecord } from "../api/types";
import { getWorldIdForCampaign } from "../worldGraph/worldGraphSurfaceContext";
import {
  SelectedWorldProvider,
  requestedWorldSelection,
  useRetrySelectedWorld,
  useSelectedWorld,
  verifyManagedWorldSelection,
} from "./SelectedWorldContext";

vi.mock("../api/liveApi", () => ({
  getExtractionRun: vi.fn(),
  getPlayRun: vi.fn(),
  getWorkspaceDocument: vi.fn(),
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
    const runId = "07a33f99-7520-4c59-bee2-b38514cb61b8";
    const view = render(
      <SelectedWorldProvider locationSnapshot={`/ingest?extractionRunId=${runId}&sourceArtifactId=artifact%3Aworldbuilding%3Asource&documentId=${document.document_id}&revision=2`}>
        <Probe />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(screen.getByText(`managed:${world.world_id}`)).toBeTruthy());
    expect(getWorkspaceDocument).toHaveBeenCalledWith(document.document_id);
    view.unmount();
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
    vi.mocked(getWorkspaceDocument).mockResolvedValue({
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
