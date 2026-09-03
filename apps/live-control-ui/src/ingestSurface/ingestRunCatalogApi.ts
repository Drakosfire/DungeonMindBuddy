/**
 * Dedicated Ingest catalog client.
 *
 * Lives outside shared liveApi so SI-5B does not collide with PR #674.
 */

import type { ExtractionRunRecord } from "../api/types";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";

export const EXTRACTION_RUN_CATALOG_SCHEMA = "dmb_extraction_run_catalog_v1" as const;

export const INGEST_RUN_CATALOG_UNAVAILABLE = "ingest_run_catalog_unavailable";
export const INGEST_RUN_CATALOG_SCHEMA_UNAVAILABLE = "ingest_run_catalog_schema_unavailable";
export const INGEST_RUN_CATALOG_INTEGRITY_ERROR = "ingest_run_catalog_integrity_error";
export const INGEST_RUN_CATALOG_ERROR = "ingest_run_catalog_error";

export interface ExtractionRunCatalogResponse {
  schema_version: typeof EXTRACTION_RUN_CATALOG_SCHEMA;
  runs: ExtractionRunRecord[];
}

export class IngestRunCatalogApiError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "IngestRunCatalogApiError";
    this.status = status;
    this.code = code;
  }
}

function parseJsonBody<T>(text: string, status: number): T {
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new IngestRunCatalogApiError(
      `API response is not valid JSON (HTTP ${status}).`,
      status,
      INGEST_RUN_CATALOG_INTEGRITY_ERROR,
    );
  }
}

function parseErrorCode(body: unknown): { message: string; code: string | null } {
  if (body && typeof body === "object") {
    const record = body as {
      detail?: unknown;
      message?: unknown;
      code?: unknown;
    };
    const detail = record.detail;
    if (detail && typeof detail === "object") {
      const detailObj = detail as { code?: unknown; message?: unknown };
      const message =
        typeof detailObj.message === "string" && detailObj.message.trim()
          ? detailObj.message
          : "Ingest run catalog request failed.";
      const code = typeof detailObj.code === "string" ? detailObj.code : null;
      return { message, code };
    }
    if (typeof detail === "string" && detail.trim()) {
      return { message: detail, code: typeof record.code === "string" ? record.code : null };
    }
    if (typeof record.message === "string" && record.message.trim()) {
      return {
        message: record.message,
        code: typeof record.code === "string" ? record.code : null,
      };
    }
  }
  return { message: "Ingest run catalog request failed.", code: null };
}

function assertCatalog(body: unknown): ExtractionRunCatalogResponse {
  if (!body || typeof body !== "object") {
    throw new IngestRunCatalogApiError(
      "Ingest run catalog response is not an object.",
      200,
      INGEST_RUN_CATALOG_INTEGRITY_ERROR,
    );
  }
  const record = body as { schema_version?: unknown; runs?: unknown };
  if (record.schema_version !== EXTRACTION_RUN_CATALOG_SCHEMA) {
    throw new IngestRunCatalogApiError(
      "Ingest run catalog schema_version is not dmb_extraction_run_catalog_v1.",
      200,
      INGEST_RUN_CATALOG_INTEGRITY_ERROR,
    );
  }
  if (!Array.isArray(record.runs)) {
    throw new IngestRunCatalogApiError(
      "Ingest run catalog runs must be an array.",
      200,
      INGEST_RUN_CATALOG_INTEGRITY_ERROR,
    );
  }
  const seen = new Set<string>();
  const runs: ExtractionRunRecord[] = [];
  for (const entry of record.runs) {
    if (!entry || typeof entry !== "object") {
      throw new IngestRunCatalogApiError(
        "Ingest run catalog contains a non-object run.",
        200,
        INGEST_RUN_CATALOG_INTEGRITY_ERROR,
      );
    }
    const runId = (entry as { run_id?: unknown }).run_id;
    if (typeof runId !== "string" || !runId.trim()) {
      throw new IngestRunCatalogApiError(
        "Ingest run catalog contains a run without an exact run_id.",
        200,
        INGEST_RUN_CATALOG_INTEGRITY_ERROR,
      );
    }
    if (seen.has(runId)) {
      throw new IngestRunCatalogApiError(
        `Ingest run catalog contains duplicate run_id: ${runId}`,
        200,
        INGEST_RUN_CATALOG_INTEGRITY_ERROR,
      );
    }
    seen.add(runId);
    runs.push(entry as ExtractionRunRecord);
  }
  return {
    schema_version: EXTRACTION_RUN_CATALOG_SCHEMA,
    runs,
  };
}

export async function getExtractionRunCatalog(): Promise<ExtractionRunCatalogResponse> {
  const response = await fetch(`${baseUrl}/api/live/graph-preview/extraction-runs`, {
    headers: { "Content-Type": "application/json" },
  });
  const text = await response.text();
  const parsed = text ? parseJsonBody<unknown>(text, response.status) : null;
  if (!response.ok) {
    const failure = parseErrorCode(parsed);
    throw new IngestRunCatalogApiError(failure.message, response.status, failure.code);
  }
  return assertCatalog(parsed);
}
