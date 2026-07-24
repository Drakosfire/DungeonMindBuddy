import { describe, expect, it } from "vitest";

import { baseCandidateDefinition } from "./editorFixtures";
import {
  buildEditorDraft,
  clearEditorDraft,
  readEditorDraft,
  restoreEditorStateFromDraft,
  writeCandidateIdToLocation,
  writeEditorDraft,
  type DraftStorage,
} from "./statblockEditorDraftStore";
import {
  createEditorStateFromOutput,
  markValidationAssociated,
  setIdentityName,
} from "./statblockEditorState";

function memoryStorage(): DraftStorage & { store: Map<string, string> } {
  const store = new Map<string, string>();
  return {
    store,
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => {
      store.set(key, value);
    },
    removeItem: (key) => {
      store.delete(key);
    },
  };
}

describe("statblockEditorDraftStore", () => {
  it("persists and restores edits for the same source fingerprint", () => {
    const storage = memoryStorage();
    const fresh = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(fresh, "Edited Brute");
    const draft = buildEditorDraft({
      candidateId: "cand_dogfood05c",
      editor: edited,
      viewMode: "edit",
      previewValidation: null,
    });
    expect(writeEditorDraft(draft, storage)).toBe(true);

    const loaded = readEditorDraft("cand_dogfood05c", storage);
    const restored = restoreEditorStateFromDraft(fresh, loaded);
    expect(restored).not.toBeNull();
    expect(restored!.editor.workingCopy.identity.name).toBe("Edited Brute");
    expect(restored!.editor.stateRevision).toBe(edited.stateRevision);
    expect(restored!.editor.validationUiStatus).toBe("dirty_unvalidated");
  });

  it("restores associated validation receipt with the working copy", () => {
    const storage = memoryStorage();
    let state = createEditorStateFromOutput(baseCandidateDefinition());
    state = markValidationAssociated(state, "validated_with_errors");
    const draft = buildEditorDraft({
      candidateId: "cand_dogfood05c",
      editor: state,
      viewMode: "edit",
      previewValidation: {
        associatedRevision: state.stateRevision,
        definitionDigest: "sha256:abc",
        receipt: {
          status: "invalid",
          mode: "editor_preview",
          validator_version: "1",
          canonicalizer_version: "1",
          definition_digest: "sha256:abc",
          issues: [
            {
              code: "ARMOR_DEFAULT",
              severity: "error",
              field_path: "defenses.armor_classes",
              message: "Exactly one armor-class profile must be marked default.",
            },
          ],
        },
      },
    });
    writeEditorDraft(draft, storage);

    const restored = restoreEditorStateFromDraft(
      createEditorStateFromOutput(baseCandidateDefinition()),
      readEditorDraft("cand_dogfood05c", storage),
    );
    expect(restored?.previewValidation?.definitionDigest).toBe("sha256:abc");
    expect(restored?.editor.validatedRevision).toBe(0);
    expect(restored?.editor.validationUiStatus).toBe("validated_with_errors");
  });

  it("rejects drafts when the source fingerprint no longer matches", () => {
    const storage = memoryStorage();
    const original = createEditorStateFromOutput(baseCandidateDefinition());
    const edited = setIdentityName(original, "Edited");
    writeEditorDraft(
      buildEditorDraft({
        candidateId: "cand_dogfood05c",
        editor: edited,
        viewMode: "edit",
        previewValidation: null,
      }),
      storage,
    );

    const mutatedSource = structuredClone(baseCandidateDefinition());
    mutatedSource.identity.name = "Server changed source";
    const fresh = createEditorStateFromOutput(mutatedSource);
    expect(restoreEditorStateFromDraft(fresh, readEditorDraft("cand_dogfood05c", storage))).toBeNull();
  });

  it("clears draft keys", () => {
    const storage = memoryStorage();
    const state = createEditorStateFromOutput(baseCandidateDefinition());
    writeEditorDraft(
      buildEditorDraft({
        candidateId: "cand_x",
        editor: state,
        viewMode: "edit",
        previewValidation: null,
      }),
      storage,
    );
    clearEditorDraft("cand_x", storage);
    expect(readEditorDraft("cand_x", storage)).toBeNull();
  });

  it("writeCandidateIdToLocation updates the query string", () => {
    window.history.pushState({}, "", "/plan?foo=1");
    writeCandidateIdToLocation("cand_abc");
    expect(window.location.search).toContain("candidateId=cand_abc");
    expect(window.location.search).toContain("foo=1");
  });
});
