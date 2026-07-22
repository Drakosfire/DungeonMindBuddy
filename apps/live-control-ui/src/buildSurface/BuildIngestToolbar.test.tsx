import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { BuildIngestToolbar } from "./BuildIngestToolbar";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocument: vi.fn(),
    launchExtractionRun: vi.fn(),
    getExtractionRun: vi.fn(),
  };
});

const DOC_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff";
const RUN_ID = "99999999-9999-4999-8999-999999999999";

describe("BuildIngestToolbar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}`);
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue({
      schema_version: "dmb_workspace_document_record_v1",
      document_id: DOC_ID,
      title: "Source",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active",
      content_status: "committed",
      revision: 2,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    });
  });

  it("disables extract until a committed source is available", async () => {
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue({
      schema_version: "dmb_workspace_document_record_v1",
      document_id: DOC_ID,
      title: "Source",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active",
      content_status: "draft",
      revision: 1,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    });
    render(<BuildIngestToolbar />);
    expect(await screen.findByTestId("build-extract-button")).toBeDisabled();
    expect(screen.getByTestId("build-open-graph-review-disabled")).toBeInTheDocument();
  });

  it("launches extraction and shows the exact run id", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.launchExtractionRun).mockResolvedValue({
      schema_version: "dmb_extraction_run_launch_v1",
      run: {
        schema_version: "dmb_extraction_run_v1",
        version: "1.0",
        run_id: RUN_ID,
        source_artifact_id: "artifact:worldbuilding:x",
        source_domain: "worldbuilding",
        status: "prepared",
      },
      source_artifact_id: "artifact:worldbuilding:x",
      document_id: DOC_ID,
      document_revision: 2,
      diagnostics: [],
      graph_review_handoff: {
        href: `/ingest?extractionRunId=${RUN_ID}&sourceArtifactId=artifact:worldbuilding:x&documentId=${DOC_ID}&revision=2`,
        extraction_run_id: RUN_ID,
        source_artifact_id: "artifact:worldbuilding:x",
        document_id: DOC_ID,
        document_revision: 2,
      },
    });

    render(<BuildIngestToolbar />);
    await waitFor(() => expect(screen.getByTestId("build-extract-button")).not.toBeDisabled());
    await user.click(screen.getByTestId("build-extract-button"));
    expect(await screen.findByTestId("build-extraction-run-id")).toHaveTextContent(RUN_ID);
    expect(screen.getByTestId("build-open-graph-review-disabled")).toBeInTheDocument();
  });

  it("enables Graph Review handoff only for reviewable exact runs", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&extractionRunId=${RUN_ID}`);
    vi.mocked(liveApi.getExtractionRun).mockResolvedValue({
      schema_version: "dmb_extraction_run_v1",
      version: "1.0",
      run_id: RUN_ID,
      source_artifact_id: "artifact:worldbuilding:x",
      source_domain: "worldbuilding",
      status: "reviewable",
    });

    render(<BuildIngestToolbar />);
    const link = await screen.findByTestId("build-open-graph-review");
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining(`extractionRunId=${RUN_ID}`),
    );
    expect(link).toHaveAttribute("href", expect.stringContaining(`documentId=${DOC_ID}`));
    expect(link.getAttribute("href")).not.toContain("latest");
  });
});
