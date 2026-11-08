// @vitest-environment jsdom
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { InMemoryLocalWorldRepository, InMemoryLocalWorldStore } from "../inMemoryLocalWorldRepository";
import { clearPendingWorldNotesDraft, getPendingWorldNotesDraft, setPendingWorldNotesDraft } from "../localWorldDocumentAuthoring";
import { LocalWorldSurface } from "./LocalWorldSurface";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../tiptap/MarkdownEditorCore", async () => {
  const React = await import("react");
  return {
    MarkdownEditorCore: ({ content, editable, onUpdate, dataTestId }: {
      content: { content?: readonly { content?: readonly { text?: string }[] }[] };
      editable?: boolean;
      onUpdate?: (json: unknown, editor: { getJSON: () => unknown }, meta: { programmatic: boolean }) => void;
      dataTestId?: string;
    }) => {
      const value = (content.content ?? []).flatMap((node) => node.content ?? []).map((node) => node.text ?? "").join("\n");
      return React.createElement("textarea", {
        "data-testid": dataTestId,
        "aria-label": "World notes editor",
        disabled: !editable,
        value,
        onChange: (event: React.ChangeEvent<HTMLTextAreaElement>) => {
          const json = { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: event.target.value }] }] };
          onUpdate?.(json, { getJSON: () => json }, { programmatic: false });
        },
      });
    },
  };
});

function renderSurface(repository: InMemoryLocalWorldRepository) {
  return render(<AgentInteractionProvider><LocalWorldSurface openRepository={async () => ({ status: "opened", repository })} /></AgentInteractionProvider>);
}

describe("local World notes editor", () => {
  it("keeps a newer tab draft separate while a persisted conflict is previewed or discarded", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    const created = await repository.createWorld({ title: "Coexisting drafts" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, markdown: "Committed winner" });
    const current = await repository.readWorld(created.record.snapshot.worldId);
    expect(current.status).toBe("found");
    if (current.status !== "found") return;
    await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: current.record.localRevision,
      nextSnapshot: { ...current.record.snapshot, title: "Coexisting drafts current" },
      edit: { classification: "buddy-local-only", description: "Concurrent title edit" },
    });
    const stale = await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 1, markdown: "Older persisted candidate" });
    expect(stale.status).toBe("conflict");
    setPendingWorldNotesDraft(created.record.snapshot.worldId, "Newer unsaved tab draft", "Committed winner");

    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Coexisting drafts current/ }));
    const editor = await screen.findByRole("textbox", { name: "World notes editor" });
    expect(editor).toHaveValue("Newer unsaved tab draft");
    expect(editor).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Recover draft 1" }));
    expect(editor).toHaveValue("Older persisted candidate");
    expect(getPendingWorldNotesDraft(created.record.snapshot.worldId)?.value).toBe("Newer unsaved tab draft");
    await user.click(screen.getByRole("button", { name: "Show newer unsaved tab draft" }));
    expect(editor).toHaveValue("Newer unsaved tab draft");
    expect(editor).toBeEnabled();
    expect(getPendingWorldNotesDraft(created.record.snapshot.worldId)?.value).toBe("Newer unsaved tab draft");
    await user.click(screen.getByRole("button", { name: "Recover draft 1" }));
    await user.click(screen.getByRole("button", { name: "Keep saved version" }));
    expect(editor).toHaveValue("Newer unsaved tab draft");
    expect(getPendingWorldNotesDraft(created.record.snapshot.worldId)?.value).toBe("Newer unsaved tab draft");
    clearPendingWorldNotesDraft(created.record.snapshot.worldId);
  });

  it("preserves a newer draft across delayed save, remount, and old conflict recovery", async () => {
    let holdFirstSave = false;
    let releaseOldSave!: () => void;
    let signalSaveStarted!: () => void;
    const oldSaveGate = new Promise<void>((resolve) => { releaseOldSave = resolve; });
    const saveStarted = new Promise<void>((resolve) => { signalSaveStarted = resolve; });
    const store = new InMemoryLocalWorldStore();
    const repository = new InMemoryLocalWorldRepository({
      store,
      beforeCommit: async (point) => {
        if (point === "document-edit" && holdFirstSave) {
          holdFirstSave = false;
          signalSaveStarted();
          await oldSaveGate;
        }
      },
    });
    const created = await repository.createWorld({ title: "Delayed conflict drafts" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, markdown: "Committed winner" });
    holdFirstSave = true;

    const user = userEvent.setup();
    const first = renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Delayed conflict drafts/ }));
    const oldEditor = await screen.findByRole("textbox", { name: "World notes editor" });
    fireEvent.change(oldEditor, { target: { value: "Older in-flight save" } });
    await saveStarted;
    act(() => first.unmount());

    const current = await repository.readWorld(created.record.snapshot.worldId);
    expect(current.status).toBe("found");
    if (current.status !== "found") return;
    await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: current.record.localRevision,
      nextSnapshot: { ...current.record.snapshot, title: "Delayed conflict current" },
      edit: { classification: "buddy-local-only", description: "Concurrent title edit" },
    });

    const second = renderSurface(new InMemoryLocalWorldRepository({ store }));
    await user.click(await screen.findByRole("button", { name: /Delayed conflict current/ }));
    const newerEditor = await screen.findByRole("textbox", { name: "World notes editor" });
    expect(newerEditor).toHaveValue("Older in-flight save");
    fireEvent.change(newerEditor, { target: { value: "Newer draft typed after remount" } });
    act(() => second.unmount());

    await act(async () => {
      releaseOldSave();
      await waitFor(async () => {
        const notes = await repository.readWorldNotes(created.record.snapshot.worldId);
        expect(notes.status).toBe("found");
        if (notes.status === "found") expect(notes.state.conflictCandidates).toHaveLength(1);
      });
    });
    expect(getPendingWorldNotesDraft(created.record.snapshot.worldId)?.value).toBe("Newer draft typed after remount\n");

    renderSurface(new InMemoryLocalWorldRepository({ store }));
    await user.click(await screen.findByRole("button", { name: /Delayed conflict current/ }));
    const reopenedEditor = await screen.findByRole("textbox", { name: "World notes editor" });
    expect(reopenedEditor).toHaveValue("Newer draft typed after remount");
    await user.click(screen.getByRole("button", { name: "Recover draft 1" }));
    expect(reopenedEditor).toHaveValue("Older in-flight save");
    expect(getPendingWorldNotesDraft(created.record.snapshot.worldId)?.value).toBe("Newer draft typed after remount\n");
    await user.click(screen.getByRole("button", { name: "Show newer unsaved tab draft" }));
    expect(reopenedEditor).toHaveValue("Newer draft typed after remount");
    expect(reopenedEditor).toBeEnabled();
    clearPendingWorldNotesDraft(created.record.snapshot.worldId);
  });

  it("creates a real shared-editor document, autosaves it, and restores it after a Surface remount", async () => {
    const user = userEvent.setup();
    const store = new InMemoryLocalWorldStore();
    const repository = new InMemoryLocalWorldRepository({ store });
    const created = await repository.createWorld({ title: "Notes World" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;

    const first = renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Notes World/ }));
    await user.click(await screen.findByRole("button", { name: "Start writing" }));
    const editable = await screen.findByRole("textbox", { name: "World notes editor" });
    fireEvent.change(editable, { target: { value: "The lighthouse watches the harbor." } });
    await waitFor(async () => {
      const state = await repository.readWorldNotes(created.record.snapshot.worldId);
      expect(state.status).toBe("found");
      if (state.status === "found") {
        expect(state.state.documentExists).toBe(true);
        expect(state.state.markdown).toContain("The lighthouse watches the harbor.");
      }
    });
    await waitFor(() => expect(screen.getAllByText("Saved in this browser").length).toBeGreaterThan(0));

    first.unmount();
    renderSurface(new InMemoryLocalWorldRepository({ store }));
    await user.click(await screen.findByRole("button", { name: /Notes World/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "World notes editor" })).toHaveValue("The lighthouse watches the harbor."));
  });

  it("keeps the old committed note and exposes a failed edit as unsaved", async () => {
    let failEdit = false;
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: (point) => {
      if (point === "document-edit" && failEdit) {
        failEdit = false;
        throw new Error("Local notes transaction aborted.");
      }
    } });
    const created = await repository.createWorld({ title: "Failure World" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const user = userEvent.setup();
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Failure World/ }));
    await user.click(await screen.findByRole("button", { name: "Start writing" }));
    await screen.findByTestId("local-world-notes-editor");
    const editable = await screen.findByRole("textbox", { name: "World notes editor" });
    failEdit = true;
    fireEvent.change(editable!, { target: { value: "An unsaved fragment." } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Local notes transaction aborted.");
    const saved = await repository.readWorldNotes(created.record.snapshot.worldId);
    expect(saved.status).toBe("found");
    if (saved.status === "found") expect(saved.state.markdown).toBe("");
    expect(screen.queryByText("Saved in this browser")).toBeNull();
  });

  it("requires an explicit recover choice after a notes conflict survives a route remount", async () => {
    const user = userEvent.setup();
    const store = new InMemoryLocalWorldStore();
    const repository = new InMemoryLocalWorldRepository({ store });
    const created = await repository.createWorld({ title: "Conflict Notes" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const first = renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Conflict Notes/ }));
    await user.click(await screen.findByRole("button", { name: "Start writing" }));
    const editor = await screen.findByRole("textbox", { name: "World notes editor" });
    fireEvent.change(editor, { target: { value: "Committed notes body." } });
    await waitFor(async () => {
      const state = await repository.readWorldNotes(created.record.snapshot.worldId);
      expect(state.status).toBe("found");
      if (state.status === "found") expect(state.state.markdown).toContain("Committed notes body.");
    });
    const current = await repository.readWorld(created.record.snapshot.worldId);
    expect(current.status).toBe("found");
    if (current.status !== "found") return;
    await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: current.record.localRevision,
      nextSnapshot: { ...current.record.snapshot, title: "Changed elsewhere" },
      edit: { classification: "buddy-local-only", description: "Concurrent title edit" },
    });
    fireEvent.change(editor, { target: { value: "Retained losing notes." } });
    await screen.findByText("Conflict draft retained");
    first.unmount();

    renderSurface(new InMemoryLocalWorldRepository({ store }));
    await user.click(await screen.findByRole("button", { name: /Changed elsewhere/ }));
    expect(await screen.findByText("Conflict draft retained")).toBeTruthy();
    const reopenedEditor = await screen.findByRole("textbox", { name: "World notes editor" });
    expect(reopenedEditor).toBeDisabled();
    expect(reopenedEditor).toHaveValue("Committed notes body.");
    await user.click(screen.getByRole("button", { name: "Recover draft 1" }));
    expect(reopenedEditor).toBeDisabled();
    expect(reopenedEditor).toHaveValue("Retained losing notes.");
    await user.click(screen.getByRole("button", { name: "Reapply recovered draft on current revision" }));
    await waitFor(async () => {
      const state = await repository.readWorldNotes(created.record.snapshot.worldId);
      expect(state.status).toBe("found");
      if (state.status === "found") {
        expect(state.state.markdown).toContain("Retained losing notes.");
        expect(state.state.conflictCandidates).toHaveLength(0);
      }
    });
  });

  it("preserves a YAML frontmatter envelope when editing the Markdown body", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    const created = await repository.createWorld({ title: "Metadata Notes" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const original = "---\ntitle: keep-me\n---\n\nOriginal note\n";
    expect((await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, markdown: original })).status).toBe("committed");
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Metadata Notes/ }));
    const editor = await screen.findByRole("textbox", { name: "World notes editor" });
    fireEvent.change(editor, { target: { value: "Edited note" } });
    await waitFor(async () => {
      const notes = await repository.readWorldNotes(created.record.snapshot.worldId);
      expect(notes.status).toBe("found");
      if (notes.status === "found") expect(notes.state.markdown).toContain("---\ntitle: keep-me\n---\nEdited note");
    });
  });

  it("keeps imported Markdown with unsupported task-list syntax intact and read-only", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    const created = await repository.createWorld({ title: "Unsupported Notes" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const original = "- [ ] unsupported task\n\nOriginal note\n";
    expect((await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, markdown: original })).status).toBe("committed");
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Unsupported Notes/ }));
    expect(await screen.findByText(/features the editor cannot preserve yet/)).toBeTruthy();
    expect(await screen.findByRole("textbox", { name: "World notes editor" })).toBeDisabled();
    const notes = await repository.readWorldNotes(created.record.snapshot.worldId);
    expect(notes.status).toBe("found");
    if (notes.status === "found") expect(notes.state.markdown).toBe(original);
  });

  it("restores the committed frontmatter after discarding a different recovered conflict envelope", async () => {
    const user = userEvent.setup();
    const repository = new InMemoryLocalWorldRepository();
    const created = await repository.createWorld({ title: "Envelope conflict" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    const savedEnvelope = "---\ntitle: committed\n---\n\nSaved body\n";
    const candidateEnvelope = "---\ntitle: losing-candidate\n---\n\nLosing body\n";
    expect((await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, markdown: savedEnvelope })).status).toBe("committed");
    const withConcurrentRevision = await repository.readWorld(created.record.snapshot.worldId);
    expect(withConcurrentRevision.status).toBe("found");
    if (withConcurrentRevision.status !== "found") return;
    await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: withConcurrentRevision.record.localRevision,
      nextSnapshot: { ...withConcurrentRevision.record.snapshot, title: "Envelope changed elsewhere" },
      edit: { classification: "buddy-local-only", description: "Concurrent title edit" },
    });
    const stale = await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 1, markdown: candidateEnvelope });
    expect(stale.status).toBe("conflict");

    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Envelope changed elsewhere/ }));
    await user.click(await screen.findByRole("button", { name: "Recover draft 1" }));
    expect(await screen.findByRole("textbox", { name: "World notes editor" })).toHaveValue("Losing body");
    await user.click(screen.getByRole("button", { name: "Keep saved version" }));
    const editor = await screen.findByRole("textbox", { name: "World notes editor" });
    expect(editor).toHaveValue("Saved body");
    fireEvent.change(editor, { target: { value: "Edited committed body" } });
    await waitFor(async () => {
      const notes = await repository.readWorldNotes(created.record.snapshot.worldId);
      expect(notes.status).toBe("found");
      if (notes.status === "found") {
        expect(notes.state.markdown).toContain("title: committed");
        expect(notes.state.markdown).not.toContain("losing-candidate");
        expect(notes.state.markdown).toContain("Edited committed body");
      }
    });
  });

  it("keeps a recovered conflict read-only after a failed reapply", async () => {
    let failReapply = false;
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: (point) => {
      if (point === "document-edit" && failReapply) { failReapply = false; throw new Error("Reapply transaction failed."); }
    } });
    const created = await repository.createWorld({ title: "Failed reapply" });
    expect(created.status).toBe("created");
    if (created.status !== "created") return;
    await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, markdown: "Committed body" });
    const current = await repository.readWorld(created.record.snapshot.worldId);
    expect(current.status).toBe("found");
    if (current.status !== "found") return;
    await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: current.record.localRevision,
      nextSnapshot: { ...current.record.snapshot, title: "Changed revision" },
      edit: { classification: "buddy-local-only", description: "Concurrent title edit" },
    });
    await repository.commitWorldNotes({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 1, markdown: "Conflict body" });
    failReapply = true;
    const user = userEvent.setup();
    renderSurface(repository);
    await user.click(await screen.findByRole("button", { name: /Changed revision/ }));
    await user.click(await screen.findByRole("button", { name: "Recover draft 1" }));
    const editor = await screen.findByRole("textbox", { name: "World notes editor" });
    expect(editor).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Reapply recovered draft on current revision" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reapply transaction failed.");
    expect(editor).toBeDisabled();
    const state = await repository.readWorldNotes(created.record.snapshot.worldId);
    expect(state.status).toBe("found");
    if (state.status === "found") {
      expect(state.state.markdown).toBe("Committed body");
      expect(state.state.conflictCandidates).toHaveLength(1);
    }
  });
});
