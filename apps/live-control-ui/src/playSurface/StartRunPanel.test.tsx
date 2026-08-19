import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../api/liveApi";
import type {
  PlayRunRecord,
  PlayRunReferenceManifest,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../api/types";
import { StartRunPanel } from "./StartRunPanel";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    listWorkspaceDocuments: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    putPlayRun: vi.fn(),
    putPlayRunReferenceManifest: vi.fn(),
    getPlayRun: vi.fn(),
    getPlayRunReferenceManifest: vi.fn(),
  };
});

import * as liveApi from "../api/liveApi";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const DOC_A = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const DOC_B = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const SHA_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

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

function snapshotFor(documentId: string): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: runbook(documentId, "North Gate"),
    markdown: "# Gate\n",
    content_sha256: SHA_A,
    file_fingerprint: "present",
    file_exists: true,
    loaded_revision: 7,
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

describe("StartRunPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(RUN_ID);
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [runbook(DOC_A, "North Gate"), runbook(DOC_B, "South Wall")],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (documentId) => snapshotFor(documentId));
    vi.mocked(liveApi.putPlayRun).mockResolvedValue(playRun());
    vi.mocked(liveApi.putPlayRunReferenceManifest).mockResolvedValue(playManifest());
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(playRun());
    vi.mocked(liveApi.getPlayRunReferenceManifest).mockResolvedValue(playManifest());
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
    expect(liveApi.getWorkspaceDocumentSnapshot).toHaveBeenCalledWith(DOC_A);
    expect(liveApi.putPlayRun).toHaveBeenCalledWith(RUN_ID, {
      playable_artifact_id: DOC_A,
      expected_playable_revision: 7,
      expected_playable_content_sha256: SHA_A,
    });
    expect(liveApi.putPlayRunReferenceManifest).toHaveBeenCalledWith(RUN_ID);
    expect(liveApi.putPlayRunReferenceManifest.mock.calls[0]?.[1]).toBeUndefined();
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
});
