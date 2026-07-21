import type { GraphAuthoringSelection } from "./graphAuthoringSelection";

export type GraphObjectAuthoringVisibility =
  | "gm_private"
  | "table_known"
  | "player_visible"
  | "character_specific"
  | "hidden_until_revealed";

export type GraphObjectAuthoringScope =
  | "recap_graph"
  | "campaign_memory_graph"
  | "gm_private_graph"
  | "player_visible_graph";

export interface GraphObjectAuthoringVisibilityOption {
  value: GraphObjectAuthoringVisibility;
  label: string;
  note?: string;
}

export const GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS: GraphObjectAuthoringVisibilityOption[] = [
  {
    value: "gm_private",
    label: "GM private",
    note: "Only the GM should see this. Safest default for prep, secrets, and uncertain memory.",
  },
  {
    value: "table_known",
    label: "Table known",
    note: "The table knows this in play, but it is not necessarily intended for future player-facing tools yet.",
  },
  {
    value: "player_visible",
    label: "Player visible",
    note: "Safe to show in future player-facing views.",
  },
  {
    value: "character_specific",
    label: "Character-specific",
    note: "Targeting specific characters will be implemented later.",
  },
  {
    value: "hidden_until_revealed",
    label: "Hidden until revealed",
    note: "Keep hidden until a future reveal state marks it safe.",
  },
];

export function friendlyVisibilityLabel(
  visibility: GraphObjectAuthoringVisibility | string,
): string {
  const option = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (candidate) => candidate.value === visibility,
  );
  return option?.label ?? visibility;
}

export const GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY: GraphObjectAuthoringVisibility = "gm_private";

export const GRAPH_OBJECT_AUTHORING_KIND_OPTIONS: string[] = [
  "party",
  "npc",
  "location",
  "faction",
  "object",
  "thread",
  "threat",
  "event",
  "concept",
  "unknown",
];

export interface GraphObjectAuthoringFormState {
  label: string;
  kind: string;
  role: string;
  aliasesText: string;
  summary: string;
  operatorNote: string;
  visibility: GraphObjectAuthoringVisibility;
}

interface GraphObjectAuthoringVisibilityPreview {
  visibility: GraphObjectAuthoringVisibility;
  revealState: "unrevealed" | "partial" | "revealed";
  visibilityNote?: string | null;
}

interface GraphObjectAuthoringProvenancePreview {
  origin: "human_authored";
  authoringSurface: "memory_ingest_graph_authoring";
  sourceGraphId?: string | null;
  sourceArtifactPath?: string | null;
  operatorNote?: string | null;
}

export interface GraphObjectAuthoringObjectProposal {
  localProposalId: string;
  proposalKind: "object";
  status: "staged_local";
  selection: GraphAuthoringSelection;
  objectRef: {
    label: string;
    kind: string;
    role?: string | null;
    aliases: string[];
    summary?: string | null;
  };
  visibility: GraphObjectAuthoringVisibilityPreview;
  graphScopes: GraphObjectAuthoringScope[];
  provenancePreview: GraphObjectAuthoringProvenancePreview;
}

export type GraphObjectAuthoringObjectRefKind =
  | "existing_graph_node"
  | "local_proposal"
  | "manual_ref";

export interface GraphObjectAuthoringObjectRef {
  refKind: GraphObjectAuthoringObjectRefKind;
  nodeId?: string | null;
  localProposalId?: string | null;
  label: string;
  kind?: string | null;
  role?: string | null;
  graphScope?: string | null;
  sourceLabel?: string | null;
  sourceGraphId?: string | null;
  sourcePath?: string | null;
  visibility?: string | null;
}

export type GraphObjectAuthoringLinkExistingOperation =
  | "alias"
  | "reference"
  | "link_existing";

export interface GraphObjectAuthoringLinkExistingProposal {
  localProposalId: string;
  proposalKind: "link_existing";
  status: "staged_local";
  selection: GraphAuthoringSelection;
  selectedText: string;
  normalizedSelectedText: string;
  existingObjectRef: GraphObjectAuthoringObjectRef;
  operation: GraphObjectAuthoringLinkExistingOperation;
  aliasText?: string | null;
  visibility: GraphObjectAuthoringVisibilityPreview;
  graphScopes: GraphObjectAuthoringScope[];
  provenancePreview: GraphObjectAuthoringProvenancePreview;
}

export type GraphObjectAuthoringRelationshipDirection = "directed" | "undirected";

export interface GraphObjectAuthoringRelationshipProposal {
  localProposalId: string;
  proposalKind: "relationship";
  status: "staged_local";
  selection?: GraphAuthoringSelection | null;
  sourceObjectRef: GraphObjectAuthoringObjectRef;
  targetObjectRef: GraphObjectAuthoringObjectRef;
  relationshipType: string;
  relationshipLabel?: string | null;
  direction: GraphObjectAuthoringRelationshipDirection;
  summary?: string | null;
  visibility: GraphObjectAuthoringVisibilityPreview;
  graphScopes: GraphObjectAuthoringScope[];
  provenancePreview: GraphObjectAuthoringProvenancePreview;
}

export type GraphObjectAuthoringProposal =
  | GraphObjectAuthoringObjectProposal
  | GraphObjectAuthoringLinkExistingProposal
  | GraphObjectAuthoringRelationshipProposal
  | GraphObjectAuthoringMergeProposal;

export type GraphObjectAuthoringMergeAliasPolicy = "preserve_all_aliases" | "manual";
export type GraphObjectAuthoringMergeRelationshipPolicy =
  | "preserve_all_relationships"
  | "manual_review_required";
export type GraphObjectAuthoringMergeEvidencePolicy = "preserve_all_evidence";

export interface GraphObjectAuthoringMergeProposal {
  localProposalId: string;
  proposalKind: "merge_objects";
  status: "staged_local";
  survivorObjectRef: GraphObjectAuthoringObjectRef;
  mergedObjectRefs: GraphObjectAuthoringObjectRef[];
  mergeReason: string;
  matchedFeatures: string[];
  aliasPolicy: GraphObjectAuthoringMergeAliasPolicy;
  relationshipPolicy: GraphObjectAuthoringMergeRelationshipPolicy;
  evidencePolicy: GraphObjectAuthoringMergeEvidencePolicy;
  visibility: GraphObjectAuthoringVisibilityPreview;
  graphScopes: GraphObjectAuthoringScope[];
  provenancePreview: GraphObjectAuthoringProvenancePreview;
}

export function createDefaultGraphObjectAuthoringFormState(
  selection: GraphAuthoringSelection | null,
): GraphObjectAuthoringFormState {
  return {
    label: selection?.selectedText ?? "",
    kind: "unknown",
    role: "",
    aliasesText: "",
    summary: "",
    operatorNote: "",
    visibility: GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY,
  };
}

export function parseAliasesText(aliasesText: string): string[] {
  return aliasesText
    .split(/[,\n]+/)
    .map((alias) => alias.trim())
    .filter((alias) => alias.length > 0);
}

export function dedupeAliasesCaseInsensitive(aliases: string[]): string[] {
  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const alias of aliases) {
    const key = alias.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(alias);
  }
  return deduped;
}

export function buildProposalAliases(
  formState: GraphObjectAuthoringFormState,
  selection: GraphAuthoringSelection | null,
): string[] {
  const parsed = parseAliasesText(formState.aliasesText);
  const label = formState.label.trim();
  const selectedText = selection?.selectedText.trim();
  if (selectedText && label && label.toLowerCase() !== selectedText.toLowerCase()) {
    parsed.push(selectedText);
  }
  return dedupeAliasesCaseInsensitive(parsed);
}

let localProposalCounter = 0;

export function createLocalGraphObjectProposalId(): string {
  localProposalCounter += 1;
  return `local-object-${Date.now()}-${localProposalCounter}`;
}

function buildVisibilityPreview(
  visibility: GraphObjectAuthoringVisibility,
): GraphObjectAuthoringVisibilityPreview {
  const visibilityOption = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (option) => option.value === visibility,
  );
  return {
    visibility,
    revealState: "unrevealed",
    visibilityNote: visibilityOption?.note ?? null,
  };
}

export function buildGraphObjectAuthoringProposal(
  selection: GraphAuthoringSelection,
  formState: GraphObjectAuthoringFormState,
  localProposalId: string = createLocalGraphObjectProposalId(),
): GraphObjectAuthoringObjectProposal {
  const aliases = buildProposalAliases(formState, selection);
  const label = formState.label.trim() || selection.selectedText;

  return {
    localProposalId,
    proposalKind: "object",
    status: "staged_local",
    selection,
    objectRef: {
      label,
      kind: formState.kind || "unknown",
      role: formState.role.trim() || null,
      aliases,
      summary: formState.summary.trim() || null,
    },
    visibility: buildVisibilityPreview(formState.visibility),
    graphScopes: ["recap_graph", "campaign_memory_graph"],
    provenancePreview: {
      origin: "human_authored",
      authoringSurface: "memory_ingest_graph_authoring",
      sourceGraphId: selection.graphId ?? null,
      sourceArtifactPath: selection.sourceArtifactPath ?? null,
      operatorNote: formState.operatorNote.trim() || null,
    },
  };
}

export function buildObjectRefFromObjectProposal(
  proposal: GraphObjectAuthoringObjectProposal,
): GraphObjectAuthoringObjectRef {
  return {
    refKind: "local_proposal",
    localProposalId: proposal.localProposalId,
    label: proposal.objectRef.label,
    kind: proposal.objectRef.kind,
    role: proposal.objectRef.role ?? null,
  };
}

export function buildObjectRefFromInspectedNode(node: {
  node_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
  graphScope?: string | null;
  sourceLabel?: string | null;
  sourceGraphId?: string | null;
  sourcePath?: string | null;
  visibility?: string | null;
}): GraphObjectAuthoringObjectRef {
  return {
    refKind: "existing_graph_node",
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind ?? null,
    role: node.role ?? null,
    graphScope: node.graphScope ?? null,
    sourceLabel: node.sourceLabel ?? null,
    sourceGraphId: node.sourceGraphId ?? null,
    sourcePath: node.sourcePath ?? null,
    visibility: node.visibility ?? null,
  };
}

export function buildObjectRefFromResolverCandidate(
  candidate: {
    candidate_id: string;
    label: string;
    kind?: string | null;
    role?: string | null;
    graph_scope?: string | null;
    source_label?: string | null;
    source_graph_id?: string | null;
    source_path?: string | null;
    visibility?: string | null;
    existing_object_ref?: Record<string, string> | null;
  },
): GraphObjectAuthoringObjectRef {
  // Prefer the server-provided bind target. Display candidate_id is not always
  // the durable graph identity (e.g. legacy party: display keys).
  const canonicalObjectId = candidate.existing_object_ref?.object_id?.trim();
  return {
    refKind: "existing_graph_node",
    nodeId: canonicalObjectId || candidate.candidate_id,
    label: candidate.label,
    kind: candidate.kind ?? null,
    role: candidate.role ?? null,
    graphScope: candidate.graph_scope ?? null,
    sourceLabel: candidate.source_label ?? null,
    sourceGraphId: candidate.source_graph_id ?? null,
    sourcePath: candidate.source_path ?? null,
    visibility: candidate.visibility ?? null,
  };
}

export function buildManualObjectRef(label: string): GraphObjectAuthoringObjectRef {
  return {
    refKind: "manual_ref",
    label: label.trim(),
  };
}

export function isValidObjectRef(
  ref: GraphObjectAuthoringObjectRef | null | undefined,
): ref is GraphObjectAuthoringObjectRef {
  return Boolean(ref && ref.label.trim().length > 0);
}

export const GRAPH_OBJECT_AUTHORING_LINK_EXISTING_OPERATION_OPTIONS: {
  value: GraphObjectAuthoringLinkExistingOperation;
  label: string;
}[] = [
  { value: "alias", label: "Alias of existing object" },
  { value: "reference", label: "Reference to existing object" },
  { value: "link_existing", label: "Link existing object" },
];

export interface GraphObjectAuthoringLinkExistingFormState {
  existingObjectRef: GraphObjectAuthoringObjectRef | null;
  operation: GraphObjectAuthoringLinkExistingOperation;
  aliasText: string;
  operatorNote: string;
  visibility: GraphObjectAuthoringVisibility;
}

export function createDefaultGraphObjectAuthoringLinkExistingFormState(): GraphObjectAuthoringLinkExistingFormState {
  return {
    existingObjectRef: null,
    operation: "alias",
    aliasText: "",
    operatorNote: "",
    visibility: GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY,
  };
}

export function buildGraphObjectAuthoringLinkExistingProposal(
  selection: GraphAuthoringSelection,
  formState: GraphObjectAuthoringLinkExistingFormState,
  localProposalId: string = createLocalGraphObjectProposalId(),
): GraphObjectAuthoringLinkExistingProposal | null {
  if (!isValidObjectRef(formState.existingObjectRef)) {
    return null;
  }

  return {
    localProposalId,
    proposalKind: "link_existing",
    status: "staged_local",
    selection,
    selectedText: selection.selectedText,
    normalizedSelectedText: selection.normalizedSelectedText,
    existingObjectRef: formState.existingObjectRef,
    operation: formState.operation,
    aliasText: formState.aliasText.trim() || null,
    visibility: buildVisibilityPreview(formState.visibility),
    graphScopes: ["recap_graph", "campaign_memory_graph"],
    provenancePreview: {
      origin: "human_authored",
      authoringSurface: "memory_ingest_graph_authoring",
      sourceGraphId: selection.graphId ?? null,
      sourceArtifactPath: selection.sourceArtifactPath ?? null,
      operatorNote: formState.operatorNote.trim() || null,
    },
  };
}

export interface GraphObjectAuthoringRelationshipTypeOption {
  value: string;
  label: string;
  example: string;
  note: string;
}

export const GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS: GraphObjectAuthoringRelationshipTypeOption[] = [
  {
    value: "has_member",
    label: "has member",
    example: "Questionable Company has member Bonogo",
    note: "Use for group membership.",
  },
  {
    value: "member_of",
    label: "member of",
    example: "Bonogo member of Questionable Company",
    note: "Use when the selected source is the individual.",
  },
  {
    value: "located_in",
    label: "located in",
    example: "Fleshbarn located in North Swamp",
    note: "Use for places within places.",
  },
  {
    value: "controls",
    label: "controls",
    example: "Shepherd cult controls Fleshbarn",
    note: "Use for command, ownership, or operational control.",
  },
  {
    value: "allied_with",
    label: "allied with",
    example: "Mireward defenders allied with the party",
    note: "Use for friendly alignment.",
  },
  {
    value: "opposes",
    label: "opposes",
    example: "Questionable Company opposes Shepherd cult",
    note: "Use for active conflict.",
  },
  {
    value: "owns",
    label: "owns",
    example: "Bonogo owns silver dagger",
    note: "Use for possession.",
  },
  {
    value: "created_by",
    label: "created by",
    example: "Flesh construct created by Shepherd cult",
    note: "Use for origin or authorship.",
  },
  {
    value: "travels_with",
    label: "travels with",
    example: "NPC travels with the group",
    note: "Use for temporary party movement.",
  },
  {
    value: "protects",
    label: "protects",
    example: "Mireward defenders protect North Gate",
    note: "Use for defense or guardianship.",
  },
  {
    value: "threatens",
    label: "threatens",
    example: "Tripod Null-Calf threatens North Gate",
    note: "Use for danger or pressure.",
  },
  {
    value: "related_to",
    label: "related to",
    example: "Festival curfew related to Shepherd threat",
    note: "Use only when no clearer relationship fits.",
  },
];

export const GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_VALUES: string[] =
  GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS.map((option) => option.value);

const IDENTITY_LIKE_RELATIONSHIP_PREDICATES = new Set([
  "same_as",
  "same as",
  "alias_of",
  "duplicate_of",
  "identity",
  "equals",
  "is",
]);

export function isKnownRelationshipType(value: string): boolean {
  return GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_VALUES.includes(value);
}

export function relationshipTypeLabel(relationshipType: string): string {
  const option = GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS.find(
    (candidate) => candidate.value === relationshipType,
  );
  if (option) {
    return option.label;
  }
  return relationshipType.trim().replaceAll("_", " ");
}

export function isIdentityLikeRelationshipPredicate(relationshipType: string): boolean {
  const normalized = relationshipType.trim().toLowerCase().replaceAll("_", " ");
  const compact = normalized.replaceAll(" ", "_");
  return (
    IDENTITY_LIKE_RELATIONSHIP_PREDICATES.has(normalized) ||
    IDENTITY_LIKE_RELATIONSHIP_PREDICATES.has(compact)
  );
}

export function areSameObjectRef(
  left: GraphObjectAuthoringObjectRef | null | undefined,
  right: GraphObjectAuthoringObjectRef | null | undefined,
): boolean {
  if (!left || !right) {
    return false;
  }
  if (left.refKind === "existing_graph_node" && right.refKind === "existing_graph_node") {
    return Boolean(left.nodeId && right.nodeId && left.nodeId === right.nodeId);
  }
  if (left.refKind === "local_proposal" && right.refKind === "local_proposal") {
    return Boolean(
      left.localProposalId &&
        right.localProposalId &&
        left.localProposalId === right.localProposalId,
    );
  }
  if (left.refKind === "manual_ref" && right.refKind === "manual_ref") {
    const leftLabel = left.label.trim().toLowerCase();
    const rightLabel = right.label.trim().toLowerCase();
    return Boolean(leftLabel && rightLabel && leftLabel === rightLabel);
  }
  return false;
}

export function objectRefIdentityKey(ref: GraphObjectAuthoringObjectRef): string | null {
  if (ref.refKind === "existing_graph_node" && ref.nodeId) {
    return `node:${ref.nodeId}`;
  }
  if (ref.refKind === "local_proposal" && ref.localProposalId) {
    return `local:${ref.localProposalId}`;
  }
  if (ref.refKind === "manual_ref") {
    const label = ref.label.trim().toLowerCase();
    return label ? `manual:${label}` : null;
  }
  return null;
}

/**
 * Total identity key mirroring the backend `_object_ref_identity_key`, including
 * the `<refKind>:<label>` fallback for refs without a stable id. Used to dedupe
 * merged refs before staging so a merge that selects the same underlying record
 * twice does not produce an assertion the backend rejects for duplicate refs.
 */
export function mergeRefDedupKey(ref: GraphObjectAuthoringObjectRef): string {
  if (ref.refKind === "existing_graph_node" && ref.nodeId) {
    return `node:${ref.nodeId}`;
  }
  if (ref.refKind === "local_proposal" && ref.localProposalId) {
    return `local:${ref.localProposalId}`;
  }
  return `${ref.refKind}:${ref.label.trim().toLowerCase()}`;
}

export function mergeObjectPairKey(
  left: GraphObjectAuthoringObjectRef,
  right: GraphObjectAuthoringObjectRef,
): string | null {
  const leftKey = objectRefIdentityKey(left);
  const rightKey = objectRefIdentityKey(right);
  if (!leftKey || !rightKey || leftKey === rightKey) {
    return null;
  }
  return [leftKey, rightKey].sort().join("::");
}

export function mergeProposalPairKeys(proposal: GraphObjectAuthoringMergeProposal): string[] {
  return proposal.mergedObjectRefs
    .map((mergedRef) => mergeObjectPairKey(proposal.survivorObjectRef, mergedRef))
    .filter((key): key is string => Boolean(key));
}

export function mergeInputClusterKeys(
  survivorObjectRef: GraphObjectAuthoringObjectRef,
  mergedObjectRefs: GraphObjectAuthoringObjectRef[],
): Set<string> {
  const keys = new Set([mergeRefDedupKey(survivorObjectRef)]);
  for (const ref of mergedObjectRefs) {
    keys.add(mergeRefDedupKey(ref));
  }
  return keys;
}

export function mergeProposalsConflict(
  left: GraphObjectAuthoringMergeProposal,
  right: GraphObjectAuthoringMergeProposal,
): boolean {
  if (left.localProposalId === right.localProposalId) {
    return false;
  }
  const leftKeys = mergeInputClusterKeys(left.survivorObjectRef, left.mergedObjectRefs);
  const rightKeys = mergeInputClusterKeys(right.survivorObjectRef, right.mergedObjectRefs);
  const sharesCluster = [...leftKeys].some((key) => rightKeys.has(key));
  if (!sharesCluster) {
    return false;
  }
  return (
    mergeRefDedupKey(left.survivorObjectRef) !== mergeRefDedupKey(right.survivorObjectRef)
  );
}

export function findConflictingMergeProposal(
  survivorObjectRef: GraphObjectAuthoringObjectRef,
  mergedObjectRefs: GraphObjectAuthoringObjectRef[],
  existingProposals: GraphObjectAuthoringProposal[],
): GraphObjectAuthoringMergeProposal | null {
  const incomingKeys = mergeInputClusterKeys(survivorObjectRef, mergedObjectRefs);
  const incomingSurvivorKey = mergeRefDedupKey(survivorObjectRef);
  for (const proposal of existingProposals) {
    if (proposal.proposalKind !== "merge_objects") {
      continue;
    }
    const proposalKeys = mergeInputClusterKeys(
      proposal.survivorObjectRef,
      proposal.mergedObjectRefs,
    );
    const sharesCluster = [...incomingKeys].some((key) => proposalKeys.has(key));
    if (!sharesCluster) {
      continue;
    }
    if (mergeRefDedupKey(proposal.survivorObjectRef) !== incomingSurvivorKey) {
      return proposal;
    }
  }
  return null;
}

export function findDuplicateMergeProposal(
  survivorObjectRef: GraphObjectAuthoringObjectRef,
  mergedObjectRefs: GraphObjectAuthoringObjectRef[],
  existingProposals: GraphObjectAuthoringProposal[],
): GraphObjectAuthoringMergeProposal | null {
  const incomingKeys = new Set(
    mergedObjectRefs
      .map((mergedRef) => mergeObjectPairKey(survivorObjectRef, mergedRef))
      .filter((key): key is string => Boolean(key)),
  );
  if (incomingKeys.size === 0) {
    return null;
  }

  for (const proposal of existingProposals) {
    if (proposal.proposalKind !== "merge_objects") {
      continue;
    }
    for (const key of mergeProposalPairKeys(proposal)) {
      if (incomingKeys.has(key)) {
        return proposal;
      }
    }
  }
  return null;
}

export function stagedMergePairKeys(proposals: GraphObjectAuthoringProposal[]): Set<string> {
  const keys = new Set<string>();
  for (const proposal of proposals) {
    if (proposal.proposalKind !== "merge_objects") {
      continue;
    }
    for (const key of mergeProposalPairKeys(proposal)) {
      keys.add(key);
    }
  }
  return keys;
}

export function formatAuthoringRelationshipStatement(
  sourceLabel: string,
  targetLabel: string,
  relationshipType: string,
  options: {
    relationshipLabel?: string | null;
    direction?: GraphObjectAuthoringRelationshipDirection;
  } = {},
): string {
  const predicate = options.relationshipLabel?.trim() || relationshipTypeLabel(relationshipType);
  if (options.direction === "undirected") {
    return `${sourceLabel} related to ${targetLabel}`;
  }
  return `${sourceLabel} ${predicate} ${targetLabel}`;
}

export function relationshipPreviewCopy(
  formState: GraphObjectAuthoringRelationshipFormState,
): string {
  const sourceLabel = formState.sourceObjectRef?.label.trim();
  const targetLabel = formState.targetObjectRef?.label.trim();
  const relationshipType = formState.relationshipType.trim();

  if (!sourceLabel || !targetLabel) {
    return "Choose two objects to preview the relationship.";
  }
  if (!relationshipType) {
    return "Choose a relationship type to preview the statement.";
  }

  return formatAuthoringRelationshipStatement(sourceLabel, targetLabel, relationshipType, {
    relationshipLabel: formState.relationshipLabel,
    direction: formState.direction,
  });
}

export function canStageRelationshipForm(
  formState: GraphObjectAuthoringRelationshipFormState,
): boolean {
  return (
    isValidObjectRef(formState.sourceObjectRef) &&
    isValidObjectRef(formState.targetObjectRef) &&
    Boolean(formState.relationshipType.trim()) &&
    !areSameObjectRef(formState.sourceObjectRef, formState.targetObjectRef)
  );
}

export interface GraphObjectAuthoringRelationshipFormState {
  sourceObjectRef: GraphObjectAuthoringObjectRef | null;
  targetObjectRef: GraphObjectAuthoringObjectRef | null;
  relationshipType: string;
  relationshipLabel: string;
  direction: GraphObjectAuthoringRelationshipDirection;
  summary: string;
  operatorNote: string;
  visibility: GraphObjectAuthoringVisibility;
}

export function createDefaultGraphObjectAuthoringRelationshipFormState(): GraphObjectAuthoringRelationshipFormState {
  return {
    sourceObjectRef: null,
    targetObjectRef: null,
    relationshipType: GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_VALUES[0],
    relationshipLabel: "",
    direction: "directed",
    summary: "",
    operatorNote: "",
    visibility: GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY,
  };
}

export function buildGraphObjectAuthoringRelationshipProposal(
  formState: GraphObjectAuthoringRelationshipFormState,
  selection: GraphAuthoringSelection | null = null,
  localProposalId: string = createLocalGraphObjectProposalId(),
): GraphObjectAuthoringRelationshipProposal | null {
  if (!canStageRelationshipForm(formState)) {
    return null;
  }

  return {
    localProposalId,
    proposalKind: "relationship",
    status: "staged_local",
    selection,
    sourceObjectRef: formState.sourceObjectRef,
    targetObjectRef: formState.targetObjectRef,
    relationshipType: formState.relationshipType,
    relationshipLabel: formState.relationshipLabel.trim() || null,
    direction: formState.direction,
    summary: formState.summary.trim() || null,
    visibility: buildVisibilityPreview(formState.visibility),
    graphScopes: ["recap_graph", "campaign_memory_graph"],
    provenancePreview: {
      origin: "human_authored",
      authoringSurface: "memory_ingest_graph_authoring",
      sourceGraphId: selection?.graphId ?? null,
      sourceArtifactPath: selection?.sourceArtifactPath ?? null,
      operatorNote: formState.operatorNote.trim() || null,
    },
  };
}

export function serializeGraphObjectAuthoringObjectRefForApi(
  ref: GraphObjectAuthoringObjectRef,
): Record<string, unknown> {
  return {
    refKind: ref.refKind,
    nodeId: ref.nodeId ?? null,
    localProposalId: ref.localProposalId ?? null,
    label: ref.label,
    kind: ref.kind ?? null,
    role: ref.role ?? null,
    graphScope: ref.graphScope ?? null,
    sourceLabel: ref.sourceLabel ?? null,
    sourceGraphId: ref.sourceGraphId ?? null,
    sourcePath: ref.sourcePath ?? null,
    visibility: ref.visibility ?? null,
  };
}

export function buildGraphObjectAuthoringMergeProposal(input: {
  survivorObjectRef: GraphObjectAuthoringObjectRef;
  mergedObjectRefs: GraphObjectAuthoringObjectRef[];
  mergeReason: string;
  matchedFeatures: string[];
  operatorNote?: string;
  sourceGraphId?: string | null;
  localProposalId?: string;
}): GraphObjectAuthoringMergeProposal | null {
  if (
    !isValidObjectRef(input.survivorObjectRef) ||
    input.mergedObjectRefs.length === 0 ||
    !input.mergedObjectRefs.every(isValidObjectRef)
  ) {
    return null;
  }

  // Drop refs that collide with the survivor and de-duplicate the remainder by
  // backend-parity identity key. Selecting the same underlying record twice (or a
  // duplicate that resolves to the survivor) would otherwise build an assertion the
  // backend rejects with "merged_object_refs cannot contain duplicate refs".
  const survivorKey = mergeRefDedupKey(input.survivorObjectRef);
  const seenMergedKeys = new Set<string>();
  const dedupedMergedRefs: GraphObjectAuthoringObjectRef[] = [];
  for (const ref of input.mergedObjectRefs) {
    const key = mergeRefDedupKey(ref);
    if (key === survivorKey || seenMergedKeys.has(key)) {
      continue;
    }
    seenMergedKeys.add(key);
    dedupedMergedRefs.push(ref);
  }
  if (dedupedMergedRefs.length === 0) {
    return null;
  }

  return {
    localProposalId: input.localProposalId ?? createLocalGraphObjectProposalId(),
    proposalKind: "merge_objects",
    status: "staged_local",
    survivorObjectRef: input.survivorObjectRef,
    mergedObjectRefs: dedupedMergedRefs,
    mergeReason: input.mergeReason,
    matchedFeatures: input.matchedFeatures,
    aliasPolicy: "preserve_all_aliases",
    relationshipPolicy: "preserve_all_relationships",
    evidencePolicy: "preserve_all_evidence",
    visibility: buildVisibilityPreview(GRAPH_OBJECT_AUTHORING_DEFAULT_VISIBILITY),
    graphScopes: ["recap_graph", "campaign_memory_graph"],
    provenancePreview: {
      origin: "human_authored",
      authoringSurface: "memory_ingest_graph_authoring",
      sourceGraphId: input.sourceGraphId ?? null,
      operatorNote: input.operatorNote?.trim() || null,
    },
  };
}

export function serializeGraphObjectAuthoringProposalForApi(
  proposal: GraphObjectAuthoringProposal,
): Record<string, unknown> {
  const base = {
    localProposalId: proposal.localProposalId,
    proposalKind: proposal.proposalKind,
    status: proposal.status,
    visibility: proposal.visibility,
    graphScopes: proposal.graphScopes,
    provenancePreview: proposal.provenancePreview,
  };

  if (proposal.proposalKind === "object") {
    return {
      ...base,
      selection: proposal.selection,
      objectRef: proposal.objectRef,
    };
  }

  if (proposal.proposalKind === "link_existing") {
    return {
      ...base,
      selection: proposal.selection,
      selectedText: proposal.selectedText,
      normalizedSelectedText: proposal.normalizedSelectedText,
      existingObjectRef: serializeGraphObjectAuthoringObjectRefForApi(
        proposal.existingObjectRef,
      ),
      operation: proposal.operation,
      aliasText: proposal.aliasText ?? null,
    };
  }

  if (proposal.proposalKind === "merge_objects") {
    return {
      ...base,
      survivorObjectRef: serializeGraphObjectAuthoringObjectRefForApi(
        proposal.survivorObjectRef,
      ),
      mergedObjectRefs: proposal.mergedObjectRefs.map((ref) =>
        serializeGraphObjectAuthoringObjectRefForApi(ref),
      ),
      mergeReason: proposal.mergeReason,
      matchedFeatures: proposal.matchedFeatures,
      aliasPolicy: proposal.aliasPolicy,
      relationshipPolicy: proposal.relationshipPolicy,
      evidencePolicy: proposal.evidencePolicy,
    };
  }

  return {
    ...base,
    selection: proposal.selection ?? null,
    sourceObjectRef: serializeGraphObjectAuthoringObjectRefForApi(proposal.sourceObjectRef),
    targetObjectRef: serializeGraphObjectAuthoringObjectRefForApi(proposal.targetObjectRef),
    relationshipType: proposal.relationshipType,
    relationshipLabel: proposal.relationshipLabel ?? null,
    direction: proposal.direction,
    summary: proposal.summary ?? null,
  };
}
