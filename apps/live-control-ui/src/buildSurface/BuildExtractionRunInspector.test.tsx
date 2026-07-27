import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../api/extractPromoteApi";
import { ExtractPromoteApiError } from "../api/extractPromoteApi";
import * as liveApi from "../api/liveApi";
import { ProjectionProvider } from "../planSurface/projection/projectionContext";
import type { PlanContextDescriptor } from "../planSurface/types";
import { BuildCanvasTestProvider } from "./buildCanvasTestProvider";
import { BuildExtractionRunInspector } from "./BuildExtractionRunInspector";
import { dispatchBuildFindExisting } from "./buildFindExisting";
import { createBuildSurfaceConfig } from "./createBuildSurfaceConfig";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    getExtractionRunStatus: vi.fn(),
  };
});

vi.mock("../api/extractPromoteApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/extractPromoteApi")>();
  return {
    ...actual,
    getExactRunReviewPackage: vi.fn(),
  };
});

const DOC_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff";
const RUN_ID = "99999999-9999-4999-8999-999999999999";
const ARTIFACT = "artifact:worldbuilding:x";

const context: PlanContextDescriptor = {
  campaignId: "eldyrwild",
  liveSession: 0,
  ingestSession: 0,
  headerLabel: "Build",
};

const workspaceRecord = {
  schema_version: "dmb_workspace_document_record_v1" as const,
  document_id: DOC_ID,
  title: "Source",
  campaign_id: "eldyrwild",
  target_session: null,
  kind: "worldbuilding_source" as const,
  target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
  status: "active" as const,
  content_status: "committed" as const,
  revision: 2,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
  source_domain: "worldbuilding",
  document_class: "lore",
  authority_state: "draft" as const,
  visibility_state: "internal" as const,
};

const reviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1" as const,
  runId: RUN_ID,
  sourceDomain: "worldbuilding",
  sourceArtifactId: ARTIFACT,
  sourceRevisionId: "sha-2",
  campaignId: "eldyrwild",
  sessionId: null,
  sourceProse: "# Lore\n\nPinned paragraph.\n",
  assertions: [
    {
      assertionId: "obj_vial",
      kind: "object" as const,
      label: "vial",
      summary: "Sample vial",
      evidence: [
        {
          sourceArtifactId: ARTIFACT,
          sourceSpanRefId: "span:1",
          paragraphText: "Pinned paragraph.",
          anchorQuotes: ["Pinned paragraph."],
          startLine: 3,
          endLine: 3,
        },
      ],
    },
  ],
  diagnostics: [],
};

function renderInspector() {
  return render(
    <ProjectionProvider config={createBuildSurfaceConfig(workspaceRecord)}>
      <BuildCanvasTestProvider documentId={DOC_ID}>
        <BuildExtractionRunInspector context={context} />
      </BuildCanvasTestProvider>
    </ProjectionProvider>,
  );
}

describe("BuildExtractionRunInspector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState(
      {},
      "",
      `/build?documentId=${DOC_ID}&extractionRunId=${RUN_ID}`,
    );
    localStorage.setItem(`dmb.buildExtractionRun.${DOC_ID}`, RUN_ID);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: workspaceRecord,
      markdown: "# Source\n",
      content_sha256: "sha-2",
      file_fingerprint: "fp",
      file_exists: true,
      loaded_revision: 2,
    });
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
    vi.mocked(extractPromoteApi.getExactRunReviewPackage).mockResolvedValue(reviewPackage);
  });

  it("loads review package and lists candidates with evidence", async () => {
    renderInspector();
    await waitFor(() => {
      expect(screen.getByTestId("build-extraction-run-inspector-run-status")).toHaveTextContent(
        "reviewable",
      );
    });
    expect(screen.getByTestId("build-extraction-run-candidate-obj_vial")).toBeInTheDocument();
    expect(screen.getByTestId("build-extraction-run-evidence-quote")).toHaveTextContent(
      "Pinned paragraph.",
    );
    expect(screen.getByTestId("build-extraction-run-inspector-source-prose")).toHaveTextContent(
      "Pinned paragraph.",
    );
  });

  it("shows draft mismatch when canvas digest differs from pinned digest", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: { ...workspaceRecord, revision: 3 },
      markdown: "# Source\n\ndraft edit\n",
      content_sha256: "sha-draft",
      file_fingerprint: "fp",
      file_exists: true,
      loaded_revision: 3,
    });

    renderInspector();
    await waitFor(() => {
      expect(screen.getByTestId("build-extraction-run-inspector-draft-mismatch")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("build-extraction-run-inspector-source-prose")).not.toBeInTheDocument();
  });

  it("surfaces inspection diagnostics when review package fetch fails", async () => {
    vi.mocked(extractPromoteApi.getExactRunReviewPackage).mockRejectedValue(
      new ExtractPromoteApiError("invalid evidence", 422, "run_not_promotable", {
        schema: "dmb_extract_promote_error_v1",
        code: "run_not_promotable",
        message: "invalid evidence",
        statusCode: 422,
        runStatus: "reviewable",
        inspectionStatus: "invalid_evidence",
        diagnostics: [
          {
            code: "false_anchor_quote",
            message: "quote missing from paragraph",
            severity: "error",
          },
        ],
      }),
    );

    renderInspector();
    await waitFor(() => {
      expect(screen.getByTestId("build-extraction-run-inspector-inspection-status")).toHaveTextContent(
        "invalid_evidence",
      );
    });
    expect(screen.getByTestId("build-extraction-run-inspector-review-diagnostics")).toHaveTextContent(
      "false_anchor_quote",
    );
  });

  it("dispatches find-existing without inserting from inspector row action", async () => {
    const user = userEvent.setup();
    const listener = vi.fn();
    window.addEventListener("dmb-build-find-existing", listener);

    renderInspector();
    await waitFor(() => {
      expect(screen.getByTestId("build-extraction-run-find-existing-obj_vial")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("build-extraction-run-find-existing-obj_vial"));
    expect(listener).toHaveBeenCalledTimes(1);
    expect((listener.mock.calls[0]?.[0] as CustomEvent).detail).toEqual({
      query: "vial",
      kindHint: "Sample vial",
    });

    window.removeEventListener("dmb-build-find-existing", listener);
    dispatchBuildFindExisting({ query: "noop" });
  });
});
