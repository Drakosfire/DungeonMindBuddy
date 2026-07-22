import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as liveApi from "./api/liveApi";
import { fixtureWorkspaceDocumentRecord } from "./planSurface/config/planSessionDescriptor";
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
    createWorkspaceDocument: vi.fn(),
    getWorkspaceDocument: vi.fn(),
  };
});

describe("App inspector integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
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
    const planRecord = fixtureWorkspaceDocumentRecord();
    const runbookRecord = fixtureWorkspaceDocumentRecord({
      document_id: "22222222-2222-4222-8222-222222222222",
      title: "North Gate Session Runbook",
      kind: "runbook",
      target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockImplementation(async (args) => ({
      schema_version: "dmb_workspace_document_registry_v1",
      records: args.kind === "runbook" ? [runbookRecord] : [planRecord],
    }));
    vi.mocked(liveApi.getWorkspaceDocument).mockImplementation(async (documentId) => {
      if (documentId === runbookRecord.document_id) return runbookRecord;
      return planRecord;
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockImplementation(async (request) => {
      if (request.kind === "worldbuilding_source") {
        return {
          schema_version: "dmb_workspace_document_record_v1",
          document_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          title: request.title,
          campaign_id: request.campaign_id,
          target_session: request.target_session ?? null,
          kind: "worldbuilding_source",
          target_relpath: "out/workspace/worldbuilding/cccccccc-cccc-4ccc-8ccc-cccccccccccc.md",
          status: "active",
          content_status: "draft",
          revision: 1,
          created_at: "2026-07-22T00:00:00Z",
          updated_at: "2026-07-22T00:00:00Z",
          source_domain: request.source_domain ?? "worldbuilding",
          document_class: request.document_class ?? "lore",
          authority_state: request.authority_state ?? "draft",
          visibility_state: request.visibility_state ?? "internal",
        };
      }
      if (request.kind === "runbook") return runbookRecord;
      return planRecord;
    });
  });

  it("renders the launcher at the root route", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /mireward local tools/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /plan prep surface/i })).toHaveAttribute("href", "/plan");
    expect(screen.getByRole("link", { name: /build worldbuilding source/i })).toHaveAttribute("href", "/build");
    expect(screen.getByRole("link", { name: /ingest memory ingest/i })).toHaveAttribute("href", "/ingest");
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

  it("renders build surface from /build", async () => {
    window.history.pushState({}, "", "/build");
    render(<App />);

    expect(await screen.findByTestId("build-surface")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Build" })).toHaveClass("active");
    expect(screen.getByTestId("build-source-metadata")).toHaveTextContent("worldbuilding_source");
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalled();
  });

  it("renders the shared editor toolbar collapsed on the Tiptap spike route", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/tiptap-callout-spike");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Tiptap Session Runbook Editor" })).toBeInTheDocument();
    expect(screen.getByTestId("tiptap-editor")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live play" })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Reset local draft" })).not.toBeDisabled();
    });

    const editToggle = await screen.findByRole(
      "button",
      { name: "Edit" },
      { timeout: 5000 },
    );
    expect(editToggle).toHaveAttribute("aria-expanded", "false");

    await user.click(editToggle);

    expect(await screen.findByRole("button", { name: /Insert Read aloud/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Lock editing/ }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Unlock editing/ })).toHaveAttribute("aria-pressed", "true");
    });
    expect(screen.getByRole("button", { name: /Insert Read aloud/ })).toBeDisabled();
  });

});
