import "../tiptap/pageComposer/apiPresentation";
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

  if ((receipt.page_presentation_sha256 ?? null) !== (snapshot.page_presentation_sha256 ?? null)) {
    return { ok: false, reason: "Saved presentation fingerprint does not match the commit receipt." };
  }
  const receiptFingerprint = receipt.file_fingerprint;
  if (receipt.writer_ok && (receiptFingerprint == null || receiptFingerprint === "")) {
    return {
      ok: false,
      reason: "Commit receipt is missing file_fingerprint after successful write.",
    };
  }
  if (receiptFingerprint != null && receiptFingerprint !== snapshot.file_fingerprint) {
    return {
      ok: false,
      reason: "Commit receipt file_fingerprint does not match snapshot file_fingerprint.",
    };
  }
  return { ok: true };
}
