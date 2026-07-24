import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import {
  buildInitialWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
} from "../tiptap/state/tiptapLocalState";
import { useBuildExtraction, validateExactRunIdentity } from "./useBuildExtraction";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    launchExtractionRun: vi.fn(),
    getExtractionRunStatus: vi.fn(),
  };
});

const DOC_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const DOC_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const RUN_A = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const RUN_B = "ffffffff-ffff-4fff-8fff-ffffffffffff";
const ARTIFACT_A = "artifact:worldbuilding:a";
const ARTIFACT_B = "artifact:worldbuilding:b";

function snapshotFor(documentId: string, revision: number, sha: string, contentStatus: "draft" | "committed" = "committed") {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record: {
      schema_version: "dmb_workspace_document_record_v1" as const,
      document_id: documentId,
      title: "Source",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source" as const,
      target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
      status: "active" as const,
      content_status: contentStatus,
      revision,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft" as const,
      visibility_state: "internal" as const,
    },
    markdown: "# Source\n",
    content_sha256: sha,
    file_fingerprint: "fp",
    file_exists: true,
    loaded_revision: revision,
  };
}

function writeCleanLocal(documentId: string, revision: number, sha: string, dirty = false) {
  const state = {
    ...buildInitialWorkspaceDocumentLocalState({
      documentId,
      title: "Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: revision,
      baseContentSha256: sha,
      starterContent: { type: "doc", content: [] },
    }),
    dirty,
  };
  writeWorkspaceDocumentLocalState(window.localStorage, state);
}

function statusEnvelope(args: {
  runId: string;
  artifactId: string;
  documentId: string;
  revision: number;
  sha: string;
  status?: "prepared" | "reviewable" | "failed";
}) {
  return {
    schema_version: "dmb_extraction_run_status_v1" as const,
    run: {
      schema_version: "dmb_extraction_run_v1" as const,
      version: "1.0",
      run_id: args.runId,
      source_artifact_id: args.artifactId,
      source_domain: "worldbuilding",
      status: args.status ?? "reviewable",
    },
    source_artifact_id: args.artifactId,
    document_id: args.documentId,
    document_revision: args.revision,
    source_content_sha256: args.sha,
    graph_review_handoff: {
      href: `/ingest?extractionRunId=${args.runId}&sourceArtifactId=${args.artifactId}&documentId=${args.documentId}&revision=${args.revision}`,
      extraction_run_id: args.runId,
      source_artifact_id: args.artifactId,
      document_id: args.documentId,
      document_revision: args.revision,
    },
  };
}

function launchEnvelope(args: {
  runId: string;
  artifactId: string;
  documentId: string;
  revision: number;
  sha: string;
}) {
  const status = statusEnvelope({ ...args, status: "prepared" });
  return {
    schema_version: "dmb_extraction_run_launch_v1" as const,
    run: status.run,
    source_artifact_id: status.source_artifact_id,
    document_id: status.document_id,
    document_revision: status.document_revision,
    source_content_sha256: status.source_content_sha256,
    diagnostics: [],
    graph_review_handoff: status.graph_review_handoff,
  };
}

describe("validateExactRunIdentity", () => {
  it("rejects a foreign document identity", () => {
    const response = statusEnvelope({
      runId: RUN_A,
      artifactId: ARTIFACT_A,
      documentId: DOC_A,
      revision: 2,
      sha: "sha-a",
    });
    const result = validateExactRunIdentity({
      selectedDocumentId: DOC_B,
      requestedRunId: RUN_A,
      response,
    });
    expect(result.ok).toBe(false);
  });
});

describe("useBuildExtraction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);
    writeCleanLocal(DOC_A, 2, "sha-a");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFor(DOC_A, 2, "sha-a"),
    );
  });

  it("retains an exact run id from the URL across refresh", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_A}&extractionRunId=${RUN_A}`);
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue(
      statusEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
        status: "prepared",
      }),
    );

    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => {
      expect(result.current.run?.run_id).toBe(RUN_A);
    });
    expect(liveApi.getExtractionRunStatus).toHaveBeenCalledWith(RUN_A);

    await act(async () => {
      await result.current.refresh();
    });
    expect(liveApi.getExtractionRunStatus).toHaveBeenLastCalledWith(RUN_A);
    expect(result.current.run?.run_id).toBe(RUN_A);
  });

  it("blocks launch when local editor is dirty", async () => {
    writeCleanLocal(DOC_A, 2, "sha-a", true);
    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => expect(result.current.snapshot).not.toBeNull());
    expect(result.current.canLaunch).toBe(false);
    await act(async () => {
      await result.current.launch();
    });
    expect(liveApi.launchExtractionRun).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/local changes/i);
  });

  it("blocks launch when local base revision differs from snapshot", async () => {
    writeCleanLocal(DOC_A, 1, "sha-a");
    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => expect(result.current.snapshot).not.toBeNull());
    expect(result.current.canLaunch).toBe(false);
    await act(async () => {
      await result.current.launch();
    });
    expect(liveApi.launchExtractionRun).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/revision/i);
  });

  it("blocks launch when local base hash differs from snapshot", async () => {
    writeCleanLocal(DOC_A, 2, "sha-stale");
    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => expect(result.current.snapshot).not.toBeNull());
    await act(async () => {
      await result.current.launch();
    });
    expect(liveApi.launchExtractionRun).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/hash|digest/i);
  });

  it("launches with both revision and digest when local state matches snapshot", async () => {
    vi.mocked(liveApi.launchExtractionRun).mockResolvedValue(
      launchEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
      }),
    );
    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => expect(result.current.canLaunch).toBe(true));
    await act(async () => {
      await result.current.launch();
    });
    expect(liveApi.launchExtractionRun).toHaveBeenCalledWith({
      document_id: DOC_A,
      expected_revision: 2,
      expected_content_sha256: "sha-a",
    });
    expect(result.current.run?.run_id).toBe(RUN_A);
    expect(window.location.search).toContain(`extractionRunId=${RUN_A}`);
    expect(localStorage.getItem(`dmb.buildExtractionRun.${DOC_A}`)).toBe(RUN_A);
  });

  it("clears handoff when URL run belongs to another document", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_B}&extractionRunId=${RUN_A}`);
    writeCleanLocal(DOC_B, 3, "sha-b");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFor(DOC_B, 3, "sha-b"),
    );
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue(
      statusEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
      }),
    );

    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_B }));
    await waitFor(() => {
      expect(result.current.run?.run_id).toBe(RUN_A);
    });
    expect(result.current.handoff).toBeNull();
    expect(result.current.canOpenGraphReview).toBe(false);
    expect(result.current.error).toMatch(/different workspace document/i);
  });

  it("keeps server-derived revision N after document advances to N+1", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_A}&extractionRunId=${RUN_A}`);
    writeCleanLocal(DOC_A, 3, "sha-a3");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFor(DOC_A, 3, "sha-a3"),
    );
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue(
      statusEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
      }),
    );

    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => {
      expect(result.current.handoff?.document_revision).toBe(2);
    });
    expect(result.current.handoff?.document_revision).not.toBe(3);
    expect(result.current.canOpenGraphReview).toBe(true);
  });

  it("does not adopt mismatched launch identity into URL or storage", async () => {
    vi.mocked(liveApi.launchExtractionRun).mockResolvedValue({
      ...launchEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
      }),
      document_id: DOC_B,
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_A}&sourceArtifactId=${ARTIFACT_A}&documentId=${DOC_B}&revision=2`,
        extraction_run_id: RUN_A,
        source_artifact_id: ARTIFACT_A,
        document_id: DOC_B,
        document_revision: 2,
      },
    });

    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => expect(result.current.canLaunch).toBe(true));
    await act(async () => {
      await result.current.launch();
    });
    expect(result.current.handoff).toBeNull();
    expect(window.location.search).not.toContain(`extractionRunId=${RUN_A}`);
    expect(localStorage.getItem(`dmb.buildExtractionRun.${DOC_A}`)).toBeNull();
    expect(result.current.error).toMatch(/different workspace document/i);
  });

  it("keeps exact run id but disables Graph Review when status recovery fails", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_A}&extractionRunId=${RUN_A}`);
    vi.mocked(liveApi.getExtractionRunStatus)
      .mockResolvedValueOnce(
        statusEnvelope({
          runId: RUN_A,
          artifactId: ARTIFACT_A,
          documentId: DOC_A,
          revision: 2,
          sha: "sha-a",
        }),
      )
      .mockRejectedValueOnce(new Error("status unavailable"));

    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_A }));
    await waitFor(() => {
      expect(result.current.canOpenGraphReview).toBe(true);
    });

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.run?.run_id).toBe(RUN_A);
    expect(result.current.handoff).toBeNull();
    expect(result.current.canOpenGraphReview).toBe(false);
    expect(result.current.error).toMatch(/status unavailable/i);
  });

  it("ignores pending refresh A after selecting document B", async () => {
    let releaseA: ((value: ReturnType<typeof statusEnvelope>) => void) | undefined;
    writeCleanLocal(DOC_B, 5, "sha-b");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (documentId: string) => {
      if (documentId === DOC_A) return snapshotFor(DOC_A, 2, "sha-a");
      return snapshotFor(DOC_B, 5, "sha-b");
    });
    vi.mocked(liveApi.getExtractionRunStatus).mockImplementation(
      () => new Promise((resolve) => {
        releaseA = resolve;
      }),
    );

    window.history.pushState({}, "", `/build?documentId=${DOC_A}&extractionRunId=${RUN_A}`);
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useBuildExtraction({ documentId }),
      { initialProps: { documentId: DOC_A } },
    );

    await waitFor(() => expect(releaseA).toBeTypeOf("function"));

    window.history.pushState({}, "", `/build?documentId=${DOC_B}`);
    localStorage.setItem(`dmb.buildExtractionRun.${DOC_B}`, RUN_B);
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue(
      statusEnvelope({
        runId: RUN_B,
        artifactId: ARTIFACT_B,
        documentId: DOC_B,
        revision: 5,
        sha: "sha-b",
      }),
    );
    rerender({ documentId: DOC_B });

    await waitFor(() => {
      expect(result.current.run?.run_id).toBe(RUN_B);
    });

    await act(async () => {
      releaseA?.(statusEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
      }));
    });

    expect(result.current.run?.run_id).toBe(RUN_B);
    expect(result.current.handoff?.document_id).toBe(DOC_B);
    expect(window.location.search).not.toContain(RUN_A);
  });

  it("ignores pending launch A after selecting document B", async () => {
    let releaseLaunch: ((value: ReturnType<typeof launchEnvelope>) => void) | undefined;
    writeCleanLocal(DOC_B, 5, "sha-b");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (documentId: string) => {
      if (documentId === DOC_A) return snapshotFor(DOC_A, 2, "sha-a");
      return snapshotFor(DOC_B, 5, "sha-b");
    });
    vi.mocked(liveApi.launchExtractionRun).mockImplementation(
      () => new Promise((resolve) => {
        releaseLaunch = resolve;
      }),
    );

    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useBuildExtraction({ documentId }),
      { initialProps: { documentId: DOC_A } },
    );
    await waitFor(() => expect(result.current.canLaunch).toBe(true));

    let launchPromise: Promise<void> | undefined;
    act(() => {
      launchPromise = result.current.launch();
    });
    await waitFor(() => expect(releaseLaunch).toBeTypeOf("function"));

    window.history.pushState({}, "", `/build?documentId=${DOC_B}`);
    rerender({ documentId: DOC_B });
    await waitFor(() => {
      expect(result.current.snapshot?.record.document_id).toBe(DOC_B);
    });

    await act(async () => {
      releaseLaunch?.(launchEnvelope({
        runId: RUN_A,
        artifactId: ARTIFACT_A,
        documentId: DOC_A,
        revision: 2,
        sha: "sha-a",
      }));
      await launchPromise;
    });

    expect(window.location.search).not.toContain(`extractionRunId=${RUN_A}`);
    expect(localStorage.getItem(workspaceDocumentStorageKey(DOC_B))).toBeTruthy();
    expect(localStorage.getItem(`dmb.buildExtractionRun.${DOC_B}`)).toBeNull();
    expect(result.current.run?.run_id).not.toBe(RUN_A);
  });

  it("recovers only the selected document stored run id", async () => {
    localStorage.setItem(`dmb.buildExtractionRun.${DOC_A}`, RUN_A);
    localStorage.setItem(`dmb.buildExtractionRun.${DOC_B}`, RUN_B);
    writeCleanLocal(DOC_B, 5, "sha-b");
    window.history.pushState({}, "", `/build?documentId=${DOC_B}`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshotFor(DOC_B, 5, "sha-b"),
    );
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue(
      statusEnvelope({
        runId: RUN_B,
        artifactId: ARTIFACT_B,
        documentId: DOC_B,
        revision: 5,
        sha: "sha-b",
      }),
    );

    const { result } = renderHook(() => useBuildExtraction({ documentId: DOC_B }));
    await waitFor(() => {
      expect(result.current.run?.run_id).toBe(RUN_B);
    });
    expect(liveApi.getExtractionRunStatus).toHaveBeenCalledWith(RUN_B);
    expect(liveApi.getExtractionRunStatus).not.toHaveBeenCalledWith(RUN_A);
  });
});
