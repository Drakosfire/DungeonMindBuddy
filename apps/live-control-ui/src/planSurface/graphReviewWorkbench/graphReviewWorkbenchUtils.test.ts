import { describe, expect, it } from "vitest";

import type {
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
} from "../../api/types";
import {
  buildGraphReviewCatalog,
  catalogSessionLabel,
  goldSessionToLane,
  graphIngestRunToLane,
  hasCatalogReviewableRun,
  pickDefaultCatalogSession,
  pickDefaultWorkbenchRun,
  pickDefaultWorkbenchSession,
} from "./graphReviewWorkbenchUtils";

function run(
  overrides: Partial<GraphIngestRunSummary> = {},
): GraphIngestRunSummary {
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

function session(
  overrides: Partial<GoldReviewSessionSummary> = {},
): GoldReviewSessionSummary {
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
    expect(lane.counts).toMatchObject({
      nodes: 7,
      edges: 4,
      beats: 2,
      evidenceRefs: 9,
    });
    expect(lane.metadata.vocabularyMode).toBe("unknown");
  });

  it("maps live runs to graph-ingest lanes and uses preview availability for status", () => {
    const availableLane = graphIngestRunToLane(
      run({ preview_union_available: true }),
    );
    const missingLane = graphIngestRunToLane(
      run({ preview_union_available: false }),
    );
    expect(availableLane.role).toBe("live");
    expect(availableLane.sourceKind).toBe("graph_ingest_run");
    expect(availableLane.status).toBe("available");
    expect(missingLane.status).toBe("missing_projection");
    expect(availableLane.counts).toMatchObject({
      nodes: 3,
      edges: 2,
      evidenceRefs: 5,
    });
  });

  it("picks deterministic default sessions with reviewable projections first", () => {
    const sessions = [
      session({
        session_id: "session-21",
        available_runs: [run({ preview_union_available: false })],
      }),
      session({ session_id: "session-22" }),
    ];
    expect(
      pickDefaultWorkbenchSession(sessions, "session-22", "session-21")
        ?.session_id,
    ).toBe("session-22");
    expect(
      pickDefaultWorkbenchSession(sessions, null, "session-21")?.session_id,
    ).toBe("session-22");
    expect(
      pickDefaultWorkbenchSession(sessions, null, "missing")?.session_id,
    ).toBe("session-22");
  });

  it("picks preview-union-ready runs before falling back to the first run", () => {
    const missing = run({
      manifest_path: "missing.json",
      preview_union_available: false,
    });
    const ready = run({
      manifest_path: "ready.json",
      preview_union_available: true,
    });
    expect(pickDefaultWorkbenchRun([missing, ready])?.manifest_path).toBe(
      "ready.json",
    );
    expect(pickDefaultWorkbenchRun([missing])?.manifest_path).toBe(
      "missing.json",
    );
    expect(pickDefaultWorkbenchRun([])).toBeNull();
  });

  it("handles missing metadata without throwing", () => {
    const lane = graphIngestRunToLane(
      run({
        run_id: null,
        generated_at: null,
        updated_at: null,
        created_at: null,
        model_id: null,
        extraction_profile: null,
        extraction_mode: null,
        preview_union_store_path: null,
        vocabulary_mode: "unknown",
      }),
    );
    expect(lane.metadata.runId).toBeUndefined();
    expect(lane.metadata.vocabularyMode).toBe("unknown");
    expect(lane.previewUnionPath).toBeUndefined();
  });

  it("merges run-only sessions without gold metadata", () => {
    const catalog = buildGraphReviewCatalog([
      run({
        campaign_id: "longmont-c1",
        session_id: "session-2",
        run_label: "C1S2 run",
      }),
    ]);
    expect(catalog).toHaveLength(1);
    expect(catalog[0]).toMatchObject({
      campaignId: "longmont-c1",
      sessionId: "session-2",
      sessionNumber: 2,
      hasGold: false,
      hasReviewableRun: true,
      goldFixtureId: null,
    });
    expect(catalogSessionLabel(catalog[0])).toBe("Session 2");
  });

  it("overlays gold metadata when runs and gold sessions share a key", () => {
    const catalog = buildGraphReviewCatalog(
      [
        run({
          campaign_id: "longmont-c1",
          session_id: "session-1",
          run_label: "Live run",
        }),
      ],
      [
        session({
          campaign_id: "longmont-c1",
          session_id: "session-1",
          session_number: 1,
          gold_fixture_id: "gold-1",
          available_runs: [],
        }),
      ],
    );
    expect(catalog).toHaveLength(1);
    expect(catalog[0]).toMatchObject({
      hasGold: true,
      hasReviewableRun: true,
      goldFixtureId: "gold-1",
    });
    expect(catalog[0].availableRuns).toHaveLength(1);
  });

  it("includes gold-only sessions without preview-ready runs", () => {
    const catalog = buildGraphReviewCatalog(
      [],
      [
        session({
          campaign_id: "longmont-c2",
          session_id: "session-99",
          session_number: 99,
          available_runs: [run({ preview_union_available: false })],
        }),
      ],
    );
    expect(catalog).toHaveLength(1);
    expect(catalog[0].hasGold).toBe(true);
    expect(hasCatalogReviewableRun(catalog[0])).toBe(false);
  });

  it("picks default catalog sessions with reviewable runs first", () => {
    const catalog = buildGraphReviewCatalog(
      [
        run({ session_id: "session-2", campaign_id: "longmont-c1" }),
        run({
          session_id: "session-21",
          campaign_id: "longmont-c2",
          preview_union_available: false,
        }),
      ],
      [session({ session_id: "session-23", campaign_id: "longmont-c2" })],
    );
    expect(
      pickDefaultCatalogSession(catalog, "session-2", "session-21")?.sessionId,
    ).toBe("session-2");
    expect(
      pickDefaultCatalogSession(catalog, null, "session-21")?.sessionId,
    ).toBe("session-2");
  });
});
