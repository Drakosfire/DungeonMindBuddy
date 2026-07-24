import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { beforeEach, vi } from "vitest";

import type { AppChromeTools } from "../chrome/AppChrome";
import {
  commitTiptapMarkdownWrite,
  createWorkspaceDocument,
  getWorkspaceDocument,
  getWorkspaceDocumentSnapshot,
  listWorkspaceDocuments,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord, WorkspaceDocumentSnapshot } from "../api/types";
import { FIXTURE_DOC_ID, fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import { TiptapCalloutBridgeSpike } from "./TiptapCalloutBridgeSpike";
import {
  normalizeCalloutKind,
  tiptapJsonToSemanticMarkdown,
} from "./markdown/calloutMarkdown";
import {
  NORTH_GATE_RUNBOOK_TARGET_RELPATH,
  runbookDescriptorFromRecord,
  tiptapRunbookStorageKey,
} from "./descriptors/tiptapRunbookDescriptors";
import {
  buildInitialWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
} from "./state/tiptapLocalState";

vi.mock("../api/liveApi", () => ({
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
  listWorkspaceDocuments: vi.fn(),
  getWorkspaceDocument: vi.fn(),
  getWorkspaceDocumentSnapshot: vi.fn(),
  createWorkspaceDocument: vi.fn(),
}));

const prepareMock = vi.mocked(prepareTiptapMarkdownWrite);
const commitMock = vi.mocked(commitTiptapMarkdownWrite);
const listMock = vi.mocked(listWorkspaceDocuments);
const getMock = vi.mocked(getWorkspaceDocument);
const snapshotMock = vi.mocked(getWorkspaceDocumentSnapshot);
const createMock = vi.mocked(createWorkspaceDocument);

const SPIKE_DOC_ID = "22222222-2222-4222-8222-222222222222";
const SPIKE_TARGET_RELPATH = "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md";
const EMPTY_CONTENT_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

const northGateRecord = (): WorkspaceDocumentRecord => fixtureWorkspaceDocumentRecord({
  document_id: FIXTURE_DOC_ID,
  title: "North Gate Session Runbook",
  kind: "runbook",
  target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
  target_session: 23,
  revision: 1,
});

const spikeRecord = (): WorkspaceDocumentRecord => fixtureWorkspaceDocumentRecord({
  document_id: SPIKE_DOC_ID,
  title: "North Gate Callout Spike",
  kind: "runbook",
  target_relpath: SPIKE_TARGET_RELPATH,
  target_session: 23,
  revision: 1,
});

const northGateDescriptor = runbookDescriptorFromRecord(northGateRecord());
const spikeDescriptor = runbookDescriptorFromRecord(spikeRecord());

const preparedResponse = {
  schema_version: "dmb_tiptap_markdown_write_prepare_v1" as const,
  document_id: FIXTURE_DOC_ID,
  title: "North Gate Session Runbook",
  target_relpath: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
  target_display_path: NORTH_GATE_RUNBOOK_TARGET_RELPATH,
  registry_revision: 1,
  file_exists: false,
  writer_ok: true,
  writer_phase: "prepare",
  writer_confirm_token: "confirm-token",
  writer_diff: "+> [!READ-ALOUD]\n",
  warnings: [],
  diagnostics: ["dry-run only; no file was written"],
};

function snapshotFor(record: WorkspaceDocumentRecord): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: "",
    content_sha256: EMPTY_CONTENT_SHA256,
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: record.revision,
  };
}

function setupRegistryMocks() {
  listMock.mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v1",
    records: [northGateRecord()],
  });
  getMock.mockImplementation(async (documentId: string) => {
    if (documentId === FIXTURE_DOC_ID) return northGateRecord();
    if (documentId === SPIKE_DOC_ID) return spikeRecord();
    throw new Error(`Unknown document id "${documentId}"`);
  });
  snapshotMock.mockImplementation(async (documentId: string) => {
    if (documentId === FIXTURE_DOC_ID) return snapshotFor(northGateRecord());
    if (documentId === SPIKE_DOC_ID) return snapshotFor(spikeRecord());
    throw new Error(`Unknown document id "${documentId}"`);
  });
  createMock.mockResolvedValue(northGateRecord());
}

async function renderLoadedSpike(path = "/tiptap-callout-spike") {
  window.history.pushState({}, "", path);
  render(<TiptapCalloutBridgeSpike />);
  expect(await screen.findByTestId("tiptap-editor")).toBeInTheDocument();
}

async function waitForEditorReady() {
  await waitFor(() => {
    expect(
      screen.getByTestId("tiptap-editor").querySelector('[data-markdown-editor-status="ready"]'),
    ).not.toBeNull();
  });
}

async function waitForEnabledToolAction(
  toolsHolder: { current: AppChromeTools | null },
  sectionId: string,
  label: string,
) {
  await waitFor(() => {
    const action = toolsHolder.current?.sections
      ?.find((section) => section.id === sectionId)
      ?.actions.find((entry) => entry.label === label);
    expect(action).toBeDefined();
    expect(action?.disabled).toBeFalsy();
  });
  return toolsHolder.current!.sections!
    .find((section) => section.id === sectionId)!
    .actions.find((entry) => entry.label === label)!;
}

function countMarkdownMarker(marker: string): number {
  const exportText = screen.getByTestId("markdown-export").textContent ?? "";
  return exportText.split(marker).length - 1;
}

describe("semantic callout Markdown bridge", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/tiptap-callout-spike");
    window.localStorage.clear();
    vi.clearAllMocks();
    vi.stubGlobal("fetch", vi.fn());
    vi.spyOn(window, "confirm").mockReturnValue(true);
    setupRegistryMocks();
    prepareMock.mockResolvedValue(preparedResponse);
    commitMock.mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: preparedResponse.document_id,
      title: preparedResponse.title,
      target_relpath: preparedResponse.target_relpath,
      target_display_path: preparedResponse.target_display_path,
      registry_revision: 2,
      committed_revision: 2,
      committed_record: {
        ...northGateRecord(),
        revision: 2,
        content_status: "committed",
      },
      normalized_content_sha256: "sha256-committed-runbook",
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: "present:fingerprint",
      diagnostics: [],
    });
  });

  it.each([
    ["read-aloud", "read-aloud"],
    ["read-aloud-text", "read-aloud"],
    ["readaloud", "read-aloud"],
    ["gm-note", "gm-note"],
    ["dm", "gm-note"],
    ["rules", "rules"],
    ["rules-note", "rules"],
    ["rule", "rules"],
    ["warning", "warning"],
    ["warn", "warning"],
    ["danger", "warning"],
    ["unknown", "warning"],
  ] as const)("normalizes %s to %s", (input, expected) => {
    expect(normalizeCalloutKind(input)).toBe(expected);
  });

  it("serializes callout JSON to semantic Markdown", () => {
    const markdown = tiptapJsonToSemanticMarkdown({
      type: "callout",
      attrs: { kind: "warning" },
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "The gate fails in 3 rounds." }],
        },
      ],
    });

    expect(markdown).toContain("> [!WARNING]\n> The gate fails in 3 rounds.");
  });

  it("serializes custom callout labels", () => {
    const markdown = tiptapJsonToSemanticMarkdown({
      type: "callout",
      attrs: { kind: "warning", label: "Breach clock" },
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "The gate fails in 3 rounds." }],
        },
      ],
    });

    expect(markdown).toContain("> [!WARNING] Breach clock");
  });

  it("serializes reference and action nodes to typed Markdown", () => {
    const markdown = tiptapJsonToSemanticMarkdown({
      type: "paragraph",
      content: [
        { type: "text", text: "Talk to " },
        { type: "runbookReference", attrs: { kind: "ref", refType: "npc", refId: "lysandro-ironveil", label: "Lysandro Ironveil" } },
        { type: "text", text: ", then launch " },
        { type: "runbookReference", attrs: { kind: "action", refType: "combat", refId: "north-gate-combat", label: "North Gate Combat" } },
        { type: "text", text: "." },
      ],
    });

    expect(markdown).toContain("Talk to [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)");
    expect(markdown).toContain("[North Gate Combat](#dmb-action:combat:north-gate-combat).");
  });

  it("escapes reference labels and falls back to text for unsupported attrs", () => {
    const safe = tiptapJsonToSemanticMarkdown({
      type: "runbookReference",
      attrs: { kind: "ref", refType: "npc", refId: "safe-id", label: "Bad [label](javascript:evil)" },
    });
    const unsupported = tiptapJsonToSemanticMarkdown({
      type: "runbookReference",
      attrs: { kind: "ref", refType: "monster", refId: "bog-thing", label: "Bog Thing" },
    });
    const malformed = tiptapJsonToSemanticMarkdown({
      type: "runbookReference",
      attrs: { kind: "mystery", refType: "npc", refId: "BadCaps", label: "Malformed NPC" },
    });

    expect(safe).toBe("[Bad \\[label\\]\\(javascript:evil\\)](#dmb-ref:npc:safe-id)\n");
    expect(unsupported).toBe("Bog Thing\n");
    expect(unsupported).not.toContain("#dmb-ref:");
    expect(malformed).toBe("Malformed NPC\n");
  });

  it("renders the spike surface and initialized callouts", async () => {
    await renderLoadedSpike();

    expect(screen.getByRole("heading", { name: "Tiptap Session Runbook Editor" })).toBeInTheDocument();
    expect(screen.getByTestId("tiptap-editor")).toHaveAttribute("data-md-theme", "command");
    expect(screen.getByTestId("tiptap-editor")).toHaveClass("md-theme-command");
    expect(screen.getByRole("heading", { name: "Editor JSON" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Exported Markdown" })).toBeInTheDocument();
    expect(screen.getByText(/saved locally in this browser/i)).toBeInTheDocument();
    expect(screen.getByText(/No backend or corpus write happens here/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset local draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Markdown" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(await screen.findAllByText("Read aloud")).not.toHaveLength(0);
    expect(screen.getAllByText("Lysandro Ironveil")[0]).toHaveClass("md-ref-chip-npc");
    expect(screen.getAllByText("North Reach Gate")[0]).toHaveClass("md-ref-chip-location");
    expect(screen.getAllByText("Sewer Meat Creature")[0]).toHaveClass("md-ref-chip-statblock");
    expect(screen.getAllByText("Gate Dilemma d12")[0]).toHaveClass("md-ref-chip-roll-table");
    expect(screen.getAllByText("Session 22 ending")[0]).toHaveClass("md-ref-chip-citation");
    expect(screen.getAllByText("North Gate Combat")[0]).toHaveClass("md-ref-chip-action-combat");
    const exportedMarkdown = screen.getByTestId("markdown-export");
    expect(exportedMarkdown).toHaveTextContent("#dmb-ref:npc:lysandro-ironveil");
    expect(exportedMarkdown).toHaveTextContent("#dmb-ref:location:north-reach-gate");
    expect(exportedMarkdown).toHaveTextContent("#dmb-ref:statblock:sewer-meat-creature");
    expect(exportedMarkdown).toHaveTextContent("#dmb-ref:roll-table:gate-dilemma-d12");
    expect(exportedMarkdown).toHaveTextContent("#dmb-ref:citation:c2s22-ending");
    expect(exportedMarkdown).toHaveTextContent("#dmb-action:combat:north-gate-combat");
  });

  it("loads registry-selected runbook by documentId query", async () => {
    await renderLoadedSpike(`/tiptap-callout-spike?documentId=${SPIKE_DOC_ID}`);

    expect(screen.getAllByText("North Gate Callout Spike").length).toBeGreaterThan(0);
    expect(screen.getByText(SPIKE_DOC_ID)).toBeInTheDocument();
    expect(screen.getByLabelText("Target path")).toHaveTextContent(SPIKE_TARGET_RELPATH);
    expect(getMock).toHaveBeenCalledWith(SPIKE_DOC_ID);
    expect(listMock).not.toHaveBeenCalled();
  });

  it("shows a load error for unknown documentId query values", async () => {
    window.history.pushState({}, "", "/tiptap-callout-spike?documentId=bogus");
    render(<TiptapCalloutBridgeSpike />);

    expect(await screen.findByText(/Unknown document id "bogus"/)).toBeInTheDocument();
    expect(screen.queryByTestId("tiptap-editor")).not.toBeInTheDocument();
  });

  it("saves with the active document id and markdown", async () => {
    const toolsHolder: { current: AppChromeTools | null } = { current: null };
    window.history.pushState({}, "", `/tiptap-callout-spike?documentId=${SPIKE_DOC_ID}`);
    render(<TiptapCalloutBridgeSpike onEditorToolsChange={(tools) => { toolsHolder.current = tools; }} />);
    await waitForEditorReady();
    prepareMock.mockResolvedValueOnce({
      ...preparedResponse,
      document_id: SPIKE_DOC_ID,
      title: "North Gate Callout Spike",
      target_relpath: SPIKE_TARGET_RELPATH,
      target_display_path: SPIKE_TARGET_RELPATH,
    });
    commitMock.mockResolvedValueOnce({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: SPIKE_DOC_ID,
      title: "North Gate Callout Spike",
      target_relpath: SPIKE_TARGET_RELPATH,
      target_display_path: SPIKE_TARGET_RELPATH,
      registry_revision: 2,
      committed_revision: 2,
      committed_record: {
        ...spikeRecord(),
        revision: 2,
        content_status: "committed",
      },
      normalized_content_sha256: "sha256-committed-runbook",
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: "present:fingerprint",
      diagnostics: [],
    });

    const insertWarning = await waitForEnabledToolAction(toolsHolder, "tiptap-insert-blocks", "Warning");
    act(() => insertWarning.onClick());
    await waitFor(() => expect(screen.getByRole("button", { name: "Save" })).not.toBeDisabled());

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(prepareMock).toHaveBeenCalledWith({
      document_id: SPIKE_DOC_ID,
      markdown: expect.stringContaining("> [!READ-ALOUD]"),
      expected_revision: 1,
    }));
    await waitFor(() => expect(commitMock).toHaveBeenCalled());
  });

  it("resets the active document starter content under its own storage key", async () => {
    await renderLoadedSpike(`/tiptap-callout-spike?documentId=${SPIKE_DOC_ID}`);

    fireEvent.click(screen.getByRole("button", { name: "Reset local draft" }));

    expect(await screen.findByText("Reset to starter")).toBeInTheDocument();
    expect(window.localStorage.getItem(tiptapRunbookStorageKey(spikeDescriptor))).toContain("# C2S23 North Gate Session Runbook");
    expect(window.localStorage.getItem(tiptapRunbookStorageKey(northGateDescriptor))).toBeNull();
    expect(screen.getByTestId("markdown-export")).toHaveTextContent("# C2S23 North Gate Session Runbook");
  });

  it("renders an import committed Markdown action", async () => {
    await renderLoadedSpike();
    expect(screen.getByRole("button", { name: "Import committed Markdown" })).toBeInTheDocument();
  });

  it("imports from the active document target and writes document-keyed local storage", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("# Imported Title\n\nTalk to [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)."));

    await renderLoadedSpike();
    fireEvent.click(screen.getByRole("button", { name: "Import committed Markdown" }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(`/${NORTH_GATE_RUNBOOK_TARGET_RELPATH}`));
    expect(await screen.findByText(/Imported committed Markdown from evals\/c2_live_prep/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("markdown-export")).toHaveTextContent("# Imported Title");
    });
    expect(screen.getByTestId("markdown-export")).toHaveTextContent("#dmb-ref:npc:lysandro-ironveil");
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(FIXTURE_DOC_ID))).toContain("Imported Title");
  });

  it("imports using the selected document target and storage key", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("# Spike Import\n\n> [!WARNING]\n> Spike warning."));

    await renderLoadedSpike(`/tiptap-callout-spike?documentId=${SPIKE_DOC_ID}`);
    fireEvent.click(screen.getByRole("button", { name: "Import committed Markdown" }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(`/${SPIKE_TARGET_RELPATH}`));
    expect(await screen.findByText(/Imported committed Markdown from evals\/c2_live_prep/)).toBeInTheDocument();
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(SPIKE_DOC_ID))).toContain("Spike Import");
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(FIXTURE_DOC_ID))).toBeNull();
  });

  it("treats imported committed Markdown as a saved draft until a file write commits", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("# Imported Title\n\nA plain imported plan."));

    await renderLoadedSpike();
    fireEvent.click(screen.getByRole("button", { name: "Import committed Markdown" }));

    expect(await screen.findByText(/Imported committed Markdown from evals\/c2_live_prep/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("markdown-export")).toHaveTextContent("A plain imported plan.");
    });
    expect(screen.getByText("Imported committed Markdown")).toBeInTheDocument();
    const importedParagraph = within(screen.getByTestId("tiptap-editor")).getByText(/A plain imported plan/);
    fireEvent.mouseMove(importedParagraph);

    expect(screen.getAllByText("Saved draft").length).toBeGreaterThan(0);
    expect(screen.queryByText("Committed prep")).not.toBeInTheDocument();
  });

  it("confirms before replacing a local draft", async () => {
    const state = buildInitialWorkspaceDocumentLocalState({
      documentId: FIXTURE_DOC_ID,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      baseRevision: 1,
      baseContentSha256: EMPTY_CONTENT_SHA256,
      starterContent: northGateDescriptor.starterContent,
    });
    state.exported_markdown = "# Existing local draft\n";
    state.tiptap_json = { type: "doc", content: [{ type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Existing local draft" }] }] };
    window.localStorage.setItem(workspaceDocumentStorageKey(FIXTURE_DOC_ID), JSON.stringify(state));
    vi.mocked(window.confirm).mockReturnValueOnce(false);

    await renderLoadedSpike();
    fireEvent.click(screen.getByRole("button", { name: "Import committed Markdown" }));

    expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByTestId("markdown-export")).toHaveTextContent("# Existing local draft");
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(FIXTURE_DOC_ID))).toContain("Existing local draft");
  });

  it("renders import errors calmly and leaves the editor unchanged", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("not found", { status: 404, statusText: "Not Found" }));

    await renderLoadedSpike();
    const before = screen.getByTestId("markdown-export").textContent;
    fireEvent.click(screen.getByRole("button", { name: "Import committed Markdown" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Import failed");
    expect(screen.getByTestId("markdown-export").textContent).toBe(before);
  });

  it("renders the explicit file write boundary without calling the backend", async () => {
    await renderLoadedSpike();
    expect(screen.getByText(/Saving asks the backend to prepare and commit/)).toBeInTheDocument();
    expect(prepareMock).not.toHaveBeenCalled();
    expect(commitMock).not.toHaveBeenCalled();
  });

  it("shows block save-state guidance when hovering reference and operational blocks", async () => {
    await renderLoadedSpike();

    fireEvent.mouseMove((await screen.findAllByText("Lysandro Ironveil"))[0]);

    expect(screen.getAllByText("Read-only reference").length).toBeGreaterThan(0);
    expect(screen.getByText(/edit surrounding prose, not the referenced canon identity/i)).toBeInTheDocument();

    fireEvent.mouseMove(screen.getAllByText("North Gate Combat")[0]);

    expect(screen.getAllByText("Operational").length).toBeGreaterThan(0);
    expect(screen.getByText(/points at a live operation\/action/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lock live block" })).toBeInTheDocument();
  });

  it("can lock the editor from an operational block badge", async () => {
    await renderLoadedSpike();

    fireEvent.mouseMove((await screen.findAllByText("North Gate Combat"))[0]);
    fireEvent.click(screen.getByRole("button", { name: "Lock live block" }));

    expect(screen.getByRole("button", { name: "Unlock live block" })).toBeInTheDocument();
    expect(screen.getAllByText("Locked for live").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Unlock live block" }));

    expect(screen.getAllByText("Operational").length).toBeGreaterThan(0);
    expect(screen.queryByText("Local scratch")).not.toBeInTheDocument();
  });

  it("prepares and commits derived Markdown in one save action", async () => {
    const toolsHolder: { current: AppChromeTools | null } = { current: null };
    render(<TiptapCalloutBridgeSpike onEditorToolsChange={(tools) => { toolsHolder.current = tools; }} />);
    await waitForEditorReady();

    const insertWarning = await waitForEnabledToolAction(toolsHolder, "tiptap-insert-blocks", "Warning");
    act(() => insertWarning.onClick());
    await waitFor(() => expect(screen.getByRole("button", { name: "Save" })).not.toBeDisabled());

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(prepareMock).toHaveBeenCalledWith({
      document_id: FIXTURE_DOC_ID,
      markdown: expect.stringContaining("> [!READ-ALOUD]"),
      expected_revision: 1,
    }));
    await waitFor(() => expect(commitMock).toHaveBeenCalledWith({
      document_id: FIXTURE_DOC_ID,
      markdown: expect.stringContaining("> [!READ-ALOUD]"),
      writer_confirm_token: "confirm-token",
      expected_revision: 1,
    }));
    await waitFor(() => {
      expect(screen.getByText("Bytes written")).toBeInTheDocument();
      expect(screen.getByText("42")).toBeInTheDocument();
    });
  });

  it("displays registry-owned target path as read-only", async () => {
    await renderLoadedSpike();
    expect(screen.getByLabelText("Target path")).toHaveTextContent(preparedResponse.target_relpath);
    expect(screen.queryByRole("textbox", { name: "Target path" })).not.toBeInTheDocument();
  });

  it("shows save errors", async () => {
    prepareMock.mockRejectedValueOnce(new Error("unsafe target"));
    const toolsHolder: { current: AppChromeTools | null } = { current: null };
    render(<TiptapCalloutBridgeSpike onEditorToolsChange={(tools) => { toolsHolder.current = tools; }} />);
    await waitForEditorReady();

    const insertWarning = await waitForEnabledToolAction(toolsHolder, "tiptap-insert-blocks", "Warning");
    act(() => insertWarning.onClick());
    await waitFor(() => expect(screen.getByRole("button", { name: "Save" })).not.toBeDisabled());

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("unsafe target");
  });

  it("resets and saves the starter content locally", async () => {
    await renderLoadedSpike();

    fireEvent.click(screen.getByRole("button", { name: "Reset local draft" }));

    expect(await screen.findByText("Reset to starter")).toBeInTheDocument();
    expect(window.localStorage.length).toBe(1);
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(FIXTURE_DOC_ID))).toContain("# C2S23 North Gate Session Runbook");
  });

  it("registers editor tools for the app chrome", async () => {
    const handleEditorToolsChange = vi.fn();

    render(<TiptapCalloutBridgeSpike onEditorToolsChange={handleEditorToolsChange} />);

    await waitFor(() => {
      expect(handleEditorToolsChange).toHaveBeenCalledWith(
        expect.objectContaining({
          pinnedActions: expect.arrayContaining([
            expect.objectContaining({ id: "tiptap-edit-lock", label: "Lock editing" }),
          ]),
          sections: expect.arrayContaining([
            expect.objectContaining({ id: "tiptap-local-state", title: "Local working state" }),
            expect.objectContaining({ id: "tiptap-insert-blocks", title: "Insert blocks" }),
            expect.objectContaining({ id: "tiptap-insert-refs", title: "Insert refs" }),
          ]),
        }),
      );
    });
  });

  it("inserts a registered reference action and updates exported Markdown", async () => {
    let tools: AppChromeTools | null = null;
    render(<TiptapCalloutBridgeSpike onEditorToolsChange={(nextTools) => { tools = nextTools; }} />);

    await waitFor(() => expect(tools?.sections?.find((section) => section.id === "tiptap-insert-refs")).toBeDefined());
    const insertLocation = tools?.sections
      ?.find((section) => section.id === "tiptap-insert-refs")
      ?.actions.find((action) => action.label === "North Reach Gate");

    expect(insertLocation).toBeDefined();
    act(() => insertLocation?.onClick());

    await waitFor(() => {
      expect(screen.getByTestId("markdown-export")).toHaveTextContent(
        "[North Reach Gate](#dmb-ref:location:north-reach-gate)",
      );
    });
  });

  it("renders malformed persisted references as invalid editor text", async () => {
    const state = buildInitialWorkspaceDocumentLocalState({
      documentId: FIXTURE_DOC_ID,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      baseRevision: 1,
      baseContentSha256: EMPTY_CONTENT_SHA256,
      starterContent: northGateDescriptor.starterContent,
    });
    state.tiptap_json = {
      type: "doc",
      content: [{
        type: "paragraph",
        content: [{
          type: "runbookReference",
          attrs: { kind: "ref", refType: "monster", refId: "bog-thing", label: "Bog Thing" },
        }],
      }],
    };
    window.localStorage.setItem(workspaceDocumentStorageKey(FIXTURE_DOC_ID), JSON.stringify(state));

    await renderLoadedSpike();

    const invalidReference = await screen.findByTitle("Invalid runbook reference");
    expect(invalidReference).toHaveTextContent("Bog Thing");
    expect(invalidReference).toHaveClass("md-ref-invalid");
    expect(invalidReference).not.toHaveClass("md-ref-chip");
    expect(invalidReference).toHaveAttribute("data-md-ref-kind", "invalid");
    expect(screen.getByTestId("markdown-export")).toHaveTextContent("Bog Thing");
    expect(screen.getByTestId("markdown-export")).not.toHaveTextContent("#dmb-ref:monster");
  });

  it("embeds the Tiptap-authored runbook from live play", () => {
    const html = readFileSync("../../evals/c2_live_prep/mireward-prep/live-play.html", "utf8");

    expect(html).toContain("content/tiptap/north-gate-session-runbook.md");
  });

  it("persists the first edit after ordinary mount", async () => {
    const toolsHolder: { current: AppChromeTools | null } = { current: null };
    render(
      <TiptapCalloutBridgeSpike
        onEditorToolsChange={(nextTools) => {
          toolsHolder.current = nextTools;
        }}
      />,
    );

    await waitForEditorReady();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    const warningCountBefore = countMarkdownMarker("> [!WARNING]");

    const insertWarning = await waitForEnabledToolAction(
      toolsHolder,
      "tiptap-insert-blocks",
      "Warning",
    );
    act(() => insertWarning.onClick());

    await waitFor(() => {
      expect(countMarkdownMarker("> [!WARNING]")).toBe(warningCountBefore + 1);
    });
  });

  it("persists the first edit after reset", async () => {
    const toolsHolder: { current: AppChromeTools | null } = { current: null };
    render(
      <TiptapCalloutBridgeSpike
        onEditorToolsChange={(nextTools) => {
          toolsHolder.current = nextTools;
        }}
      />,
    );
    await waitForEditorReady();

    fireEvent.click(screen.getByRole("button", { name: "Reset local draft" }));
    expect(await screen.findByText("Reset to starter")).toBeInTheDocument();
    await waitForEditorReady();
    const warningCountBefore = countMarkdownMarker("> [!WARNING]");

    const insertWarning = await waitForEnabledToolAction(
      toolsHolder,
      "tiptap-insert-blocks",
      "Warning",
    );
    act(() => insertWarning.onClick());

    await waitFor(() => {
      expect(countMarkdownMarker("> [!WARNING]")).toBe(warningCountBefore + 1);
    });
  });

  it("persists the first edit after imported Markdown remount", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("# Imported title\n\nImported body.\n", {
        status: 200,
        headers: { "Content-Type": "text/markdown" },
      }),
    );
    const toolsHolder: { current: AppChromeTools | null } = { current: null };
    render(
      <TiptapCalloutBridgeSpike
        onEditorToolsChange={(nextTools) => {
          toolsHolder.current = nextTools;
        }}
      />,
    );
    await waitForEditorReady();

    fireEvent.click(screen.getByRole("button", { name: "Import committed Markdown" }));
    expect(await screen.findByText(/Imported committed Markdown from evals\/c2_live_prep/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("markdown-export")).toHaveTextContent("Imported body.");
    });
    await waitForEditorReady();
    expect(countMarkdownMarker("> [!WARNING]")).toBe(0);

    const insertWarning = await waitForEnabledToolAction(
      toolsHolder,
      "tiptap-insert-blocks",
      "Warning",
    );
    act(() => insertWarning.onClick());

    await waitFor(() => {
      expect(countMarkdownMarker("> [!WARNING]")).toBe(1);
    });
    fetchMock.mockRestore();
  });

  it("does not render page-local tool copy", async () => {
    await renderLoadedSpike();

    expect(screen.queryByText("Callouts")).not.toBeInTheDocument();
    expect(screen.queryByText("Insert semantic Markdown blocks.")).not.toBeInTheDocument();
  });
});
