import { isWorkspaceDocumentLocalState, workspaceDocumentStorageKey, type WorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";

type RecoveryStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
export interface WorkspaceDraftRecoveryReview {
  documentId: string;
  fence: string;
  preservedMarkdown: string;
  editorText: string;
}
interface Checkpoint {
  schema: "dmb_workspace_draft_recovery_v1";
  original: WorkspaceDocumentLocalState;
  replacement: WorkspaceDocumentLocalState;
}
export const draftRecoveryKey = (id: string) => `${workspaceDocumentStorageKey(id)}.recovery.v1`;

/** Ignore timestamps only; all content, authority and base identity still participate. */
export function draftRecoveryIdentity(state: WorkspaceDocumentLocalState): string {
  const { created_at: _created, updated_at: _updated, last_local_save_at: _saved, ...identity } = state;
  return JSON.stringify(identity);
}
/** Detect independently changed storage; localStorage is not an atomic cross-tab CAS. */
export function assertPersistedDraft(storage: Pick<Storage, "getItem">, expected: WorkspaceDocumentLocalState): string {
  const raw = storage.getItem(workspaceDocumentStorageKey(expected.document_id));
  let stored: unknown;
  try { stored = raw == null ? null : JSON.parse(raw); } catch { stored = null; }
  if (!isWorkspaceDocumentLocalState(stored) || draftRecoveryIdentity(stored) !== draftRecoveryIdentity(expected)) {
    throw new Error("The stored draft changed in another tab or is unavailable. Your stored edits and recovery copy have been kept. Reopen the document before recovery.");
  }
  return raw!;
}
export function readDraftRecovery(storage: Pick<Storage, "getItem">, id: string): Checkpoint | null {
  const raw = storage.getItem(draftRecoveryKey(id));
  if (raw == null) return null;
  const parsed: unknown = JSON.parse(raw);
  if (typeof parsed !== "object" || parsed == null) throw new Error("Recovery copy is unreadable; it has been kept.");
  const value = parsed as Checkpoint;
  if (value.schema !== "dmb_workspace_draft_recovery_v1"
      || !isWorkspaceDocumentLocalState(value.original) || !isWorkspaceDocumentLocalState(value.replacement)
      || value.original.document_id !== id || value.replacement.document_id !== id
      || value.original.base_revision !== value.replacement.base_revision
      || value.original.base_content_sha256 !== value.replacement.base_content_sha256
      || !value.original.exported_markdown_authoritative || value.replacement.exported_markdown_authoritative) {
    throw new Error("Recovery copy does not match this document; it has been kept.");
  }
  return value;
}
export function writeVerifiedLocalState(storage: Pick<Storage, "getItem" | "setItem">, state: WorkspaceDocumentLocalState): void {
  const raw = JSON.stringify(state);
  const key = workspaceDocumentStorageKey(state.document_id);
  storage.setItem(key, raw);
  if (storage.getItem(key) !== raw) throw new Error("Browser storage did not verify the draft. The recovery copy is still available.");
}
export function preserveDraftRecovery(storage: RecoveryStorage, original: WorkspaceDocumentLocalState, replacement: WorkspaceDocumentLocalState): void {
  const key = draftRecoveryKey(original.document_id);
  if (storage.getItem(key) != null) throw new Error("A recovery copy already exists. Restore it before replacing this draft again.");
  const raw = JSON.stringify({ schema: "dmb_workspace_draft_recovery_v1", original, replacement } satisfies Checkpoint);
  storage.setItem(key, raw);
  if (storage.getItem(key) !== raw) throw new Error("Browser storage could not verify the recovery copy. Your draft has not been replaced.");
}
