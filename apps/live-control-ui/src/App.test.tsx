import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as liveApi from "./api/liveApi";
import type { WorkspaceDocumentSnapshot } from "./api/types";
import { fixtureWorkspaceDocumentRecord, FIXTURE_DOC_ID } from "./planSurface/config/planSessionDescriptor";
import { NORTH_GATE_RUNBOOK_TARGET_RELPATH } from "./tiptap/descriptors/tiptapRunbookDescriptors";
import { makeCapabilityResponse, makeRollTableArtifact, mockCatalog, mockLayout, mockPlanView, mockState } from "./test/fixtures";

vi.mock("./api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/liveApi")>();
  return {
    ...actual,
    getSurface: vi.fn(),
    getEvents: vi.fn(),
    getJobs: vi.fn(),
    getPlanView: vi.fn(),
    getGraphIngestRuns: vi.fn(),
    getGoldReviewSessions: vi.fn(),
    getManualReviewBeds: vi.fn(),
    getArtifact: vi.fn(),
    getCapabilities: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
    listWorkspaceDocuments: vi.fn(),
    getWorkspaceDocument: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    createWorkspaceDocument: vi.fn(),
  };
});

function northGateRunbookRecord() {
  return fixtureWorkspaceDocumentRecord({
    document_id: FIXTURE_DOC_ID,
    title: "North Gate Session Runbook",
    kind: "runbook",
    target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
    target_session: 23,
    revision: 1,
  });
}

function fixtureSnapshot(
  overrides: Partial<WorkspaceDocumentSnapshot> = {},
): WorkspaceDocumentSnapshot {
  const record = overrides.record ?? fixtureWorkspaceDocumentRecord();
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: "",
    content_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: record.revision,
    ...overrides,
  };
}

describe("App inspector integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
    localStorage.clear();
    vi.mocked(liveApi.getSurface).mockResolvedValue({
      catalog: mockCatalog,
      layout: mockLayout,
      state: mockState,
    });
    vi.mocked(liveApi.getEvents).mockResolvedValue({ events: [] });
    vi.mocked(liveApi.getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(liveApi.getPlanView).mockResolvedValue(mockPlanView);
    vi.mocked(liveApi.getGraphIngestRuns).mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "test",
      runs: [],
    });
    vi.mocked(liveApi.getGoldReviewSessions).mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "test",
      sessions: [],
    });
    vi.mocked(liveApi.getManualReviewBeds).mockResolvedValue({
      schema_version: "dmb_graph_manual_review_beds_v1",
      version: "test",
      beds: [],
    });
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    vi.mocked(liveApi.getCapabilities).mockResolvedValue(makeCapabilityResponse());
    vi.mocked(liveApi.listWorkspaceDocuments).mockImplementation(async (params) => {
      if (params?.kind === "runbook") {
        return {
          schema_version: "dmb_workspace_document_registry_v1",
          records: [northGateRunbookRecord()],
        };
      }
      return {
        schema_version: "dmb_workspace_document_registry_v1",
        records: [fixtureWorkspaceDocumentRecord()],
      };
    });
    vi.mocked(liveApi.getWorkspaceDocument).mockImplementation(async (documentId) => {
      if (documentId === FIXTURE_DOC_ID) {
        return northGateRunbookRecord();
      }
      return fixtureWorkspaceDocumentRecord({ document_id: documentId });
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockImplementation(async (payload) => {
      if (payload.kind === "runbook") {
        return northGateRunbookRecord();
      }
      return fixtureWorkspaceDocumentRecord();
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (documentId) => {
      if (documentId === FIXTURE_DOC_ID) {
        return fixtureSnapshot({ record: northGateRunbookRecord() });
      }
      return fixtureSnapshot({ record: fixtureWorkspaceDocumentRecord({ document_id: documentId }) });
    });
  });

  it("renders the launcher at the root route", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /mireward local tools/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /plan prep surface/i })).toHaveAttribute("href", "/plan");
    expect(screen.getByRole("link", { name: /ingest memory ingest/i })).toHaveAttribute("href", "/ingest");
    expect(screen.getByRole("link", { name: /worldbuilding source/i })).toHaveAttribute("href", "/build");
    expect(screen.getByRole("link", { name: /live play command board/i })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );
    expect(screen.getByRole("link", { name: /retrieval dogfood surface/i })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/retrieval.html",
    );
    expect(screen.getByRole("link", { name: /live control react surface/i })).toHaveAttribute(
      "href",
      "/surface",
    );
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(liveApi.getSurface).not.toHaveBeenCalled();
  });

  it("opens empty inspector from app chrome control", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/surface");
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /inspector/i }));
    expect(screen.getByText(/Select a timeline ref or record event to inspect/i)).toBeInTheDocument();
  });

  it("renders plan surface from /plan", async () => {
    window.history.pushState({}, "", "/plan");
    render(<App />);

    expect(await screen.findByTestId("plan-canvas-title")).toHaveTextContent(/C2 Session 23 Prep/i);
    const toolbox = screen.getByRole("navigation", { name: "Toolbox tools" });
    expect(toolbox).toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Ingest Recap" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Graph Preview" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Graph Gold Review" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Graph Review" })).not.toBeInTheDocument();
    expect(within(toolbox).queryByRole("button", { name: "Vocabulary Review" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(liveApi.getPlanView).toHaveBeenCalled();
  });

  it("renders memory ingest from /ingest", async () => {
    window.history.pushState({}, "", "/ingest");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    expect(screen.queryByText(/Review extracted graph runs against gold/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ingest" })).toHaveClass("active");
    expect(await screen.findByText(/No preview-ready graph runs are available/i)).toBeInTheDocument();
    expect(liveApi.getPlanView).toHaveBeenCalled();
    expect(liveApi.getGraphIngestRuns).toHaveBeenCalled();
    expect(liveApi.getGoldReviewSessions).toHaveBeenCalled();
  });

  it("renders the shared editor toolbar collapsed on the Tiptap spike route", async () => {
    const runbookRecord = fixtureWorkspaceDocumentRecord({
      document_id: FIXTURE_DOC_ID,
      kind: "runbook",
      title: "North Gate Session Runbook",
      target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
      target_session: 23,
      revision: 1,
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [runbookRecord],
    });
    vi.mocked(liveApi.getWorkspaceDocument).mockResolvedValue(runbookRecord);
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(runbookRecord);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      fixtureSnapshot({
        record: runbookRecord,
        loaded_revision: runbookRecord.revision,
        markdown: "",
      }),
    );

    window.history.pushState({}, "", "/tiptap-callout-spike");
    render(<App />);

    // Authority-safe open: runbook kind accepted; editor shell mounts under App chrome.
    expect(await screen.findByRole("heading", { name: "Tiptap Session Runbook Editor" })).toBeInTheDocument();
    expect(screen.getByTestId("tiptap-editor")).toBeInTheDocument();
    expect(screen.queryByText(/wrong document kind|Failed to load runbook/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live play" })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );

    const editToggle = await screen.findByRole("button", { name: "Edit" });
    expect(editToggle).toHaveAttribute("aria-expanded", "false");
  });

});
