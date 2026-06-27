import { describe, expect, it } from "vitest";

import type { RecapArtifactRecord } from "../../api/types";
import {
  filterNumericRecapArtifactRecords,
  recapArtifactSessionLabel,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";

function sampleRecord(sessionId: string, path: string): RecapArtifactRecord {
  return {
    schema_version: "dmb_recap_artifact_record_v1",
    artifact_id: `longmont-c2/${sessionId}`,
    campaign_id: "longmont-c2",
    session_id: sessionId,
    source_recap_path: path,
    run_bundle_uri: "evals/graph_memory_layer/runs/live_recap_ingest/session_21_category_study",
    run_manifest_uri: "evals/graph_memory_layer/runs/live_recap_ingest/session_21_category_study/run_manifest.json",
    source_span_index_uri:
      "evals/graph_memory_layer/runs/live_recap_ingest/session_21_category_study/source_span_index.json",
    graph_run_refs: [],
    default_projection_mode: "recap_graph",
    registered_at: "2026-06-27T00:00:00Z",
    updated_at: "2026-06-27T00:00:00Z",
    registry_source: "scan",
  };
}

describe("recapSessionLabels", () => {
  it("labels sessions with recap title from source path", () => {
    const record = sampleRecord(
      "session-21",
      "corpus/.../_normalized/Session 21 - Drake Nest Mirathorn Call.md",
    );
    expect(recapArtifactSessionLabel(record)).toBe("Session 21 · Drake Nest Mirathorn Call");
  });

  it("filters and sorts numeric recap sessions", () => {
    const records = [
      sampleRecord("session-test", "corpus/test.md"),
      sampleRecord("session-22", "corpus/Session 22 - Foo.md"),
      sampleRecord("session-21", "corpus/Session 21 - Bar.md"),
    ];
    const filtered = filterNumericRecapArtifactRecords(records);
    expect(filtered.map((record) => record.session_id)).toEqual(["session-22", "session-21"]);
    expect(sortRecapArtifactRecords(filtered).map((record) => record.session_id)).toEqual([
      "session-21",
      "session-22",
    ]);
  });
});
