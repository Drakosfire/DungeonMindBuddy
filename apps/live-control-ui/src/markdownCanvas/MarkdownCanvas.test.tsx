import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import {
  buildInitialWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { MarkdownCanvas } from "./MarkdownCanvas";
import { MarkdownCanvasSessionProvider, useMarkdownCanvasSession } from "./MarkdownCanvasSession";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function snapshot(contentStatus: "draft" | "committed" = "committed") {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record: {
      schema_version: "dmb_workspace_document_record_v1" as const,
      document_id: DOC_ID,
      title: "Canvas Doc",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source" as const,
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active" as const,
      content_status: contentStatus,
      revision: 3,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft" as const,
      visibility_state: "internal" as const,
    },
    markdown: "# Canvas Doc\n",
    content_sha256: "sha-canvas",
    file_fingerprint: "fp",
    file_exists: true,
    loaded_revision: 3,
  };
}

function AdmissionProbe() {
  const session = useMarkdownCanvasSession();
  const envelope = session.getAdmittedDocument("committed_clean");
  return (
    <div
      data-testid="admission-probe"
      data-has-envelope={envelope ? "yes" : "no"}
      data-revision={envelope?.revision ?? "none"}
      data-digest={envelope?.contentSha256 ?? "none"}
    />
  );
}

describe("MarkdownCanvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    writeWorkspaceDocumentLocalState(window.localStorage, {
      ...buildInitialWorkspaceDocumentLocalState({
        documentId: DOC_ID,
        title: "Canvas Doc",
        campaignId: "eldyrwild",
        kind: "worldbuilding_source",
        targetSession: null,
        surface: "build",
        baseRevision: 3,
        baseContentSha256: "sha-canvas",
        starterContent: { type: "doc", content: [] },
      }),
      dirty: false,
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot("committed"));
  });

  it("renders editor content from the shared session", async () => {
    render(
      <MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source">
        <MarkdownCanvas />
      </MarkdownCanvasSessionProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("markdown-canvas")).toBeInTheDocument();
    });
    expect(screen.getByTestId("markdown-canvas-editor")).toBeInTheDocument();
  });

  it("admits committed_clean only when local CAS matches snapshot", async () => {
    render(
      <MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source">
        <AdmissionProbe />
        <MarkdownCanvas />
      </MarkdownCanvasSessionProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("admission-probe")).toHaveAttribute("data-has-envelope", "yes");
    });
    expect(screen.getByTestId("admission-probe")).toHaveAttribute("data-revision", "3");
    expect(screen.getByTestId("admission-probe")).toHaveAttribute("data-digest", "sha-canvas");
  });

  it("withholds committed_clean while dirty", async () => {
    writeWorkspaceDocumentLocalState(window.localStorage, {
      ...buildInitialWorkspaceDocumentLocalState({
        documentId: DOC_ID,
        title: "Canvas Doc",
        campaignId: "eldyrwild",
        kind: "worldbuilding_source",
        targetSession: null,
        surface: "build",
        baseRevision: 3,
        baseContentSha256: "sha-canvas",
        starterContent: { type: "doc", content: [] },
      }),
      dirty: true,
    });
    render(
      <MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source">
        <AdmissionProbe />
      </MarkdownCanvasSessionProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("admission-probe")).toHaveAttribute("data-has-envelope", "no");
    });
  });
});
