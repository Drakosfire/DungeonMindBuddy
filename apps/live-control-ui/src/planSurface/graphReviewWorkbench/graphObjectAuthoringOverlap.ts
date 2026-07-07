import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildProposalAliases,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringLinkExistingFormState,
  type GraphObjectAuthoringObjectProposal,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";

export type GraphObjectAuthoringOverlapCode =
  | "authored_overlay_possible_duplicate_label"
  | "authored_overlay_possible_duplicate_alias"
  | "authored_overlay_possible_duplicate_source_anchor"
  | "staged_proposal_possible_duplicate"
  | "extracted_graph_possible_duplicate_label"
  | "extracted_graph_possible_duplicate_alias";

export interface GraphObjectAuthoringOverlapWarning {
  code: GraphObjectAuthoringOverlapCode;
  message: string;
  localProposalId?: string;
}

export interface GraphObjectAuthoringOverlapContext {
  stagedProposals: GraphObjectAuthoringProposal[];
  existingNodes: GraphObjectAuthoringInspectedNode[];
  authoredOverlayLabels: string[];
  authoredOverlayAliases: string[];
  authoredOverlaySourceAnchors: string[];
}

export function normalizeOverlapText(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, " ");
}

function addToken(tokens: Set<string>, text: string | null | undefined): void {
  if (!text) return;
  const normalized = normalizeOverlapText(text);
  if (normalized) tokens.add(normalized);
}

function objectProposalTokens(proposal: GraphObjectAuthoringObjectProposal): Set<string> {
  const tokens = new Set<string>();
  addToken(tokens, proposal.objectRef.label);
  for (const alias of proposal.objectRef.aliases) {
    addToken(tokens, alias);
  }
  addToken(tokens, proposal.selection.selectedText);
  addToken(tokens, proposal.selection.normalizedSelectedText);
  return tokens;
}

function linkExistingProposalTokens(
  proposal: Extract<GraphObjectAuthoringProposal, { proposalKind: "link_existing" }>,
): Set<string> {
  const tokens = new Set<string>();
  addToken(tokens, proposal.selectedText);
  addToken(tokens, proposal.normalizedSelectedText);
  addToken(tokens, proposal.aliasText);
  addToken(tokens, proposal.existingObjectRef.label);
  return tokens;
}

function proposalTokens(proposal: GraphObjectAuthoringProposal): Set<string> {
  if (proposal.proposalKind === "object") {
    return objectProposalTokens(proposal);
  }
  if (proposal.proposalKind === "link_existing") {
    return linkExistingProposalTokens(proposal);
  }
  if (proposal.proposalKind === "merge_objects") {
    const tokens = new Set<string>();
    addToken(tokens, proposal.survivorObjectRef.label);
    for (const ref of proposal.mergedObjectRefs) {
      addToken(tokens, ref.label);
    }
    return tokens;
  }
  const tokens = new Set<string>();
  addToken(tokens, proposal.sourceObjectRef.label);
  addToken(tokens, proposal.targetObjectRef.label);
  return tokens;
}

function formDraftTokens(
  formState: GraphObjectAuthoringFormState,
  selection: GraphAuthoringSelection | null,
): { label: string; tokens: Set<string> } {
  const label = formState.label.trim();
  const aliases = buildProposalAliases(formState, selection);
  const tokens = new Set<string>();
  addToken(tokens, label);
  for (const alias of aliases) {
    addToken(tokens, alias);
  }
  if (selection) {
    addToken(tokens, selection.selectedText);
    addToken(tokens, selection.normalizedSelectedText);
  }
  return { label, tokens };
}

function linkExistingFormTokens(
  formState: GraphObjectAuthoringLinkExistingFormState,
  selectedText: string,
): Set<string> {
  const tokens = new Set<string>();
  addToken(tokens, selectedText);
  addToken(tokens, formState.aliasText);
  if (formState.existingObjectRef) {
    addToken(tokens, formState.existingObjectRef.label);
  }
  return tokens;
}

function authoredNodes(nodes: GraphObjectAuthoringInspectedNode[]): GraphObjectAuthoringInspectedNode[] {
  return nodes.filter((node) => node.authored);
}

function extractedNodes(nodes: GraphObjectAuthoringInspectedNode[]): GraphObjectAuthoringInspectedNode[] {
  return nodes.filter((node) => !node.authored);
}

function indexOverlayStrings(
  values: string[],
): Map<string, string> {
  const index = new Map<string, string>();
  for (const value of values) {
    const normalized = normalizeOverlapText(value);
    if (normalized && !index.has(normalized)) {
      index.set(normalized, value);
    }
  }
  return index;
}

function indexExistingNodes(
  nodes: GraphObjectAuthoringInspectedNode[],
): { labels: Map<string, string>; aliases: Map<string, string> } {
  const labels = new Map<string, string>();
  const aliases = new Map<string, string>();
  for (const node of nodes) {
    const normalizedLabel = normalizeOverlapText(node.label);
    if (normalizedLabel) {
      labels.set(normalizedLabel, node.label);
    }
    for (const alias of node.aliases ?? []) {
      const normalizedAlias = normalizeOverlapText(alias);
      if (normalizedAlias) {
        aliases.set(normalizedAlias, node.label);
      }
    }
  }
  return { labels, aliases };
}

function warnForTokens(
  tokens: Set<string>,
  normalizedPrimaryLabel: string,
  context: GraphObjectAuthoringOverlapContext,
  localProposalId?: string,
): GraphObjectAuthoringOverlapWarning[] {
  const warnings: GraphObjectAuthoringOverlapWarning[] = [];
  const overlayLabels = indexOverlayStrings(context.authoredOverlayLabels);
  const overlayAliases = indexOverlayStrings(context.authoredOverlayAliases);
  const overlayAnchors = indexOverlayStrings(context.authoredOverlaySourceAnchors);
  const extracted = indexExistingNodes(extractedNodes(context.existingNodes));
  const authored = indexExistingNodes(authoredNodes(context.existingNodes));

  if (normalizedPrimaryLabel && overlayLabels.has(normalizedPrimaryLabel)) {
    warnings.push({
      code: "authored_overlay_possible_duplicate_label",
      message: `Possible duplicate: label "${overlayLabels.get(normalizedPrimaryLabel)}" already exists in authored graph memory.`,
      localProposalId,
    });
  }

  for (const token of tokens) {
    if (overlayAliases.has(token)) {
      warnings.push({
        code: "authored_overlay_possible_duplicate_alias",
        message: `Possible duplicate: "${token}" is already an alias of authored object "${overlayAliases.get(token)}".`,
        localProposalId,
      });
    } else if (overlayLabels.has(token) && token !== normalizedPrimaryLabel) {
      warnings.push({
        code: "authored_overlay_possible_duplicate_label",
        message: `Possible duplicate: "${token}" matches authored object label "${overlayLabels.get(token)}".`,
        localProposalId,
      });
    } else if (overlayAnchors.has(token)) {
      warnings.push({
        code: "authored_overlay_possible_duplicate_source_anchor",
        message: `Possible duplicate: "${overlayAnchors.get(token)}" is already linked in authored graph memory.`,
        localProposalId,
      });
    }

    if (extracted.labels.has(token)) {
      warnings.push({
        code: "extracted_graph_possible_duplicate_label",
        message: `Possible duplicate: "${token}" matches extracted graph object "${extracted.labels.get(token)}" (not merged).`,
        localProposalId,
      });
    } else if (extracted.aliases.has(token)) {
      warnings.push({
        code: "extracted_graph_possible_duplicate_alias",
        message: `Possible duplicate: "${token}" matches extracted alias on "${extracted.aliases.get(token)}" (not merged).`,
        localProposalId,
      });
    }

    if (authored.labels.has(token) && token !== normalizedPrimaryLabel) {
      warnings.push({
        code: "authored_overlay_possible_duplicate_label",
        message: `Possible duplicate: "${token}" matches authored memory object "${authored.labels.get(token)}".`,
        localProposalId,
      });
    } else if (authored.aliases.has(token)) {
      warnings.push({
        code: "authored_overlay_possible_duplicate_alias",
        message: `Possible duplicate: "${token}" is already an alias on authored memory object "${authored.aliases.get(token)}".`,
        localProposalId,
      });
    }
  }

  for (const proposal of context.stagedProposals) {
    if (proposal.proposalKind !== "object" || proposal.localProposalId === localProposalId) {
      continue;
    }
    const stagedTokens = objectProposalTokens(proposal);
    for (const token of tokens) {
      if (stagedTokens.has(token)) {
        warnings.push({
          code: "staged_proposal_possible_duplicate",
          message: `Possible duplicate: "${token}" also appears in staged draft "${proposal.objectRef.label}".`,
          localProposalId,
        });
      }
    }
  }

  return dedupeWarnings(warnings);
}

export function dedupeWarnings(
  warnings: GraphObjectAuthoringOverlapWarning[],
): GraphObjectAuthoringOverlapWarning[] {
  const seen = new Set<string>();
  const deduped: GraphObjectAuthoringOverlapWarning[] = [];
  for (const warning of warnings) {
    const key = `${warning.code}:${warning.message}:${warning.localProposalId ?? ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(warning);
  }
  return deduped;
}

export function detectObjectFormOverlapWarnings(
  formState: GraphObjectAuthoringFormState,
  selection: GraphAuthoringSelection | null,
  context: GraphObjectAuthoringOverlapContext,
): GraphObjectAuthoringOverlapWarning[] {
  const { label, tokens } = formDraftTokens(formState, selection);
  return warnForTokens(tokens, normalizeOverlapText(label), context);
}

export function detectLinkExistingFormOverlapWarnings(
  formState: GraphObjectAuthoringLinkExistingFormState,
  selectedText: string,
  context: GraphObjectAuthoringOverlapContext,
): GraphObjectAuthoringOverlapWarning[] {
  const tokens = linkExistingFormTokens(formState, selectedText);
  return warnForTokens(tokens, normalizeOverlapText(selectedText), context);
}

export function detectProposalOverlapWarnings(
  proposal: GraphObjectAuthoringProposal,
  context: GraphObjectAuthoringOverlapContext,
): GraphObjectAuthoringOverlapWarning[] {
  const tokens = proposalTokens(proposal);
  const primaryLabel =
    proposal.proposalKind === "object"
      ? proposal.objectRef.label
      : proposal.proposalKind === "link_existing"
        ? proposal.selectedText
        : proposal.proposalKind === "merge_objects"
          ? proposal.survivorObjectRef.label
          : proposal.sourceObjectRef.label;
  return warnForTokens(
    tokens,
    normalizeOverlapText(primaryLabel),
    context,
    proposal.localProposalId,
  );
}

export function findPickerCrossGroupHint(
  ref: GraphObjectAuthoringInspectedNode | null,
  context: GraphObjectAuthoringOverlapContext,
): string | null {
  if (!ref) return null;
  const normalizedLabel = normalizeOverlapText(ref.label);
  const authored = indexExistingNodes(authoredNodes(context.existingNodes));
  const extracted = indexExistingNodes(extractedNodes(context.existingNodes));

  if (ref.authored) {
    if (extracted.labels.has(normalizedLabel) || extracted.aliases.has(normalizedLabel)) {
      return `Possible same object as extracted graph: ${extracted.labels.get(normalizedLabel) ?? extracted.aliases.get(normalizedLabel)}`;
    }
    return null;
  }

  if (authored.labels.has(normalizedLabel) || authored.aliases.has(normalizedLabel)) {
    return `Possible same object as authored memory: ${authored.labels.get(normalizedLabel) ?? authored.aliases.get(normalizedLabel)}`;
  }
  return null;
}

export function formatPickerNodeLabel(node: GraphObjectAuthoringInspectedNode): string {
  const kindSuffix = node.kind ? ` · ${node.kind}` : "";
  const aliasSuffix =
    node.aliases && node.aliases.length > 0 ? ` · aliases: ${node.aliases.join(", ")}` : "";
  const authoredSuffix = node.authored ? " · authored" : "";
  return `${node.label}${kindSuffix}${aliasSuffix}${authoredSuffix}`;
}

export function buildOverlapContextFromProjection(
  stagedProposals: GraphObjectAuthoringProposal[],
  existingNodes: GraphObjectAuthoringInspectedNode[],
): GraphObjectAuthoringOverlapContext {
  const authoredOverlayLabels: string[] = [];
  const authoredOverlayAliases: string[] = [];
  const authoredOverlaySourceAnchors: string[] = [];

  for (const node of authoredNodes(existingNodes)) {
    authoredOverlayLabels.push(node.label);
    for (const alias of node.aliases ?? []) {
      authoredOverlayAliases.push(alias);
    }
    if (node.sourceAnchorText) {
      authoredOverlaySourceAnchors.push(node.sourceAnchorText);
    }
  }

  return {
    stagedProposals,
    existingNodes,
    authoredOverlayLabels,
    authoredOverlayAliases,
    authoredOverlaySourceAnchors,
  };
}
