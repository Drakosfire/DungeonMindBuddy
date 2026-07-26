import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCanvasCommand } from "./useCanvasCommand";
import type { AdmittedDocumentEnvelope } from "./markdownCanvasTypes";

const ENVELOPE: AdmittedDocumentEnvelope = {
  documentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  revision: 2,
  contentSha256: "sha-a",
  contentStatus: "committed",
  documentKind: "worldbuilding_source",
  surfaceId: "build",
};

const SAVE_ID = "document.save";
const PLUGIN_WORK_ID = "plugin.work";

describe("useCanvasCommand", () => {
  it("refuses duplicate synchronous command entry", async () => {
    let release: (() => void) | undefined;
    const { result } = renderHook(() => useCanvasCommand({
      documentId: ENVELOPE.documentId,
      lookupAdmission: () => ({ ok: true, envelope: ENVELOPE }),
    }));

    let first!: Promise<unknown>;
    act(() => {
      first = result.current.runDocumentCommand(
        { id: SAVE_ID, conflictsWith: [PLUGIN_WORK_ID], admission: "none" },
        () => new Promise((resolve) => {
          release = () => resolve("saved");
        }),
      );
    });
    await waitFor(() => expect(result.current.activeCommand?.id).toBe(SAVE_ID));

    let second!: Awaited<ReturnType<typeof result.current.runDocumentCommand>>;
    await act(async () => {
      second = await result.current.runDocumentCommand(
        { id: SAVE_ID, conflictsWith: [PLUGIN_WORK_ID], admission: "none" },
        async () => "nope",
      );
    });
    expect(second.ok).toBe(false);
    if (!second.ok) expect(second.code).toBe("duplicate_command");

    await act(async () => {
      release?.();
      await first;
    });
  });

  it("refuses plugin work while save is active", async () => {
    let release: (() => void) | undefined;
    const { result } = renderHook(() => useCanvasCommand({
      documentId: ENVELOPE.documentId,
      lookupAdmission: () => ({ ok: true, envelope: ENVELOPE }),
    }));

    let savePromise!: Promise<unknown>;
    act(() => {
      savePromise = result.current.runDocumentCommand(
        { id: SAVE_ID, conflictsWith: [PLUGIN_WORK_ID], admission: "none" },
        () => new Promise((resolve) => {
          release = () => resolve("saved");
        }),
      );
    });
    await waitFor(() => expect(result.current.activeCommand?.id).toBe(SAVE_ID));

    let work!: Awaited<ReturnType<typeof result.current.runDocumentCommand>>;
    await act(async () => {
      work = await result.current.runDocumentCommand(
        { id: PLUGIN_WORK_ID, conflictsWith: [SAVE_ID], admission: "committed_clean" },
        async () => "launched",
      );
    });
    expect(work.ok).toBe(false);
    if (!work.ok) expect(work.code).toBe("conflict");

    await act(async () => {
      release?.();
      await savePromise;
    });
  });

  it("suppresses stale completion after document change", async () => {
    let release: ((value: string) => void) | undefined;
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useCanvasCommand({
        documentId,
        lookupAdmission: () => ({
          ok: true,
          envelope: { ...ENVELOPE, documentId },
        }),
      }),
      { initialProps: { documentId: ENVELOPE.documentId } },
    );

    let commandPromise!: Promise<Awaited<ReturnType<typeof result.current.runDocumentCommand>>>;
    act(() => {
      commandPromise = result.current.runDocumentCommand(
        { id: PLUGIN_WORK_ID, conflictsWith: [SAVE_ID], admission: "committed_clean" },
        () => new Promise((resolve) => {
          release = resolve;
        }),
      );
    });
    await waitFor(() => expect(release).toBeTypeOf("function"));

    rerender({ documentId: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" });

    let settled!: Awaited<typeof commandPromise>;
    await act(async () => {
      release?.("too-late");
      settled = await commandPromise;
    });
    expect(settled.ok).toBe(false);
    if (!settled.ok) expect(["invalidated", "aborted"]).toContain(settled.code);
  });

  it("passes admitted envelope into execute and refuses failed admission with codes", async () => {
    const lookup = vi.fn()
      .mockReturnValueOnce({ ok: false, code: "document_dirty" })
      .mockReturnValue({ ok: true, envelope: ENVELOPE });

    const { result } = renderHook(() => useCanvasCommand({
      documentId: ENVELOPE.documentId,
      lookupAdmission: lookup,
    }));

    let denied!: Awaited<ReturnType<typeof result.current.runDocumentCommand>>;
    await act(async () => {
      denied = await result.current.runDocumentCommand(
        { id: PLUGIN_WORK_ID, conflictsWith: [SAVE_ID], admission: "committed_clean" },
        async () => "nope",
      );
    });
    expect(denied.ok).toBe(false);
    if (!denied.ok) {
      expect(denied.code).toBe("admission_failed");
      expect(denied.admissionCode).toBe("document_dirty");
      expect(denied.reason).toBe("document_dirty");
    }

    let seen: AdmittedDocumentEnvelope | null = null;
    let allowed!: Awaited<ReturnType<typeof result.current.runDocumentCommand>>;
    await act(async () => {
      allowed = await result.current.runDocumentCommand(
        { id: PLUGIN_WORK_ID, conflictsWith: [SAVE_ID], admission: "committed_clean" },
        async ({ envelope }) => {
          seen = envelope;
          return "ok";
        },
      );
    });
    expect(allowed.ok).toBe(true);
    expect(seen).toEqual(ENVELOPE);
  });
});
