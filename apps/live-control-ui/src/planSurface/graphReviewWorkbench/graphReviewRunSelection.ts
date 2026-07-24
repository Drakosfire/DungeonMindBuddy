/** Exact Graph Review handoff identity — never uses latest-run inference. */

/** Workspace lineage confirmed by the server, never read from the URL. */
export interface GraphReviewExactRunLineage {
  documentId: string;
  revision: number;
}

export interface GraphReviewExactRunHandoff {
  extractionRunId: string;
  sourceArtifactId: string | null;
  documentId: string | null;
  revision: number | null;
  errors: string[];
}

const IDENTITY_PARAMS = ["extractionRunId", "sourceArtifactId", "documentId", "revision"] as const;

function singleValue(
  params: URLSearchParams,
  name: string,
  errors: string[],
): string | null {
  const values = params.getAll(name);
  if (values.length === 0) return null;
  if (values.length > 1) {
    errors.push(`${name} must appear at most once`);
    return null;
  }
  const text = values[0].trim();
  if (!text) {
    errors.push(`${name} is present but empty`);
    return null;
  }
  if (text.toLowerCase().includes("latest")) {
    errors.push(`${name} must be an exact identifier, not "latest"`);
    return null;
  }
  return text;
}

export function parseGraphReviewRunHandoff(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): GraphReviewExactRunHandoff | null {
  const params = new URLSearchParams(search ?? "");
  if (!IDENTITY_PARAMS.some((name) => params.has(name))) return null;

  const errors: string[] = [];
  const extractionRunId = singleValue(params, "extractionRunId", errors);
  const sourceArtifactId = singleValue(params, "sourceArtifactId", errors);
  const documentId = singleValue(params, "documentId", errors);
  const revisionRaw = singleValue(params, "revision", errors);

  let revision: number | null = null;
  if (revisionRaw !== null) {
    const parsed = Number(revisionRaw);
    if (!Number.isInteger(parsed) || parsed < 1) {
      errors.push("revision must be a positive integer");
    } else {
      revision = parsed;
    }
  }
  if (!extractionRunId && !errors.some((item) => item.startsWith("extractionRunId"))) {
    errors.push("extractionRunId is required");
  }

  return {
    extractionRunId: extractionRunId ?? "",
    sourceArtifactId,
    documentId,
    revision,
    errors,
  };
}

export function assertExactRunHandoff(handoff: GraphReviewExactRunHandoff): string[] {
  const errors = [...handoff.errors];
  if (!handoff.extractionRunId && !errors.length) {
    errors.push("extractionRunId is required");
  }
  // A claimed workspace lineage is only meaningful as a complete pair; a lone
  // document or revision cannot be checked against the server's lineage.
  if ((handoff.documentId === null) !== (handoff.revision === null)) {
    errors.push("documentId and revision must be supplied together");
  }
  return errors;
}
