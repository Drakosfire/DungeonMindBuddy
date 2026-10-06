import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getPlayActiveRun,
  getPlayRun,
  getCommittedWorkspaceRevision,
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedRunbookCommittedRevision,
  getWorldPlayRun,
  getWorldPlayRunReferenceManifest,
  listPlayRuns,
  listWorldPlayRuns,
  putPlayActiveRun,
  putWorldPlayRunRebase,
} from "../api/liveApi";
import { LiveApiError } from "../api/liveApi";
import type { WorldOwnedCommittedRevisionV2, WorldOwnedRunbookCommittedRevisionV2, WorldPlayRunRecordV2 } from "../api/types";
import { PlaySurfacePage } from "./PlaySurfacePage";

const selectedWorldHarness = vi.hoisted(() => ({ worldId: "world-b" }));

vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getPlayActiveRun: vi.fn(),
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
const artifactId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const workRevisionId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const newerWorkRevisionId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const shaA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const shaB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

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
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(listWorldPlayRuns).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(listPlayRuns).not.toHaveBeenCalled();
    expect(getWorldPlayRunReferenceManifest).toHaveBeenCalledWith(runId, "world-b");
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(artifactId, "world-b", 1, shaA);
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(artifactId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).toHaveBeenCalledWith(runId);
  });

  it("reopens an exact discarded World Plan revision without requiring the Plan to remain active or current", async () => {
    const planRun = worldRun({ playable_work_revision_id: workRevisionId });
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
      revision_n: 1,
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
      playable_revision: 1,
      playable_content_sha256: shaA,
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "scene", element_id: "scene:gate" },
      ],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockResolvedValue(committedPlan);

    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(getWorldOwnedPlanCommittedRevision).toHaveBeenCalledExactlyOnceWith(artifactId, 1);
    expect(getWorldOwnedRunbookCommittedRevision).not.toHaveBeenCalled();
    expect(putWorldPlayRunRebase).not.toHaveBeenCalled();
    expect(putPlayActiveRun).toHaveBeenCalledExactlyOnceWith(runId);
  });

  it("does not follow a global active Run from another World", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getPlayActiveRun).mockResolvedValue({ run_id: runId } as Awaited<ReturnType<typeof getPlayActiveRun>>);
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun({ world_id: "world-a" }));
    render(<PlaySurfacePage />);
    await waitFor(() => expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument());
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("keeps the World chooser when the active pointer cannot be resolved in World V2", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getPlayActiveRun).mockResolvedValue({ run_id: runId } as Awaited<ReturnType<typeof getPlayActiveRun>>);
    vi.mocked(getWorldPlayRun).mockRejectedValue(new Error("World detail unavailable"));
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent("Choose a Run explicitly");
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("ignores a late World V2 detail after navigation returns to the chooser", async () => {
    let resolveWorldRun: ((run: WorldPlayRunRecordV2) => void) | null = null;
    vi.mocked(getWorldPlayRun).mockImplementation(() => new Promise((resolve) => {
      resolveWorldRun = resolve;
    }));
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
