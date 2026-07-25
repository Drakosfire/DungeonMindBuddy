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

  it("keeps committed truth when verification fails without post-receipt edits", () => {
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
      dirty: false,
    });
    expect(state.phase).toBe("committed_verification_pending");
    expect(state.verificationStatus).toBe("failed");
    expect(state.error).toContain("snapshot unavailable");
    expect(statusLabelForPhase({
      phase: state.phase,
      contentStatus: "committed",
      error: state.error,
      verificationStatus: state.verificationStatus,
    })).toContain("Committed");
  });

  it("preserves ready_dirty and unsaved status when verification fails after edits", () => {
    let state = initialAuthoringMachineState();
    state = reduceAuthoringMachine(state, { type: "OPEN_READY", dirty: false });
    state = reduceAuthoringMachine(state, { type: "VERIFICATION_STARTED" });
    state = reduceAuthoringMachine(state, { type: "EDIT" });
    expect(state.phase).toBe("ready_dirty");
    expect(state.verificationStatus).toBe("pending");
    state = reduceAuthoringMachine(state, {
      type: "VERIFICATION_FAILED",
      message: "snapshot unavailable",
      dirty: true,
    });
    expect(state.phase).toBe("ready_dirty");
    expect(state.verificationStatus).toBe("failed");
    expect(statusLabelForPhase({
      phase: state.phase,
      contentStatus: "committed",
      error: state.error,
      verificationStatus: state.verificationStatus,
    })).toMatch(/Unsaved local changes/);
  });

  it("surfaces save failures without collapsing to load_error", () => {
    let state = initialAuthoringMachineState();
    state = reduceAuthoringMachine(state, { type: "OPEN_READY", dirty: true });
    state = reduceAuthoringMachine(state, { type: "SAVE_FAILED", message: "prepare failed" });
    expect(state.phase).toBe("save_error");
    expect(state.error).toBe("prepare failed");
  });

  it("enters conflict when post-commit verification mismatches receipt", () => {
    let state = initialAuthoringMachineState();
    state = reduceAuthoringMachine(state, { type: "OPEN_READY", dirty: false });
    state = reduceAuthoringMachine(state, { type: "COMMIT_SUCCEEDED" });
    state = reduceAuthoringMachine(state, { type: "VERIFICATION_STARTED" });
    state = reduceAuthoringMachine(state, {
      type: "VERIFICATION_MISMATCH",
      reason: "Commit receipt revision 2 does not match snapshot loaded_revision 3.",
    });
    expect(state.phase).toBe("conflict");
    expect(state.conflictReason).toContain("revision 2");
    expect(state.error).toBeNull();
  });

  it("allows edit during committed_verification_pending to return to ready_dirty", () => {
    let state = initialAuthoringMachineState();
    state = reduceAuthoringMachine(state, { type: "OPEN_READY", dirty: false });
    state = reduceAuthoringMachine(state, { type: "VERIFICATION_STARTED" });
    state = reduceAuthoringMachine(state, { type: "EDIT" });
    expect(state.phase).toBe("ready_dirty");
    expect(state.verificationStatus).toBe("pending");
  });
});
