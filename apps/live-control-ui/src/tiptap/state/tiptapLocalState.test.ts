import { vi } from "vitest";

import {
  getTiptapRunbookDescriptor,
  tiptapRunbookStorageKey,
} from "../descriptors/tiptapRunbookDescriptors";
import {
  TIPTAP_WORKING_BOARD_KEY,
  buildInitialWorkingBoardState,
  clearTiptapWorkingBoardState,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
} from "./tiptapLocalState";

const northGateDescriptor = getTiptapRunbookDescriptor("north-gate-session-runbook");
const spikeDescriptor = getTiptapRunbookDescriptor("north-gate-callout-spike");

describe("Tiptap local working-board state", () => {
  it("builds descriptor-derived initial state for the session runbook", () => {
    const now = "2026-06-18T12:00:00.000Z";
    const state = buildInitialWorkingBoardState(northGateDescriptor, now);

    expect(TIPTAP_WORKING_BOARD_KEY).toBe(tiptapRunbookStorageKey(northGateDescriptor));
    expect(state).toMatchObject({
      schema_version: "dmb_tiptap_working_board_state_v1",
      document_id: "north-gate-session-runbook",
      title: "North Gate Session Runbook",
      campaign_id: "longmont-c2",
      session: 23,
      surface: "tiptap-callout-spike",
      dirty: false,
      created_at: now,
      updated_at: now,
      last_local_save_at: now,
    });
    expect(state.tiptap_json).toEqual(expect.objectContaining({ type: "doc" }));
    expect(state.exported_markdown).toContain("# C2S23 North Gate Session Runbook");
    expect(state.exported_markdown).toContain("## Table start checklist");
    expect(state.exported_markdown).toContain("## First player prompt");
    expect(state.exported_markdown).toContain("### Gate clock");
    expect(state.exported_markdown).toContain("## What to say when they stall");
    expect(state.exported_markdown).toContain("## Exit ramps into combat / council / chase");
  });

  it("builds descriptor-derived initial state for the callout spike", () => {
    const state = buildInitialWorkingBoardState(spikeDescriptor, "2026-06-18T12:00:00.000Z");

    expect(state).toMatchObject({
      document_id: "north-gate-callout-spike",
      title: "North Gate Callout Spike",
      campaign_id: "longmont-c2",
      session: 23,
    });
    expect(state.exported_markdown).toContain("# North Gate Callout Spike");
  });

  it("reads valid descriptor-keyed local state", () => {
    const state = buildInitialWorkingBoardState(northGateDescriptor, "2026-06-18T12:00:00.000Z");
    const storage = { getItem: vi.fn(() => JSON.stringify(state)) };

    expect(readTiptapWorkingBoardState(storage, northGateDescriptor)).toEqual(state);
    expect(storage.getItem).toHaveBeenCalledWith(tiptapRunbookStorageKey(northGateDescriptor));
  });

  it("re-derives exported Markdown from stored Tiptap JSON", () => {
    const state = {
      ...buildInitialWorkingBoardState(northGateDescriptor, "2026-06-18T12:00:00.000Z"),
      exported_markdown: "stale unsafe markdown",
    };

    const loaded = readTiptapWorkingBoardState({ getItem: () => JSON.stringify(state) }, northGateDescriptor);

    expect(loaded?.exported_markdown).toContain("# C2S23 North Gate Session Runbook");
    expect(loaded?.exported_markdown).not.toContain("stale unsafe markdown");
  });

  it("rejects malformed JSON", () => {
    expect(readTiptapWorkingBoardState({ getItem: () => "{bad" }, northGateDescriptor)).toBeNull();
  });

  it("rejects the wrong schema version", () => {
    const state = {
      ...buildInitialWorkingBoardState(northGateDescriptor, "2026-06-18T12:00:00.000Z"),
      schema_version: "obsolete",
    };

    expect(readTiptapWorkingBoardState({ getItem: () => JSON.stringify(state) }, northGateDescriptor)).toBeNull();
  });

  it("writes and reads two descriptors under isolated keys", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: vi.fn((key: string) => values.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => { values.set(key, value); }),
    };
    const sessionState = buildInitialWorkingBoardState(northGateDescriptor, "2026-06-18T12:00:00.000Z");
    const spikeState = buildInitialWorkingBoardState(spikeDescriptor, "2026-06-18T12:00:00.000Z");

    writeTiptapWorkingBoardState(storage, northGateDescriptor, sessionState);
    writeTiptapWorkingBoardState(storage, spikeDescriptor, spikeState);

    expect(storage.setItem).toHaveBeenCalledWith(tiptapRunbookStorageKey(northGateDescriptor), JSON.stringify(sessionState));
    expect(storage.setItem).toHaveBeenCalledWith(tiptapRunbookStorageKey(spikeDescriptor), JSON.stringify(spikeState));
    expect(tiptapRunbookStorageKey(northGateDescriptor)).not.toBe(tiptapRunbookStorageKey(spikeDescriptor));
    expect(readTiptapWorkingBoardState(storage, northGateDescriptor)?.document_id).toBe("north-gate-session-runbook");
    expect(readTiptapWorkingBoardState(storage, spikeDescriptor)?.document_id).toBe("north-gate-callout-spike");
  });

  it("clears state under the descriptor key", () => {
    const removeItem = vi.fn();

    clearTiptapWorkingBoardState({ removeItem }, northGateDescriptor);

    expect(removeItem).toHaveBeenCalledWith(tiptapRunbookStorageKey(northGateDescriptor));
  });
});
