import { useMemo, useState } from "react";

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

const RESULT_LIMIT = 40;

function normalizeSearchText(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function haystackForParts(parts: Array<string | null | undefined>): string {
  return normalizeSearchText(parts.filter(Boolean).join(" "));
}

function matchesQuery(haystack: string, query: string): boolean {
  const tokens = normalizeSearchText(query).split(" ").filter(Boolean);
  if (tokens.length === 0) {
    return true;
  }
  return tokens.every((token) => haystack.includes(token));
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

function formatStagedProposalLabel(proposal: GraphObjectAuthoringObjectProposal): string {
  const kindSuffix = proposal.objectRef.kind ? ` · ${proposal.objectRef.kind}` : "";
  const aliasSuffix =
    proposal.objectRef.aliases.length > 0
      ? ` · aliases: ${proposal.objectRef.aliases.join(", ")}`
      : "";
  return `${proposal.objectRef.label}${kindSuffix}${aliasSuffix}`;
}

type PickerResult =
  | {
      key: string;
      group: string;
      label: string;
      meta: string;
      select: () => void;
    };

/** Exported for unit tests — filters picker candidates by typeahead query. */
export function filterObjectRefPickerCandidates(input: {
  query: string;
  objectProposals: GraphObjectAuthoringObjectProposal[];
  existingNodes: GraphObjectAuthoringInspectedNode[];
  scopeCandidates: GraphReviewExistingObjectCandidate[];
  limit?: number;
}): PickerResult[] {
  const limit = input.limit ?? RESULT_LIMIT;
  const results: PickerResult[] = [];

  for (const proposal of input.objectProposals) {
    const haystack = haystackForParts([
      proposal.objectRef.label,
      proposal.objectRef.kind,
      proposal.objectRef.role,
      ...proposal.objectRef.aliases,
    ]);
    if (!matchesQuery(haystack, input.query)) {
      continue;
    }
    results.push({
      key: `local_proposal:${proposal.localProposalId}`,
      group: "Staged local drafts",
      label: proposal.objectRef.label,
      meta: formatStagedProposalLabel(proposal),
      select: () => undefined,
    });
    if (results.length >= limit) {
      return results;
    }
  }

  for (const node of input.existingNodes) {
    const haystack = haystackForParts([
      node.label,
      node.node_id,
      node.kind,
      node.role,
      ...(node.aliases ?? []),
    ]);
    if (!matchesQuery(haystack, input.query)) {
      continue;
    }
    const group = node.authored ? "Authored memory" : "Current recap";
    results.push({
      key: `existing_node:${node.node_id}`,
      group,
      label: node.label,
      meta: formatPickerNodeLabel(node),
      select: () => undefined,
    });
    if (results.length >= limit) {
      return results;
    }
  }

  for (const candidate of input.scopeCandidates) {
    const haystack = haystackForParts([
      candidate.label,
      candidate.candidate_id,
      candidate.kind,
      ...(candidate.aliases ?? []),
      candidate.reason,
    ]);
    if (!matchesQuery(haystack, input.query)) {
      continue;
    }
    const scope = candidate.graph_scope ?? "unknown";
    const group =
      scope === "unknown"
        ? "Other sources"
        : (GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS[
            scope as keyof typeof GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS
          ] ?? scope);
    results.push({
      key: `scope_candidate:${scope}:${candidate.candidate_id}`,
      group,
      label: candidate.label,
      meta: formatScopeCandidateLabel(candidate),
      select: () => undefined,
    });
    if (results.length >= limit) {
      return results;
    }
  }

  return results;
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
  const [query, setQuery] = useState("");
  const [manualMode, setManualMode] = useState(false);

  const objectProposals = stagedObjectProposals(proposals);
  const sortedExistingNodes = useMemo(() => dedupeAndSortNodes(existingNodes), [existingNodes]);
  const scopeCandidateNodes = useMemo(
    () => scopeCandidates.map((candidate) => resolverCandidateToInspectedNode(candidate)),
    [scopeCandidates],
  );
  const allExistingNodes = useMemo(
    () => dedupeAndSortNodes([...sortedExistingNodes, ...scopeCandidateNodes]),
    [sortedExistingNodes, scopeCandidateNodes],
  );

  const hasLabeledValue = Boolean(value?.label?.trim());
  const showManualInput = manualMode;
  const showSelectedChip = hasLabeledValue && !manualMode;
  const manualLabelValue = value?.refKind === "manual_ref" ? value.label : query;

  const filtered = useMemo(() => {
    const skeleton = filterObjectRefPickerCandidates({
      query,
      objectProposals,
      existingNodes: sortedExistingNodes,
      scopeCandidates,
    });
    return skeleton.map((item) => {
      if (item.key.startsWith("local_proposal:")) {
        const localProposalId = item.key.slice("local_proposal:".length);
        const proposal = objectProposals.find(
          (candidate) => candidate.localProposalId === localProposalId,
        );
        return {
          ...item,
          select: () => {
            if (proposal) {
              onChange(buildObjectRefFromObjectProposal(proposal));
              setQuery("");
              setManualMode(false);
            }
          },
        };
      }
      if (item.key.startsWith("scope_candidate:")) {
        const [, scope, nodeId] = item.key.split(":");
        const candidate = scopeCandidates.find(
          (entry) =>
            entry.candidate_id === nodeId && (entry.graph_scope ?? "unknown") === scope,
        );
        return {
          ...item,
          select: () => {
            if (candidate) {
              onChange(
                buildObjectRefFromInspectedNode(resolverCandidateToInspectedNode(candidate)),
              );
              setQuery("");
              setManualMode(false);
            }
          },
        };
      }
      if (item.key.startsWith("existing_node:")) {
        const nodeId = item.key.slice("existing_node:".length);
        const node = allExistingNodes.find((candidate) => candidate.node_id === nodeId);
        return {
          ...item,
          select: () => {
            if (node) {
              onChange(buildObjectRefFromInspectedNode(node));
              setQuery("");
              setManualMode(false);
            }
          },
        };
      }
      return item;
    });
  }, [
    allExistingNodes,
    objectProposals,
    onChange,
    query,
    scopeCandidates,
    sortedExistingNodes,
  ]);

  const selectedExistingNode =
    value?.refKind === "existing_graph_node" && value.nodeId
      ? allExistingNodes.find((node) => node.node_id === value.nodeId) ?? null
      : null;
  const crossGroupHint =
    overlapContext && selectedExistingNode
      ? findPickerCrossGroupHint(selectedExistingNode, overlapContext)
      : null;

  const inputId = `graph-object-authoring-ref-picker-${label.toLowerCase().replace(/\s+/g, "-")}`;
  const selectedValueAttr = (() => {
    if (!value) return "";
    if (value.refKind === "manual_ref") return "manual";
    if (value.refKind === "local_proposal" && value.localProposalId) {
      return `local_proposal:${value.localProposalId}`;
    }
    if (value.refKind === "existing_graph_node" && value.nodeId) {
      return `existing_node:${value.nodeId}`;
    }
    return value.refKind;
  })();

  return (
    <div
      className="graph-object-authoring-ref-picker"
      data-testid="graph-object-authoring-ref-picker"
      role="group"
      aria-label={label}
      data-ref-value={selectedValueAttr}
    >
      <span className="graph-object-authoring-ref-picker-label" id={`${inputId}-label`}>
        {label}
      </span>

      {showSelectedChip && value ? (
        <div
          className="graph-object-authoring-ref-picker-selected"
          data-testid="graph-object-authoring-ref-picker-selected"
        >
          <p className="graph-object-authoring-ref-picker-summary">
            Selected: {value.label || "—"}{" "}
            <span className="graph-object-authoring-ref-picker-kind">
              ({value.refKind.replaceAll("_", " ")})
            </span>
            {value.sourceLabel ? (
              <span className="graph-object-authoring-ref-picker-source-label">
                {" "}
                · {value.sourceLabel}
              </span>
            ) : null}
          </p>
          <button
            type="button"
            className="graph-object-authoring-ref-picker-clear"
            data-testid="graph-object-authoring-ref-picker-clear"
            aria-label={`Change ${label}`}
            onClick={() => {
              onChange(null);
              setQuery("");
              setManualMode(false);
            }}
          >
            Change
          </button>
        </div>
      ) : showManualInput ? (
        <div className="graph-object-authoring-ref-picker-manual-block">
          <input
            type="text"
            data-testid="graph-object-authoring-ref-picker-manual-input"
            aria-label={`${label} manual label`}
            placeholder={manualPlaceholder}
            value={manualLabelValue}
            onChange={(event) => {
              setQuery(event.target.value);
              onChange(buildManualObjectRef(event.target.value));
            }}
          />
          <div className="graph-object-authoring-ref-picker-manual-actions">
            <button
              type="button"
              className="graph-object-authoring-ref-picker-clear"
              data-testid="graph-object-authoring-ref-picker-done-manual"
              disabled={!hasLabeledValue}
              onClick={() => {
                setManualMode(false);
                setQuery("");
              }}
            >
              Done
            </button>
            <button
              type="button"
              className="graph-object-authoring-ref-picker-clear"
              data-testid="graph-object-authoring-ref-picker-cancel-manual"
              onClick={() => {
                setManualMode(false);
                setQuery("");
                onChange(null);
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <input
            id={inputId}
            type="search"
            className="graph-object-authoring-ref-picker-search"
            data-testid="graph-object-authoring-ref-picker-search"
            aria-labelledby={`${inputId}-label`}
            value={query}
            placeholder="Search objects by name, alias, or kind…"
            autoComplete="off"
            onChange={(event) => {
              setQuery(event.target.value);
              setManualMode(false);
            }}
            onKeyDown={(event) => {
              if (event.key !== "Enter") {
                return;
              }
              const first = filtered[0];
              if (!first) {
                return;
              }
              event.preventDefault();
              first.select();
            }}
          />
          <ul
            className="graph-object-authoring-ref-picker-results"
            data-testid="graph-object-authoring-ref-picker-results"
            role="listbox"
            aria-label={`${label} matches`}
          >
            {filtered.length === 0 && query.trim() ? (
              <li className="graph-object-authoring-ref-picker-empty">
                No objects match “{query.trim()}”.
              </li>
            ) : null}
            {filtered.length === 0 && !query.trim() ? (
              <li className="graph-object-authoring-ref-picker-empty">
                Type to search staged drafts and projected objects.
              </li>
            ) : null}
            {filtered.map((item) => (
              <li key={item.key} role="option">
                <button
                  type="button"
                  className="graph-object-authoring-ref-picker-result"
                  onClick={item.select}
                >
                  <span className="graph-object-authoring-ref-picker-result-label">
                    {item.label}
                  </span>
                  <span className="graph-object-authoring-ref-picker-result-meta">
                    {item.group}
                    {item.meta !== item.label ? ` · ${item.meta}` : ""}
                  </span>
                </button>
              </li>
            ))}
            <li role="option">
              <button
                type="button"
                className="graph-object-authoring-ref-picker-result graph-object-authoring-ref-picker-result--manual"
                data-testid="graph-object-authoring-ref-picker-manual"
                onClick={() => {
                  setManualMode(true);
                  onChange(buildManualObjectRef(query.trim()));
                }}
              >
                Manual label entry…
              </button>
            </li>
          </ul>
        </>
      )}

      <p className="graph-object-authoring-ref-picker-no-merge-copy">
        Selecting an existing object stages a link/reference. It does not merge identities
        automatically.
      </p>
      {crossGroupHint ? (
        <p className="graph-object-authoring-ref-picker-cross-group-hint">{crossGroupHint}</p>
      ) : null}
    </div>
  );
}
