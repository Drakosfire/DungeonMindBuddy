import { vi } from "vitest";

import {
  TIPTAP_WORKING_BOARD_KEY,
  buildInitialWorkingBoardState,
  clearTiptapWorkingBoardState,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
} from "./tiptapLocalState";

describe("Tiptap local working-board state", () => {
  it("builds the initial state", () => {
    const now = "2026-06-18T12:00:00.000Z";
    const state = buildInitialWorkingBoardState(now);

    expect(state).toMatchObject({
      schema_version: "dmb_tiptap_working_board_state_v1",
      document_id: "north-gate-callout-spike",
      title: "North-gate callout spike",
      campaign_id: "longmont-c2",
      session: 23,
      surface: "tiptap-callout-spike",
      dirty: false,
      created_at: now,
      updated_at: now,
      last_local_save_at: now,
    });
    expect(state.tiptap_json).toEqual(expect.objectContaining({ type: "doc" }));
    expect(state.exported_markdown).toContain("## North-gate opening spike");
  });

  it("reads valid local state", () => {
    const state = buildInitialWorkingBoardState("2026-06-18T12:00:00.000Z");
    const storage = { getItem: vi.fn(() => JSON.stringify(state)) };

    expect(readTiptapWorkingBoardState(storage)).toEqual(state);
    expect(storage.getItem).toHaveBeenCalledWith(TIPTAP_WORKING_BOARD_KEY);
  });

  it("rejects malformed JSON", () => {
    expect(readTiptapWorkingBoardState({ getItem: () => "{bad" })).toBeNull();
  });

  it("rejects the wrong schema version", () => {
    const state = {
      ...buildInitialWorkingBoardState("2026-06-18T12:00:00.000Z"),
      schema_version: "obsolete",
    };

    expect(readTiptapWorkingBoardState({ getItem: () => JSON.stringify(state) })).toBeNull();
  });

  it("writes state under the stable key", () => {
    const setItem = vi.fn();
    const state = buildInitialWorkingBoardState("2026-06-18T12:00:00.000Z");

    writeTiptapWorkingBoardState({ setItem }, state);

    expect(setItem).toHaveBeenCalledWith(TIPTAP_WORKING_BOARD_KEY, JSON.stringify(state));
  });

  it("clears state under the stable key", () => {
    const removeItem = vi.fn();

    clearTiptapWorkingBoardState({ removeItem });

    expect(removeItem).toHaveBeenCalledWith(TIPTAP_WORKING_BOARD_KEY);
  });
});
