import { StrictMode, useState } from "react";
import { webcrypto } from "node:crypto";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LiveApiError } from "../../api/liveApi";
import { getWorldPlayRunContent, getWorldPlayRunContentCommand, putWorldPlayRunContentCommand } from "../../api/playRunContentApi";
import { contentSha256 } from "../playRunEffectiveContent";
import type { PlayRunContent, PlayRunContentCommitRequest, PlayRunContentReceipt } from "../playRunContentTypes";
import { playRunContentJournalKey } from "./playRunContentJournal";
import { usePlayRunContentController } from "./usePlayRunContentController";

vi.mock("../../api/playRunContentApi", () => ({ getWorldPlayRunContent: vi.fn(), getWorldPlayRunContentCommand: vi.fn(), putWorldPlayRunContentCommand: vi.fn() }));

const worldId = "world";
const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const artifactId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const workId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
let content: PlayRunContent;

const canonicalJson = (value: unknown): string => Array.isArray(value) ? `[${value.map(canonicalJson).join(",")}]`
  : typeof value === "object" && value !== null ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`).join(",")}}`
    : JSON.stringify(value) ?? "null";

async function receiptFor(commandId: string, request: PlayRunContentCommitRequest): Promise<PlayRunContentReceipt> {
  return { schema_version: "dmb_world_play_run_content_receipt_v1", world_id: worldId, run_id: runId, command_id: commandId,
    request_sha256: await contentSha256(canonicalJson({ world_id: worldId, run_id: runId, command_id: commandId, ...request })),
    origin: content.origin, expected_edition_revision: request.expected_edition_revision,
    expected_content_sha256: request.expected_content_sha256, accepted_edition_revision: request.expected_edition_revision + 1,
    accepted_edition_revision_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", accepted_content_sha256: await contentSha256(request.markdown),
    committed_at: "2026-10-18T01:00:00Z", observed_run_revision: 2 };
}

beforeEach(async () => {
  vi.restoreAllMocks();
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.stubGlobal("crypto", webcrypto);
  window.localStorage.clear();
  const markdown = "# Gate\n\nOriginal.\n";
  const contentSha = await contentSha256(markdown);
  content = { schema_version: "dmb_world_play_run_content_v1", world_id: worldId, run_id: runId,
    origin: { playable_artifact_id: artifactId, playable_revision: 1, playable_work_revision_id: workId, playable_content_sha256: contentSha },
    source: "pinned", edition_revision: 0, edition_revision_id: null, markdown, content_sha256: contentSha,
    structure_sha256: "e".repeat(64), committed_at: "2026-10-18T00:00:00Z", observed_run_revision: 1 };
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("Play session-copy autosave controller", () => {
  it("journals the exact request before sending and marks only its acknowledged draft saved", async () => {
    const edited = "# Gate\n\nEdited.\n";
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation(async (_run, _world, commandId, request) => {
      const journal = JSON.parse(window.localStorage.getItem(playRunContentJournalKey({ worldId, runId, origin: content.origin }))!);
      expect(journal.pending).toEqual({ commandId, draftGeneration: 1, request });
      return receiptFor(commandId, request);
    });
    vi.mocked(getWorldPlayRunContent).mockImplementation(async () => {
      const sha = await contentSha256(edited);
      return { ...content, source: "edition", edition_revision: 1, edition_revision_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        markdown: edited, content_sha256: sha, committed_at: "2026-10-18T01:00:00Z" };
    });
    const onAccepted = vi.fn();
    const onUnsubmitted = vi.fn();
    const hook = renderHook(() => usePlayRunContentController(content, onAccepted, onUnsubmitted));
    act(() => hook.result.current.changeDraft(edited));
    expect(hook.result.current.state.saveState).toBe("dirty");
    await act(async () => { await vi.advanceTimersByTimeAsync(651); });
    vi.useRealTimers();
    await waitFor(() => expect(hook.result.current.state.saveState).toBe("saved"));
    expect(putWorldPlayRunContentCommand).toHaveBeenCalledOnce();
    expect(vi.mocked(putWorldPlayRunContentCommand).mock.calls[0][3].markdown).toBe(edited);
    expect(onAccepted).toHaveBeenCalledWith(expect.objectContaining({ edition_revision: 1, markdown: edited }));
    expect(window.localStorage.getItem(playRunContentJournalKey({ worldId, runId, origin: content.origin }))).toBeNull();
  });

  it("recovers an ambiguous result with the same command and exact body instead of resending a new command", async () => {
    vi.mocked(putWorldPlayRunContentCommand).mockRejectedValue(new LiveApiError("transport uncertain", 503));
    vi.mocked(getWorldPlayRunContentCommand).mockImplementation(async (_run, _world, commandId) => {
      const journal = JSON.parse(window.localStorage.getItem(playRunContentJournalKey({ worldId, runId, origin: content.origin }))!);
      expect(journal.pending.commandId).toBe(commandId);
      expect(journal.pending.request.markdown).toBe("# Gate\n\nRecovery draft.\n");
      return receiptFor(commandId, journal.pending.request);
    });
    vi.mocked(getWorldPlayRunContent).mockImplementation(async () => {
      const markdown = "# Gate\n\nRecovery draft.\n";
      return { ...content, source: "edition", edition_revision: 1, edition_revision_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        markdown, content_sha256: await contentSha256(markdown), committed_at: "2026-10-18T01:00:00Z" };
    });
    const hook = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    act(() => hook.result.current.changeDraft("# Gate\n\nRecovery draft.\n"));
    await act(async () => { await vi.advanceTimersByTimeAsync(651); });
    vi.useRealTimers();
    await waitFor(() => expect(hook.result.current.state.saveState).toBe("unknown"));
    const rawBefore = window.localStorage.getItem(playRunContentJournalKey({ worldId, runId, origin: content.origin }))!;
    const original = JSON.parse(rawBefore).pending;
    act(() => hook.result.current.retryRecovery());
    await waitFor(() => expect(hook.result.current.state.saveState).toBe("saved"));
    expect(getWorldPlayRunContentCommand).toHaveBeenCalledWith(runId, worldId, original.commandId);
    expect(putWorldPlayRunContentCommand).toHaveBeenCalledTimes(1);
    expect(hook.result.current.state.accepted.markdown).toBe(original.request.markdown);
  });

  it("does not let an older receipt mark a newer edit as saved", async () => {
    let resolvePut!: () => Promise<void>;
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation((_run, _world, commandId, request) => new Promise(resolve => { resolvePut = async () => resolve(await receiptFor(commandId, request)); }));
    vi.mocked(getWorldPlayRunContent).mockImplementation(async () => {
      const markdown = "# Gate\n\nFirst edit.\n";
      return { ...content, source: "edition", edition_revision: 1, edition_revision_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        markdown, content_sha256: await contentSha256(markdown), committed_at: "2026-10-18T01:00:00Z" };
    });
    const hook = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    act(() => hook.result.current.changeDraft("# Gate\n\nFirst edit.\n"));
    await act(async () => { await vi.advanceTimersByTimeAsync(651); });
    expect(hook.result.current.state.saveState).toBe("saving");
    act(() => hook.result.current.changeDraft("# Gate\n\nNewer edit.\n"));
    vi.useRealTimers();
    await act(async () => { resolvePut(); });
    await waitFor(() => expect(hook.result.current.state.accepted.edition_revision).toBe(1));
    expect(hook.result.current.state.draftMarkdown).toBe("# Gate\n\nNewer edit.\n");
    expect(hook.result.current.state.saveState).toBe("dirty");
  });

  it("treats a request-body size rejection as definitive while retaining the editable draft", async () => {
    const draft = "# Gate\n\nA request that exceeded the transport limit.\n";
    vi.mocked(putWorldPlayRunContentCommand).mockRejectedValue(new LiveApiError("Request body exceeds the server limit.", 413));
    const hook = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    act(() => hook.result.current.changeDraft(draft));
    await act(async () => { await vi.advanceTimersByTimeAsync(651); });
    vi.useRealTimers();
    await waitFor(() => expect(hook.result.current.state.saveState).toBe("rejected"));
    expect(hook.result.current.state.draftMarkdown).toBe(draft);
    expect(hook.result.current.state.message).toContain("server limit");
    expect(JSON.parse(window.localStorage.getItem(playRunContentJournalKey({ worldId, runId, origin: content.origin }))!).pending).toBeNull();
    expect(putWorldPlayRunContentCommand).toHaveBeenCalledOnce();
  });

  it("blocks transport and exposes recovery failure when browser storage cannot journal a draft", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new DOMException("quota", "QuotaExceededError"); });
    const hook = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    act(() => hook.result.current.changeDraft("# Gate\n\nMust remain local.\n"));
    expect(hook.result.current.state.saveState).toBe("storage-error");
    expect(hook.result.current.state.message).toMatch(/storage/i);
    expect(putWorldPlayRunContentCommand).not.toHaveBeenCalled();
  });
  it.each([false, true])("recovers once under StrictMode and host feedback, pending=%s", async pending => {
    const identity = { worldId, runId, origin: content.origin };
    const markdown = "# Gate\n\nRecovered.\n";
    const request: PlayRunContentCommitRequest = { schema_version: "dmb_world_play_run_content_commit_v1", expected_origin: content.origin,
      expected_edition_revision: 0, expected_content_sha256: content.content_sha256, markdown };
    const command = { commandId: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", draftGeneration: 1, request };
    window.localStorage.setItem(playRunContentJournalKey(identity), JSON.stringify({ schema_version: "dmb_play_run_content_journal_v1",
      identity, accepted: content, draft_markdown: markdown, draft_generation: 1, pending: pending ? command : null }));
    vi.mocked(getWorldPlayRunContentCommand).mockImplementation(async () => receiptFor(command.commandId, request));
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation(async (_r, _w, id, body) => receiptFor(id, body));
    vi.mocked(getWorldPlayRunContent).mockRejectedValue(new Error("offline read"));
    vi.useRealTimers();
    const hook = renderHook(() => {
      const [host, setHost] = useState(content);
      return usePlayRunContentController(host, setHost, () => {});
    }, { wrapper: StrictMode });
    await waitFor(() => expect(hook.result.current.state.saveState).toBe("saved"));
    expect(hook.result.current.state.accepted.edition_revision).toBe(1);
    expect(hook.result.current.state.draftMarkdown).toBe(markdown);
    expect(getWorldPlayRunContentCommand).toHaveBeenCalledTimes(pending ? 1 : 0);
    expect(putWorldPlayRunContentCommand).toHaveBeenCalledTimes(pending ? 0 : 1);
    expect(window.localStorage.getItem(playRunContentJournalKey(identity))).toBeNull();
    act(() => hook.result.current.changeDraft("# Gate\n\nNext.\n"));
    expect(hook.result.current.state.saveState).toBe("dirty");
    hook.unmount();
  });

  it.each([409, 413, 422])("GET404 retries identical uncertain PUT and handles definitive %s", async status => {
    vi.mocked(putWorldPlayRunContentCommand).mockRejectedValueOnce(new LiveApiError("uncertain", 503))
      .mockRejectedValueOnce(new LiveApiError("definitive rejection", status));
    vi.mocked(getWorldPlayRunContentCommand).mockRejectedValue(new LiveApiError("not found yet", 404));
    vi.mocked(getWorldPlayRunContent).mockResolvedValue(content);
    const hook = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    act(() => hook.result.current.changeDraft("# Gate\n\nDraft.\n"));
    await act(async () => { await vi.advanceTimersByTimeAsync(651); });
    expect(hook.result.current.state.saveState).toBe("unknown");
    const original = vi.mocked(putWorldPlayRunContentCommand).mock.calls[0];
    await act(async () => hook.result.current.retryRecovery());
    expect(vi.mocked(putWorldPlayRunContentCommand).mock.calls[1]).toEqual(original);
    expect(hook.result.current.state.saveState).toBe(status === 409 ? "conflict" : status === 413 ? "rejected" : "invalid");
    expect(hook.result.current.state.draftMarkdown).toContain("Draft.");
    if (status === 409) {
      act(() => hook.result.current.changeDraft("# Gate\n\nGated.\n", ["diagnostic"]));
      expect(hook.result.current.state.saveState).toBe("conflict");
      act(() => hook.result.current.changeDraft("# Gate\n\nGated valid.\n"));
      await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
      expect(hook.result.current.state.saveState).toBe("conflict");
      expect(putWorldPlayRunContentCommand).toHaveBeenCalledTimes(2);
    }
    hook.unmount();
    vi.useRealTimers();
    const reopened = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    await waitFor(() => expect(reopened.result.current.state.saveState).toBe(status === 409 ? "conflict" : status === 413 ? "rejected" : "invalid"));
    expect(putWorldPlayRunContentCommand).toHaveBeenCalledTimes(2);
    reopened.unmount();
  });

  it("retains an unmounted A command across B and a returning A controller", async () => {
    let finishOld!: (value: PlayRunContentReceipt) => void;
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation(() => new Promise(resolve => { finishOld = resolve; }));
    const oldAccepted = vi.fn();
    const firstA = renderHook(() => usePlayRunContentController(content, oldAccepted, vi.fn()));
    act(() => firstA.result.current.changeDraft("# Gate\n\nPending A.\n"));
    await act(async () => { await vi.advanceTimersByTimeAsync(651); });
    const call = vi.mocked(putWorldPlayRunContentCommand).mock.calls[0];
    firstA.unmount();
    const b = renderHook(() => usePlayRunContentController({ ...content, world_id: "other-world" }, vi.fn(), vi.fn()));
    await act(async () => finishOld(await receiptFor(call[2], call[3])));
    expect(b.result.current.state.accepted.world_id).toBe("other-world");
    expect(oldAccepted).not.toHaveBeenCalled();
    b.unmount();
    vi.mocked(getWorldPlayRunContentCommand).mockImplementation(async () => receiptFor(call[2], call[3]));
    vi.mocked(getWorldPlayRunContent).mockRejectedValue(new Error("offline read"));
    vi.useRealTimers();
    const returningA = renderHook(() => usePlayRunContentController(content, vi.fn(), vi.fn()));
    await waitFor(() => expect(returningA.result.current.state.saveState).toBe("saved"));
    expect(returningA.result.current.state.accepted.markdown).toBe(call[3].markdown);
    expect(putWorldPlayRunContentCommand).toHaveBeenCalledOnce();
  });

});
