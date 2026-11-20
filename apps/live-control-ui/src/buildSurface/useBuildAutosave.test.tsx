import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { MarkdownCanvasSessionValue } from "../markdownCanvas/MarkdownCanvasSession";
import { buildSavedAt, useBuildAutosave } from "./useBuildAutosave";

const DOC_ID = "11111111-1111-4111-8111-111111111111";
const SAVED_AT = "2026-10-18T19:30:00.000Z";

function makeSession(overrides: Partial<MarkdownCanvasSessionValue> = {}): MarkdownCanvasSessionValue {
  const record = {
    document_id: DOC_ID,
    kind: "worldbuilding_source",
    content_status: "committed",
    revision: 4,
    updated_at: SAVED_AT,
  } as MarkdownCanvasSessionValue["record"];
  const snapshot = {
    record,
    loaded_revision: 4,
    content_sha256: "sha-4",
  } as MarkdownCanvasSessionValue["snapshot"];
  return {
    documentId: DOC_ID,
    documentKey: `${DOC_ID}:4`,
    phase: "ready_clean",
    record,
    snapshot,
    dirty: false,
    error: null,
    saveDisabled: true,
    saveDisabledReason: "No unsaved changes.",
    activeCommand: null,
    editor: {
      isDestroyed: false,
      on: () => undefined,
      off: () => undefined,
    } as unknown as MarkdownCanvasSessionValue["editor"],
    saveMarkdown: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  } as unknown as MarkdownCanvasSessionValue;
}

describe("useBuildAutosave", () => {
  afterEach(() => vi.useRealTimers());

  it("debounces dirty edits through the shared save command and reports the durable snapshot time", async () => {
    vi.useFakeTimers();
    const session = makeSession();
    const dirtySession = makeSession({
      phase: "ready_dirty",
      dirty: true,
      saveDisabled: false,
      saveDisabledReason: null,
    });
    const { result, rerender } = renderHook(({ value }) => useBuildAutosave(value), {
      initialProps: { value: session },
    });

    expect(result.current).toBe("saved");
    expect(buildSavedAt(session)).toBe(SAVED_AT);
    rerender({ value: dirtySession });
    expect(result.current).toBe("unsaved");

    await act(async () => { await vi.advanceTimersByTimeAsync(799); });
    expect(dirtySession.saveMarkdown).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(dirtySession.saveMarkdown).toHaveBeenCalledTimes(1);
  });

  it("restarts the quiet period on every mounted editor transaction", async () => {
    vi.useFakeTimers();
    let onUpdate: (() => void) | null = null;
    const editor = {
      isDestroyed: false,
      on: (_event: string, listener: () => void) => { onUpdate = listener; },
      off: () => { onUpdate = null; },
    } as unknown as MarkdownCanvasSessionValue["editor"];
    const clean = makeSession({ editor });
    const dirty = makeSession({ editor, phase: "ready_dirty", dirty: true, saveDisabled: false });
    const { rerender } = renderHook(({ value }) => useBuildAutosave(value), {
      initialProps: { value: clean },
    });
    rerender({ value: dirty });

    await act(async () => { await vi.advanceTimersByTimeAsync(650); });
    act(() => onUpdate?.());
    await act(async () => { await vi.advanceTimersByTimeAsync(750); });
    expect(dirty.saveMarkdown).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(50); });
    expect(dirty.saveMarkdown).toHaveBeenCalledTimes(1);
  });

  it("does not autosave an edit behind an authoring or recovery guard", async () => {
    vi.useFakeTimers();
    const guarded = makeSession({
      phase: "ready_dirty",
      dirty: true,
      saveDisabled: true,
      saveDisabledReason: "Review the protected source before saving.",
      exportedMarkdownAuthoritative: true,
    });
    const { result } = renderHook(() => useBuildAutosave(guarded));

    expect(result.current).toBe("needs-attention");
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(guarded.saveMarkdown).not.toHaveBeenCalled();
  });

  it("waits for an active document command to settle before scheduling the save", async () => {
    vi.useFakeTimers();
    const busy = makeSession({
      phase: "ready_dirty",
      dirty: true,
      saveDisabled: true,
      saveDisabledReason: "Wait for the current document action to finish.",
      activeCommand: { id: "document.metadata.update", documentId: DOC_ID, startedAt: Date.now() },
    });
    const ready = makeSession({ phase: "ready_dirty", dirty: true, saveDisabled: false });
    const { result, rerender } = renderHook(({ value }) => useBuildAutosave(value), {
      initialProps: { value: busy },
    });

    expect(result.current).toBe("unsaved");
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(busy.saveMarkdown).not.toHaveBeenCalled();
    rerender({ value: ready });
    await act(async () => { await vi.advanceTimersByTimeAsync(800); });
    expect(ready.saveMarkdown).toHaveBeenCalledTimes(1);
  });

  it("cancels the previous document timer when the selected source changes", async () => {
    vi.useFakeTimers();
    const first = makeSession({ phase: "ready_dirty", dirty: true, saveDisabled: false });
    const second = makeSession({
      documentId: "22222222-2222-4222-8222-222222222222",
      documentKey: "22222222-2222-4222-8222-222222222222:2",
      record: {
        ...first.record!,
        document_id: "22222222-2222-4222-8222-222222222222",
        revision: 2,
      },
      snapshot: {
        ...first.snapshot!,
        record: {
          ...first.snapshot!.record,
          document_id: "22222222-2222-4222-8222-222222222222",
          revision: 2,
        },
        loaded_revision: 2,
      },
      phase: "ready_dirty",
      dirty: true,
      saveDisabled: false,
    });
    const { rerender } = renderHook(({ value }) => useBuildAutosave(value), {
      initialProps: { value: first },
    });

    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    rerender({ value: second });
    await act(async () => { await vi.advanceTimersByTimeAsync(799); });
    expect(first.saveMarkdown).not.toHaveBeenCalled();
    expect(second.saveMarkdown).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(first.saveMarkdown).not.toHaveBeenCalled();
    expect(second.saveMarkdown).toHaveBeenCalledTimes(1);
  });

  it("withholds the durable timestamp when snapshot identity or revision is not verified", () => {
    const session = makeSession({
      snapshot: {
        ...makeSession().snapshot!,
        loaded_revision: 3,
      },
    });
    expect(buildSavedAt(session)).toBeNull();
  });

  it("keeps a clean server draft distinct from a committed save", () => {
    const draftRecord = { ...makeSession().record!, content_status: "draft" as const };
    const draft = makeSession({
      record: draftRecord,
      snapshot: { ...makeSession().snapshot!, record: draftRecord },
    });
    const { result } = renderHook(() => useBuildAutosave(draft));
    expect(result.current).toBe("draft");
    expect(buildSavedAt(draft)).toBeNull();
  });
});
