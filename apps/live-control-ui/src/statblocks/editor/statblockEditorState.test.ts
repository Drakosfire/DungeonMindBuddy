import { describe, expect, it } from "vitest";

import { baseCandidateDefinition } from "./editorFixtures";
import {
  beginValidationAttempt,
  createEditorStateFromOutput,
  getLocalFingerprint,
  getUiStatus,
  markValidationAssociated,
  markValidationUnavailable,
  redo,
  setIdentityName,
  setRuleElementRulesText,
  undo,
} from "./statblockEditorState";

describe("statblockEditorState", () => {
  it("starts clean and unvalidated", () => {
    const state = createEditorStateFromOutput(baseCandidateDefinition());
    expect(getUiStatus(state)).toBe("clean_unvalidated");
    expect(state.validatedRevision).toBeNull();
    expect(state.validationAttempt).toBe("none");
    expect(getLocalFingerprint(state)).toBe(state.baselineFingerprint);
    expect(state.stateRevision).toBe(0);
  });

  it("marks dirty after edits and clears validation association", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const associated = markValidationAssociated(initial, "validated_with_warnings");
    expect(associated.validatedRevision).toBe(0);

    const edited = setIdentityName(associated, "Edited Name");
    expect(edited.validatedRevision).toBeNull();
    expect(edited.validationAttempt).toBe("none");
    expect(getUiStatus(edited)).toBe("dirty_unvalidated");
    expect(edited.stateRevision).toBeGreaterThan(initial.stateRevision);
  });

  it("keeps validated status while dirty vs baseline when revision matches receipt", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "Edited Name");
    expect(getLocalFingerprint(edited)).not.toBe(edited.baselineFingerprint);

    const associated = markValidationAssociated(edited, "validated_with_warnings");
    expect(associated.validatedRevision).toBe(edited.stateRevision);
    expect(getUiStatus(associated)).toBe("validated_with_warnings");
    expect(getLocalFingerprint(associated)).not.toBe(associated.baselineFingerprint);
  });

  it("associates clean valid receipt with edited revision and clears on subsequent edit", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "Clean Valid");
    expect(getUiStatus(edited)).toBe("dirty_unvalidated");

    const associated = markValidationAssociated(edited, "validated");
    expect(associated.validatedRevision).toBe(edited.stateRevision);
    expect(associated.validationAttempt).toBe("none");
    expect(getUiStatus(associated)).toBe("validated");
    expect(getLocalFingerprint(associated)).not.toBe(associated.baselineFingerprint);

    const editedAgain = setIdentityName(associated, "After Valid");
    expect(editedAgain.validatedRevision).toBeNull();
    expect(editedAgain.validationAttempt).toBe("none");
    expect(getUiStatus(editedAgain)).toBe("dirty_unvalidated");
  });

  it("invalidates association on subsequent edit", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "Once");
    const associated = markValidationAssociated(edited, "validated_with_errors");
    const editedAgain = setIdentityName(associated, "Twice");
    expect(editedAgain.validatedRevision).toBeNull();
    expect(getUiStatus(editedAgain)).toBe("dirty_unvalidated");
  });

  it("treats validating as a pending attempt with no receipt association", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "Pending");
    const pending = beginValidationAttempt(edited);
    expect(pending.validatedRevision).toBeNull();
    expect(pending.validationAttempt).toBe("validating");
    expect(getUiStatus(pending)).toBe("validating");
    expect(pending.workingCopy.identity.name).toBe("Pending");
  });

  it("treats validation_unavailable as no receipt association while retaining working copy", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "Kept");
    const unavailable = markValidationUnavailable(edited);
    expect(unavailable.validatedRevision).toBeNull();
    expect(unavailable.validationAttempt).toBe("unavailable");
    expect(getUiStatus(unavailable)).toBe("validation_unavailable");
    expect(unavailable.workingCopy.identity.name).toBe("Kept");
  });

  it("clears pending validating attempt on edit, undo, and redo", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "A");
    const pending = beginValidationAttempt(edited);
    expect(getUiStatus(pending)).toBe("validating");

    const editedAgain = setIdentityName(pending, "B");
    expect(editedAgain.validationAttempt).toBe("none");
    expect(editedAgain.validatedRevision).toBeNull();
    expect(getUiStatus(editedAgain)).toBe("dirty_unvalidated");

    const pending2 = beginValidationAttempt(editedAgain);
    const undone = undo(pending2);
    expect(undone.validationAttempt).toBe("none");
    expect(undone.validatedRevision).toBeNull();

    const pending3 = beginValidationAttempt(undone);
    const redone = redo(pending3);
    expect(redone.validationAttempt).toBe("none");
    expect(redone.validatedRevision).toBeNull();
  });

  it("clears unavailable attempt on edit", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const unavailable = markValidationUnavailable(setIdentityName(initial, "X"));
    const edited = setIdentityName(unavailable, "Y");
    expect(edited.validationAttempt).toBe("none");
    expect(getUiStatus(edited)).toBe("dirty_unvalidated");
  });

  it("supports undo and redo while clearing association", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const associated = markValidationAssociated(initial, "validated_with_errors");
    const edited = setIdentityName(associated, "Edited Name");
    const undone = undo(edited);
    expect(undone.workingCopy.identity.name).toBe(initial.workingCopy.identity.name);
    expect(undone.validatedRevision).toBeNull();

    const redone = redo(undone);
    expect(redone.workingCopy.identity.name).toBe("Edited Name");
    expect(redone.validatedRevision).toBeNull();
  });

  it("does not resurrect validation receipt when returning to baseline fingerprint", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const originalName = initial.workingCopy.identity.name;
    const edited = setIdentityName(initial, "Temporary");
    const associated = markValidationAssociated(edited, "validated_with_warnings");
    expect(getUiStatus(associated)).toBe("validated_with_warnings");

    const restored = setIdentityName(associated, originalName);
    expect(getLocalFingerprint(restored)).toBe(restored.baselineFingerprint);
    expect(restored.validatedRevision).toBeNull();
    expect(getUiStatus(restored)).toBe("clean_unvalidated");
  });

  it("does not change stateRevision when associating validation", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "X");
    const revisionBefore = edited.stateRevision;
    const associated = markValidationAssociated(edited, "validated_with_warnings");
    expect(associated.stateRevision).toBe(revisionBefore);
  });

  it("increments stateRevision only when working copy changes", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const associated = markValidationAssociated(initial, "validated_with_warnings");
    expect(associated.stateRevision).toBe(initial.stateRevision);

    const edited = setIdentityName(associated, "Changed");
    expect(edited.stateRevision).toBe(initial.stateRevision + 1);

    const noopUndo = undo(createEditorStateFromOutput(baseCandidateDefinition()));
    expect(noopUndo.stateRevision).toBe(0);
  });

  it("preserves untouched definition fields on dedicated edits", () => {
    const state = createEditorStateFromOutput(baseCandidateDefinition());
    const elementKey = state.workingCopy.rule_elements[0].key;
    const beforeMechanic = structuredClone(state.workingCopy.rule_elements[0].mechanic);

    const renamed = setIdentityName(state, "New Name");
    expect(renamed.workingCopy.movement).toEqual(state.workingCopy.movement);
    expect(renamed.workingCopy.rule_elements[0].mechanic).toEqual(beforeMechanic);

    const rulesEdited = setRuleElementRulesText(renamed, elementKey, "Updated rules text.");
    expect(rulesEdited.workingCopy.rule_elements[0].mechanic).toEqual(beforeMechanic);
    expect(rulesEdited.workingCopy.identity.name).toBe("New Name");
  });

  it("keeps source output reference immutable", () => {
    const output = baseCandidateDefinition();
    const state = createEditorStateFromOutput(output);
    setIdentityName(state, "Changed");
    expect(output.identity.name).toBe("Ironhide Brute");
  });
});
