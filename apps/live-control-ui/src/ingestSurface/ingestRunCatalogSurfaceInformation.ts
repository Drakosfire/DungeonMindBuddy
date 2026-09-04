/**
 * Ingest ExtractionRun catalog → Surface Information mapping (SI-5B).
 *
 * Collection authority is unrevisioned. Individual run.revision is payload data.
 */

import type {
  SurfaceInformationDescriptor,
  SurfaceInformationDiagnostic,
  SurfaceInformationState,
} from "../surfaceInformation";
import {
  INGEST_RUN_CATALOG_INTEGRITY_ERROR,
  INGEST_RUN_CATALOG_SCHEMA_UNAVAILABLE,
  INGEST_RUN_CATALOG_UNAVAILABLE,
  IngestRunCatalogApiError,
  type ExtractionRunCatalogResponse,
} from "./ingestRunCatalogApi";

export const INGEST_RUN_CATALOG_CHANNEL_ID = "ingest-extraction-run-catalog:v1";
export const INGEST_RUN_CATALOG_INFORMATION_KIND = "extraction_run_catalog";
export const INGEST_RUN_CATALOG_PROVIDER_ID = "ingest_extraction_run_catalog";

const MAX_SAFE_DIAGNOSTICS = 8;

export const INGEST_RUN_CATALOG_DESCRIPTOR: SurfaceInformationDescriptor = Object.freeze({
  channelId: INGEST_RUN_CATALOG_CHANNEL_ID,
  informationKind: INGEST_RUN_CATALOG_INFORMATION_KIND,
  providerId: INGEST_RUN_CATALOG_PROVIDER_ID,
  authority: "buddy_app_state",
  subject: Object.freeze({ kind: "application_state_collection", id: "ingest.run" }),
  scope: Object.freeze([]),
});

const UNREVISIONED = Object.freeze({ kind: "unrevisioned" as const });

function boundedDiagnostics(
  diagnostics: readonly SurfaceInformationDiagnostic[],
): readonly SurfaceInformationDiagnostic[] {
  return diagnostics.slice(0, MAX_SAFE_DIAGNOSTICS).map((diagnostic) => ({
    code: diagnostic.code,
    message: diagnostic.message,
  }));
}

function observedMetadata(diagnostics: readonly SurfaceInformationDiagnostic[] = []) {
  return {
    revision: UNREVISIONED,
    provenance: [{ kind: "application_state_collection", id: "ingest.run" }],
    inspectionTargets: [{ kind: "application_state_collection", id: "ingest.run" }],
    diagnostics: boundedDiagnostics(diagnostics),
  };
}

export function isCatalogUnavailableCode(code: string | null | undefined): boolean {
  return (
    code === INGEST_RUN_CATALOG_UNAVAILABLE
    || code === INGEST_RUN_CATALOG_SCHEMA_UNAVAILABLE
  );
}

export function isCatalogIntegrityCode(code: string | null | undefined): boolean {
  return code === INGEST_RUN_CATALOG_INTEGRITY_ERROR;
}

export function mapIngestRunCatalogObservation(input: {
  response?: ExtractionRunCatalogResponse | null;
  error?: unknown;
}): Exclude<SurfaceInformationState<ExtractionRunCatalogResponse>, { status: "loading" }> {
  if (input.response) {
    if (input.response.runs.length === 0) {
      return {
        status: "empty",
        ...observedMetadata(),
      };
    }
    return {
      status: "ready",
      value: input.response,
      ...observedMetadata(),
    };
  }

  const error = input.error;
  if (error instanceof IngestRunCatalogApiError) {
    const diagnostics = boundedDiagnostics([
      { code: error.code?.trim() || "ingest_run_catalog_error", message: error.message },
    ]);
    if (isCatalogIntegrityCode(error.code) || error.status === 200) {
      return {
        status: "integrity_error",
        reason: error.message,
        diagnostics,
      };
    }
    return {
      status: "unavailable",
      reason: error.message,
      diagnostics,
    };
  }

  const message = error instanceof Error ? error.message : "Ingest run catalog request failed.";
  return {
    status: "unavailable",
    reason: message,
    diagnostics: boundedDiagnostics([{ code: "ingest_run_catalog_error", message }]),
  };
}
