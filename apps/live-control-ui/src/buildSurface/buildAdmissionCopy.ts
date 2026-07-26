import type {
  DocumentAdmissionFailureCode,
  DocumentCommandResult,
} from "../markdownCanvas/markdownCanvasTypes";

/** Map neutral canvas admission codes to Build extraction operator copy. */
export function translateBuildExtractionAdmission(
  code: DocumentAdmissionFailureCode,
  detail?: string,
): string {
  switch (code) {
    case "document_missing":
      return "Open and save this Build source before extraction.";
    case "document_identity_mismatch":
      return "Snapshot does not belong to the selected document.";
    case "authority_mismatch":
      return "Local draft does not belong to this Build document.";
    case "document_dirty":
      return "Save and commit local changes before extraction.";
    case "document_not_committed":
      return "Source must be committed before extraction.";
    case "revision_mismatch": {
      if (detail?.includes("!=")) {
        const [localRev, snapshotRev] = detail.split("!=");
        return `Local base revision ${localRev} does not match snapshot revision ${snapshotRev}.`;
      }
      return "Local base revision does not match snapshot revision.";
    }
    case "digest_mismatch":
      return "Local base content hash does not match the authoritative snapshot digest.";
    case "document_not_ready":
      return "Document is not ready for extraction.";
    case "document_not_loaded":
      return "Document is not loaded.";
    case "document_not_editable":
      return "Document is not editable in the current phase.";
    default:
      return "Document is not ready for extraction.";
  }
}

export function translateBuildDocumentCommandFailure(
  result: Extract<DocumentCommandResult<unknown>, { ok: false }>,
): string {
  if (result.code === "admission_failed" && result.admissionCode) {
    return translateBuildExtractionAdmission(result.admissionCode, result.admissionDetail);
  }
  if (result.code === "conflict") {
    return "Extraction conflicts with an active document command.";
  }
  return result.reason;
}
