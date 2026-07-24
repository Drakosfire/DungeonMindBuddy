import { describe, expect, it } from "vitest";

import { baseCandidateDefinition } from "./editorFixtures";
import {
  createEditorStateFromOutput,
  getLocalFingerprint,
  getUiStatus,
  markValidationAssociated,
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
    expect(getLocalFingerprint(state)).toBe(state.baselineFingerprint);
    expect(state.stateRevision).toBe(0);
  });

  it("marks dirty after edits and clears validation association", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const associated = markValidationAssociated(initial, "validated_with_warnings");
    expect(associated.validatedRevision).toBe(0);

    const edited = setIdentityName(associated, "Edited Name");
    expect(edited.validatedRevision).toBeNull();
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

  it("invalidates association on subsequent edit", () => {
    const initial = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(initial, "Once");
    const associated = markValidationAssociated(edited, "validated_with_errors");
    const editedAgain = setIdentityName(associated, "Twice");
    expect(editedAgain.validatedRevision).toBeNull();
    expect(getUiStatus(editedAgain)).toBe("dirty_unvalidated");
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
