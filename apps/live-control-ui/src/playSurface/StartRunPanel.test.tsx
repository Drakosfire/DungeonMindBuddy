import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../api/liveApi";
import type {
  PlayRunRecord,
  PlayRunReferenceManifest,
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
    putPlayRun: vi.fn(),
    putPlayRunReferenceManifest: vi.fn(),
    getPlayRun: vi.fn(),
    getPlayRunReferenceManifest: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
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

describe("StartRunPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(RUN_ID);
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [runbook(DOC_A, "North Gate"), runbook(DOC_B, "South Wall")],
    });
    vi.mocked(liveApi.getCommittedWorkspaceRevision).mockImplementation(async (documentId) => committedFor(documentId));
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
    expect(liveApi.getCommittedWorkspaceRevision).toHaveBeenCalledWith(DOC_A);
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
});

