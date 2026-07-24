/**
 * Browser-local editor draft for a loaded candidate.
 *
 * Survives tab close/reopen. Not a Server save / accept path (SBW07).
 * Bound to candidateId + source fingerprint so a changed/reloaded source
 * does not silently reapply stale edits.
 */
import type {
  StatblockDefinitionV1_Input,
  ValidationReceiptV1,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import {
  fingerprintDefinition,
  type StatblockEditorState,
  type ValidationAttempt,
  type ValidationUiStatus,
} from "./statblockEditorState";

export const EDITOR_DRAFT_SCHEMA = "dmb_statblock_editor_draft_v1" as const;
export const EDITOR_DRAFT_KEY_PREFIX = "dmb.statblock.editorDraft.v1:";
const MAX_DRAFT_BYTES = 1_500_000;

export type EditorDraftPreviewValidationV1 = {
  associatedRevision: number;
  receipt: ValidationReceiptV1;
  definitionDigest: string;
};

export type StatblockEditorDraftV1 = {
  schema: typeof EDITOR_DRAFT_SCHEMA;
  candidateId: string;
  /** Fingerprint of the working copy initialized from the source candidate. */
  sourceFingerprint: string;
  workingCopy: StatblockDefinitionV1_Input;
  undoStack: StatblockDefinitionV1_Input[];
  redoStack: StatblockDefinitionV1_Input[];
  stateRevision: number;
  validatedRevision: number | null;
  validationAttempt: ValidationAttempt;
  validationUiStatus: ValidationUiStatus;
  viewMode: "review" | "edit";
  previewValidation: EditorDraftPreviewValidationV1 | null;
  savedAt: string;
};

export type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function draftKey(candidateId: string): string {
  return `${EDITOR_DRAFT_KEY_PREFIX}${candidateId}`;
}

function defaultStorage(): DraftStorage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function writeCandidateIdToLocation(candidateId: string): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  const trimmed = candidateId.trim();
  if (trimmed) {
    url.searchParams.set("candidateId", trimmed);
  } else {
    url.searchParams.delete("candidateId");
  }
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

export function readEditorDraft(
  candidateId: string,
  storage: DraftStorage | null = defaultStorage(),
): StatblockEditorDraftV1 | null {
  if (!storage || !candidateId.trim()) return null;
  try {
    const raw = storage.getItem(draftKey(candidateId.trim()));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StatblockEditorDraftV1;
    if (parsed?.schema !== EDITOR_DRAFT_SCHEMA) return null;
    if (parsed.candidateId !== candidateId.trim()) return null;
    if (typeof parsed.sourceFingerprint !== "string") return null;
    if (!parsed.workingCopy || typeof parsed.workingCopy !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeEditorDraft(
  draft: StatblockEditorDraftV1,
  storage: DraftStorage | null = defaultStorage(),
): boolean {
  if (!storage) return false;
  try {
    const encoded = JSON.stringify(draft);
    if (encoded.length > MAX_DRAFT_BYTES) return false;
    storage.setItem(draftKey(draft.candidateId), encoded);
    return true;
  } catch {
    return false;
  }
}

export function clearEditorDraft(
  candidateId: string,
  storage: DraftStorage | null = defaultStorage(),
): void {
  if (!storage || !candidateId.trim()) return;
  try {
    storage.removeItem(draftKey(candidateId.trim()));
  } catch {
    // ignore quota / privacy mode
  }
}

export function buildEditorDraft(args: {
  candidateId: string;
  editor: StatblockEditorState;
  viewMode: "review" | "edit";
  previewValidation: {
    associatedRevision: number;
    receipt: ValidationReceiptV1;
    definitionDigest: string;
  } | null;
}): StatblockEditorDraftV1 {
  const attempt: ValidationAttempt =
    args.editor.validationAttempt === "validating" ? "none" : args.editor.validationAttempt;

  let previewValidation: EditorDraftPreviewValidationV1 | null = null;
  let validatedRevision = args.editor.validatedRevision;
  let validationUiStatus = args.editor.validationUiStatus;
  let validationAttempt = attempt;

  const preview = args.previewValidation;
  const receiptAssociated =
    preview != null &&
    validatedRevision != null &&
    preview.associatedRevision === validatedRevision &&
    args.editor.stateRevision === validatedRevision &&
    (validationUiStatus === "validated" ||
      validationUiStatus === "validated_with_warnings" ||
      validationUiStatus === "validated_with_errors");

  if (receiptAssociated && preview) {
    previewValidation = {
      associatedRevision: preview.associatedRevision,
      receipt: preview.receipt,
      definitionDigest: preview.definitionDigest,
    };
  } else {
    // Do not rehydrate a stale or in-flight receipt across tab restore.
    validatedRevision = null;
    previewValidation = null;
    if (validationAttempt === "unavailable") {
      validationUiStatus = "validation_unavailable";
    } else {
      validationAttempt = "none";
      const dirty =
        fingerprintDefinition(args.editor.workingCopy) !== args.editor.baselineFingerprint;
      validationUiStatus = dirty ? "dirty_unvalidated" : "clean_unvalidated";
    }
  }

  return {
    schema: EDITOR_DRAFT_SCHEMA,
    candidateId: args.candidateId,
    sourceFingerprint: args.editor.baselineFingerprint,
    workingCopy: args.editor.workingCopy,
    undoStack: args.editor.undoStack,
    redoStack: args.editor.redoStack,
    stateRevision: args.editor.stateRevision,
    validatedRevision,
    validationAttempt,
    validationUiStatus,
    viewMode: args.viewMode,
    previewValidation,
    savedAt: new Date().toISOString(),
  };
}

/**
 * Apply a stored draft onto a freshly initialized editor for the same source.
 * Returns null when the draft is missing or bound to a different source fingerprint.
 */
export function restoreEditorStateFromDraft(
  fresh: StatblockEditorState,
  draft: StatblockEditorDraftV1 | null,
): {
  editor: StatblockEditorState;
  viewMode: "review" | "edit";
  previewValidation: EditorDraftPreviewValidationV1 | null;
} | null {
  if (!draft) return null;
  if (draft.sourceFingerprint !== fresh.baselineFingerprint) return null;

  const editor: StatblockEditorState = {
    ...fresh,
    workingCopy: structuredClone(draft.workingCopy),
    undoStack: structuredClone(draft.undoStack),
    redoStack: structuredClone(draft.redoStack),
    stateRevision: draft.stateRevision,
    validatedRevision: draft.validatedRevision,
    validationAttempt: draft.validationAttempt === "validating" ? "none" : draft.validationAttempt,
    validationUiStatus:
      draft.validationAttempt === "validating" ? "dirty_unvalidated" : draft.validationUiStatus,
  };

  let previewValidation: EditorDraftPreviewValidationV1 | null = null;
  if (
    draft.previewValidation &&
    draft.validatedRevision != null &&
    draft.previewValidation.associatedRevision === draft.validatedRevision &&
    draft.stateRevision === draft.validatedRevision
  ) {
    previewValidation = draft.previewValidation;
  } else {
    editor.validatedRevision = null;
    if (editor.validationAttempt !== "unavailable") {
      editor.validationAttempt = "none";
      editor.validationUiStatus =
        fingerprintDefinition(editor.workingCopy) !== editor.baselineFingerprint
          ? "dirty_unvalidated"
          : "clean_unvalidated";
    }
  }

  return {
    editor,
    viewMode: draft.viewMode,
    previewValidation,
  };
}
