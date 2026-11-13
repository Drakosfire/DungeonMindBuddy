import type { NativeAssertion, NativeGraphCatalog } from "../api/nativeGraphInspection";
import type { NativeGraph } from "./nativeGraphDemoApi";
import { nativeGraphPresentation } from "./nativeGraphPresentation";

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function field(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function describePoint(value: unknown): string {
  const point = record(value);
  return field(point.raw_expression) || field(point.value) || field(point.session_id);
}

function occurrenceLabel(value: unknown): string {
  const occurrence = record(value);
  if (occurrence.kind === "point") return describePoint(occurrence.point);
  if (occurrence.kind !== "interval") return "";
  const start = describePoint(occurrence.start);
  const end = describePoint(occurrence.end);
  return field(occurrence.raw_expression) || (start && end ? `${start} to ${end}` : start || end);
}

export function buildGraphChronology(graph: NativeGraph, catalogue: NativeGraphCatalog) {
  const assertionsByEntity = new Map<string, NativeAssertion[]>();
  for (const assertion of catalogue.assertions) {
    const assertions = assertionsByEntity.get(assertion.subject_entity_id);
    if (assertions) assertions.push(assertion);
    else assertionsByEntity.set(assertion.subject_entity_id, [assertion]);
  }

  const campaigns = new Set(graph.nodes
    .filter(node => node.presentation?.classification_terms.length === 1
      && node.presentation.classification_terms[0] === "dungeonbuddy:campaign")
    .map(node => node.id));

  return graph.nodes.filter(node => nativeGraphPresentation(node).displayKind === "event").map(node => {
    const assertions = assertionsByEntity.get(node.id) ?? [];
    const occurrences = new Set<string>();
    const sourceSessions = new Set<string>();
    const campaignIds = new Set<string>();
    const placements: NativeAssertion[] = [];
    const placementSessions = new Map<string, Set<number>>();
    for (const assertion of assertions) {
      const temporal = record(assertion.metadata.temporal_scope);
      if (assertion.predicate === "dungeonbuddy.custom:on_timeline"
        && assertion.value.kind === "entity_ref" && campaigns.has(assertion.value.entity_id)) {
        const campaignId = assertion.value.entity_id;
        campaignIds.add(campaignId);
        placements.push(assertion);
        const session = record(record(temporal.payload).start).session;
        if (assertion.metadata.claim_mode === "dungeonbuddy.claim:observed_event"
          && temporal.schema === "dungeonbuddy.time:fictional_anchor_v1"
          && typeof session === "number" && Number.isSafeInteger(session) && session > 0) {
          const sessions = placementSessions.get(campaignId) ?? new Set<number>();
          sessions.add(session);
          placementSessions.set(campaignId, sessions);
        }
      }
      if (temporal.schema === "dmb_temporal_envelope_v1") {
        const label = occurrenceLabel(temporal.occurrence_time);
        if (label) occurrences.add(label);
      }
      const session = field(record(temporal.source_time).session_id) || field(temporal.session_id);
      if (session) sourceSessions.add(session);
    }
    return {
      node, assertions, placements, placementSessions, campaignIds: [...campaignIds],
      occurrences: [...occurrences], sourceSessions: [...sourceSessions],
    };
  });
}
