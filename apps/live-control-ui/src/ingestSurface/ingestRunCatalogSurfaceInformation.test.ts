import { describe, expect, it } from "vitest";

import {
  INGEST_RUN_CATALOG_INTEGRITY_ERROR,
  INGEST_RUN_CATALOG_UNAVAILABLE,
  IngestRunCatalogApiError,
  type ExtractionRunCatalogResponse,
} from "./ingestRunCatalogApi";
import {
  INGEST_RUN_CATALOG_DESCRIPTOR,
  mapIngestRunCatalogObservation,
} from "./ingestRunCatalogSurfaceInformation";
import type { ExtractionRunRecord } from "../api/types";

function run(runId = "er_a"): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: runId,
    source_artifact_id: "sa_1",
    source_domain: "recap",
    status: "reviewable",
    campaign_id: "longmont-c2",
    session_id: "session-23",
  };
}

describe("ingestRunCatalogSurfaceInformation", () => {
  it("describes an unrevisioned APP-STATE collection", () => {
    expect(INGEST_RUN_CATALOG_DESCRIPTOR).toMatchObject({
      channelId: "ingest-extraction-run-catalog:v1",
      informationKind: "extraction_run_catalog",
      providerId: "ingest_extraction_run_catalog",
      authority: "buddy_app_state",
      subject: { kind: "application_state_collection", id: "ingest.run" },
      scope: [],
    });
  });

  it("maps populated catalog to READY unrevisioned", () => {
    const response: ExtractionRunCatalogResponse = {
      schema_version: "dmb_extraction_run_catalog_v1",
      runs: [run()],
    };
    const state = mapIngestRunCatalogObservation({ response });
    expect(state.status).toBe("ready");
    if (state.status === "ready") {
      expect(state.value.runs[0]?.run_id).toBe("er_a");
      expect(state.revision).toEqual({ kind: "unrevisioned" });
    }
  });

  it("maps zero rows to EMPTY unrevisioned", () => {
    const state = mapIngestRunCatalogObservation({
      response: { schema_version: "dmb_extraction_run_catalog_v1", runs: [] },
    });
    expect(state.status).toBe("empty");
    if (state.status === "empty") {
      expect(state.revision).toEqual({ kind: "unrevisioned" });
    }
  });

  it("maps unavailable/schema codes to UNAVAILABLE", () => {
    const state = mapIngestRunCatalogObservation({
      error: new IngestRunCatalogApiError("down", 503, INGEST_RUN_CATALOG_UNAVAILABLE),
    });
    expect(state.status).toBe("unavailable");
  });

  it("maps integrity codes to INTEGRITY_ERROR", () => {
    const state = mapIngestRunCatalogObservation({
      error: new IngestRunCatalogApiError("dup", 200, INGEST_RUN_CATALOG_INTEGRITY_ERROR),
    });
    expect(state.status).toBe("integrity_error");
  });
});
