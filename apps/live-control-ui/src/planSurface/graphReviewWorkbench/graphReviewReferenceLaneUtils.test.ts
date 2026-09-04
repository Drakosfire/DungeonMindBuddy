import { describe, expect, it } from "vitest";
import type {
  ExtractionRunRecord,
  GoldReviewCompareResponse,
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
  ManualReviewBedDetail,
  ManualReviewVariantDetail,
} from "../../api/types";
import { manualVariantToLaneView } from "./graphReviewVariantReferenceUtils";
import {
  buildPrimaryLiveLaneView,
  buildReferenceLaneView,
  compactRecordSummary,
} from "./graphReviewReferenceLaneUtils";
import { toCatalogRun } from "./graphReviewWorkbenchUtils";

function canonicalRun(overrides: Partial<ExtractionRunRecord> = {}): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: "run-1",
    source_artifact_id: "sa_1",
    source_domain: "recap",
    status: "reviewable",
    campaign_id: "c1",
    session_id: "s1",
    ...overrides,
  };
}

const catalogRun = toCatalogRun(canonicalRun(), "runs/m.json");
const legacyRun: GraphIngestRunSummary = {
  manifest_path: "runs/m.json",
  run_dir: "runs",
  campaign_id: "c1",
  session_id: "s1",
  status: "succeeded",
  node_count: 2,
  edge_count: 3,
  evidence_ref_count: 4,
  next_actions: [],
  run_id: "run-1",
  run_label: "Run Label",
  vocabulary_mode: "node",
  runner_options_summary: {},
  diagnostics_summary: {},
  preview_union_available: true,
  preview_union_store_path: "union.json",
};
const session: GoldReviewSessionSummary = {
  session_id: "s1",
  session_number: 1,
  campaign_id: "c1",
  gold_fixture_id: "fixture-1",
  gold_manifest_path: "gold/manifest.json",
  gold_graph_path: "gold/graph.json",
  gold_counts: { nodes: 2, edges: 1 },
  available_runs: [legacyRun],
};
const compare: GoldReviewCompareResponse = {
  schema_version: "dmb_graph_gold_review_compare_v1",
  version: "1",
  session_id: "s1",
  campaign_id: "c1",
  gold_fixture_id: "fixture-1",
  gold_manifest_path: "gold/manifest.json",
  gold_graph_path: "gold/graph.json",
  live_run: legacyRun,
  comparison: {
    scores: { recall: 0.8 },
    coverage: { nodes: true },
    soft_misses: [{ issue: "missing", detail: "one" }],
  },
  object_index: { gold: {}, live: {} },
  match_pairs: {},
};
const variant: ManualReviewVariantDetail = {
  variant_name: "v1",
  node_count: 1,
  edge_count: 1,
  cost_usd: 0.2,
  nodes: [],
  edges: [],
  node_kinds: { actor: 1 },
  edge_predicates: { helps: 1 },
  gold_comparison: { available: true },
  party_context: {},
};
const bed: ManualReviewBedDetail = {
  schema_version: "dmb_graph_manual_review_bed_v1",
  version: "1",
  bed_id: "bed-1",
  campaign_id: "c1",
  session_id: "s1",
  generated_at: "2026-07-02",
  model_id: "model-1",
  node_prompt_contexts: {},
  edge_prompt_context: "",
  variant_names: ["v1"],
  variants: { v1: variant },
};
const variantView = manualVariantToLaneView({ bed, variantName: "v1" })!;

describe("graphReviewReferenceLaneUtils", () => {
  it("buildPrimaryLiveLaneView(null) returns null", () =>
    expect(buildPrimaryLiveLaneView(null)).toBeNull());
  it("buildPrimaryLiveLaneView uses canonical run_id as label", () =>
    expect(buildPrimaryLiveLaneView(catalogRun)?.label).toBe("run-1"));
  it("empty reference returns empty_reference", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: null,
        compare: null,
        selectedVariantLaneView: null,
        preferredReference: "auto",
      }).kind,
    ).toBe("empty_reference"));
  it("gold session returns gold_reference", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: session,
        compare: null,
        selectedVariantLaneView: null,
        preferredReference: "auto",
      }).kind,
    ).toBe("gold_reference"));
  it("gold reference works without compare and includes warning", () => {
    const view = buildReferenceLaneView({
      selectedSession: session,
      compare: null,
      selectedVariantLaneView: null,
      preferredReference: "gold",
    });
    expect(view.warnings).toContain("Gold/live compare data is not loaded yet.");
    expect(view.summaryItems.some((item) => item.label === "Gold fixture id")).toBe(true);
  });
  it("gold reference includes score/coverage/soft-miss summaries when compare exists", () => {
    const labels = buildReferenceLaneView({
      selectedSession: session,
      compare,
      selectedVariantLaneView: null,
      preferredReference: "gold",
    }).summaryItems.map((item) => item.label);
    expect(labels).toEqual(
      expect.arrayContaining(["Soft misses count", "Coverage keys", "Scores"]),
    );
  });
  it("manual variant reference returns manual_variant_reference", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: null,
        compare: null,
        selectedVariantLaneView: variantView,
        preferredReference: "manual_variant",
      }).kind,
    ).toBe("manual_variant_reference"));
  it("preferredReference manual_variant uses manual variant when available", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: session,
        compare,
        selectedVariantLaneView: variantView,
        preferredReference: "manual_variant",
      }).laneId,
    ).toBe(variantView.lane.laneId));
  it("preferredReference gold uses gold even if manual variant exists", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: session,
        compare,
        selectedVariantLaneView: variantView,
        preferredReference: "gold",
      }).kind,
    ).toBe("gold_reference"));
  it("preferredReference auto prefers manual variant when selected", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: session,
        compare,
        selectedVariantLaneView: variantView,
        preferredReference: "auto",
      }).kind,
    ).toBe("manual_variant_reference"));
  it("compact record summary truncates large maps deterministically", () =>
    expect(compactRecordSummary({ c: 3, a: 1, b: 2 }, 2)).toBe('{"a":1,"b":2} +1 more'));
  it("notes explicitly say projected source rendering is not implemented", () =>
    expect(
      buildReferenceLaneView({
        selectedSession: session,
        compare,
        selectedVariantLaneView: null,
        preferredReference: "gold",
      }).note,
    ).toContain("projected source rendering is not implemented"));
});
