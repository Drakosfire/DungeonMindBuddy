import type { WorkspaceDocumentSnapshot } from "../api/types";
import { isWorkspaceDocumentLocalState, workspaceDocumentStorageKey, type WorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";

export interface WorkspaceConflictReview {
  documentId: string;
  fence: string;
  local: WorkspaceDocumentLocalState;
  saved: WorkspaceDocumentSnapshot;
}
export interface WorkspaceConflictRecovery {
  prepare: () => WorkspaceConflictReview;
  resolve: (review: WorkspaceConflictReview, choice: "local" | "saved") => Promise<void>;
  protectedCopies: string | null;
}
export const conflictCopiesKey = (id: string) => `${workspaceDocumentStorageKey(id)}.conflict-copies.v1`;

/** Append complete copies, including richer editor JSON; never replace an older backup. */
export function preserveConflictCopies(storage: Pick<Storage, "getItem" | "setItem">, review: WorkspaceConflictReview): void {
  const key = conflictCopiesKey(review.documentId);
  const old = storage.getItem(key);
  const copies = old === null ? { schema: "dmb_workspace_conflict_copies_v1", copies: [] as WorkspaceConflictReview[] } : JSON.parse(old);
  if (!copies || typeof copies !== "object" || copies.schema !== "dmb_workspace_conflict_copies_v1" || !Array.isArray(copies.copies)
    || copies.copies.some((copy: WorkspaceConflictReview) => !copy || typeof copy !== "object" || copy.documentId !== review.documentId
      || !isWorkspaceDocumentLocalState(copy.local) || copy.local.document_id !== review.documentId
      || copy.saved?.record?.document_id !== review.documentId || typeof copy.saved.markdown !== "string")) {
    throw new Error("Previous recovery copies could not be read. They were kept; no draft was replaced.");
  }
  const next = JSON.stringify({ ...copies, copies: [...copies.copies, { documentId:review.documentId, local:review.local, saved:review.saved }] });
  if (storage.getItem(key) !== old) throw new Error("Recovery copies changed in another tab. Reopen the comparison.");
  storage.setItem(key, next);
  if (storage.getItem(key) !== next) throw new Error("Both copies could not be verified in browser storage. No draft was replaced.");
}
