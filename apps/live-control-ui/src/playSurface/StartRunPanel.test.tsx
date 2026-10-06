import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../api/liveApi";
import type {
  PlayRunRecord,
  PlayRunReferenceManifest,
  WorldOwnedCommittedRevisionV2,
  WorldOwnedPlanRecordV2,
  WorldOwnedRunbookCommittedRevisionV2,
  WorldOwnedRunbookRecordV2,
  WorldPlayRunRecordV2,
  WorkspaceCommittedRevision,
  WorkspaceDocumentRecord,
} from "../api/types";
import { StartRunPanel } from "./StartRunPanel";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    listWorkspaceDocuments: vi.fn(),
    getCommittedWorkspaceRevision: vi.fn(),
    getWorldOwnedPlanCommittedRevision: vi.fn(),
    getWorldOwnedRunbookCommittedRevision: vi.fn(),
    listWorldOwnedPlans: vi.fn(),
    listWorldOwnedRunbooks: vi.fn(),
    putWorldPlayRun: vi.fn(),
    putWorldPlayRunReferenceManifest: vi.fn(),
    getWorldPlayRun: vi.fn(),
    getWorldPlayRunReferenceManifest: vi.fn(),
    putPlayRun: vi.fn(),
    putPlayRunReferenceManifest: vi.fn(),
    getPlayRun: vi.fn(),
    getPlayRunReferenceManifest: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    createWorldOwnedRunbook: vi.fn(),
    prepareWorldRunbookMarkdownWrite: vi.fn(),
    commitWorldRunbookMarkdownWrite: vi.fn(),
    getWorldOwnedRunbookSnapshot: vi.fn(),
  };
});

import * as liveApi from "../api/liveApi";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const DOC_A = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const DOC_B = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const DOC_CREATED = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const SHA_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const WORLD_ID = "longmont-c2";
const WORLD_WORK_REVISION_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function runbook(documentId: string, title: string): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: documentId,
    title,
    campaign_id: "longmont-c2",
    target_session: 23,
    kind: "runbook",
    target_relpath: `out/workspace/runbooks/${documentId}.md`,
    status: "active",
    content_status: "committed",
    revision: 7,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
  };
}

function committedFor(documentId: string): WorkspaceCommittedRevision {
  return {
    schema_version: "dmb_workspace_committed_revision_v1",
    document_id: documentId,
    kind: "runbook",
    campaign_id: "longmont-c2",
    title: "North Gate",
    status: "active",
    object_revision: 7,
    work_revision_id: "11111111-1111-4111-8111-111111111111",
    revision_n: 7,
    markdown: "# Gate\n",
    content_sha256: SHA_A,
    has_divergent_working_copy: false,
    target_relpath: `out/workspace/runbooks/${documentId}.md`,
  };
}

function playRun(): PlayRunRecord {
  return {
    schema_version: "dmb_play_run_record_v1",
    run_id: RUN_ID,
    campaign_id: "longmont-c2",
    playable_artifact_id: DOC_A,
    playable_revision: 7,
    playable_content_sha256: SHA_A,
    run_revision: 1,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
    progress: {
      current_scene_id: null,
      current_beat_id: null,
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
  };
}

function playManifest(): PlayRunReferenceManifest {
  const run = playRun();
  return {
    schema_version: "dmb_play_run_reference_manifest_v1",
    run_id: run.run_id,
    playable_artifact_id: run.playable_artifact_id,
    playable_revision: run.playable_revision,
    playable_content_sha256: run.playable_content_sha256,
    elements: [{ kind: "scene", element_id: "scene:gate" }],
    sealed_at: "2026-08-17T00:00:00Z",
  };
}

function worldRunbook(documentId: string = DOC_A, worldId: string = WORLD_ID): WorldOwnedRunbookRecordV2 {
  return {
    schema_version: "dmb_world_owned_runbook_record_v2",
    scope_mode: "world",
    document_id: documentId,
    title: "World North Gate",
    campaign_id: null,
    world_id: worldId,
    target_session: null,
    kind: "runbook",
    target_relpath: null,
    status: "active",
    content_status: "committed",
    revision: 7,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
  };
}

function worldPlanRecord(documentId: string = DOC_A, worldId: string = WORLD_ID): WorldOwnedPlanRecordV2 {
  return {
    schema_version: "dmb_world_owned_plan_record_v2",
    scope_mode: "world",
    document_id: documentId,
    title: "World Plan",
    campaign_id: null,
    world_id: worldId,
    target_session: null,
    kind: "plan",
    target_relpath: null,
    status: "active",
    content_status: "committed",
    revision: 7,
    created_at: "2026-10-06T00:00:00Z",
    updated_at: "2026-10-06T00:00:00Z",
  };
}

function worldPlanCommittedFor(documentId: string = DOC_A, worldId: string = WORLD_ID): WorldOwnedCommittedRevisionV2 {
  return {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    kind: "plan",
    campaign_id: null,
    title: "World Plan",
    status: "active",
    object_revision: 8,
    work_revision_id: WORLD_WORK_REVISION_ID,
    revision_n: 7,
    markdown: "# Plan\n",
    content_sha256: SHA_A,
    has_divergent_working_copy: false,
    target_relpath: null,
  };
}

function worldCommittedFor(documentId: string, worldId: string = WORLD_ID): WorldOwnedRunbookCommittedRevisionV2 {
  return {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    kind: "runbook",
    campaign_id: null,
    title: "World North Gate",
    status: "active",
    object_revision: 7,
    work_revision_id: WORLD_WORK_REVISION_ID,
    revision_n: 7,
    markdown: "# Gate\n",
    content_sha256: SHA_A,
    has_divergent_working_copy: false,
    target_relpath: null,
  };
}

function worldPlayRun(worldId: string = WORLD_ID): WorldPlayRunRecordV2 {
  return {
    schema_version: "dmb_world_play_run_record_v2",
    run_id: RUN_ID,
    world_id: worldId,
    playable_artifact_id: DOC_A,
    playable_revision: 7,
    playable_work_revision_id: WORLD_WORK_REVISION_ID,
    playable_content_sha256: SHA_A,
    run_revision: 1,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
    progress: {
      current_scene_id: null,
      current_beat_id: null,
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
  };
}

function worldPlayManifest(): PlayRunReferenceManifest {
  const run = worldPlayRun();
  return {
    schema_version: "dmb_play_run_reference_manifest_v1",
    run_id: run.run_id,
    playable_artifact_id: run.playable_artifact_id,
    playable_revision: run.playable_revision,
    playable_content_sha256: run.playable_content_sha256,
    elements: [{ kind: "scene", element_id: "scene:gate" }],
    sealed_at: "2026-08-17T00:00:00Z",
  };
}

describe("StartRunPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(RUN_ID);
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [runbook(DOC_A, "North Gate"), runbook(DOC_B, "South Wall")],
    });
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockImplementation(async (documentId) => committedFor(documentId));
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockResolvedValue({
      schema_version: "dmb_world_owned_runbooks_list_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      records: [],
    });
    vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      records: [],
    });
    vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockImplementation(
      async (documentId) => worldPlanCommittedFor(documentId),
    );
    vi.mocked(liveApi.getWorldOwnedRunbookCommittedRevision).mockImplementation(
      async (documentId, worldId = WORLD_ID) => worldCommittedFor(documentId, worldId),
    );
    vi.mocked(liveApi.putWorldPlayRun).mockResolvedValue(worldPlayRun());
    vi.mocked(liveApi.getWorldPlayRun).mockResolvedValue(worldPlayRun());
    vi.mocked(liveApi.putWorldPlayRunReferenceManifest).mockResolvedValue(worldPlayManifest());
    vi.mocked(liveApi.getWorldPlayRunReferenceManifest).mockResolvedValue(worldPlayManifest());
    vi.mocked(liveApi.putPlayRun).mockResolvedValue(playRun());
    vi.mocked(liveApi.putPlayRunReferenceManifest).mockResolvedValue(playManifest());
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(playRun());
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockResolvedValue(playManifest());
  });

  it("ignores a late World A Runbook list after the selected World changes to B", async () => {
    type WorldList = Awaited<ReturnType<typeof liveApi.listWorldOwnedRunbooks>>;
    const worldAList = deferred<WorldList>();
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockImplementation(async (worldId) => {
      if (worldId === "world-a") return worldAList.promise;
      return {
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: "world-b",
        records: [worldRunbook(DOC_B, "world-b")],
      };
    });
    const view = render(<StartRunPanel onStarted={vi.fn()} verifiedWorldId="world-a" />);
    await waitFor(() => expect(liveApi.listWorldOwnedRunbooks).toHaveBeenCalledWith("world-a"));

    view.rerender(<StartRunPanel onStarted={vi.fn()} verifiedWorldId="world-b" />);
    expect(await screen.findByTestId(`play-start-runbook-${DOC_B}`)).toBeInTheDocument();
    await act(async () => {
      worldAList.resolve({
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: "world-a",
        records: [worldRunbook(DOC_A, "world-a")],
      });
      await worldAList.promise;
    });

    expect(screen.getByTestId(`play-start-runbook-${DOC_B}`)).toBeInTheDocument();
    expect(screen.queryByTestId(`play-start-runbook-${DOC_A}`)).not.toBeInTheDocument();
    expect(liveApi.listWorkspaceDocuments).not.toHaveBeenCalled();
  });

  it("does not navigate to a World A Run when its create and seal finish after switching to B", async () => {
    const pendingWorldCreate = deferred<WorldPlayRunRecordV2>();
    const pendingWorldManifest = deferred<PlayRunReferenceManifest>();
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockImplementation(async (worldId) => ({
      schema_version: "dmb_world_owned_runbooks_list_v2",
      scope_mode: "world",
      world_id: worldId,
      records: [worldRunbook(worldId === "world-a" ? DOC_A : DOC_B, worldId)],
    }));
    vi.mocked(liveApi.getWorldOwnedRunbookCommittedRevision).mockImplementation(
      async (documentId, worldId = WORLD_ID) => worldCommittedFor(documentId, worldId),
    );
    vi.mocked(liveApi.putWorldPlayRun).mockReturnValueOnce(pendingWorldCreate.promise);
    vi.mocked(liveApi.putWorldPlayRunReferenceManifest).mockReturnValueOnce(pendingWorldManifest.promise);
    const onStarted = vi.fn();
    const user = userEvent.setup();
    const view = render(<StartRunPanel onStarted={onStarted} verifiedWorldId="world-a" />);

    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    await user.click(screen.getByTestId("play-start-run-submit"));
    await waitFor(() => expect(liveApi.putWorldPlayRun).toHaveBeenCalledWith(
      RUN_ID,
      "world-a",
      expect.objectContaining({ playable_artifact_id: DOC_A }),
    ));

    view.rerender(<StartRunPanel onStarted={onStarted} verifiedWorldId="world-b" />);
    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_B}`));
    await act(async () => {
      pendingWorldCreate.resolve(worldPlayRun("world-a"));
      await pendingWorldCreate.promise;
    });
    await waitFor(() => expect(liveApi.putWorldPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID, "world-a"));
    await act(async () => {
      pendingWorldManifest.resolve(worldPlayManifest());
      await pendingWorldManifest.promise;
    });

    expect(screen.getByTestId(`play-start-runbook-${DOC_B}`)).toHaveAttribute("aria-pressed", "true");
    expect(onStarted).not.toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("keeps a World B selection when a World A blank Runbook create finishes late", async () => {
    const pendingWorldCreate = deferred<WorldOwnedRunbookRecordV2>();
    const blank = worldRunbook(DOC_A, "world-a");
    const committedBlank = { ...blank, content_status: "committed" as const };
    let worldAListReads = 0;
    let committedWorldA: WorldOwnedRunbookRecordV2 | null = null;
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockImplementation(async (worldId) => {
      const records = worldId === "world-a"
        ? (worldAListReads++ > 0 && committedWorldA ? [committedWorldA] : [])
        : [worldRunbook(DOC_B, "world-b")];
      return {
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: worldId,
        records,
      };
    });
    vi.mocked(liveApi.createWorldOwnedRunbook).mockReturnValueOnce(pendingWorldCreate.promise);
    vi.mocked(liveApi.prepareWorldRunbookMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v2",
      scope_mode: "world",
      world_id: "world-a",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "world-a-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitWorldRunbookMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: "world-a",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: committedBlank,
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    const user = userEvent.setup();
    const view = render(<StartRunPanel onStarted={vi.fn()} verifiedWorldId="world-a" />);
    await screen.findByTestId("play-start-run-empty");
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));
    await waitFor(() => expect(liveApi.createWorldOwnedRunbook).toHaveBeenCalledWith({
      world_id: "world-a",
      title: "Blank Runbook",
    }));

    view.rerender(<StartRunPanel onStarted={vi.fn()} verifiedWorldId="world-b" />);
    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_B}`));
    await act(async () => {
      pendingWorldCreate.resolve(blank);
      await pendingWorldCreate.promise;
    });
    await waitFor(() => expect(liveApi.commitWorldRunbookMarkdownWrite).toHaveBeenCalledWith(
      "world-a",
      expect.objectContaining({ document_id: DOC_A }),
    ));
    committedWorldA = committedBlank;

    expect(await screen.findByTestId(`play-start-runbook-${DOC_B}`)).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId(`play-start-runbook-${DOC_A}`)).not.toBeInTheDocument();
    expect(liveApi.listWorldOwnedRunbooks.mock.calls.map(([worldId]) => worldId)).toEqual([
      "world-a",
      "world-b",
    ]);
    expect(liveApi.createWorldOwnedRunbook).toHaveBeenCalledWith({ world_id: "world-a", title: "Blank Runbook" });
    expect(liveApi.prepareWorldRunbookMarkdownWrite).toHaveBeenCalledWith(
      "world-a",
      expect.objectContaining({ document_id: DOC_A }),
    );
    expect(liveApi.listWorkspaceDocuments).not.toHaveBeenCalled();

    view.rerender(<StartRunPanel onStarted={vi.fn()} verifiedWorldId="world-a" />);
    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toBeInTheDocument();
    expect(liveApi.listWorldOwnedRunbooks.mock.calls.map(([worldId]) => worldId)).toEqual([
      "world-a",
      "world-b",
      "world-a",
    ]);
  });

  it("does not navigate from a stale Start Run after the selected Runbook changes A to B and back to A within one World", async () => {
    const pendingWorldCreate = deferred<WorldPlayRunRecordV2>();
    const pendingWorldManifest = deferred<PlayRunReferenceManifest>();
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockResolvedValue({
      schema_version: "dmb_world_owned_runbooks_list_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      records: [
        worldRunbook(DOC_A, WORLD_ID),
        worldRunbook(DOC_B, WORLD_ID),
      ],
    });
    vi.mocked(liveApi.putWorldPlayRun).mockReturnValueOnce(pendingWorldCreate.promise);
    vi.mocked(liveApi.putWorldPlayRunReferenceManifest).mockReturnValueOnce(pendingWorldManifest.promise);
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} verifiedWorldId={WORLD_ID} />);

    await user.click(await screen.findByTestId("play-start-runbook-" + DOC_A));
    await user.click(screen.getByTestId("play-start-run-submit"));
    await waitFor(() => expect(liveApi.putWorldPlayRun).toHaveBeenCalledWith(
      RUN_ID,
      WORLD_ID,
      expect.objectContaining({ playable_artifact_id: DOC_A }),
    ));

    await user.click(screen.getByTestId("play-start-runbook-" + DOC_B));
    await user.click(screen.getByTestId("play-start-runbook-" + DOC_A));
    expect(screen.getByTestId("play-start-runbook-" + DOC_A)).toHaveAttribute("aria-pressed", "true");

    await act(async () => {
      pendingWorldCreate.resolve(worldPlayRun(WORLD_ID));
      await pendingWorldCreate.promise;
    });
    await waitFor(() => expect(liveApi.putWorldPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID, WORLD_ID));
    await act(async () => {
      pendingWorldManifest.resolve(worldPlayManifest());
      await pendingWorldManifest.promise;
    });

    expect(onStarted).not.toHaveBeenCalled();
    expect(screen.getByTestId("play-start-runbook-" + DOC_A)).toHaveAttribute("aria-pressed", "true");
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("does not select a blank Runbook after the selected Runbook changes A to B and back to A within one World", async () => {
    const pendingWorldCreate = deferred<WorldOwnedRunbookRecordV2>();
    const created = { ...worldRunbook(DOC_CREATED, WORLD_ID), content_status: "draft" as const };
    const committed = { ...created, content_status: "committed" as const };
    vi.mocked(liveApi.listWorldOwnedRunbooks)
      .mockResolvedValueOnce({
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: WORLD_ID,
        records: [
          worldRunbook(DOC_A, WORLD_ID),
          worldRunbook(DOC_B, WORLD_ID),
        ],
      })
      .mockResolvedValueOnce({
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: WORLD_ID,
        records: [
          worldRunbook(DOC_A, WORLD_ID),
          worldRunbook(DOC_B, WORLD_ID),
          committed,
        ],
      });
    vi.mocked(liveApi.createWorldOwnedRunbook).mockReturnValueOnce(pendingWorldCreate.promise);
    vi.mocked(liveApi.prepareWorldRunbookMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      document_id: DOC_CREATED,
      title: created.title,
      target_relpath: "runbook:" + DOC_CREATED,
      target_display_path: "runbook:" + DOC_CREATED,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "created-runbook-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitWorldRunbookMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      document_id: DOC_CREATED,
      title: created.title,
      target_relpath: "runbook:" + DOC_CREATED,
      target_display_path: "runbook:" + DOC_CREATED,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: committed,
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} verifiedWorldId={WORLD_ID} />);

    await user.click(await screen.findByTestId("play-start-runbook-" + DOC_A));
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));
    await waitFor(() => expect(liveApi.createWorldOwnedRunbook).toHaveBeenCalledWith({
      world_id: WORLD_ID,
      title: "Blank Runbook",
    }));

    await user.click(screen.getByTestId("play-start-runbook-" + DOC_B));
    await user.click(screen.getByTestId("play-start-runbook-" + DOC_A));
    expect(screen.getByTestId("play-start-runbook-" + DOC_A)).toHaveAttribute("aria-pressed", "true");

    await act(async () => {
      pendingWorldCreate.resolve(created);
      await pendingWorldCreate.promise;
    });
    await waitFor(() => expect(liveApi.commitWorldRunbookMarkdownWrite).toHaveBeenCalledWith(
      WORLD_ID,
      expect.objectContaining({ document_id: DOC_CREATED }),
    ));

    expect(await screen.findByTestId("play-start-runbook-" + DOC_CREATED)).toBeInTheDocument();
    expect(screen.getByTestId("play-start-runbook-" + DOC_A)).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("play-start-runbook-" + DOC_CREATED)).toHaveAttribute("aria-pressed", "false");
    expect(liveApi.listWorkspaceDocuments).not.toHaveBeenCalled();
  });

  it("does not write until an explicit Runbook is chosen and started", async () => {
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);

    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toBeInTheDocument();
    expect(screen.getByTestId(`play-start-runbook-${DOC_B}`)).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("play-start-run-submit")).toBeDisabled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();

    await user.click(screen.getByTestId(`play-start-runbook-${DOC_A}`));
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    await user.click(screen.getByTestId("play-start-run-submit"));

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN_ID));
    expect(liveApi.getCommittedWorkspaceRevision).toHaveBeenCalledWith(DOC_A);
    expect(liveApi.putPlayRun).toHaveBeenCalledWith(RUN_ID, {
      playable_artifact_id: DOC_A,
      expected_playable_revision: 7,
      expected_playable_content_sha256: SHA_A,
    });
    expect(liveApi.putPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID);
    expect(liveApi.putPlayRunReferenceManifest.mock.calls[0]?.[1]).toBeUndefined();
  });

  it("uses World V2 list and Start Run when the World ID equals a Campaign ID", async () => {
    const onStarted = vi.fn();
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockResolvedValue({
      schema_version: "dmb_world_owned_runbooks_list_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      records: [worldRunbook()],
    });
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} verifiedWorldId={WORLD_ID} />);

    const runbookButton = await screen.findByTestId(`play-start-runbook-${DOC_A}`);
    expect(runbookButton).toHaveTextContent(`World ${WORLD_ID}`);
    await user.click(runbookButton);
    await user.click(screen.getByTestId("play-start-run-submit"));

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN_ID));
    expect(liveApi.listWorldOwnedRunbooks).toHaveBeenCalledExactlyOnceWith(WORLD_ID);
    expect(liveApi.listWorkspaceDocuments).not.toHaveBeenCalled();
    expect(liveApi.getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(DOC_A, WORLD_ID);
    expect(liveApi.putWorldPlayRun).toHaveBeenCalledWith(RUN_ID, WORLD_ID, {
      playable_artifact_id: DOC_A,
      expected_playable_revision: 7,
      expected_playable_content_sha256: SHA_A,
    });
    expect(liveApi.putWorldPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID, WORLD_ID);
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRunReferenceManifest).not.toHaveBeenCalled();
  });


  it("starts only from the exact saved World Plan selected on the Plan surface", async () => {
    const onStarted = vi.fn();
    vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      records: [worldPlanRecord()],
    });
    const user = userEvent.setup();
    render(
      <StartRunPanel
        onStarted={onStarted}
        verifiedWorldId={WORLD_ID}
        initialPlanId={DOC_A}
        initialPlanRevisionPin={{
          revisionN: 7,
          workRevisionId: WORLD_WORK_REVISION_ID,
          contentSha256: SHA_A,
        }}
      />,
    );

    expect(await screen.findByTestId("play-start-selected-plan")).toHaveTextContent(DOC_A);
    expect(screen.getByTestId("play-start-run-submit")).toHaveTextContent("Start Run from Plan");
    await user.click(screen.getByTestId("play-start-run-submit"));

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN_ID));
    expect(liveApi.listWorldOwnedPlans).toHaveBeenCalledExactlyOnceWith(WORLD_ID);
    expect(liveApi.getWorldOwnedPlanCommittedRevision).toHaveBeenCalledExactlyOnceWith(DOC_A);
    expect(liveApi.getWorldOwnedRunbookCommittedRevision).not.toHaveBeenCalled();
    expect(liveApi.listWorldOwnedRunbooks).not.toHaveBeenCalled();
    expect(liveApi.putWorldPlayRun).toHaveBeenCalledWith(RUN_ID, WORLD_ID, {
      playable_artifact_id: DOC_A,
      expected_playable_revision: 7,
      expected_playable_content_sha256: SHA_A,
    });
    expect(liveApi.putWorldPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID, WORLD_ID);
  });

  it("blocks Plan start when its exact WorkRevision pin changed after Plan reopen", async () => {
    const onStarted = vi.fn();
    vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      records: [worldPlanRecord()],
    });
    vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue({
      ...worldPlanCommittedFor(),
      revision_n: 8,
      work_revision_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
      content_sha256: "b".repeat(64),
    });
    const user = userEvent.setup();
    render(
      <StartRunPanel
        onStarted={onStarted}
        verifiedWorldId={WORLD_ID}
        initialPlanId={DOC_A}
        initialPlanRevisionPin={{
          revisionN: 7,
          workRevisionId: WORLD_WORK_REVISION_ID,
          contentSha256: SHA_A,
        }}
      />,
    );

    await screen.findByTestId("play-start-selected-plan");
    await user.click(screen.getByTestId("play-start-run-submit"));
    expect(await screen.findByTestId("play-start-run-blocked")).toHaveTextContent("changed after it was opened");
    expect(liveApi.putWorldPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putWorldPlayRunReferenceManifest).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();
  });

  it("does not navigate after a Plan-start response arrives for an unmounted source selection", async () => {
    const onStarted = vi.fn();
    const pendingRun = deferred<WorldPlayRunRecordV2>();
    vi.mocked(liveApi.listWorldOwnedPlans).mockImplementation(async (worldId) => ({
      schema_version: "dmb_workspace_document_registry_v2",
      scope_mode: "world",
      world_id: worldId,
      records: [worldPlanRecord(DOC_A, worldId), worldPlanRecord(DOC_B, worldId)],
    }));
    vi.mocked(liveApi.putWorldPlayRun).mockReturnValue(pendingRun.promise);
    function Source({ documentId }: { documentId: string }) {
      return (
        <StartRunPanel
          key={documentId}
          onStarted={onStarted}
          verifiedWorldId={WORLD_ID}
          initialPlanId={documentId}
          initialPlanRevisionPin={{
            revisionN: 7,
            workRevisionId: WORLD_WORK_REVISION_ID,
            contentSha256: SHA_A,
          }}
        />
      );
    }
    const view = render(<Source documentId={DOC_A} />);
    const user = userEvent.setup();
    await screen.findByTestId("play-start-selected-plan");
    await user.click(screen.getByTestId("play-start-run-submit"));
    await waitFor(() => expect(liveApi.putWorldPlayRun).toHaveBeenCalledWith(RUN_ID, WORLD_ID, expect.any(Object)));

    view.rerender(<Source documentId={DOC_B} />);
    await screen.findByText("World Plan");
    await act(async () => {
      pendingRun.resolve(worldPlayRun());
      await pendingRun.promise;
    });
    expect(onStarted).not.toHaveBeenCalled();
  });

  it("keeps World Runbook discovery failures on the World route without V1 fallback", async () => {
    vi.mocked(liveApi.listWorldOwnedRunbooks).mockRejectedValue(new LiveApiError("World Runbooks unavailable", 503));
    render(<StartRunPanel onStarted={vi.fn()} verifiedWorldId={WORLD_ID} />);

    expect(await screen.findByTestId("play-start-run-unavailable")).toHaveTextContent("World Runbooks unavailable");
    expect(liveApi.listWorldOwnedRunbooks).toHaveBeenCalledExactlyOnceWith(WORLD_ID);
    expect(liveApi.listWorkspaceDocuments).not.toHaveBeenCalled();
  });

  it("creates a blank Runbook through World V2 without Campaign input or starting a Run", async () => {
    const blank = worldRunbook();
    vi.mocked(liveApi.listWorldOwnedRunbooks)
      .mockResolvedValueOnce({
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: WORLD_ID,
        records: [],
      })
      .mockResolvedValueOnce({
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: WORLD_ID,
        records: [],
      });
    vi.mocked(liveApi.createWorldOwnedRunbook).mockResolvedValue(blank);
    vi.mocked(liveApi.prepareWorldRunbookMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "world-token-1",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitWorldRunbookMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: WORLD_ID,
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: { ...blank, content_status: "committed" },
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} verifiedWorldId={WORLD_ID} />);

    expect(await screen.findByTestId("play-start-run-empty")).toBeInTheDocument();
    expect(screen.getByTestId("play-create-blank-runbook-world-context")).toHaveTextContent(`World ${WORLD_ID}`);
    expect(screen.queryByTestId("play-create-blank-runbook-campaign")).not.toBeInTheDocument();
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));

    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toHaveAttribute("aria-pressed", "true");
    expect(liveApi.createWorldOwnedRunbook).toHaveBeenCalledWith({ world_id: WORLD_ID, title: "Blank Runbook" });
    expect(liveApi.prepareWorldRunbookMarkdownWrite).toHaveBeenCalledWith(WORLD_ID, expect.objectContaining({
      document_id: DOC_A,
      expected_revision: 7,
      markdown: expect.stringContaining("kind=beat id=beat:"),
    }));
    expect(liveApi.commitWorldRunbookMarkdownWrite).toHaveBeenCalledWith(WORLD_ID, expect.objectContaining({
      document_id: DOC_A,
      writer_confirm_token: "world-token-1",
      expected_revision: 7,
    }));
    expect(liveApi.listWorkspaceDocuments).not.toHaveBeenCalled();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(liveApi.putWorldPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("blocks a stale snapshot 409 without sealing or navigating", async () => {
    vi.mocked(liveApi.putPlayRun).mockRejectedValue(new LiveApiError("stale snapshot", 409));
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);

    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    await user.click(screen.getByTestId("play-start-run-submit"));

    expect(await screen.findByTestId("play-start-run-blocked")).toBeInTheDocument();
    expect(liveApi.putPlayRunReferenceManifest).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
  });

  it("keeps one UUID across a lost create response", async () => {
    vi.mocked(liveApi.putPlayRun).mockRejectedValueOnce(new Error("network"));
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);

    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    await user.click(screen.getByTestId("play-start-run-submit"));

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN_ID));
    expect(onStarted).toHaveBeenCalledTimes(1);
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
  });

  it("does not navigate when Run create succeeds but seal fails", async () => {
    vi.mocked(liveApi.putPlayRunReferenceManifest).mockRejectedValue(new LiveApiError("workspace advanced", 409));
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockRejectedValue(new LiveApiError("missing", 404));
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);

    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    await user.click(screen.getByTestId("play-start-run-submit"));

    expect(await screen.findByTestId("play-start-run-incomplete")).toHaveTextContent(RUN_ID);
    expect(onStarted).not.toHaveBeenCalled();
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
  });

  it("navigates once after a lost seal is reconciled by exact GET", async () => {
    vi.mocked(liveApi.putPlayRunReferenceManifest).mockRejectedValue(new Error("network"));
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);

    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    await user.click(screen.getByTestId("play-start-run-submit"));

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN_ID));
    expect(onStarted).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID);
  });

  it("does not hide an Existing Runs sibling when Runbook discovery fails", async () => {
    vi.mocked(liveApi.listWorkspaceDocuments).mockRejectedValue(
      new LiveApiError("workspace documents unavailable", 503),
    );
    render(
      <div>
        <section data-testid="play-existing-runs">
          <a href={`/play?run=${RUN_ID}`}>{RUN_ID}</a>
        </section>
        <StartRunPanel onStarted={vi.fn()} />
      </div>,
    );

    expect(await screen.findByTestId("play-start-run-unavailable")).toBeInTheDocument();
    expect(screen.getByTestId("play-existing-runs")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: RUN_ID })).toHaveAttribute("href", `/play?run=${RUN_ID}`);
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("creates a blank Runbook from an explicit campaign without starting a Run", async () => {
    const blank = runbook(DOC_A, "Blank Runbook");
    blank.campaign_id = "operator-campaign";
    blank.target_session = null;
    blank.target_relpath = null;
    blank.revision = 1;
    vi.mocked(liveApi.listWorkspaceDocuments)
      .mockResolvedValueOnce({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [],
      })
      .mockResolvedValueOnce({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [blank],
      });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(blank);
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "token-1",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: blank,
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);

    expect(await screen.findByTestId("play-start-run-empty")).toHaveTextContent(
      "No active Runbooks are available.",
    );
    expect(screen.getByTestId("play-create-blank-runbook-submit")).toBeDisabled();
    await user.type(screen.getByTestId("play-create-blank-runbook-campaign"), "operator-campaign");
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));

    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "runbook",
        campaign_id: "operator-campaign",
        title: "Blank Runbook",
        target_relpath: null,
      }),
    );
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();
    expect(screen.getByTestId("play-start-run-submit")).not.toBeDisabled();
  });

  it("uses valid product campaign context and does not invent longmont-c2", async () => {
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [],
    });
    render(<StartRunPanel onStarted={vi.fn()} productCampaignId="from-world" />);

    expect(await screen.findByTestId("play-create-blank-runbook-campaign-context")).toHaveTextContent(
      "Campaign from-world",
    );
    expect(screen.queryByTestId("play-create-blank-runbook-campaign")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-create-blank-runbook-submit")).not.toBeDisabled();
  });

  it("retries prepare against the same WorkObject after the first create succeeds", async () => {
    const blank = runbook(DOC_A, "Blank Runbook");
    blank.campaign_id = "operator-campaign";
    blank.target_session = null;
    blank.target_relpath = null;
    blank.revision = 1;
    vi.mocked(liveApi.listWorkspaceDocuments)
      .mockResolvedValueOnce({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [],
      })
      .mockResolvedValue({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [blank],
      });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue({
      ...blank,
      content_status: "draft",
    });
    vi.mocked(liveApi.prepareTiptapMarkdownWrite)
      .mockRejectedValueOnce(new Error("prepare unavailable"))
      .mockResolvedValue({
        schema_version: "dmb_tiptap_markdown_write_prepare_v1",
        document_id: DOC_A,
        title: blank.title,
        target_relpath: `runbook:${DOC_A}`,
        target_display_path: `runbook:${DOC_A}`,
        registry_revision: 1,
        file_exists: false,
        writer_ok: true,
        writer_confirm_token: "token-2",
        warnings: [],
        diagnostics: [],
      });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: blank,
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: { ...blank, content_status: "draft" },
      markdown: "# pending\n",
      content_sha256: SHA_A,
      file_fingerprint: "fp",
      file_exists: false,
      loaded_revision: 1,
    });
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} />);

    await user.type(await screen.findByTestId("play-create-blank-runbook-campaign"), "operator-campaign");
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));
    expect(await screen.findByTestId("play-create-blank-runbook-error")).toHaveTextContent("prepare unavailable");

    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));
    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toHaveAttribute("aria-pressed", "true");
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(2);
    expect(screen.queryByTestId("play-create-blank-runbook-error")).not.toBeInTheDocument();
  });

  it("keeps a successful commit even when the Runbook list refresh fails", async () => {
    const blank = runbook(DOC_A, "Blank Runbook");
    blank.campaign_id = "operator-campaign";
    blank.target_session = null;
    blank.target_relpath = null;
    blank.revision = 1;
    vi.mocked(liveApi.listWorkspaceDocuments)
      .mockResolvedValueOnce({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [],
      })
      .mockRejectedValueOnce(new LiveApiError("list unavailable", 503));
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue({
      ...blank,
      content_status: "draft",
    });
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "token-1",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: blank,
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} />);

    await user.type(await screen.findByTestId("play-create-blank-runbook-campaign"), "operator-campaign");
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));

    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("play-create-blank-runbook-list-warning")).toHaveTextContent("committed");
    expect(screen.queryByTestId("play-create-blank-runbook-error")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-start-run-submit")).not.toBeDisabled();
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("disables Edit Runbook until a Runbook is selected", async () => {
    render(<StartRunPanel onStarted={vi.fn()} />);
    expect(await screen.findByTestId(`play-start-runbook-${DOC_A}`)).toBeInTheDocument();
    expect(screen.getByTestId("play-edit-runbook")).toBeDisabled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRunReferenceManifest).not.toHaveBeenCalled();
  });

  it("targets the exact selected WorkObject even when it is not first in the list", async () => {
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} />);
    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_B}`));
    const edit = screen.getByTestId("play-edit-runbook");
    expect(edit).toHaveAttribute("href", `/plan?documentId=${DOC_B}`);
    expect(edit.getAttribute("href")).not.toContain(DOC_A);
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRunReferenceManifest).not.toHaveBeenCalled();
    expect(screen.getByTestId(`play-start-runbook-${DOC_B}`)).toHaveAttribute("aria-pressed", "true");
  });

  it("offers Edit Runbook on a newly created blank Runbook without starting a Run", async () => {
    const blank = runbook(DOC_A, "Blank Runbook");
    blank.campaign_id = "operator-campaign";
    blank.target_session = null;
    blank.target_relpath = null;
    blank.revision = 1;
    vi.mocked(liveApi.listWorkspaceDocuments)
      .mockResolvedValueOnce({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [],
      })
      .mockResolvedValueOnce({
        schema_version: "dmb_workspace_document_registry_v1",
        records: [blank],
      });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(blank);
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "token-1",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_A,
      title: blank.title,
      target_relpath: `runbook:${DOC_A}`,
      target_display_path: `runbook:${DOC_A}`,
      registry_revision: 2,
      committed_revision: 1,
      committed_record: blank,
      normalized_content_sha256: SHA_A,
      writer_ok: true,
      diagnostics: [],
    });
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} />);
    await user.type(await screen.findByTestId("play-create-blank-runbook-campaign"), "operator-campaign");
    await user.click(screen.getByTestId("play-create-blank-runbook-submit"));

    expect(await screen.findByTestId("play-edit-runbook")).toHaveAttribute(
      "href",
      `/plan?documentId=${DOC_A}`,
    );
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
    expect(liveApi.putPlayRunReferenceManifest).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();
  });

  it("disables Edit Runbook when the selected Runbook campaign mismatches Play", async () => {
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} productCampaignId="longmont-c1" />);
    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_B}`));
    const edit = screen.getByTestId("play-edit-runbook");
    expect(edit).toBeDisabled();
    expect(edit).not.toHaveAttribute("href");
    expect(screen.getByTestId("play-edit-runbook-campaign-mismatch")).toHaveTextContent("longmont-c2");
    expect(screen.getByTestId("play-edit-runbook-campaign-mismatch")).toHaveTextContent("longmont-c1");
    expect(screen.getByTestId("play-start-run-submit")).not.toBeDisabled();
    expect(liveApi.putPlayRun).not.toHaveBeenCalled();
  });

  it("still starts an exact Run when Edit is blocked by campaign mismatch", async () => {
    const onStarted = vi.fn();
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={onStarted} productCampaignId="longmont-c1" />);
    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    expect(screen.getByTestId("play-edit-runbook")).toBeDisabled();
    await user.click(screen.getByTestId("play-start-run-submit"));
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(RUN_ID));
    expect(liveApi.putPlayRun).toHaveBeenCalledWith(RUN_ID, expect.objectContaining({
      playable_artifact_id: DOC_A,
      expected_playable_revision: 7,
    }));
  });

  it("keeps Edit Runbook available when the product campaign matches", async () => {
    const user = userEvent.setup();
    render(<StartRunPanel onStarted={vi.fn()} productCampaignId="longmont-c2" />);
    await user.click(await screen.findByTestId(`play-start-runbook-${DOC_A}`));
    expect(screen.getByTestId("play-edit-runbook")).toHaveAttribute("href", `/plan?documentId=${DOC_A}`);
    expect(screen.queryByTestId("play-edit-runbook-campaign-mismatch")).not.toBeInTheDocument();
  });
});
