import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import {
  buildInitialWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { BuildCanvasTestProvider } from "./buildCanvasTestProvider";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { createBuildSurfaceConfig } from "./createBuildSurfaceConfig";
import { ProjectionSurfacePublisher } from "../planSurface/projection/projectionTestHost";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    launchExtractionRun: vi.fn(),
    getExtractionRunStatus: vi.fn(),
  };
});

const DOC_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff";
const DOC_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const RUN_ID = "99999999-9999-4999-8999-999999999999";
const RUN_B = "88888888-8888-4888-8888-888888888888";
const ARTIFACT = "artifact:worldbuilding:x";

function seedCleanLocal(documentId: string, revision: number, sha: string) {
  writeWorkspaceDocumentLocalState(window.localStorage, {
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
    dirty: false,
  });
}

function snapshot(documentId: string, revision: number, sha: string, contentStatus: "draft" | "committed" = "committed") {
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

function renderToolbar(documentId: string) {
  const snap = snapshot(documentId, 2, "sha-2");
  return render(
    <AgentInteractionProvider>
      <ProjectionSurfacePublisher config={createBuildSurfaceConfig(snap.record)}>
        <BuildCanvasTestProvider documentId={documentId}>
          <BuildIngestToolbar documentId={documentId} />
        </BuildCanvasTestProvider>
      </ProjectionSurfacePublisher>
    </AgentInteractionProvider>,
  );
}

describe("BuildIngestToolbar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);
    seedCleanLocal(DOC_ID, 2, "sha-2");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshot(DOC_ID, 2, "sha-2"),
    );
  });

  it("disables extract until a committed clean source is available", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshot(DOC_ID, 1, "sha-1", "draft"),
    );
    renderToolbar(DOC_ID);
    expect(await screen.findByTestId("build-extract-button")).toBeDisabled();
    expect(screen.getByTestId("build-open-graph-review-disabled")).toBeInTheDocument();
  });

  it("launches extraction and enables Graph Review for a reviewable exact run", async () => {
    const user = userEvent.setup();
    const href =
      `/ingest?extractionRunId=${RUN_ID}&sourceArtifactId=${ARTIFACT}&documentId=${DOC_ID}&revision=2`;
    vi.mocked(liveApi.launchExtractionRun).mockResolvedValue({
      schema_version: "dmb_extraction_run_launch_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        source_domain: "worldbuilding",
        status: "reviewable",
      },
      source_artifact_id: ARTIFACT,
      document_id: DOC_ID,
      document_revision: 2,
      source_content_sha256: "sha-2",
      diagnostics: [],
      graph_review_handoff: {
        href,
        extraction_run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        document_id: DOC_ID,
        document_revision: 2,
      },
    });

    renderToolbar(DOC_ID);
    await waitFor(() => expect(screen.getByTestId("build-extract-button")).not.toBeDisabled());
    await user.click(screen.getByTestId("build-extract-button"));
    expect(await screen.findByTestId("build-extraction-run-id")).toHaveTextContent(RUN_ID);
    expect(screen.getByTestId("build-extraction-run-status")).toHaveTextContent("reviewable");
    expect(screen.getByTestId("build-extraction-pinned-revision")).toHaveTextContent("2");
    expect(screen.getByTestId("build-extraction-pinned-digest")).toHaveTextContent("sha-2");
    expect(screen.getByTestId("build-inspect-run")).toBeInTheDocument();
    expect(liveApi.launchExtractionRun).toHaveBeenCalledTimes(1);
    expect(liveApi.launchExtractionRun).toHaveBeenCalledWith({
      document_id: DOC_ID,
      expected_revision: 2,
      expected_content_sha256: "sha-2",
      profile_id: "worldbuilding_shepherds_flock_v0",
      profile_version: "0.1",
    });
    const link = await screen.findByTestId("build-open-graph-review");
    expect(link).toHaveAttribute("href", href);
  });

  it("keeps Graph Review disabled and shows diagnostics when launch fails model execution", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.launchExtractionRun).mockResolvedValue({
      schema_version: "dmb_extraction_run_launch_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        source_domain: "worldbuilding",
        status: "failed",
      },
      source_artifact_id: ARTIFACT,
      document_id: DOC_ID,
      document_revision: 2,
      source_content_sha256: "sha-2",
      failure_kind: "model",
      diagnostics: ["OPENAI_API_KEY missing after loading server env"],
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_ID}&sourceArtifactId=${ARTIFACT}&documentId=${DOC_ID}&revision=2`,
        extraction_run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        document_id: DOC_ID,
        document_revision: 2,
      },
    });

    renderToolbar(DOC_ID);
    await waitFor(() => expect(screen.getByTestId("build-extract-button")).not.toBeDisabled());
    await user.click(screen.getByTestId("build-extract-button"));
    expect(await screen.findByTestId("build-extraction-run-id")).toHaveTextContent(RUN_ID);
    expect(await screen.findByTestId("build-extraction-error")).toHaveTextContent(
      "OPENAI_API_KEY missing after loading server env",
    );
    expect(screen.getByTestId("build-open-graph-review-disabled")).toBeInTheDocument();
  });

  it("enables Graph Review handoff only for reviewable exact runs", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&extractionRunId=${RUN_ID}`);
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue({
      schema_version: "dmb_extraction_run_status_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        source_domain: "worldbuilding",
        status: "reviewable",
      },
      source_artifact_id: ARTIFACT,
      document_id: DOC_ID,
      document_revision: 2,
      source_content_sha256: "sha-2",
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_ID}&sourceArtifactId=${ARTIFACT}&documentId=${DOC_ID}&revision=2`,
        extraction_run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        document_id: DOC_ID,
        document_revision: 2,
      },
    });

    renderToolbar(DOC_ID);
    const link = await screen.findByTestId("build-open-graph-review");
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining(`extractionRunId=${RUN_ID}`),
    );
    expect(link).toHaveAttribute("href", expect.stringContaining(`documentId=${DOC_ID}`));
    expect(link.getAttribute("href")).not.toContain("latest");
  });

  it("drops reviewable document A handoff when selection changes to B", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&extractionRunId=${RUN_ID}`);
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue({
      schema_version: "dmb_extraction_run_status_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        source_domain: "worldbuilding",
        status: "reviewable",
      },
      source_artifact_id: ARTIFACT,
      document_id: DOC_ID,
      document_revision: 2,
      source_content_sha256: "sha-2",
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_ID}&sourceArtifactId=${ARTIFACT}&documentId=${DOC_ID}&revision=2`,
        extraction_run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        document_id: DOC_ID,
        document_revision: 2,
      },
    });

    const snapA = snapshot(DOC_ID, 2, "sha-2");
    const { rerender } = render(
      <AgentInteractionProvider>
        <ProjectionSurfacePublisher config={createBuildSurfaceConfig(snapA.record)}>
          <BuildCanvasTestProvider documentId={DOC_ID}>
            <BuildIngestToolbar documentId={DOC_ID} />
          </BuildCanvasTestProvider>
        </ProjectionSurfacePublisher>
      </AgentInteractionProvider>,
    );
    expect(await screen.findByTestId("build-open-graph-review")).toBeInTheDocument();

    seedCleanLocal(DOC_B, 5, "sha-b");
    window.history.pushState({}, "", `/build?documentId=${DOC_B}`);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshot(DOC_B, 5, "sha-b"),
    );
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue({
      schema_version: "dmb_extraction_run_status_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_B,
        source_artifact_id: "artifact:worldbuilding:b",
        source_domain: "worldbuilding",
        status: "prepared",
      },
      source_artifact_id: "artifact:worldbuilding:b",
      document_id: DOC_B,
      document_revision: 5,
      source_content_sha256: "sha-b",
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_B}&sourceArtifactId=artifact:worldbuilding:b&documentId=${DOC_B}&revision=5`,
        extraction_run_id: RUN_B,
        source_artifact_id: "artifact:worldbuilding:b",
        document_id: DOC_B,
        document_revision: 5,
      },
    });
    localStorage.setItem(`dmb.buildExtractionRun.${DOC_B}`, RUN_B);

    const snapB = snapshot(DOC_B, 5, "sha-b");
    rerender(
      <AgentInteractionProvider>
        <ProjectionSurfacePublisher config={createBuildSurfaceConfig(snapB.record)}>
          <BuildCanvasTestProvider documentId={DOC_B}>
            <BuildIngestToolbar documentId={DOC_B} />
          </BuildCanvasTestProvider>
        </ProjectionSurfacePublisher>
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(screen.queryByTestId("build-open-graph-review")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("build-open-graph-review-disabled")).toBeInTheDocument();
    expect(screen.queryByText(RUN_ID)).not.toBeInTheDocument();
  });

  it("disables Refresh and Graph Review while Extract is in flight", async () => {
    const user = userEvent.setup();
    let releaseLaunch: ((value: unknown) => void) | undefined;
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&extractionRunId=${RUN_ID}`);
    vi.mocked(liveApi.getExtractionRunStatus).mockResolvedValue({
      schema_version: "dmb_extraction_run_status_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        source_domain: "worldbuilding",
        status: "reviewable",
      },
      source_artifact_id: ARTIFACT,
      document_id: DOC_ID,
      document_revision: 2,
      source_content_sha256: "sha-2",
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_ID}&sourceArtifactId=${ARTIFACT}&documentId=${DOC_ID}&revision=2`,
        extraction_run_id: RUN_ID,
        source_artifact_id: ARTIFACT,
        document_id: DOC_ID,
        document_revision: 2,
      },
    });
    vi.mocked(liveApi.launchExtractionRun).mockImplementation(
      () => new Promise((resolve) => {
        releaseLaunch = resolve;
      }),
    );

    renderToolbar(DOC_ID);
    expect(await screen.findByTestId("build-open-graph-review")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("build-extract-button")).not.toBeDisabled());

    await user.click(screen.getByTestId("build-extract-button"));
    await waitFor(() => {
      expect(screen.getByTestId("build-extract-button")).toHaveTextContent("Extracting…");
    });
    expect(screen.getByTestId("build-extraction-refresh")).toBeDisabled();
    expect(screen.getByTestId("build-open-graph-review-disabled")).toBeInTheDocument();
    expect(screen.queryByTestId("build-open-graph-review")).not.toBeInTheDocument();

    const statusCalls = vi.mocked(liveApi.getExtractionRunStatus).mock.calls.length;
    await user.click(screen.getByTestId("build-extraction-refresh"));
    expect(vi.mocked(liveApi.getExtractionRunStatus).mock.calls.length).toBe(statusCalls);

    releaseLaunch?.({
      schema_version: "dmb_extraction_run_launch_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_B,
        source_artifact_id: ARTIFACT,
        source_domain: "worldbuilding",
        status: "reviewable",
      },
      source_artifact_id: ARTIFACT,
      document_id: DOC_ID,
      document_revision: 2,
      source_content_sha256: "sha-2",
      diagnostics: [],
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_B}&sourceArtifactId=${ARTIFACT}&documentId=${DOC_ID}&revision=2`,
        extraction_run_id: RUN_B,
        source_artifact_id: ARTIFACT,
        document_id: DOC_ID,
        document_revision: 2,
      },
    });

    expect(await screen.findByTestId("build-open-graph-review")).toHaveAttribute(
      "href",
      expect.stringContaining(`extractionRunId=${RUN_B}`),
    );
    expect(screen.getByTestId("build-extraction-refresh")).not.toBeDisabled();
    expect(await screen.findByTestId("build-extraction-run-id")).toHaveTextContent(RUN_B);
  });
});
