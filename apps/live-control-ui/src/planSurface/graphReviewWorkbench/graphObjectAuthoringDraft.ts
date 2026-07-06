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

export interface GraphObjectAuthoringProposal {
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
  visibility: {
    visibility: GraphObjectAuthoringVisibility;
    revealState: "unrevealed" | "partial" | "revealed";
    visibilityNote?: string | null;
  };
  graphScopes: GraphObjectAuthoringScope[];
  provenancePreview: {
    origin: "human_authored";
    authoringSurface: "memory_ingest_graph_authoring";
    sourceGraphId?: string | null;
    sourceArtifactPath?: string | null;
    operatorNote?: string | null;
  };
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

export function buildGraphObjectAuthoringProposal(
  selection: GraphAuthoringSelection,
  formState: GraphObjectAuthoringFormState,
  localProposalId: string = createLocalGraphObjectProposalId(),
): GraphObjectAuthoringProposal {
  const aliases = buildProposalAliases(formState, selection);
  const label = formState.label.trim() || selection.selectedText;
  const visibilityOption = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (option) => option.value === formState.visibility,
  );

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
    visibility: {
      visibility: formState.visibility,
      revealState: "unrevealed",
      visibilityNote: visibilityOption?.note ?? null,
    },
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
