import type {
  GoldReviewCompareResponse,
  GoldReviewObjectIndexEntry,
  GraphReviewLane,
  ManualReviewBedDetail,
  ManualReviewEdge,
  ManualReviewNode,
  ManualReviewVariantDetail,
} from "../../api/types";

export type GraphReviewVariantInventoryStatus =
  | "variant_only"
  | "live_only"
  | "label_overlap"
  | "kind_label_overlap"
  | "comparator_uncertain";

export type GraphReviewVariantObjectKind = "node" | "edge" | "unknown";

export interface GraphReviewManualVariantSelection {
  bedId: string;
  variantName: string;
}

export interface GraphReviewManualVariantLaneView {
  lane: GraphReviewLane;
  bed: ManualReviewBedDetail;
  variant: ManualReviewVariantDetail;
}

export interface GraphReviewVariantInventoryRow {
  rowId: string;
  status: GraphReviewVariantInventoryStatus;
  objectKind: GraphReviewVariantObjectKind;
  label: string;
  normalizedLabel: string;
  variantNode?: ManualReviewNode | null;
  variantEdge?: ManualReviewEdge | null;
  liveObjects: GoldReviewObjectIndexEntry[];
  summary: string;
  evidenceSpanIds: string[];
  anchorQuotes: string[];
}

export interface GraphReviewVariantInventoryIndex {
  rows: GraphReviewVariantInventoryRow[];
  countsByStatus: Record<GraphReviewVariantInventoryStatus, number>;
  warnings: string[];
}

const STATUSES: GraphReviewVariantInventoryStatus[] = [
  "variant_only",
  "live_only",
  "label_overlap",
  "kind_label_overlap",
  "comparator_uncertain",
];
const SORT_PRIORITY: Record<GraphReviewVariantInventoryStatus, number> = {
  comparator_uncertain: 0,
  variant_only: 1,
  live_only: 2,
  kind_label_overlap: 3,
  label_overlap: 4,
};

export function normalizeInventoryLabel(label: string | null | undefined): string {
  return (label ?? "")
    .toLowerCase()
    .trim()
    .replace(/^[\s"'`.,:;!?()[\]{}<>-]+|[\s"'`.,:;!?()[\]{}<>-]+$/g, "")
    .replace(/\s+/g, " ");
}

export function manualVariantToLaneView(input: {
  bed: ManualReviewBedDetail;
  variantName: string;
}): GraphReviewManualVariantLaneView | null {
  const variant = input.bed.variants[input.variantName];
  if (!variant) return null;
  const lane: GraphReviewLane = {
    laneId: `manual:${input.bed.bed_id}:${variant.variant_name}`,
    role: "variant",
    sourceKind: "manual_review_variant",
    label: `Manual variant · ${variant.variant_name}`,
    campaignId: input.bed.campaign_id ?? "unknown",
    sessionId: input.bed.session_id ?? "unknown",
    status: "available",
    counts: { nodes: variant.node_count ?? variant.nodes.length, edges: variant.edge_count ?? variant.edges.length },
    metadata: {
      modelId: input.bed.model_id ?? undefined,
      generatedAt: input.bed.generated_at ?? undefined,
      diagnostics: {
        bedId: input.bed.bed_id,
        sourceLabel: input.bed.source_label,
        costUsd: variant.cost_usd,
        nodeKinds: variant.node_kinds,
        edgePredicates: variant.edge_predicates,
        goldComparison: variant.gold_comparison,
      },
    },
  };
  return { lane, bed: input.bed, variant };
}

function emptyCounts(): Record<GraphReviewVariantInventoryStatus, number> {
  return Object.fromEntries(STATUSES.map((status) => [status, 0])) as Record<GraphReviewVariantInventoryStatus, number>;
}

function variantEntries(variant: ManualReviewVariantDetail) {
  return [
    ...variant.nodes.map((node) => ({ kind: "node" as const, label: node.label, key: node.node_id, node, edge: null })),
    ...variant.edges.map((edge) => ({ kind: "edge" as const, label: edge.relationship_type, key: edge.edge_id, node: null, edge })),
  ];
}

function liveKind(entry: GoldReviewObjectIndexEntry): GraphReviewVariantObjectKind {
  const kind = entry.object_kind.toLowerCase();
  if (kind === "node" || kind === "nodes") return "node";
  if (kind === "edge" || kind === "edges") return "edge";
  return "unknown";
}

function compatible(kind: GraphReviewVariantObjectKind, live: GoldReviewObjectIndexEntry): boolean {
  return kind !== "unknown" && kind === liveKind(live);
}

function sortRows(rows: GraphReviewVariantInventoryRow[]) {
  return rows.sort((a, b) =>
    SORT_PRIORITY[a.status] - SORT_PRIORITY[b.status] ||
    a.objectKind.localeCompare(b.objectKind) ||
    a.label.localeCompare(b.label) ||
    a.rowId.localeCompare(b.rowId),
  );
}

export function buildVariantLiveInventoryIndex(input: {
  variant: ManualReviewVariantDetail | null;
  compare: GoldReviewCompareResponse | null;
}): GraphReviewVariantInventoryIndex {
  const countsByStatus = emptyCounts();
  const warnings: string[] = [];
  if (!input.variant) return { rows: [], countsByStatus, warnings: ["Select a manual review variant to compare its inventory against the selected live run."] };

  const variantItems = variantEntries(input.variant).map((item) => ({ ...item, normalizedLabel: normalizeInventoryLabel(item.label) }));
  const liveObjects = Object.values(input.compare?.object_index.live ?? {}).map((live) => ({ ...live, normalizedLabel: normalizeInventoryLabel(live.label) }));
  if (!input.compare) warnings.push("Live compare data is unavailable, so rows are variant inventory only.");

  const variantByLabel = new Map<string, typeof variantItems>();
  const liveByLabel = new Map<string, typeof liveObjects>();
  for (const item of variantItems) variantByLabel.set(item.normalizedLabel, [...(variantByLabel.get(item.normalizedLabel) ?? []), item]);
  for (const live of liveObjects) liveByLabel.set(live.normalizedLabel, [...(liveByLabel.get(live.normalizedLabel) ?? []), live]);

  const labels = new Set([...variantByLabel.keys(), ...liveByLabel.keys()]);
  const rows: GraphReviewVariantInventoryRow[] = [];
  for (const label of labels) {
    const variants = variantByLabel.get(label) ?? [];
    const lives = liveByLabel.get(label) ?? [];
    const uncertain = variants.length > 1 || lives.length > 1;
    if (!variants.length) {
      for (const live of lives) rows.push({ rowId: `live:${live.object_id}`, status: uncertain ? "comparator_uncertain" : "live_only", objectKind: liveKind(live), label: live.label, normalizedLabel: label, liveObjects: [live], summary: `Live-only ${live.object_kind} label`, evidenceSpanIds: [], anchorQuotes: [] });
      continue;
    }
    for (const item of variants) {
      const matchingLives = lives as GoldReviewObjectIndexEntry[];
      const status: GraphReviewVariantInventoryStatus = uncertain
        ? "comparator_uncertain"
        : !matchingLives.length
          ? "variant_only"
          : matchingLives.some((live) => compatible(item.kind, live))
            ? "kind_label_overlap"
            : "label_overlap";
      rows.push({
        rowId: `variant:${item.kind}:${item.key}`,
        status,
        objectKind: item.kind,
        label: item.label,
        normalizedLabel: label,
        variantNode: item.node,
        variantEdge: item.edge,
        liveObjects: matchingLives,
        summary: matchingLives.length ? `${status.replace(/_/g, " ")} with ${matchingLives.length} live candidate(s)` : `Variant-only ${item.kind}`,
        evidenceSpanIds: item.node?.evidence_span_ids ?? item.edge?.evidence_span_ids ?? [],
        anchorQuotes: item.node?.anchor_quotes ?? item.edge?.anchor_quotes ?? [],
      });
    }
  }
  for (const row of rows) countsByStatus[row.status] += 1;
  return { rows: sortRows(rows), countsByStatus, warnings };
}
