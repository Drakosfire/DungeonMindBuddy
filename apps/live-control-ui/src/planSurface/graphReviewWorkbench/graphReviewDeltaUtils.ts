import type {
  GoldReviewCompareResponse,
  GoldReviewObjectIndexEntry,
  GraphReviewLane,
  GraphReviewLaneRole,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import type {
  GraphReviewContextualDelta,
  GraphReviewDeltaIndex,
  GraphReviewDeltaObjectKind,
  GraphReviewDeltaStatus,
  GraphReviewLaneObjectRef,
} from "./graphReviewDeltaTypes";
import { GRAPH_REVIEW_DELTA_OBJECT_KINDS, GRAPH_REVIEW_DELTA_STATUSES } from "./graphReviewDeltaTypes";

export interface BuildGraphReviewDeltaIndexInput {
  compare: GoldReviewCompareResponse | null;
  liveProjection: UnionSupergraphProjectionResponse | null;
  goldLane: GraphReviewLane | null;
  liveLane: GraphReviewLane | null;
}

const STATUS_SORT: GraphReviewDeltaStatus[] = [
  "comparator_uncertain",
  "gold_only",
  "live_only",
  "matched",
  "changed_type",
  "changed_label",
  "changed_evidence",
  "changed_edges",
];

function emptyCounts<T extends string>(values: T[]): Record<T, number> {
  return Object.fromEntries(values.map((value) => [value, 0])) as Record<T, number>;
}

const OBJECT_KIND_ALIASES: Record<string, GraphReviewDeltaObjectKind> = {
  node: "node",
  nodes: "node",
  edge: "edge",
  edges: "edge",
  mention: "mention",
  mentions: "mention",
  source_span: "source_span",
  source_spans: "source_span",
  beat: "beat",
  beats: "beat",
  proposed_write: "write",
  proposed_writes: "write",
  write: "write",
  writes: "write",
  ignored_item: "ignored_item",
  ignored_items: "ignored_item",
  deferred_item: "deferred_item",
  deferred_items: "deferred_item",
};

function normalizeObjectKind(kind: string | null | undefined, warnings: string[]): GraphReviewDeltaObjectKind {
  const normalized = kind ? OBJECT_KIND_ALIASES[kind] : undefined;
  if (normalized) return normalized;
  warnings.push(`Unknown object kind ${kind || "(missing)"}; normalized to unknown.`);
  return "unknown";
}

function objectKey(objectKind: GraphReviewDeltaObjectKind, objectId: string): string {
  return `${objectKind}:${objectId}`;
}

function unique(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value && value.trim()))));
}

function payloadSpanRefs(payload: Record<string, unknown> | undefined): string[] {
  if (!payload) return [];
  const refs: string[] = [];
  for (const key of ["source_span_ref_id", "source_span_refs", "source_span_ref_ids", "evidence_span_ids"] as const) {
    const value = payload[key];
    if (typeof value === "string") refs.push(value);
    if (Array.isArray(value)) refs.push(...value.filter((item): item is string => typeof item === "string"));
  }
  for (const key of ["evidence_refs", "evidence"] as const) {
    const value = payload[key];
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item && typeof item === "object" && "source_span_ref_id" in item) {
          const spanId = (item as { source_span_ref_id?: unknown }).source_span_ref_id;
          if (typeof spanId === "string") refs.push(spanId);
        }
      }
    }
  }
  return unique(refs);
}

function payloadEvidenceRefs(payload: Record<string, unknown> | undefined): string[] {
  if (!payload) return [];
  const direct = payload.evidence_ref_ids ?? payload.evidence_refs;
  if (Array.isArray(direct)) return unique(direct.map((item) => (typeof item === "string" ? item : null)));
  return [];
}

export function buildLiveProjectionNodeSpanIndex(
  projection: UnionSupergraphProjectionResponse | null,
): Map<string, string[]> {
  const index = new Map<string, string[]>();
  for (const node of Object.values(projection?.node_views ?? {})) {
    index.set(
      node.node_id,
      unique(node.evidence_badges.map((badge) => badge.source_span_ref_id)),
    );
  }
  return index;
}

function refFor(
  lane: GraphReviewLane | null,
  laneRole: GraphReviewLaneRole,
  entry: GoldReviewObjectIndexEntry,
  objectKind: GraphReviewDeltaObjectKind,
  score?: number | null,
): GraphReviewLaneObjectRef {
  return {
    laneId: lane?.laneId ?? laneRole,
    laneRole,
    objectKind,
    objectId: entry.object_id,
    label: entry.label,
    matchScore: score ?? null,
  };
}

function deltaSummary(
  status: GraphReviewDeltaStatus,
  objectKind: GraphReviewDeltaObjectKind,
  label: string | null | undefined,
  reason?: string | null,
): string {
  if (status === "comparator_uncertain") return `Comparator uncertain: ${reason ?? "structurally suspicious comparison data"}`;
  const prefix = status === "gold_only" ? "Gold-only" : status === "live_only" ? "Live-only" : "Matched";
  return `${prefix} ${objectKind}: ${label || "unlabeled object"}`;
}

function makeDelta(args: {
  status: GraphReviewDeltaStatus;
  objectKind: GraphReviewDeltaObjectKind;
  label?: string | null;
  refs: GraphReviewLaneObjectRef[];
  sourceSpanRefIds?: string[];
  evidenceRefIds?: string[];
  comparatorReason?: string | null;
  metadata?: Record<string, string | number | boolean | null>;
}): GraphReviewContextualDelta {
  const refPart = args.refs.map((ref) => `${ref.laneRole}:${ref.objectKind}:${ref.objectId}`).join("|") || "no-ref";
  const reasonPart = args.comparatorReason ? `:${args.comparatorReason}` : "";
  const deltaId = `${args.status}:${args.objectKind}:${refPart}${reasonPart}`;
  const sourceSpanRefIds = unique(args.sourceSpanRefIds ?? []);
  return {
    deltaId,
    objectKind: args.objectKind,
    status: args.status,
    laneObjectRefs: args.refs,
    label: args.label ?? null,
    summary: deltaSummary(args.status, args.objectKind, args.label, args.comparatorReason),
    comparatorReason: args.comparatorReason ?? null,
    sourceSpanRefIds,
    primarySourceSpanRefId: sourceSpanRefIds[0] ?? null,
    evidenceRefIds: unique(args.evidenceRefIds ?? []),
    confidence: args.status === "comparator_uncertain" ? "low" : "high",
    metadata: args.metadata,
  };
}

export function buildGraphReviewDeltaIndex(input: BuildGraphReviewDeltaIndexInput): GraphReviewDeltaIndex {
  const warnings: string[] = [];
  const base = {
    schemaVersion: "dmb_graph_review_contextual_delta_index_v1" as const,
    campaignId: input.compare?.campaign_id ?? input.goldLane?.campaignId ?? input.liveLane?.campaignId ?? "",
    sessionId: input.compare?.session_id ?? input.goldLane?.sessionId ?? input.liveLane?.sessionId ?? "",
    goldLaneId: input.goldLane?.laneId ?? null,
    liveLaneId: input.liveLane?.laneId ?? null,
    liveRunManifestPath: input.liveLane?.manifestPath ?? input.compare?.live_run?.manifest_path ?? null,
  };
  const countsByStatus = emptyCounts(GRAPH_REVIEW_DELTA_STATUSES);
  const countsByObjectKind = emptyCounts(GRAPH_REVIEW_DELTA_OBJECT_KINDS);
  if (!input.compare) {
    return { ...base, deltas: [], countsByStatus, countsByObjectKind, warnings: ["Comparison is not loaded yet."] };
  }

  const liveSpanIndex = buildLiveProjectionNodeSpanIndex(input.liveProjection);
  const goldObjects = new Map<string, GoldReviewObjectIndexEntry>();
  const liveObjects = new Map<string, GoldReviewObjectIndexEntry>();
  for (const entry of Object.values(input.compare.object_index.gold ?? {})) {
    goldObjects.set(objectKey(normalizeObjectKind(entry.object_kind, warnings), entry.object_id), entry);
  }
  for (const entry of Object.values(input.compare.object_index.live ?? {})) {
    liveObjects.set(objectKey(normalizeObjectKind(entry.object_kind, warnings), entry.object_id), entry);
  }

  const deltas: GraphReviewContextualDelta[] = [];
  const matchedGold = new Set<string>();
  const matchedLive = new Set<string>();
  const seenGold = new Set<string>();
  const seenLive = new Set<string>();

  for (const [rawKind, pairs] of Object.entries(input.compare.match_pairs ?? {})) {
    const objectKind = normalizeObjectKind(rawKind, warnings);
    for (const pair of pairs) {
      const goldKey = objectKey(objectKind, pair.gold_id);
      const liveKey = objectKey(objectKind, pair.live_id);
      const gold = goldObjects.get(goldKey);
      const live = liveObjects.get(liveKey);
      const reasons: string[] = [];
      if (!gold) reasons.push(`pair references missing gold object ${pair.gold_id}`);
      if (!live) reasons.push(`pair references missing live object ${pair.live_id}`);
      if (seenGold.has(goldKey)) reasons.push(`duplicate gold object paired to multiple live objects ${pair.gold_id}`);
      if (seenLive.has(liveKey)) reasons.push(`duplicate live object paired to multiple gold objects ${pair.live_id}`);
      if (objectKind === "unknown") reasons.push(`unknown object kind ${rawKind || "(missing)"}`);
      seenGold.add(goldKey);
      seenLive.add(liveKey);
      if (reasons.length) {
        deltas.push(makeDelta({ status: "comparator_uncertain", objectKind, label: gold?.label ?? live?.label ?? pair.live_id, refs: [], comparatorReason: reasons.join("; ") }));
        continue;
      }
      matchedGold.add(goldKey);
      matchedLive.add(liveKey);
      const sourceSpanRefIds = unique([
        ...((objectKind === "node" && live) ? liveSpanIndex.get(live.object_id) ?? [] : []),
        ...payloadSpanRefs(live?.payload),
        ...payloadSpanRefs(gold?.payload),
      ]);
      deltas.push(makeDelta({
        status: "matched",
        objectKind,
        label: live?.label ?? gold?.label,
        refs: [refFor(input.goldLane, "gold", gold!, objectKind, pair.score), refFor(input.liveLane, "live", live!, objectKind, pair.score)],
        sourceSpanRefIds,
        evidenceRefIds: unique([...payloadEvidenceRefs(live?.payload), ...payloadEvidenceRefs(gold?.payload)]),
        metadata: { matchScore: pair.score },
      }));
    }
  }

  for (const [key, entry] of goldObjects) {
    if (matchedGold.has(key)) continue;
    const objectKind = normalizeObjectKind(entry.object_kind, warnings);
    deltas.push(makeDelta({ status: "gold_only", objectKind, label: entry.label, refs: [refFor(input.goldLane, "gold", entry, objectKind)], sourceSpanRefIds: payloadSpanRefs(entry.payload), evidenceRefIds: payloadEvidenceRefs(entry.payload) }));
  }
  for (const [key, entry] of liveObjects) {
    if (matchedLive.has(key)) continue;
    const objectKind = normalizeObjectKind(entry.object_kind, warnings);
    const sourceSpanRefIds = unique([...((objectKind === "node") ? liveSpanIndex.get(entry.object_id) ?? [] : []), ...payloadSpanRefs(entry.payload)]);
    deltas.push(makeDelta({ status: "live_only", objectKind, label: entry.label, refs: [refFor(input.liveLane, "live", entry, objectKind)], sourceSpanRefIds, evidenceRefIds: payloadEvidenceRefs(entry.payload) }));
  }

  deltas.sort((a, b) =>
    STATUS_SORT.indexOf(a.status) - STATUS_SORT.indexOf(b.status) ||
    GRAPH_REVIEW_DELTA_OBJECT_KINDS.indexOf(a.objectKind) - GRAPH_REVIEW_DELTA_OBJECT_KINDS.indexOf(b.objectKind) ||
    (a.label ?? "").localeCompare(b.label ?? "") ||
    a.deltaId.localeCompare(b.deltaId),
  );
  for (const delta of deltas) {
    countsByStatus[delta.status] += 1;
    countsByObjectKind[delta.objectKind] += 1;
  }
  return { ...base, deltas, countsByStatus, countsByObjectKind, warnings: unique(warnings) };
}
