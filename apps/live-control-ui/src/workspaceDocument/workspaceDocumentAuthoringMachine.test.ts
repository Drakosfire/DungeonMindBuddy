import { describe, expect, it } from "vitest";

import {
  initialAuthoringMachineState,
  reduceAuthoringMachine,
  statusLabelForPhase,
} from "./workspaceDocumentAuthoringMachine";

describe("workspaceDocumentAuthoringMachine", () => {
  it("labels clean drafts as Draft not Committed", () => {
    expect(statusLabelForPhase({
      phase: "ready_clean",
      contentStatus: "draft",
    })).toBe("Draft");
    expect(statusLabelForPhase({
      phase: "ready_clean",
      contentStatus: "committed",
    })).toBe("Committed");
  });

  it("keeps committed truth when verification fails", () => {
    let state = initialAuthoringMachineState();
    state = reduceAuthoringMachine(state, { type: "OPEN_STARTED" });
    state = reduceAuthoringMachine(state, { type: "OPEN_READY", dirty: true });
    state = reduceAuthoringMachine(state, { type: "PREPARE_STARTED" });
    state = reduceAuthoringMachine(state, { type: "COMMIT_STARTED" });
    state = reduceAuthoringMachine(state, { type: "COMMIT_SUCCEEDED" });
    state = reduceAuthoringMachine(state, { type: "VERIFICATION_STARTED" });
    state = reduceAuthoringMachine(state, {
      type: "VERIFICATION_FAILED",
      message: "snapshot unavailable",
    });
    expect(state.phase).toBe("committed_verification_pending");
    expect(state.error).toContain("snapshot unavailable");
    expect(statusLabelForPhase({
      phase: state.phase,
      contentStatus: "committed",
      error: state.error,
    })).toContain("Committed");
  });

  it("surfaces save failures without collapsing to load_error", () => {
    let state = initialAuthoringMachineState();
    state = reduceAuthoringMachine(state, { type: "OPEN_READY", dirty: true });
    state = reduceAuthoringMachine(state, { type: "SAVE_FAILED", message: "prepare failed" });
    expect(state.phase).toBe("save_error");
    expect(state.error).toBe("prepare failed");
  });
});
