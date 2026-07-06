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
  { value: "gm_private", label: "GM private" },
  { value: "table_known", label: "Table known / player visible" },
  {
    value: "character_specific",
    label: "Character-specific",
    note: "Targeting specific characters will be implemented later.",
  },
  { value: "hidden_until_revealed", label: "Hidden until revealed" },
];

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
  | GraphObjectAuthoringRelationshipProposal;

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
}): GraphObjectAuthoringObjectRef {
  return {
    refKind: "existing_graph_node",
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind ?? null,
    role: node.role ?? null,
  };
}

export function buildManualObjectRef(label: string): GraphObjectAuthoringObjectRef {
  return {
    refKind: "manual_ref",
    label: label.trim(),
  };
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
  if (!formState.existingObjectRef) {
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

export const GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS: string[] = [
  "has_member",
  "member_of",
  "located_in",
  "controls",
  "allied_with",
  "opposes",
  "owns",
  "created_by",
  "travels_with",
  "protects",
  "threatens",
  "related_to",
];

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
    relationshipType: GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS[0],
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
  if (
    !formState.sourceObjectRef ||
    !formState.targetObjectRef ||
    !formState.relationshipType.trim()
  ) {
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
