import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import { TiptapCalloutBridgeSpike } from "./TiptapCalloutBridgeSpike";
import {
  normalizeCalloutKind,
  tiptapJsonToSemanticMarkdown,
} from "./markdown/calloutMarkdown";
import { commitTiptapMarkdownWrite, prepareTiptapMarkdownWrite } from "../api/liveApi";

vi.mock("../api/liveApi", () => ({
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const prepareMock = vi.mocked(prepareTiptapMarkdownWrite);
const commitMock = vi.mocked(commitTiptapMarkdownWrite);

const preparedResponse = {
  schema_version: "dmb_tiptap_markdown_write_prepare_v1" as const,
  document_id: "north-gate-callout-spike",
  title: "North-gate callout spike",
  target_relpath: "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md",
  target_display_path: "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md",
  file_exists: false,
  writer_ok: true,
  writer_phase: "prepare",
  writer_confirm_token: "confirm-token",
  writer_diff: "+> [!READ-ALOUD]\n",
  warnings: [],
  diagnostics: ["dry-run only; no file was written"],
};

describe("semantic callout Markdown bridge", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    prepareMock.mockResolvedValue(preparedResponse);
    commitMock.mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: preparedResponse.document_id,
      title: preparedResponse.title,
      target_relpath: preparedResponse.target_relpath,
      target_display_path: preparedResponse.target_display_path,
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: "fingerprint",
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
    render(<TiptapCalloutBridgeSpike />);

    expect(screen.getByRole("heading", { name: "Tiptap Semantic Callout Bridge Spike" })).toBeInTheDocument();
    expect(screen.getByTestId("tiptap-editor")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Editor JSON" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Exported Markdown" })).toBeInTheDocument();
    expect(screen.getByText(/saved locally in this browser/i)).toBeInTheDocument();
    expect(screen.getByText(/No backend or corpus write happens here/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset local draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Markdown" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Commit reviewed file write" })).toBeDisabled();
    expect(await screen.findAllByText("Read aloud")).not.toHaveLength(0);
    expect(screen.getByText("Gate Dilemma d12")).toHaveClass("md-ref-chip-roll-table");
    expect(screen.getByText("North Gate Combat")).toHaveClass("md-ref-chip-action-combat");
    expect(screen.getByText("Lysandro Ironveil")).toHaveClass("md-ref-chip-npc");
  });

  it("renders the explicit file write boundary without calling the backend", () => {
    render(<TiptapCalloutBridgeSpike />);
    expect(screen.getByText(/Preparing a write asks the backend/)).toBeInTheDocument();
    expect(screen.getByText(/Committing writes the reviewed Markdown to disk/)).toBeInTheDocument();
    expect(prepareMock).not.toHaveBeenCalled();
    expect(commitMock).not.toHaveBeenCalled();
  });

  it("prepares derived Markdown, shows its diff, and commits the reviewed token", async () => {
    render(<TiptapCalloutBridgeSpike />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare file write" }));

    await waitFor(() => expect(prepareMock).toHaveBeenCalledWith(expect.objectContaining({
      document_id: "north-gate-callout-spike",
      title: "North-gate callout spike",
      target_relpath: preparedResponse.target_relpath,
      markdown: expect.stringContaining("> [!READ-ALOUD]"),
    })));
    expect(await screen.findByText("+> [!READ-ALOUD]", { exact: false })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Commit reviewed file write" }));
    await waitFor(() => expect(commitMock).toHaveBeenCalledWith(expect.objectContaining({
      writer_confirm_token: "confirm-token",
      markdown: expect.stringContaining("> [!READ-ALOUD]"),
    })));
    expect(await screen.findByText(/Local draft remains available/)).toBeInTheDocument();
  });

  it("disables commit when the target changes after prepare", async () => {
    render(<TiptapCalloutBridgeSpike />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare file write" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Commit reviewed file write" })).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Target path"), { target: { value: `${preparedResponse.target_relpath}-changed` } });
    expect(screen.getByRole("button", { name: "Commit reviewed file write" })).toBeDisabled();
    expect(screen.getByText(/Target path changed after prepare/)).toBeInTheDocument();
  });

  it("clears prior commit success when the target changes", async () => {
    render(<TiptapCalloutBridgeSpike />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare file write" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Commit reviewed file write" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Commit reviewed file write" }));
    expect(await screen.findByText(/Local draft remains available/)).toBeInTheDocument();
    expect(screen.getByText("fingerprint")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Target path"), { target: { value: `${preparedResponse.target_relpath}-changed` } });

    expect(screen.queryByText(/Local draft remains available/)).not.toBeInTheDocument();
    expect(screen.queryByText("fingerprint")).not.toBeInTheDocument();
  });

  it("shows prepare errors", async () => {
    prepareMock.mockRejectedValueOnce(new Error("unsafe target"));
    render(<TiptapCalloutBridgeSpike />);
    fireEvent.click(screen.getByRole("button", { name: "Prepare file write" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("unsafe target");
  });

  it("resets and saves the starter content locally", async () => {
    render(<TiptapCalloutBridgeSpike />);

    fireEvent.click(screen.getByRole("button", { name: "Reset local draft" }));

    expect(await screen.findByText("Reset to starter")).toBeInTheDocument();
    expect(window.localStorage.length).toBe(1);
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

  it("does not render page-local tool copy", () => {
    render(<TiptapCalloutBridgeSpike />);

    expect(screen.queryByText("Callouts")).not.toBeInTheDocument();
    expect(screen.queryByText("Insert semantic Markdown blocks.")).not.toBeInTheDocument();
  });
});
