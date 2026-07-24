import { describe, expect, it } from "vitest";

import { baseCandidateDefinition } from "./editorFixtures";
import {
  createEditorStateFromOutput,
  getLocalFingerprint,
  getUiStatus,
  markValidationAssociated,
  redo,
  setIdentityName,
  undo,
} from "./statblockEditorState";

describe("statblockEditorState", () => {
  it("starts clean and unvalidated", () => {
    const state = createEditorStateFromOutput(baseCandidateDefinition());
    expect(getUiStatus(state)).toBe("clean_unvalidated");
    expect(state.validationEligibility).toBe("unvalidated");
    expect(getLocalFingerprint(state)).toBe(state.baselineFingerprint);
  });

  it("marks dirty after edits and clears validation eligibility", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const associated = markValidationAssociated(initial, "validated_with_warnings");
    expect(associated.validationEligibility).toBe("associated");

    const edited = setIdentityName(associated, "Edited Name");
    expect(edited.validationEligibility).toBe("unvalidated");
    expect(getUiStatus(edited)).toBe("dirty_unvalidated");
    expect(edited.stateRevision).toBeGreaterThan(initial.stateRevision);
  });

  it("supports undo and redo while clearing eligibility", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const associated = markValidationAssociated(initial, "validated_with_errors");
    const edited = setIdentityName(associated, "Edited Name");
    const undone = undo(edited);
    expect(undone.workingCopy.identity.name).toBe(initial.workingCopy.identity.name);
    expect(undone.validationEligibility).toBe("unvalidated");

    const redone = redo(undone);
    expect(redone.workingCopy.identity.name).toBe("Edited Name");
    expect(redone.validationEligibility).toBe("unvalidated");
  });

  it("keeps source output reference immutable", () => {
    const output = baseCandidateDefinition();
    const state = createEditorStateFromOutput(output);
    setIdentityName(state, "Changed");
    expect(output.identity.name).toBe("Ironhide Brute");
  });
});
