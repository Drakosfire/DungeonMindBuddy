import { renderHook, act, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { useBuildExtraction } from "./useBuildExtraction";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocument: vi.fn(),
    launchExtractionRun: vi.fn(),
    getExtractionRun: vi.fn(),
  };
});

const DOC_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const RUN_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";

describe("useBuildExtraction", () => {
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

  it("retains an exact run id from the URL across refresh", async () => {
    window.history.pushState({}, "", `/build?documentId=${DOC_ID}&extractionRunId=${RUN_ID}`);
    vi.mocked(liveApi.getExtractionRun).mockResolvedValue({
      schema_version: "dmb_extraction_run_v1",
      version: "1.0",
      run_id: RUN_ID,
      source_artifact_id: "artifact:worldbuilding:x",
      source_domain: "worldbuilding",
      status: "prepared",
      profile_id: "worldbuilding_plumbing_v0@0.1",
    });

    const { result } = renderHook(() => useBuildExtraction());
    await waitFor(() => {
      expect(result.current.run?.run_id).toBe(RUN_ID);
    });
    expect(liveApi.getExtractionRun).toHaveBeenCalledWith(RUN_ID);

    await act(async () => {
      await result.current.refresh();
    });
    expect(liveApi.getExtractionRun).toHaveBeenLastCalledWith(RUN_ID);
    expect(result.current.run?.run_id).toBe(RUN_ID);
  });

  it("blocks launch when source is not committed", async () => {
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
    const { result } = renderHook(() => useBuildExtraction());
    await waitFor(() => expect(result.current.document).not.toBeNull());
    expect(result.current.canLaunch).toBe(false);
  });

  it("stores exact run id after launch", async () => {
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

    const { result } = renderHook(() => useBuildExtraction());
    await waitFor(() => expect(result.current.canLaunch).toBe(true));
    await act(async () => {
      await result.current.launch();
    });
    expect(result.current.run?.run_id).toBe(RUN_ID);
    expect(window.location.search).toContain(`extractionRunId=${RUN_ID}`);
    expect(localStorage.getItem(`dmb.buildExtractionRun.${DOC_ID}`)).toBe(RUN_ID);
  });
});
