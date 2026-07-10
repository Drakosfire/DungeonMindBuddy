// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
// Retained until PR007/PR008 removes preview/latest-ingest selectors from surface APIs.
import type {
  GoldReviewCompareResponse,
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
} from "../../api/types";
import type { GraphReviewManualVariantLaneView } from "./graphReviewVariantReferenceUtils";

export type GraphReviewReferenceLaneKind = "empty_reference" | "gold_reference" | "manual_variant_reference";

export interface GraphReviewReferenceLaneSummaryItem { label: string; value: string; }

export interface GraphReviewReferenceLaneView {
  kind: GraphReviewReferenceLaneKind;
  laneId: string;
  label: string;
  role: "gold" | "variant" | "reference";
  sourceKind: "gold_fixture" | "manual_review_variant" | "projection_payload";
  status: "available" | "missing_projection" | "unknown";
  summaryItems: GraphReviewReferenceLaneSummaryItem[];
  warnings: string[];
  note: string;
}

export interface GraphReviewPrimaryLaneView {
  laneId: string;
  label: string;
  runLabel: string;
  manifestPath: string;
  previewUnionPath?: string | null;
  status: string;
  counts: { nodes: number; edges: number; evidenceRefs: number };
}

const NO_REFERENCE_NOTE = "Projected source rendering is not implemented for this reference lane yet.";

function stringValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function compactRecordSummary(value: Record<string, unknown> | null | undefined, limit = 4): string {
  const entries = Object.entries(value ?? {}).sort(([a], [b]) => a.localeCompare(b));
  if (!entries.length) return "—";
  const shown = entries.slice(0, limit);
  const summary = Object.fromEntries(shown);
  const suffix = entries.length > limit ? ` +${entries.length - limit} more` : "";
  return `${JSON.stringify(summary)}${suffix}`;
}

export function buildPrimaryLiveLaneView(liveRun: GraphIngestRunSummary | null): GraphReviewPrimaryLaneView | null {
  if (!liveRun) return null;
  const label = liveRun.run_label || liveRun.run_id || liveRun.manifest_path;
  return {
    laneId: `live:${liveRun.manifest_path}`,
    label,
    runLabel: label,
    manifestPath: liveRun.manifest_path,
    previewUnionPath: liveRun.preview_union_store_path ?? null,
    status: liveRun.status,
    counts: { nodes: liveRun.node_count, edges: liveRun.edge_count, evidenceRefs: liveRun.evidence_ref_count },
  };
}

function emptyReference(): GraphReviewReferenceLaneView {
  return {
    kind: "empty_reference",
    laneId: "reference:empty",
    label: "No reference lane selected",
    role: "reference",
    sourceKind: "projection_payload",
    status: "unknown",
    summaryItems: [],
    warnings: ["No reference lane selected yet. Select a gold session or manual review variant to populate reference context."],
    note: NO_REFERENCE_NOTE,
  };
}

function goldReference(selectedSession: GoldReviewSessionSummary, compare: GoldReviewCompareResponse | null): GraphReviewReferenceLaneView {
  const warnings = compare ? [] : ["Gold/live compare data is not loaded yet."];
  const items: GraphReviewReferenceLaneSummaryItem[] = [
    { label: "Gold fixture id", value: stringValue(selectedSession.gold_fixture_id) },
    { label: "Campaign id", value: stringValue(selectedSession.campaign_id) },
    { label: "Session id", value: stringValue(selectedSession.session_id) },
    { label: "Gold manifest path", value: stringValue(selectedSession.gold_manifest_path) },
    { label: "Gold graph path", value: stringValue(selectedSession.gold_graph_path) },
    { label: "Gold counts", value: compactRecordSummary(selectedSession.gold_counts) },
    { label: "Gold/live compare readiness", value: compare ? "loaded" : "not loaded" },
  ];
  if (compare) {
    items.push(
      { label: "Soft misses count", value: String(compare.comparison.soft_misses.length) },
      { label: "Coverage keys", value: Object.keys(compare.comparison.coverage).sort().join(", ") || "—" },
      { label: "Scores", value: compactRecordSummary(compare.comparison.scores) },
    );
  }
  return {
    kind: "gold_reference",
    laneId: `gold:${selectedSession.gold_fixture_id}`,
    label: `Gold fixture · ${selectedSession.gold_fixture_id}`,
    role: "gold",
    sourceKind: "gold_fixture",
    status: "missing_projection",
    summaryItems: items,
    warnings,
    note: "Gold fixture metadata is shown here. Full gold projected source rendering is not implemented in this PR. Projected source rendering is not implemented for this reference lane yet.",
  };
}

function manualReference(view: GraphReviewManualVariantLaneView): GraphReviewReferenceLaneView {
  const { bed, variant, lane } = view;
  return {
    kind: "manual_variant_reference",
    laneId: lane.laneId,
    label: lane.label,
    role: "variant",
    sourceKind: "manual_review_variant",
    status: "missing_projection",
    summaryItems: [
      { label: "Manual bed id", value: stringValue(bed.bed_id) },
      { label: "Variant name", value: stringValue(variant.variant_name) },
      { label: "Campaign id", value: stringValue(bed.campaign_id) },
      { label: "Session id", value: stringValue(bed.session_id) },
      { label: "Node count", value: stringValue(variant.node_count) },
      { label: "Edge count", value: stringValue(variant.edge_count) },
      { label: "Model id", value: stringValue(bed.model_id) },
      { label: "Generated at", value: stringValue(bed.generated_at) },
      { label: "Cost estimate", value: variant.cost_usd === null || variant.cost_usd === undefined ? "—" : `$${variant.cost_usd}` },
      { label: "Node kind counts", value: compactRecordSummary(variant.node_kinds) },
      { label: "Edge predicate counts", value: compactRecordSummary(variant.edge_predicates) },
      { label: "Gold comparison availability", value: Object.keys(variant.gold_comparison ?? {}).length ? "available" : "not available" },
    ],
    warnings: [],
    note: "Manual variant metadata is shown here. Full manual variant projected source rendering is not implemented in this PR. Projected source rendering is not implemented for this reference lane yet.",
  };
}

export function buildReferenceLaneView(input: {
  selectedSession: GoldReviewSessionSummary | null;
  compare: GoldReviewCompareResponse | null;
  selectedVariantLaneView: GraphReviewManualVariantLaneView | null;
  preferredReference: "gold" | "manual_variant" | "auto";
}): GraphReviewReferenceLaneView {
  if (input.preferredReference === "manual_variant" && input.selectedVariantLaneView) return manualReference(input.selectedVariantLaneView);
  if (input.preferredReference === "gold" && input.selectedSession) return goldReference(input.selectedSession, input.compare);
  if (input.preferredReference === "auto") {
    if (input.selectedVariantLaneView) return manualReference(input.selectedVariantLaneView);
    if (input.selectedSession) return goldReference(input.selectedSession, input.compare);
  }
  if (input.selectedSession && input.preferredReference === "manual_variant") return goldReference(input.selectedSession, input.compare);
  if (input.selectedVariantLaneView && input.preferredReference === "gold") return manualReference(input.selectedVariantLaneView);
  return emptyReference();
}
