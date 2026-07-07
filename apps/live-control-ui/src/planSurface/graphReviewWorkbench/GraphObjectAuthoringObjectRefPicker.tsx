import { useMemo } from "react";

import {
  buildManualObjectRef,
  buildObjectRefFromInspectedNode,
  buildObjectRefFromObjectProposal,
  type GraphObjectAuthoringObjectProposal,
  type GraphObjectAuthoringObjectRef,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";
import {
  findPickerCrossGroupHint,
  formatPickerNodeLabel,
  type GraphObjectAuthoringOverlapContext,
} from "./graphObjectAuthoringOverlap";
import {
  GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS,
  GRAPH_OBJECT_CANDIDATE_SCOPE_ORDER,
  resolverCandidateToInspectedNode,
} from "./graphObjectCandidateScope";
import type { GraphReviewExistingObjectCandidate } from "../../api/types";

export interface GraphObjectAuthoringInspectedNode {
  node_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
  aliases?: string[];
  authored?: boolean;
  sourceAnchorText?: string | null;
  graphScope?: string | null;
  sourceLabel?: string | null;
  sourceGraphId?: string | null;
  sourcePath?: string | null;
  visibility?: string | null;
}

type PickerOptionValue =
  | { source: "empty" }
  | { source: "manual" }
  | { source: "local_proposal"; localProposalId: string }
  | { source: "existing_node"; nodeId: string }
  | { source: "scope_candidate"; nodeId: string; scope: string };

function encodeOptionValue(value: PickerOptionValue): string {
  if (value.source === "local_proposal") {
    return `local_proposal:${value.localProposalId}`;
  }
  if (value.source === "existing_node") {
    return `existing_node:${value.nodeId}`;
  }
  if (value.source === "scope_candidate") {
    return `scope_candidate:${value.scope}:${value.nodeId}`;
  }
  return value.source;
}

function stagedObjectProposals(
  proposals: GraphObjectAuthoringProposal[],
): GraphObjectAuthoringObjectProposal[] {
  return proposals.filter(
    (proposal): proposal is GraphObjectAuthoringObjectProposal => proposal.proposalKind === "object",
  );
}

function dedupeAndSortNodes(
  nodes: GraphObjectAuthoringInspectedNode[],
): GraphObjectAuthoringInspectedNode[] {
  const byId = new Map<string, GraphObjectAuthoringInspectedNode>();
  for (const node of nodes) {
    if (!byId.has(node.node_id)) {
      byId.set(node.node_id, node);
    }
  }
  return Array.from(byId.values()).sort((a, b) => a.label.localeCompare(b.label));
}

function formatScopeCandidateLabel(candidate: GraphReviewExistingObjectCandidate): string {
  const kindSuffix = candidate.kind ? ` · ${candidate.kind}` : "";
  const aliasSuffix =
    candidate.aliases && candidate.aliases.length > 0
      ? ` · aliases: ${candidate.aliases.join(", ")}`
      : "";
  const reasonSuffix = candidate.reason ? ` · ${candidate.reason}` : "";
  return `${candidate.label}${kindSuffix}${aliasSuffix}${reasonSuffix}`;
}

function scopeCandidatesByGroup(
  candidates: GraphReviewExistingObjectCandidate[],
): Array<{ scope: string; label: string; candidates: GraphReviewExistingObjectCandidate[] }> {
  const grouped = new Map<string, GraphReviewExistingObjectCandidate[]>();
  for (const candidate of candidates) {
    const scope = candidate.graph_scope ?? "unknown";
    const bucket = grouped.get(scope) ?? [];
    bucket.push(candidate);
    grouped.set(scope, bucket);
  }
  const ordered = [
    ...GRAPH_OBJECT_CANDIDATE_SCOPE_ORDER.filter((scope) => grouped.has(scope)),
    ...(grouped.has("unknown") ? (["unknown"] as const) : []),
  ];
  return ordered.map((scope) => ({
    scope,
    label: scope === "unknown" ? "Other sources" : GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS[scope],
    candidates: grouped.get(scope) ?? [],
  }));
}
function formatStagedProposalLabel(proposal: GraphObjectAuthoringObjectProposal): string {
  const kindSuffix = proposal.objectRef.kind ? ` · ${proposal.objectRef.kind}` : "";
  const aliasSuffix =
    proposal.objectRef.aliases.length > 0
      ? ` · aliases: ${proposal.objectRef.aliases.join(", ")}`
      : "";
  return `${proposal.objectRef.label}${kindSuffix}${aliasSuffix}`;
}

export function GraphObjectAuthoringObjectRefPicker({
  label,
  value,
  onChange,
  proposals,
  existingNodes = [],
  scopeCandidates = [],
  overlapContext,
  manualPlaceholder = "Type a label for an object not staged yet",
}: {
  label: string;
  value: GraphObjectAuthoringObjectRef | null;
  onChange: (ref: GraphObjectAuthoringObjectRef | null) => void;
  proposals: GraphObjectAuthoringProposal[];
  existingNodes?: GraphObjectAuthoringInspectedNode[];
  scopeCandidates?: GraphReviewExistingObjectCandidate[];
  overlapContext?: GraphObjectAuthoringOverlapContext;
  manualPlaceholder?: string;
}) {
  const objectProposals = stagedObjectProposals(proposals);
  const sortedExistingNodes = useMemo(() => dedupeAndSortNodes(existingNodes), [existingNodes]);
  const groupedScopeCandidates = useMemo(
    () => scopeCandidatesByGroup(scopeCandidates),
    [scopeCandidates],
  );
  const scopeCandidateNodes = useMemo(
    () => scopeCandidates.map((candidate) => resolverCandidateToInspectedNode(candidate)),
    [scopeCandidates],
  );
  const allExistingNodes = useMemo(
    () => dedupeAndSortNodes([...sortedExistingNodes, ...scopeCandidateNodes]),
    [sortedExistingNodes, scopeCandidateNodes],
  );
  const authoredNodes = useMemo(
    () => sortedExistingNodes.filter((node) => node.authored),
    [sortedExistingNodes],
  );
  const extractedNodes = useMemo(
    () => sortedExistingNodes.filter((node) => !node.authored),
    [sortedExistingNodes],
  );
  const showManualInput = value?.refKind === "manual_ref";
  const manualLabelValue = value?.refKind === "manual_ref" ? value.label : "";

  const selectedExistingNode =
    value?.refKind === "existing_graph_node" && value.nodeId
      ? allExistingNodes.find((node) => node.node_id === value.nodeId) ?? null
      : null;
  const crossGroupHint =
    overlapContext && selectedExistingNode
      ? findPickerCrossGroupHint(selectedExistingNode, overlapContext)
      : null;

  const selectedOptionValue: string = (() => {
    if (!value) return encodeOptionValue({ source: "empty" });
    if (value.refKind === "manual_ref") return encodeOptionValue({ source: "manual" });
    if (value.refKind === "local_proposal" && value.localProposalId) {
      return encodeOptionValue({ source: "local_proposal", localProposalId: value.localProposalId });
    }
    if (value.refKind === "existing_graph_node" && value.nodeId) {
      const scopeCandidate = scopeCandidates.find(
        (candidate) => candidate.candidate_id === value.nodeId,
      );
      if (scopeCandidate?.graph_scope) {
        return encodeOptionValue({
          source: "scope_candidate",
          scope: scopeCandidate.graph_scope,
          nodeId: value.nodeId,
        });
      }
      return encodeOptionValue({ source: "existing_node", nodeId: value.nodeId });
    }
    return encodeOptionValue({ source: "empty" });
  })();

  const handleSelectChange = (rawValue: string) => {
    if (rawValue === "empty") {
      onChange(null);
      return;
    }
    if (rawValue === "manual") {
      onChange(buildManualObjectRef(manualLabelValue));
      return;
    }
    if (rawValue.startsWith("local_proposal:")) {
      const localProposalId = rawValue.slice("local_proposal:".length);
      const proposal = objectProposals.find((candidate) => candidate.localProposalId === localProposalId);
      if (proposal) {
        onChange(buildObjectRefFromObjectProposal(proposal));
      }
      return;
    }
    if (rawValue.startsWith("scope_candidate:")) {
      const [, scope, nodeId] = rawValue.split(":");
      const candidate = scopeCandidates.find(
        (item) => item.candidate_id === nodeId && (item.graph_scope ?? "unknown") === scope,
      );
      if (candidate) {
        onChange(buildObjectRefFromInspectedNode(resolverCandidateToInspectedNode(candidate)));
      }
      return;
    }
    if (rawValue.startsWith("existing_node:")) {
      const nodeId = rawValue.slice("existing_node:".length);
      const node = allExistingNodes.find((candidate) => candidate.node_id === nodeId);
      if (node) {
        onChange(buildObjectRefFromInspectedNode(node));
      }
      return;
    }
    onChange(null);
  };

  return (
    <div className="graph-object-authoring-ref-picker">
      <label>
        {label}
        <select
          value={selectedOptionValue}
          onChange={(event) => handleSelectChange(event.target.value)}
        >
          <option value="empty">— choose an object —</option>
          {objectProposals.length ? (
            <optgroup label="Staged local drafts">
              {objectProposals.map((proposal) => (
                <option
                  key={proposal.localProposalId}
                  value={encodeOptionValue({
                    source: "local_proposal",
                    localProposalId: proposal.localProposalId,
                  })}
                >
                  {formatStagedProposalLabel(proposal)}
                </option>
              ))}
            </optgroup>
          ) : null}
          {authoredNodes.length ? (
            <optgroup label="Authored memory">
              {authoredNodes.map((node) => (
                <option
                  key={node.node_id}
                  value={encodeOptionValue({ source: "existing_node", nodeId: node.node_id })}
                >
                  {formatPickerNodeLabel(node)}
                </option>
              ))}
            </optgroup>
          ) : null}
          {extractedNodes.length ? (
            <optgroup label="Current recap">
              {extractedNodes.map((node) => (
                <option
                  key={node.node_id}
                  value={encodeOptionValue({ source: "existing_node", nodeId: node.node_id })}
                >
                  {formatPickerNodeLabel(node)}
                </option>
              ))}
            </optgroup>
          ) : null}
          {groupedScopeCandidates.map((group) =>
            group.candidates.length ? (
              <optgroup key={group.scope} label={group.label}>
                {group.candidates.map((candidate) => (
                  <option
                    key={`${group.scope}-${candidate.candidate_id}`}
                    value={encodeOptionValue({
                      source: "scope_candidate",
                      scope: group.scope,
                      nodeId: candidate.candidate_id,
                    })}
                  >
                    {formatScopeCandidateLabel(candidate)}
                  </option>
                ))}
              </optgroup>
            ) : null,
          )}
          <option value="manual">Manual label entry…</option>
        </select>
      </label>
      {showManualInput ? (
        <input
          type="text"
          placeholder={manualPlaceholder}
          value={manualLabelValue}
          onChange={(event) => onChange(buildManualObjectRef(event.target.value))}
        />
      ) : null}
      {value ? (
        <p className="graph-object-authoring-ref-picker-summary">
          Selected: {value.label || "—"}{" "}
          <span className="graph-object-authoring-ref-picker-kind">({value.refKind.replaceAll("_", " ")})</span>
          {value.sourceLabel ? (
            <span className="graph-object-authoring-ref-picker-source-label"> · {value.sourceLabel}</span>
          ) : null}
        </p>
      ) : null}
      <p className="graph-object-authoring-ref-picker-no-merge-copy">
        Selecting an existing object stages a link/reference. It does not merge identities automatically.
      </p>
      {crossGroupHint ? (
        <p className="graph-object-authoring-ref-picker-cross-group-hint">{crossGroupHint}</p>
      ) : null}
    </div>
  );
}
