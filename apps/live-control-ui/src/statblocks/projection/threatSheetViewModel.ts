import type {
  ThreatBindingHydrationV1,
  ThreatQueryHydrationHitV1,
  ThreatQueryHydrationRequestV1,
  ThreatQueryHydrationResponseV1,
  WorldGraphProjectionRelationshipView,
} from "../../api/types";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import type { ExactGraphReferenceScope, GraphReferenceResolution } from "../../graphReference/types";
import { validateExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";

export type ThreatSheetLoadStatus =
  | "loading"
  | "ready"
  | "not_found"
  | "unavailable"
  | "integrity_failure";

export interface ThreatSheetBindingViewModel {
  relationshipEdgeId: string;
  bindingId: string | null;
  role: string | null;
  phaseKey: string | null;
  variantLabel: string | null;
  statblockId: string | null;
  revisionId: string | null;
  definitionDigest: string | null;
  hydrationStatus: ThreatBindingHydrationV1["hydrationStatus"];
  revision: StatblockRevisionResourceV1 | null;
  message: string | null;
}

export interface ThreatSheetViewModel {
  scope: ExactGraphReferenceScope | null;
  threatNodeId: string;
  label: string;
  summary: string | null;
  threatKind: string | null;
  intendedRole: string | null;
  aliases: readonly string[];
  relationships: readonly GraphObjectRelationshipViewModel[];
  bindings: readonly ThreatSheetBindingViewModel[];
  mechanicsDisposition: string;
  loadStatus: ThreatSheetLoadStatus;
  message: string | null;
}

export type ThreatSelectionTuple = {
  worldId: string;
  campaignId: string;
  scopeMode: "campaign" | "world";
  revisionId: string;
  threatNodeId: string;
};

export type ExactThreatSelectionResult =
  | { status: "ready"; hit: ThreatQueryHydrationHitV1 }
  | { status: "not_found"; message?: string | null }
  | { status: "integrity_failure"; message: string }
  | { status: "revision_mismatch"; message: string };

const SORT_AFTER = "\uffff";
const THREAT_NODE_KINDS = new Set(["threat", "creature", "npc", "monster"]);
const THREAT_NODE_ROLES = new Set(["threat", "creature", "npc", "monster"]);
const ENTITY_THREAT_ROLES = new Set(["threat", "antagonist", "creature"]);

export function normalizeGraphObjectKind(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/_/g, "-");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Runtime gate for the complete generated revision contract used by the renderer. */
export function isCompleteStatblockRevisionResource(
  value: unknown,
): value is StatblockRevisionResourceV1 {
  if (!isRecord(value)) return false;
  const definition = value.definition;
  const validationReceipt = value.validation_receipt;
  if (!isRecord(definition) || !isRecord(validationReceipt)) return false;
  const requiredDefinitionKeys = [
    "ruleset",
    "identity",
    "defenses",
    "vitality",
    "movement",
    "abilities",
    "proficiencies",
    "senses",
    "communication",
    "challenge",
    "rule_elements",
  ];
  return (
    typeof value.statblock_id === "string"
    && typeof value.revision_id === "string"
    && value.contract === "dungeonmind.dungeonbuddy-statblocks"
    && value.contract_version === "1.0.0"
    && typeof value.canonical_definition === "string"
    && value.canonical_definition.length >= 2
    && typeof value.definition_digest === "string"
    && typeof value.created_at === "string"
    && typeof validationReceipt.status === "string"
    && typeof validationReceipt.mode === "string"
    && typeof validationReceipt.validator_version === "string"
    && typeof validationReceipt.canonicalizer_version === "string"
    && typeof validationReceipt.definition_digest === "string"
    && validationReceipt.definition_digest === value.definition_digest
    && requiredDefinitionKeys.every((key) => isRecord(definition[key]))
    && Array.isArray(definition.rule_elements)
  );
}

export function isExactResolvedThreat(resolution: GraphReferenceResolution): boolean {
  return (
    isResolvedThreat(resolution)
    && resolution.kind === "resolved_graph"
    && validateExactGraphReferenceScope(resolution.graphScope)
  );
}

export function isResolvedThreat(resolution: GraphReferenceResolution): boolean {
  if (resolution.kind !== "resolved_graph") return false;
  const kind = normalizeGraphObjectKind(resolution.graphObject.kind);
  const role = normalizeGraphObjectKind(resolution.graphObject.role);
  return (
    THREAT_NODE_KINDS.has(kind)
    || THREAT_NODE_ROLES.has(role)
    || (kind === "entity" && ENTITY_THREAT_ROLES.has(role))
  );
}

export function threatSelectionTupleFromResolution(
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>,
): ThreatSelectionTuple | null {
  if (!validateExactGraphReferenceScope(resolution.graphScope)) return null;
  return {
    worldId: resolution.graphScope.worldId,
    campaignId: resolution.graphScope.campaignId,
    scopeMode: resolution.graphScope.scopeMode,
    revisionId: resolution.graphScope.revisionId,
    threatNodeId: resolution.graphNodeId,
  };
}

export function threatSelectionTupleKey(tuple: ThreatSelectionTuple): string {
  return `${tuple.worldId}\0${tuple.campaignId}\0${tuple.scopeMode}\0${tuple.revisionId}\0${tuple.threatNodeId}`;
}

export function buildThreatQueryHydrationRequest(
  scope: ExactGraphReferenceScope,
  threatNodeId: string,
): ThreatQueryHydrationRequestV1 {
  return {
    schema: "dmb_threat_query_hydration_request_v1",
    worldId: scope.worldId,
    campaignId: scope.campaignId,
    scopeMode: scope.scopeMode,
    revisionPin: scope.revisionId,
    queryText: threatNodeId,
    focusNodeIds: [threatNodeId],
    maxHits: 64,
    includeMechanics: true,
  };
}

export function selectExactThreatHit(
  response: ThreatQueryHydrationResponseV1,
  requestedScope: ExactGraphReferenceScope,
  selectedThreatNodeId: string,
): ExactThreatSelectionResult {
  if (
    response.worldId !== requestedScope.worldId
    || response.campaignId !== requestedScope.campaignId
    || response.scopeMode !== requestedScope.scopeMode
    || response.revisionId !== requestedScope.revisionId
  ) {
    return {
      status: "revision_mismatch",
      message:
        `Response graph scope "${response.worldId}/${response.campaignId}/${response.scopeMode}/${response.revisionId}" `
        + `does not match requested scope "${requestedScope.worldId}/${requestedScope.campaignId}/${requestedScope.scopeMode}/${requestedScope.revisionId}".`,
    };
  }

  const matches = response.hits.filter((hit) => hit.threat.nodeId === selectedThreatNodeId);
  if (matches.length === 0) {
    return { status: "not_found", message: response.message };
  }
  if (matches.length > 1) {
    return {
      status: "integrity_failure",
      message: `Multiple exact Threat matches for node "${selectedThreatNodeId}".`,
    };
  }
  const [hit] = matches;
  if (!hit) {
    return { status: "not_found", message: response.message };
  }
  return { status: "ready", hit };
}

function bindingSortKey(binding: ThreatSheetBindingViewModel): [string, string, string, string] {
  return [
    binding.role ?? SORT_AFTER,
    binding.phaseKey ?? SORT_AFTER,
    binding.variantLabel ?? SORT_AFTER,
    binding.bindingId ?? SORT_AFTER,
  ];
}

export function sortThreatSheetBindings(
  bindings: ThreatSheetBindingViewModel[],
): ThreatSheetBindingViewModel[] {
  return [...bindings].sort((left, right) => {
    const leftKey = bindingSortKey(left);
    const rightKey = bindingSortKey(right);
    for (let index = 0; index < leftKey.length; index += 1) {
      const delta = leftKey[index].localeCompare(rightKey[index]);
      if (delta !== 0) return delta;
    }
    return 0;
  });
}

function mapBindingHydration(binding: ThreatBindingHydrationV1): ThreatSheetBindingViewModel {
  const typedBinding = binding.binding;
  const completeRevision =
    binding.hydrationStatus === "available"
    && isCompleteStatblockRevisionResource(binding.revision);
  const hydrationStatus = completeRevision ? "available" : (
    binding.hydrationStatus === "available" ? "integrity_failure" : binding.hydrationStatus
  );
  return {
    relationshipEdgeId: binding.relationshipEdgeId,
    bindingId: binding.bindingId,
    role: binding.bindingRole ?? typedBinding?.role ?? null,
    phaseKey: typedBinding?.phaseKey ?? null,
    variantLabel: typedBinding?.variantLabel ?? null,
    statblockId: binding.statblockId,
    revisionId: binding.revisionId,
    definitionDigest: binding.definitionDigest,
    hydrationStatus,
    revision: completeRevision ? binding.revision : null,
    message: completeRevision
      ? binding.message
      : binding.hydrationStatus === "available"
        ? "Exact revision response is incomplete; mechanics were withheld."
        : binding.message,
  };
}

function otherEndpoint(
  relationship: WorldGraphProjectionRelationshipView,
  threatNodeId: string,
): string {
  return relationship.sourceNodeId === threatNodeId
    ? relationship.targetNodeId
    : relationship.sourceNodeId;
}

export function mapThreatRelationshipsToViewModels(
  relationships: WorldGraphProjectionRelationshipView[],
  threatNodeId: string,
  nodeLabels: Map<string, { label: string; kind: string }>,
  existingRelationships: readonly GraphObjectRelationshipViewModel[] = [],
): GraphObjectRelationshipViewModel[] {
  const existingById = new Map(existingRelationships.map((relationship) => [relationship.id, relationship]));
  return relationships
    .filter((relationship) => relationship.predicate !== "uses_statblock")
    .map((relationship) => {
      const targetId = otherEndpoint(relationship, threatNodeId);
      const target = nodeLabels.get(targetId);
      const existing = existingById.get(relationship.edgeId);
      if (existing) {
        return {
          ...existing,
          id: relationship.edgeId,
          targetId,
          predicate: relationship.predicate,
          direction: relationship.direction,
          evidenceRefIds: relationship.evidenceRefIds,
          sourceDomains: relationship.sourceDomains,
          sessionIds: relationship.sessionIds,
          campaignScope: relationship.campaignScope ?? null,
        };
      }
      return {
        id: relationship.edgeId,
        label: target?.label ?? relationship.label,
        predicate: relationship.predicate,
        direction: relationship.direction,
        summary: null,
        targetId,
        targetKind: target?.kind ?? null,
        evidenceRefIds: relationship.evidenceRefIds,
        sourceDomains: relationship.sourceDomains,
        sessionIds: relationship.sessionIds,
        campaignScope: relationship.campaignScope ?? null,
      };
    });
}

export function availableBindingCount(bindings: readonly ThreatSheetBindingViewModel[]): number {
  return bindings.filter((binding) => binding.hydrationStatus === "available").length;
}

export function buildThreatSheetViewModel(input: {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
  hit: ThreatQueryHydrationHitV1 | null;
  loadStatus: ThreatSheetLoadStatus;
  message?: string | null;
}): ThreatSheetViewModel {
  const scope = validateExactGraphReferenceScope(input.resolution.graphScope)
    ? input.resolution.graphScope
    : null;
  const graphObject = input.resolution.graphObject;
  const hit = input.hit;
  const nodeLabels = new Map<string, { label: string; kind: string }>();
  if (hit) {
    nodeLabels.set(hit.threat.nodeId, { label: hit.threat.label, kind: hit.threat.kind });
    for (const relationship of hit.relationships) {
      const targetId = otherEndpoint(relationship, hit.threat.nodeId);
      nodeLabels.set(targetId, {
        label: relationship.label,
        kind: relationship.predicate,
      });
    }
  }

  const relationships = hit
    ? mapThreatRelationshipsToViewModels(
        hit.relationships,
        hit.threat.nodeId,
        nodeLabels,
        graphObject.relationships ?? [],
      )
    : (graphObject.relationships ?? []);

  const bindings = hit
    ? sortThreatSheetBindings(hit.bindings.map(mapBindingHydration))
    : [];

  return {
    scope,
    threatNodeId: input.resolution.graphNodeId,
    label: graphObject.label,
    summary: graphObject.summary ?? hit?.threat.summary ?? null,
    threatKind: graphObject.kind ?? hit?.threat.kind ?? null,
    intendedRole: graphObject.role ?? hit?.threat.role ?? null,
    aliases: graphObject.aliases ?? hit?.threat.aliases ?? [],
    relationships,
    bindings,
    mechanicsDisposition: hit?.mechanicsDisposition ?? "not_requested",
    loadStatus: input.loadStatus,
    message: input.message ?? null,
  };
}

export function mapHydrationResultLabelToLoadStatus(
  resultLabel: ThreatQueryHydrationResponseV1["resultLabel"],
  selection: ExactThreatSelectionResult,
): ThreatSheetLoadStatus {
  if (selection.status === "revision_mismatch" || selection.status === "integrity_failure") {
    return "integrity_failure";
  }
  if (selection.status === "not_found") {
    return "not_found";
  }
  if (
    resultLabel === "threat_query_hydration_unavailable"
    || resultLabel === "threat_query_hydration_not_found"
  ) {
    return resultLabel === "threat_query_hydration_unavailable" ? "unavailable" : "not_found";
  }
  if (resultLabel === "threat_query_hydration_integrity_failure") {
    return "integrity_failure";
  }
  return "ready";
}
