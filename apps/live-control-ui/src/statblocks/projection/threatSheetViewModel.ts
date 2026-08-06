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
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isString);
}

function isDistance(value: unknown): boolean {
  return (
    isRecord(value)
    && isFiniteNumber(value.value)
    && (value.unit === undefined || value.unit === "feet")
  );
}

function isHitPointProfile(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const formula = value.formula;
  return (
    (value.method === "fixed" || value.method === "formula")
    && (value.displayed_average === null || isFiniteNumber(value.displayed_average))
    && (value.fixed_value === null || isFiniteNumber(value.fixed_value))
    && (
      formula === null
      || (
        isRecord(formula)
        && isFiniteNumber(formula.count)
        && isFiniteNumber(formula.die)
        && (formula.modifier === undefined || isFiniteNumber(formula.modifier))
      )
    )
  );
}

function isRuleElement(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const activation = value.activation;
  const usage = value.usage;
  const mechanic = value.mechanic;
  return (
    isString(value.key)
    && isString(value.name)
    && isString(value.rules_text)
    && isString(value.section)
    && isString(value.automation_support)
    && isRecord(activation)
    && isString(activation.kind)
    && isRecord(usage)
    && isString(usage.kind)
    && isRecord(mechanic)
    && isString(mechanic.kind)
    && (value.costs === undefined || value.costs === null || Array.isArray(value.costs))
  );
}

/** Defense-in-depth renderer gate; the backend validates the full generated model. */
export function isCompleteStatblockRevisionResource(
  value: unknown,
): value is StatblockRevisionResourceV1 {
  if (!isRecord(value)) return false;
  const definition = value.definition;
  const validationReceipt = value.validation_receipt;
  if (!isRecord(definition) || !isRecord(validationReceipt)) return false;
  const ruleset = definition.ruleset;
  const identity = definition.identity;
  const defenses = definition.defenses;
  const vitality = definition.vitality;
  const movement = definition.movement;
  const abilities = definition.abilities;
  const proficiencies = definition.proficiencies;
  const senses = definition.senses;
  const communication = definition.communication;
  const challenge = definition.challenge;
  const armorClasses = isRecord(defenses) ? defenses.armor_classes : null;
  const movementModes = isRecord(movement) ? movement.modes : null;
  const hitPoints = isRecord(vitality) ? vitality.hit_points : null;
  const issueList = validationReceipt.issues;
  return (
    isString(value.statblock_id)
    && isString(value.revision_id)
    && value.contract === "dungeonmind.dungeonbuddy-statblocks"
    && value.contract_version === "1.0.0"
    && isString(value.canonical_definition)
    && value.canonical_definition.length >= 2
    && isString(value.definition_digest)
    && isString(value.created_at)
    && isString(validationReceipt.status)
    && isString(validationReceipt.mode)
    && isString(validationReceipt.validator_version)
    && isString(validationReceipt.canonicalizer_version)
    && isString(validationReceipt.definition_digest)
    && validationReceipt.definition_digest === value.definition_digest
    && (
      issueList === undefined
      || issueList === null
      || (
        Array.isArray(issueList)
        && issueList.every((issue) => (
          isRecord(issue)
          && isString(issue.code)
          && isString(issue.field_path)
          && isString(issue.message)
          && isString(issue.severity)
        ))
      )
    )
    && isRecord(ruleset)
    && isString(ruleset.system)
    && isString(ruleset.edition)
    && isRecord(identity)
    && isString(identity.name)
    && isString(identity.size)
    && isString(identity.creature_type)
    && (identity.subtypes === undefined || identity.subtypes === null || isStringArray(identity.subtypes))
    && isRecord(defenses)
    && Array.isArray(armorClasses)
    && armorClasses.length > 0
    && armorClasses.every((armorClass) => (
      isRecord(armorClass)
      && isString(armorClass.key)
      && isFiniteNumber(armorClass.value)
      && typeof armorClass.default === "boolean"
    ))
    && isRecord(vitality)
    && isHitPointProfile(hitPoints)
    && isRecord(movement)
    && Array.isArray(movementModes)
    && movementModes.length > 0
    && movementModes.every((mode) => (
      isRecord(mode)
      && isString(mode.key)
      && isString(mode.mode)
      && isDistance(mode.distance)
      && (mode.qualifiers === undefined || mode.qualifiers === null || isStringArray(mode.qualifiers))
    ))
    && isRecord(abilities)
    && ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
      .every((ability) => isFiniteNumber(abilities[ability]))
    && isRecord(proficiencies)
    && (proficiencies.saving_throws === undefined
      || proficiencies.saving_throws === null
      || Array.isArray(proficiencies.saving_throws))
    && (proficiencies.skills === undefined
      || proficiencies.skills === null
      || Array.isArray(proficiencies.skills))
    && isRecord(senses)
    && isFiniteNumber(senses.passive_perception)
    && (senses.senses === undefined || senses.senses === null || Array.isArray(senses.senses))
    && isRecord(communication)
    && (communication.languages === undefined
      || communication.languages === null
      || isStringArray(communication.languages))
    && (communication.special_modes === undefined
      || communication.special_modes === null
      || isStringArray(communication.special_modes))
    && (communication.telepathy_range === undefined
      || communication.telepathy_range === null
      || isDistance(communication.telepathy_range))
    && isRecord(challenge)
    && isString(challenge.rating)
    && isFiniteNumber(challenge.proficiency_bonus)
    && Array.isArray(definition.rule_elements)
    && definition.rule_elements.length > 0
    && definition.rule_elements.every(isRuleElement)
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

/** Chip-hover parchment card: authored Threat identity, not every creature/npc node. */
export function isThreatHoverPresentation(input: {
  nodeId: string;
  kind?: string | null;
  role?: string | null;
}): boolean {
  const kind = normalizeGraphObjectKind(input.kind);
  const role = normalizeGraphObjectKind(input.role);
  if (kind === "threat" || role === "threat") return true;
  return String(input.nodeId ?? "").startsWith("threat:");
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

export function mapBindingHydration(binding: ThreatBindingHydrationV1): ThreatSheetBindingViewModel {
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

function recomputeMechanicsDisposition(
  bindings: readonly ThreatSheetBindingViewModel[],
): string {
  if (!bindings.length) return "no_binding";
  const effective = new Set(
    bindings
      .map((binding) => binding.hydrationStatus)
      .filter((status) => status !== "not_requested"),
  );
  if (!effective.size) return "not_requested";
  if (effective.size === 1 && effective.has("available")) return "hydrated";

  const hasAvailable = effective.has("available");
  const hasUnavailable = effective.has("unavailable");
  const hasMissing = effective.has("exact_revision_missing");
  const hasIntegrityFailure = effective.has("integrity_failure");
  if (hasIntegrityFailure && !hasAvailable && !hasUnavailable && !hasMissing) {
    return "integrity_failure";
  }
  if (hasAvailable) return "partial";
  if ([...effective].every((status) => status === "unavailable" || status === "exact_revision_missing")) {
    return "unavailable";
  }
  if (hasIntegrityFailure) return "integrity_failure";
  return "unavailable";
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
  const frontendIntegrityFailure = bindings.some(
    (binding) => binding.hydrationStatus === "integrity_failure",
  );
  const mechanicsDisposition = hit
    ? recomputeMechanicsDisposition(bindings)
    : "not_requested";

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
    mechanicsDisposition,
    loadStatus: frontendIntegrityFailure ? "integrity_failure" : input.loadStatus,
    message: input.message
      ?? (
        frontendIntegrityFailure
          ? "One or more exact revision payloads failed complete contract validation."
          : null
      ),
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
