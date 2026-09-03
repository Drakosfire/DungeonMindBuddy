import { describe, expect, it } from "vitest";

import type {
  ExtractionRunRecord,
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
} from "../../api/types";
import {
  buildGraphReviewCatalog,
  catalogSessionLabel,
  formatCompactAppliedLoadLabel,
  goldSessionToLane,
  graphIngestRunToLane,
  pickDefaultCatalogSession,
  pickDefaultWorkbenchRun,
  pickDefaultWorkbenchSession,
  toCatalogRun,
  type GraphReviewCatalogRun,
} from "./graphReviewWorkbenchUtils";

function extractionRun(
  overrides: Partial<ExtractionRunRecord> = {},
): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: "er_run_a",
    source_artifact_id: "sa_1",
    source_domain: "recap",
    status: "reviewable",
    campaign_id: "longmont-c2",
    session_id: "session-23",
    ...overrides,
  };
}

function catalogRun(
  overrides: Partial<ExtractionRunRecord> = {},
  compatibilityManifestPath: string | null = null,
): GraphReviewCatalogRun {
  return toCatalogRun(extractionRun(overrides), compatibilityManifestPath);
}

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

  it("picks reviewable catalog runs as the UI default and does not invent identity", () => {
    const draft = catalogRun({ status: "draft", run_id: "er_draft" });
    const reviewable = catalogRun({ status: "reviewable", run_id: "er_ready" });
    expect(pickDefaultWorkbenchRun([draft, reviewable])?.run.run_id).toBe("er_ready");
    expect(pickDefaultWorkbenchRun([draft])).toBeNull();
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

  it("builds the product catalog from APP-STATE recap runs only", () => {
    const catalog = buildGraphReviewCatalog([
      extractionRun({
        campaign_id: "longmont-c1",
        session_id: "session-2",
        run_id: "er_c1s2",
      }),
      extractionRun({
        source_domain: "worldbuilding",
        campaign_id: "longmont-c1",
        session_id: null,
        run_id: "er_world",
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
    expect(catalog[0].availableRuns.map((entry) => entry.run.run_id)).toEqual(["er_c1s2"]);
    expect(catalogSessionLabel(catalog[0])).toBe("Session 2");
  });

  it("formats compact applied load labels without run pipeline metadata", () => {
    const catalog = buildGraphReviewCatalog([
      extractionRun({
        campaign_id: "longmont-c1",
        session_id: "session-1",
        run_id: "er_s1",
      }),
    ]);
    expect(formatCompactAppliedLoadLabel(catalog[0])).toBe("Session 1 · longmont-c1");
  });

  it("W5: gold available_runs cannot inject a product run; exact run_id may only enrich locator", () => {
    const canonical = extractionRun({
      run_id: "er_canonical",
      campaign_id: "longmont-c1",
      session_id: "session-1",
    });
    const catalog = buildGraphReviewCatalog(
      [canonical],
      [
        session({
          campaign_id: "longmont-c1",
          session_id: "session-1",
          session_number: 1,
          gold_fixture_id: "gold-1",
          available_runs: [
            run({
              run_id: "er_canonical",
              manifest_path: "gold/er_canonical/manifest.json",
              campaign_id: "longmont-c1",
              session_id: "session-1",
            }),
            run({
              run_id: "er_gold_only",
              manifest_path: "gold/only/manifest.json",
              campaign_id: "longmont-c1",
              session_id: "session-1",
            }),
          ],
        }),
      ],
    );
    expect(catalog).toHaveLength(1);
    expect(catalog[0].availableRuns).toHaveLength(1);
    expect(catalog[0].availableRuns[0]?.run.run_id).toBe("er_canonical");
    expect(catalog[0].availableRuns[0]?.run.status).toBe("reviewable");
    expect(catalog[0].availableRuns[0]?.compatibilityManifestPath).toBe(
      "gold/er_canonical/manifest.json",
    );
  });

  it("W3: conflicting same-id legacy run cannot override DB fields", () => {
    const catalog = buildGraphReviewCatalog(
      [
        extractionRun({
          run_id: "er_same",
          status: "reviewable",
          campaign_id: "longmont-c2",
          session_id: "session-23",
        }),
      ],
      [
        session({
          available_runs: [
            run({
              run_id: "er_same",
              status: "failed",
              campaign_id: "other-campaign",
              session_id: "session-99",
              manifest_path: "legacy/er_same.json",
            }),
          ],
        }),
      ],
    );
    expect(catalog[0].availableRuns[0]?.run.status).toBe("reviewable");
    expect(catalog[0].availableRuns[0]?.run.campaign_id).toBe("longmont-c2");
    expect(catalog[0].availableRuns[0]?.compatibilityManifestPath).toBeNull();
  });

  it("W4: gold/manifest-only runs are absent from the product catalog", () => {
    const catalog = buildGraphReviewCatalog(
      [],
      [
        session({
          campaign_id: "longmont-c2",
          session_id: "session-99",
          session_number: 99,
          available_runs: [run({ run_id: "er_file_only", preview_union_available: true })],
        }),
      ],
    );
    expect(catalog).toHaveLength(0);
  });

  it("picks default catalog sessions with inspectable runs first", () => {
    const catalog = buildGraphReviewCatalog([
      extractionRun({ session_id: "session-2", campaign_id: "longmont-c1", run_id: "er_s2" }),
      extractionRun({
        session_id: "session-21",
        campaign_id: "longmont-c2",
        run_id: "er_s21",
        status: "draft",
      }),
    ]);
    expect(
      pickDefaultCatalogSession(catalog, "session-2", "session-21")?.sessionId,
    ).toBe("session-2");
  });
});
