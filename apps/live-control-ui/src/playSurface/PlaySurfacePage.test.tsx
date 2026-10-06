import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getPlayActiveRun,
  getWorldPlayActiveRun,
  getPlayRun,
  getCommittedWorkspaceRevision,
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedRunbookCommittedRevision,
  getWorldPlayRun,
  getWorldPlayRunReferenceManifest,
  listPlayRuns,
  listWorldPlayRuns,
  putPlayActiveRun,
  putWorldPlayActiveRun,
  putWorldPlayRunProgress,
  putWorldPlayRunRebase,
} from "../api/liveApi";
import { LiveApiError } from "../api/liveApi";
import type { WorldOwnedCommittedRevisionV2, WorldOwnedRunbookCommittedRevisionV2, WorldPlayRunRecordV2 } from "../api/types";
import { PlaySurfacePage } from "./PlaySurfacePage";

const selectedWorldHarness = vi.hoisted(() => ({ worldId: "world-b" }));

vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getPlayActiveRun: vi.fn(),
  getWorldPlayActiveRun: vi.fn(),
  getPlayRun: vi.fn(),
  getPlayRunReferenceManifest: vi.fn(),
  getCommittedWorkspaceRevision: vi.fn(),
  getWorldOwnedPlanCommittedRevision: vi.fn(),
  listPlayRuns: vi.fn(),
  getWorldOwnedRunbookCommittedRevision: vi.fn(),
  getWorldPlayRun: vi.fn(),
  getWorldPlayRunReferenceManifest: vi.fn(),
  listWorldPlayRuns: vi.fn(),
  putWorldPlayRunRebase: vi.fn(),
  putPlayActiveRun: vi.fn(),
  putWorldPlayActiveRun: vi.fn(),
  putWorldPlayRunProgress: vi.fn(),
}));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => ({
    kind: "managed",
    worldId: selectedWorldHarness.worldId,
    name: `World ${selectedWorldHarness.worldId}`,
    documentId: null,
  }),
}));
vi.mock("../chrome/AppChrome", () => ({ AppChrome: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("../agentInteraction/usePublishAgentSurfaceContext", () => ({ usePublishAgentSurfaceContext: () => undefined }));
vi.mock("../agentInteraction/usePublishSurfaceInteraction", () => ({ usePublishSurfaceInteraction: () => undefined }));
vi.mock("../graphLens", () => ({ useOptionalWorldGraphLens: () => null }));
vi.mock("./StartRunPanel", () => ({ StartRunPanel: () => <div>Start Run</div> }));

const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const secondRunId = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const artifactId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const workRevisionId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const newerWorkRevisionId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const shaA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const shaB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

function worldActiveRun(run: string | null = runId, worldId = "world-b") {
  return {
    schema_version: "dmb_world_play_active_run_v2" as const,
    world_id: worldId,
    run_id: run,
    selected_at: run === null ? null : "2026-10-06T00:00:00Z",
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function worldRun(overrides: Partial<WorldPlayRunRecordV2> = {}): WorldPlayRunRecordV2 {
  return {
    schema_version: "dmb_world_play_run_record_v2",
    run_id: runId,
    world_id: "world-b",
    playable_artifact_id: artifactId,
    playable_revision: 1,
    playable_work_revision_id: workRevisionId,
    playable_content_sha256: shaA,
    run_revision: 1,
    created_at: "2026-09-30T00:00:00Z",
    updated_at: "2026-09-30T00:00:00Z",
    progress: {
      current_scene_id: null,
      current_beat_id: null,
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
    ...overrides,
  };
}

function worldCommitted(
  overrides: Partial<WorldOwnedRunbookCommittedRevisionV2> = {},
): WorldOwnedRunbookCommittedRevisionV2 {
  return {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: "world-b",
    document_id: artifactId,
    kind: "runbook",
    campaign_id: null,
    title: "North Gate",
    status: "active",
    object_revision: 1,
    work_revision_id: workRevisionId,
    revision_n: 1,
    markdown: "# Gate\n",
    content_sha256: shaA,
    has_divergent_working_copy: false,
    target_relpath: null,
    ...overrides,
  };
}

const worldPlayableMarkdown = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
  "## Gate",
  "",
  "A held north gate.",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
  "### Approach",
  "",
  "The wardens wait.",
  "",
].join("\n");

function mockReadyWorldRuns(runIds: string[] = [runId]) {
  vi.mocked(listWorldPlayRuns).mockResolvedValue({
    schema_version: "dmb_world_play_runs_list_v2",
    records: runIds.map((selectedRunId) => worldRun({ run_id: selectedRunId })),
  });
  vi.mocked(getWorldPlayRun).mockImplementation(async (selectedRunId) => worldRun({ run_id: selectedRunId }));
  vi.mocked(getWorldPlayRunReferenceManifest).mockImplementation(async (selectedRunId) => ({
    schema_version: "dmb_play_run_reference_manifest_v1",
    run_id: selectedRunId,
    playable_artifact_id: artifactId,
    playable_revision: 1,
    playable_content_sha256: shaA,
    elements: [
      { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
      { kind: "scene", element_id: "scene:gate" },
    ],
    sealed_at: "2026-09-30T00:00:00Z",
  }));
  vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(
    worldCommitted({ markdown: worldPlayableMarkdown }),
  );
}

describe("Play selected-World admission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    selectedWorldHarness.worldId = "world-b";
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockRejectedValue(new LiveApiError("Plan revision not found", 404));
    vi.mocked(listPlayRuns).mockResolvedValue({ records: [] } as Awaited<ReturnType<typeof listPlayRuns>>);
    vi.mocked(listWorldPlayRuns).mockResolvedValue({
      schema_version: "dmb_world_play_runs_list_v2",
      records: [],
    });
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
  });

  it("rejects a foreign World V2 Run without using campaign V1", async () => {
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun({ world_id: "world-a" }));
    render(<PlaySurfacePage />);
    expect(await screen.findByText(`Run ${runId} does not belong to World world-b.`)).toBeInTheDocument();
    expect(getWorldPlayRun).toHaveBeenCalledExactlyOnceWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("lists, selects, and resumes a World V2 Run from its exact World Runbook pin", async () => {
    const committed = worldCommitted({ markdown: worldPlayableMarkdown });
    window.history.replaceState({}, "", "/play?world=world-b&choose=1");
    vi.mocked(listWorldPlayRuns).mockResolvedValue({
      schema_version: "dmb_world_play_runs_list_v2",
      records: [worldRun()],
    });
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(committed);

    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    const listedRun = await screen.findByRole("link", { name: new RegExp(runId) });
    expect(listedRun).toHaveTextContent("World world-b");
    await user.click(listedRun);

    const ready = await screen.findByTestId("play-surface-ready");
    expect(ready).toHaveAttribute("data-play-campaign-id", "");
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(screen.getByTestId("play-source-cue")).toHaveTextContent("Created from saved Runbook version 1");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(listWorldPlayRuns).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(listPlayRuns).not.toHaveBeenCalled();
    expect(getWorldPlayRunReferenceManifest).toHaveBeenCalledWith(runId, "world-b");
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(artifactId, "world-b", 1, shaA);
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(artifactId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).toHaveBeenCalledWith("world-b", runId);
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("reenters the exact World Run through the scoped active pointer and validates its detail", async () => {
    const committed = worldCommitted({ markdown: worldPlayableMarkdown });
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(committed);

    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(getWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(getWorldPlayRun).toHaveBeenCalledTimes(2);
    expect(getWorldPlayRun).toHaveBeenNthCalledWith(1, runId, "world-b");
    expect(getWorldPlayRun).toHaveBeenNthCalledWith(2, runId, "world-b");
    expect(window.location.search).toBe(`?world=world-b&run=${runId}`);
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
    expect(getPlayActiveRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("selects the same Run again after another World pointer is read and the chooser is reopened", async () => {
    mockReadyWorldRuns([runId, secondRunId]);
    vi.mocked(getWorldPlayActiveRun).mockResolvedValueOnce(worldActiveRun(secondRunId));
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId));

    await act(async () => {
      window.history.pushState({}, "", "/play?world=world-b");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(window.location.search).toBe(`?world=world-b&run=${secondRunId}`));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("play-start-new-run"));
    const firstRun = await screen.findByRole("link", { name: new RegExp(runId) });
    await user.click(firstRun);
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();

    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2));
    expect(putWorldPlayActiveRun).toHaveBeenLastCalledWith("world-b", runId);
  });

  it("allows an explicit same-Run selection to retry after the active-pointer PUT fails", async () => {
    mockReadyWorldRuns([runId]);
    vi.mocked(putWorldPlayActiveRun)
      .mockRejectedValueOnce(new Error("pointer write failed"))
      .mockResolvedValue(worldActiveRun());
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-save-warning")).toHaveTextContent("pointer write failed");
    expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId);

    await user.click(screen.getByTestId("play-start-new-run"));
    await user.click(await screen.findByRole("link", { name: new RegExp(runId) }));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();

    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2));
    expect(putWorldPlayActiveRun).toHaveBeenLastCalledWith("world-b", runId);
  });

  it("does not repeat the active-pointer PUT when a same-Run progress update triggers re-admission", async () => {
    mockReadyWorldRuns([runId]);
    vi.mocked(putWorldPlayRunProgress).mockResolvedValue(worldRun({
      run_revision: 2,
      playable_revision: 2,
      playable_work_revision_id: newerWorkRevisionId,
      playable_content_sha256: shaB,
    }));
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId));
    await user.click(screen.getByRole("button", { name: "Set current Scene" }));

    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledTimes(2));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId);
  });

  it("keeps a newer World selection fence when an older active-pointer PUT fails late", async () => {
    mockReadyWorldRuns([runId, secondRunId]);
    const firstSelection = deferred<Awaited<ReturnType<typeof putWorldPlayActiveRun>>>();
    vi.mocked(putWorldPlayActiveRun).mockImplementation(async (_worldId, selectedRunId) => {
      if (selectedRunId === runId) return firstSelection.promise;
      return worldActiveRun(selectedRunId);
    });
    vi.mocked(putWorldPlayRunProgress).mockResolvedValue(worldRun({
      run_id: secondRunId,
      run_revision: 2,
      playable_revision: 2,
      playable_work_revision_id: newerWorkRevisionId,
      playable_content_sha256: shaB,
    }));
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId));
    await user.click(screen.getByTestId("play-start-new-run"));
    await user.click(await screen.findByRole("link", { name: new RegExp(secondRunId) }));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();

    await act(async () => {
      firstSelection.reject(new Error("stale pointer PUT failed"));
    });
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2));
    expect(putWorldPlayActiveRun).toHaveBeenLastCalledWith("world-b", secondRunId);

    await user.click(screen.getByRole("button", { name: "Set current Scene" }));
    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledTimes(3));
    expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2);
  });

  it("keeps the exact saved Plan source cue at version 3 after the current Plan advances to 4", async () => {
    const planRun = worldRun({ playable_revision: 3, run_revision: 2, playable_work_revision_id: workRevisionId });
    const committedPlan: WorldOwnedCommittedRevisionV2 = {
      schema_version: "dmb_workspace_committed_revision_v2",
      scope_mode: "world",
      world_id: "world-b",
      campaign_id: null,
      document_id: artifactId,
      kind: "plan",
      title: "North Gate Plan",
      status: "discarded",
      object_revision: 9,
      work_revision_id: workRevisionId,
      revision_n: 3,
      markdown: worldPlayableMarkdown,
      content_sha256: shaA,
      has_divergent_working_copy: true,
      target_relpath: null,
    };
    vi.mocked(getWorldPlayRun).mockResolvedValue(planRun);
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 3,
      playable_content_sha256: shaA,
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    const currentPlan = {
      ...committedPlan,
      status: "active" as const,
      object_revision: 10,
      work_revision_id: newerWorkRevisionId,
      revision_n: 4,
      content_sha256: shaB,
    };
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockImplementation(async (_documentId, revisionN) => (
      revisionN === undefined ? currentPlan : committedPlan
    ));

    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(screen.getByTestId("play-source-cue")).toHaveTextContent("Created from saved Plan version 3");
    expect(screen.queryByText(/version 4/)).not.toBeInTheDocument();
    expect(getWorldOwnedPlanCommittedRevision).toHaveBeenCalledExactlyOnceWith(artifactId, 3);
    expect(getWorldOwnedRunbookCommittedRevision).not.toHaveBeenCalled();
    expect(putWorldPlayRunRebase).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId);
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("keeps a chooser when World active detail belongs to another World", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun({ world_id: "world-a" }));
    render(<PlaySurfacePage />);
    await waitFor(() => expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument());
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(getPlayActiveRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("uses the empty World v2 pointer as an explicit chooser state", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun(null));
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayRun).not.toHaveBeenCalled();
    expect(getPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("does not navigate through an invalid World active pointer", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue({
      ...worldActiveRun(),
      run_id: "not-a-canonical-run-id",
    });
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent("malformed");
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("keeps the World chooser when the active pointer cannot be resolved in World V2", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    vi.mocked(getWorldPlayRun).mockRejectedValue(new Error("World detail unavailable"));
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent("Choose a Run explicitly");
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("ignores a late World V2 detail after navigation returns to the chooser", async () => {
    let resolveWorldRun: ((run: WorldPlayRunRecordV2) => void) | null = null;
    vi.mocked(getWorldPlayRun).mockImplementation(() => new Promise((resolve) => {
      resolveWorldRun = resolve;
    }));
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    render(<PlaySurfacePage />);
    expect(await screen.findByTestId("play-status-loading")).toBeInTheDocument();

    await act(async () => {
      window.history.pushState({}, "", "/play?world=world-b&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await act(async () => {
      resolveWorldRun?.(worldRun());
    });

    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b"));
    expect(screen.queryByTestId("play-surface-ready")).not.toBeInTheDocument();
    expect(getWorldPlayRunReferenceManifest).not.toHaveBeenCalled();
    expect(getWorldOwnedRunbookCommittedRevision).not.toHaveBeenCalled();
    expect(getPlayRun).not.toHaveBeenCalled();
  });

  it("offers an explicit same-World rebase and keeps the exact Run on conflict", async () => {
    const exact = worldCommitted();
    const current = worldCommitted({
      object_revision: 2,
      work_revision_id: newerWorkRevisionId,
      revision_n: 2,
      content_sha256: shaB,
      markdown: "# New Gate\n",
    });
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      elements: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision)
      .mockResolvedValueOnce(exact)
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(current);
    vi.mocked(putWorldPlayRunRebase).mockRejectedValue(new Error("revision changed"));
    vi.mocked(getWorldPlayRun).mockResolvedValueOnce(worldRun()).mockResolvedValueOnce(worldRun());

    const user = userEvent.setup();
    render(<PlaySurfacePage />);
    const rebase = await screen.findByTestId("play-world-run-rebase");
    expect(screen.getByText(/pinned to revision 1/)).toBeInTheDocument();
    await user.click(rebase);

    expect(putWorldPlayRunRebase).toHaveBeenCalledWith(runId, "world-b", {
      expected_run_revision: 1,
      target_playable_revision: 2,
      target_playable_content_sha256: shaB,
    });
    await waitFor(() => expect(screen.getByText(/revision changed/)).toBeInTheDocument());
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(getCommittedWorkspaceRevision).not.toHaveBeenCalled();
    expect(getWorldPlayRun).toHaveBeenCalledTimes(2);
  });

  it("does not adopt a completed World B rebase after the route switches to World A", async () => {
    const exact = worldCommitted();
    const current = worldCommitted({
      object_revision: 2,
      work_revision_id: newerWorkRevisionId,
      revision_n: 2,
      content_sha256: shaB,
      markdown: "# New Gate\n",
    });
    const pendingRebase = deferred<WorldPlayRunRecordV2>();
    vi.mocked(getWorldPlayRun).mockResolvedValueOnce(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      elements: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision)
      .mockResolvedValueOnce(exact)
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(current);
    vi.mocked(putWorldPlayRunRebase).mockReturnValueOnce(pendingRebase.promise);

    const user = userEvent.setup();
    const view = render(<PlaySurfacePage />);
    await user.click(await screen.findByTestId("play-world-run-rebase"));
    await waitFor(() => expect(putWorldPlayRunRebase).toHaveBeenCalledWith(runId, "world-b", {
      expected_run_revision: 1,
      target_playable_revision: 2,
      target_playable_content_sha256: shaB,
    }));

    await act(async () => {
      selectedWorldHarness.worldId = "world-a";
      window.history.replaceState({}, "", "/play?world=world-a&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
      view.rerender(<PlaySurfacePage />);
    });
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await waitFor(() => expect(listWorldPlayRuns).toHaveBeenCalledWith("world-a"));

    await act(async () => {
      pendingRebase.resolve(worldRun({
        playable_revision: 2,
        playable_work_revision_id: newerWorkRevisionId,
        playable_content_sha256: shaB,
        run_revision: 2,
        rebased_from_run_revision: 1,
      }));
      await pendingRebase.promise;
    });

    expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.search).toBe("?world=world-a&choose=1");
    expect(getWorldPlayRun).toHaveBeenCalledExactlyOnceWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(listPlayRuns).not.toHaveBeenCalled();
  });

  it("does not adopt World B after an uncertain rebase is confirmed by exact reconciliation", async () => {
    const exact = worldCommitted();
    const current = worldCommitted({
      object_revision: 2,
      work_revision_id: newerWorkRevisionId,
      revision_n: 2,
      content_sha256: shaB,
      markdown: "# New Gate\n",
    });
    const pendingRebase = deferred<WorldPlayRunRecordV2>();
    const pendingReconciliation = deferred<WorldPlayRunRecordV2>();
    vi.mocked(getWorldPlayRun)
      .mockResolvedValueOnce(worldRun())
      .mockReturnValueOnce(pendingReconciliation.promise);
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      elements: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision)
      .mockResolvedValueOnce(exact)
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(current);
    vi.mocked(putWorldPlayRunRebase).mockReturnValueOnce(pendingRebase.promise);

    const user = userEvent.setup();
    const view = render(<PlaySurfacePage />);
    await user.click(await screen.findByTestId("play-world-run-rebase"));
    await waitFor(() => expect(putWorldPlayRunRebase).toHaveBeenCalledWith(runId, "world-b", {
      expected_run_revision: 1,
      target_playable_revision: 2,
      target_playable_content_sha256: shaB,
    }));

    await act(async () => {
      selectedWorldHarness.worldId = "world-a";
      window.history.replaceState({}, "", "/play?world=world-a&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
      view.rerender(<PlaySurfacePage />);
    });
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await waitFor(() => expect(listWorldPlayRuns).toHaveBeenCalledWith("world-a"));

    await act(async () => {
      pendingRebase.reject(new Error("rebase response lost"));
    });
    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledTimes(2));
    await act(async () => {
      pendingReconciliation.resolve(worldRun({
        playable_revision: 2,
        playable_work_revision_id: newerWorkRevisionId,
        playable_content_sha256: shaB,
        run_revision: 2,
        rebased_from_run_revision: 1,
      }));
      await pendingReconciliation.promise;
    });

    expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.search).toBe("?world=world-a&choose=1");
    expect(getWorldPlayRun).toHaveBeenCalledTimes(2);
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(listPlayRuns).not.toHaveBeenCalled();
  });
});
