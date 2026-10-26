import { isWorkspaceDocumentLocalState, workspaceDocumentStorageKey, type WorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";

type RecoveryStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
export interface WorkspaceDraftRecoveryReview {
  documentId: string;
  fence: string;
  preservedMarkdown: string;
  editorText: string;
  canKeepCurrent?: boolean;
  canNormalizeCurrent?: boolean;
  removedSpacers?: number;
  canUsePreserved?: boolean;
  currentPageIssue?: string | null;
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

export interface DraftRecoveryCopy {
  id: string;
  label: string;
  state: WorkspaceDocumentLocalState;
}
interface RecoveryJournal {
  schema: "dmb_workspace_draft_recovery_v2";
  documentId: string;
  copies: DraftRecoveryCopy[];
}
export interface WorkspaceDraftRestoreReview {
  documentId: string;
  fence: string;
  copies: DraftRecoveryCopy[];
}
export const draftRecoveryJournalKey = (id: string) => `${workspaceDocumentStorageKey(id)}.recovery.v2`;

/** V1 is retained evidence, never an execution fallback for new recoveries. */
export function readDraftRecoveryCopies(storage: Pick<Storage, "getItem">, id: string): DraftRecoveryCopy[] {
  const raw = storage.getItem(draftRecoveryJournalKey(id));
  if (raw == null) return [];
  let value: RecoveryJournal;
  try { value = JSON.parse(raw); } catch { throw new Error("Recovery history is unreadable. Its bytes were kept."); }
  if (!value || value.schema !== "dmb_workspace_draft_recovery_v2" || value.documentId !== id || !Array.isArray(value.copies)
      || value.copies.some(copy => !copy || typeof copy.id !== "string" || !copy.id || typeof copy.label !== "string" || !copy.label
        || !isWorkspaceDocumentLocalState(copy.state) || copy.state.document_id !== id)
      || new Set(value.copies.map(copy => copy.id)).size !== value.copies.length) {
    throw new Error("Recovery history does not match this document. Its bytes were kept.");
  }
  const owner=value.copies[0]?.state;
  if(owner && value.copies.some(copy=>copy.state.kind!==owner.kind || copy.state.surface!==owner.surface || copy.state.campaign_id!==owner.campaign_id))
    throw new Error("Recovery history has a different document owner. All copies were kept.");
  return value.copies;
}

/** Caller holds the document's Web Lock. No existing copy or V1 bytes are removed. */
export function appendDraftRecoveryCopies(storage: RecoveryStorage, id: string,
  snapshots: Array<{label: string; state: WorkspaceDocumentLocalState}>): DraftRecoveryCopy[] {
  const key = draftRecoveryJournalKey(id), before = storage.getItem(key);
  const copies = readDraftRecoveryCopies(storage, id);
  const old = readDraftRecovery(storage, id);
  const candidates = [
    ...(old ? [{label: "Earlier protected draft", state: old.original}, {label: "Earlier recovered draft", state: old.replacement}] : []),
    ...snapshots,
  ];
  for (const {label, state} of candidates) {
    if (!isWorkspaceDocumentLocalState(state) || state.document_id !== id) throw new Error("Recovery snapshot belongs to another document. Nothing was replaced.");
    if (copies.some(copy => copy.state.kind !== state.kind || copy.state.campaign_id !== state.campaign_id || copy.state.surface !== state.surface)) {
      throw new Error("Recovery history has a different document owner. All copies were kept.");
    }
    if (!copies.some(copy => draftRecoveryIdentity(copy.state) === draftRecoveryIdentity(state))) {
      const entry = {id: crypto.randomUUID(), label, state: JSON.parse(JSON.stringify(state)) as WorkspaceDocumentLocalState};
      if (copies.some(copy => copy.id === entry.id)) throw new Error("Recovery snapshot identity collided. Nothing was replaced.");
      copies.push(entry);
    }
  }
  if (storage.getItem(key) !== before) throw new Error("Recovery history changed in another tab. All copies were kept.");
  const raw = JSON.stringify({schema: "dmb_workspace_draft_recovery_v2", documentId: id, copies} satisfies RecoveryJournal);
  if (raw !== before) storage.setItem(key, raw);
  if (storage.getItem(key) !== raw) throw new Error("Browser storage could not verify recovery history. Your draft was not replaced.");
  return copies;
}
