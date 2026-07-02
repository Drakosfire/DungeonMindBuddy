import { describe, expect, it } from "vitest";

import type { GoldReviewSessionSummary, GraphIngestRunSummary } from "../../api/types";
import {
  goldSessionToLane,
  graphIngestRunToLane,
  pickDefaultWorkbenchRun,
  pickDefaultWorkbenchSession,
} from "./graphReviewWorkbenchUtils";

function run(overrides: Partial<GraphIngestRunSummary> = {}): GraphIngestRunSummary {
  return {
    manifest_path: "runs/manifest.json",
    run_dir: "runs/run-a",
    campaign_id: "longmont-c2",
    session_id: "session-23",
    status: "complete",
    updated_at: "2026-07-01T00:00:00Z",
    created_at: "2026-07-01T00:00:00Z",
    preview_union_store_path: "runs/union.json",
    preview_union_store_valid: true,
    node_count: 3,
    edge_count: 2,
    evidence_ref_count: 5,
    next_actions: [],
    run_id: "run-a",
    run_label: "Run A",
    generated_at: "2026-07-01T00:01:00Z",
    model_id: "gpt-test",
    model_provider: "openai",
    extraction_profile: "profile-a",
    extraction_mode: "category",
    vocabulary_mode: "node",
    runner_options_summary: { dryRun: true },
    diagnostics_summary: { warnings: 0 },
    preview_union_available: true,
    ...overrides,
  };
}

function session(overrides: Partial<GoldReviewSessionSummary> = {}): GoldReviewSessionSummary {
  return {
    session_id: "session-23",
    session_number: 23,
    campaign_id: "longmont-c2",
    gold_fixture_id: "gold-23",
    gold_manifest_path: "gold/manifest.json",
    gold_graph_path: "gold/graph.json",
    gold_counts: { nodes: 7, edges: 4, beats: 2, evidence_refs: 9 },
    available_runs: [run()],
    ...overrides,
  };
}

describe("graphReviewWorkbenchUtils", () => {
  it("maps a gold session to a gold fixture lane", () => {
    const lane = goldSessionToLane(session());
    expect(lane.role).toBe("gold");
    expect(lane.sourceKind).toBe("gold_fixture");
    expect(lane.status).toBe("available");
    expect(lane.counts).toMatchObject({ nodes: 7, edges: 4, beats: 2, evidenceRefs: 9 });
    expect(lane.metadata.vocabularyMode).toBe("unknown");
  });

  it("maps live runs to graph-ingest lanes and uses preview availability for status", () => {
    const availableLane = graphIngestRunToLane(run({ preview_union_available: true }));
    const missingLane = graphIngestRunToLane(run({ preview_union_available: false }));
    expect(availableLane.role).toBe("live");
    expect(availableLane.sourceKind).toBe("graph_ingest_run");
    expect(availableLane.status).toBe("available");
    expect(missingLane.status).toBe("missing_projection");
    expect(availableLane.counts).toMatchObject({ nodes: 3, edges: 2, evidenceRefs: 5 });
  });

  it("picks deterministic default sessions", () => {
    const sessions = [session({ session_id: "session-21" }), session({ session_id: "session-22" })];
    expect(pickDefaultWorkbenchSession(sessions, "session-22", "session-21")?.session_id).toBe("session-22");
    expect(pickDefaultWorkbenchSession(sessions, null, "session-21")?.session_id).toBe("session-21");
    expect(pickDefaultWorkbenchSession(sessions, null, "missing")?.session_id).toBe("session-21");
  });

  it("picks preview-union-ready runs before falling back to the first run", () => {
    const missing = run({ manifest_path: "missing.json", preview_union_available: false });
    const ready = run({ manifest_path: "ready.json", preview_union_available: true });
    expect(pickDefaultWorkbenchRun([missing, ready])?.manifest_path).toBe("ready.json");
    expect(pickDefaultWorkbenchRun([missing])?.manifest_path).toBe("missing.json");
    expect(pickDefaultWorkbenchRun([])).toBeNull();
  });

  it("handles missing metadata without throwing", () => {
    const lane = graphIngestRunToLane(run({
      run_id: null,
      generated_at: null,
      updated_at: null,
      created_at: null,
      model_id: null,
      extraction_profile: null,
      extraction_mode: null,
      preview_union_store_path: null,
      vocabulary_mode: "unknown",
    }));
    expect(lane.metadata.runId).toBeUndefined();
    expect(lane.metadata.vocabularyMode).toBe("unknown");
    expect(lane.previewUnionPath).toBeUndefined();
  });
});
