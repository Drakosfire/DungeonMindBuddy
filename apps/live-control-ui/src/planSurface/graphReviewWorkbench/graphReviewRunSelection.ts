/** Exact Graph Review handoff identity — never uses latest-run inference. */

export interface GraphReviewExactRunHandoff {
  extractionRunId: string;
  sourceArtifactId: string | null;
  documentId: string | null;
  revision: number | null;
}

export function parseGraphReviewRunHandoff(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): GraphReviewExactRunHandoff | null {
  const params = new URLSearchParams(search ?? "");
  const extractionRunId = params.get("extractionRunId")?.trim() || "";
  if (!extractionRunId) return null;
  const revisionRaw = params.get("revision");
  const revision = revisionRaw != null && revisionRaw.trim() !== ""
    ? Number(revisionRaw)
    : null;
  return {
    extractionRunId,
    sourceArtifactId: params.get("sourceArtifactId")?.trim() || null,
    documentId: params.get("documentId")?.trim() || null,
    revision: Number.isFinite(revision) ? revision : null,
  };
}

export function assertExactRunHandoff(handoff: GraphReviewExactRunHandoff): string[] {
  const errors: string[] = [];
  if (!handoff.extractionRunId) errors.push("extractionRunId is required");
  if (handoff.extractionRunId.toLowerCase().includes("latest")) {
    errors.push("latest-run handoff is forbidden");
  }
  return errors;
}
