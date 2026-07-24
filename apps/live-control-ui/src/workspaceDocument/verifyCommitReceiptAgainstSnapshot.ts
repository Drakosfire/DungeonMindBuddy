import type {
  TiptapMarkdownWriteCommitResponse,
  WorkspaceDocumentSnapshot,
} from "../api/types";

export type CommitReceiptVerificationResult =
  | { ok: true }
  | { ok: false; reason: string };

export function verifyCommitReceiptAgainstSnapshot(
  receipt: TiptapMarkdownWriteCommitResponse,
  snapshot: WorkspaceDocumentSnapshot,
): CommitReceiptVerificationResult {
  if (receipt.document_id !== snapshot.record.document_id) {
    return {
      ok: false,
      reason: "Commit receipt document_id does not match snapshot record document_id.",
    };
  }
  if (receipt.committed_revision !== snapshot.loaded_revision) {
    return {
      ok: false,
      reason: `Commit receipt revision ${receipt.committed_revision} does not match snapshot loaded_revision ${snapshot.loaded_revision}.`,
    };
  }
  if (receipt.normalized_content_sha256 !== snapshot.content_sha256) {
    return {
      ok: false,
      reason: "Commit receipt normalized_content_sha256 does not match snapshot content_sha256.",
    };
  }
  const receiptFingerprint = receipt.file_fingerprint;
  if (receiptFingerprint != null && receiptFingerprint !== snapshot.file_fingerprint) {
    return {
      ok: false,
      reason: "Commit receipt file_fingerprint does not match snapshot file_fingerprint.",
    };
  }
  return { ok: true };
}
