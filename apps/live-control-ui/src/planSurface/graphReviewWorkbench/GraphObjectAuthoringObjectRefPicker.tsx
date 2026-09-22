import { useEffect, useId, useMemo, useRef, useState } from "react";

import type { GraphReviewExistingObjectCandidate } from "../../api/types";
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
  type GraphObjectAuthoringOverlapContext,
} from "./graphObjectAuthoringOverlap";
import {
  GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS,
  GRAPH_OBJECT_CANDIDATE_SCOPE_ORDER,
  resolverCandidateToInspectedNode,
} from "./graphObjectCandidateScope";
import { getGraphReviewBindTargetNodeId } from "./graphExistingObjectEligibility";
import {
  rankGraphObjectAuthoringSearchItems,
  type GraphObjectAuthoringSearchItem,
} from "./graphObjectAuthoringSearch";

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
  | { source: "local_proposal"; localProposalId: string }
  | { source: "existing_node"; nodeId: string }
  | { source: "scope_candidate"; nodeId: string; scope: string };

interface PickerOption extends GraphObjectAuthoringSearchItem {
  encodedValue: string;
  ref: GraphObjectAuthoringObjectRef;
}

const SEARCH_PREVIEW_LIMIT = 12;
const SEARCH_MATCH_LIMIT = 60;

function encodeOptionValue(value: PickerOptionValue): string {
  if (value.source === "local_proposal") {
    return `local_proposal:${value.localProposalId}`;
  }
  if (value.source === "existing_node") {
    return `existing_node:${value.nodeId}`;
  }
  return `scope_candidate:${value.scope}:${value.nodeId}`;
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
  return Array.from(byId.values()).sort((a, b) =>
    a.label.localeCompare(b.label) || (a.sourceLabel ?? "").localeCompare(b.sourceLabel ?? ""),
  );
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

function sourceMeta(
  node: GraphObjectAuthoringInspectedNode,
  fallbackGroup: string,
): string {
  return [
    node.sourceLabel ?? fallbackGroup,
    node.kind,
    node.role && node.role !== node.kind ? node.role : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function candidateMeta(
  candidate: GraphReviewExistingObjectCandidate,
  fallbackGroup: string,
): string {
  return [
    candidate.source_label ?? fallbackGroup,
    candidate.kind,
    candidate.role && candidate.role !== candidate.kind ? candidate.role : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function formatStagedProposalLabel(proposal: GraphObjectAuthoringObjectProposal): string {
  const kindSuffix = proposal.objectRef.kind ? ` · ${proposal.objectRef.kind}` : "";
  const aliasSuffix =
    proposal.objectRef.aliases.length > 0
      ? ` · aliases: ${proposal.objectRef.aliases.join(", ")}`
      : "";
  return `${proposal.objectRef.label}${kindSuffix}${aliasSuffix}`;
}

function optionForNode(
  node: GraphObjectAuthoringInspectedNode,
  group: string,
): PickerOption {
  const ref = buildObjectRefFromInspectedNode(node);
  return {
    key: `existing:${node.node_id}`,
    encodedValue: encodeOptionValue({ source: "existing_node", nodeId: node.node_id }),
    label: node.label,
    group,
    meta: sourceMeta(node, group),
    searchText: [node.label, ...(node.aliases ?? []), node.kind ?? "", node.role ?? "", node.sourceLabel ?? ""].join(" "),
    ref,
  };
}

function canonicalInspectedNodeForCandidate(
  candidate: GraphReviewExistingObjectCandidate,
): GraphObjectAuthoringInspectedNode {
  const node = resolverCandidateToInspectedNode(candidate);
  const bindTargetNodeId = getGraphReviewBindTargetNodeId(candidate);
  return bindTargetNodeId ? { ...node, node_id: bindTargetNodeId } : node;
}

function optionForCandidate(
  candidate: GraphReviewExistingObjectCandidate,
  group: string,
): PickerOption {
  const node = canonicalInspectedNodeForCandidate(candidate);
  return {
    key: `candidate:${candidate.graph_scope ?? "unknown"}:${candidate.candidate_id}`,
    encodedValue: encodeOptionValue({
      source: "scope_candidate",
      scope: candidate.graph_scope ?? "unknown",
      nodeId: candidate.candidate_id,
    }),
    label: candidate.label,
    group,
    meta: candidateMeta(candidate, group),
    searchText: [
      candidate.label,
      ...(candidate.aliases ?? []),
      candidate.kind ?? "",
      candidate.role ?? "",
      candidate.source_label ?? "",
      candidate.reason ?? "",
    ].join(" "),
    ref: buildObjectRefFromInspectedNode(node),
  };
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
  const pickerRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [showAll, setShowAll] = useState(false);

  const objectProposals = stagedObjectProposals(proposals);
  const sortedExistingNodes = useMemo(() => dedupeAndSortNodes(existingNodes), [existingNodes]);
  const governedNodeIds = useMemo(
    () => new Set(sortedExistingNodes.map((node) => node.node_id)),
    [sortedExistingNodes],
  );
  const governedScopeCandidates = useMemo(
    () => scopeCandidates.filter((candidate) => {
      const bindTargetNodeId = getGraphReviewBindTargetNodeId(candidate);
      return Boolean(bindTargetNodeId && governedNodeIds.has(bindTargetNodeId));
    }),
    [governedNodeIds, scopeCandidates],
  );
  const groupedScopeCandidates = useMemo(
    () => scopeCandidatesByGroup(governedScopeCandidates),
    [governedScopeCandidates],
  );
  const scopeCandidateNodes = useMemo(
    () => governedScopeCandidates.map(canonicalInspectedNodeForCandidate),
    [governedScopeCandidates],
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

  const pickerOptions = useMemo(() => {
    const options: PickerOption[] = [];
    for (const proposal of objectProposals) {
      const ref = buildObjectRefFromObjectProposal(proposal);
      options.push({
        key: `local:${proposal.localProposalId}`,
        encodedValue: encodeOptionValue({
          source: "local_proposal",
          localProposalId: proposal.localProposalId,
        }),
        label: ref.label,
        group: "Staged local drafts",
        meta: formatStagedProposalLabel(proposal),
        searchText: [ref.label, ...proposal.objectRef.aliases, ref.kind ?? "", ref.role ?? ""].join(" "),
        ref,
      });
    }
    authoredNodes.forEach((node) => options.push(optionForNode(node, "Authored memory")));
    extractedNodes.forEach((node) => options.push(optionForNode(node, "Current recap")));
    groupedScopeCandidates.forEach((group) => {
      group.candidates.forEach((candidate) => options.push(optionForCandidate(candidate, group.label)));
    });
    return options;
  }, [authoredNodes, extractedNodes, groupedScopeCandidates, objectProposals]);

  const selectedOptionValue: string | null = (() => {
    if (!value) return null;
    if (value.refKind === "local_proposal" && value.localProposalId) {
      return encodeOptionValue({ source: "local_proposal", localProposalId: value.localProposalId });
    }
    if (value.refKind === "existing_graph_node" && value.nodeId) {
      const scopeCandidate = governedScopeCandidates.find(
        (candidate) =>
          candidate.candidate_id === value.nodeId ||
          getGraphReviewBindTargetNodeId(candidate) === value.nodeId,
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
    return null;
  })();

  const selectedExistingNode =
    value?.refKind === "existing_graph_node" && value.nodeId
      ? allExistingNodes.find((node) => node.node_id === value.nodeId) ?? null
      : null;
  const crossGroupHint =
    overlapContext && selectedExistingNode
      ? findPickerCrossGroupHint(selectedExistingNode, overlapContext)
      : null;

  const rankedOptions = useMemo(
    () => rankGraphObjectAuthoringSearchItems(pickerOptions, query),
    [pickerOptions, query],
  );
  const visibleOptions = rankedOptions.slice(
    0,
    showAll ? rankedOptions.length : query.trim() ? SEARCH_MATCH_LIMIT : SEARCH_PREVIEW_LIMIT,
  );
  const hasMoreOptions = visibleOptions.length < rankedOptions.length;
  const selectedOption = pickerOptions.find((option) => option.encodedValue === selectedOptionValue);
  const inputValue = open
    ? query
    : selectedOption?.label ?? (value?.refKind === "manual_ref" ? "" : value?.label ?? "");

  useEffect(() => {
    function handleOutsidePointerDown(event: PointerEvent) {
      if (!pickerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("pointerdown", handleOutsidePointerDown);
    return () => document.removeEventListener("pointerdown", handleOutsidePointerDown);
  }, []);

  const handleSelectChange = (rawValue: string) => {
    if (rawValue === "manual") {
      onChange(buildManualObjectRef(value?.refKind === "manual_ref" ? value.label : ""));
      return;
    }
    if (rawValue.startsWith("local_proposal:")) {
      const localProposalId = rawValue.slice("local_proposal:".length);
      const proposal = objectProposals.find((candidate) => candidate.localProposalId === localProposalId);
      if (proposal) onChange(buildObjectRefFromObjectProposal(proposal));
      return;
    }
    if (rawValue.startsWith("scope_candidate:")) {
      const remainder = rawValue.slice("scope_candidate:".length);
      const separatorIndex = remainder.indexOf(":");
      const scope = separatorIndex < 0 ? remainder : remainder.slice(0, separatorIndex);
      const nodeId = separatorIndex < 0 ? "" : remainder.slice(separatorIndex + 1);
      const candidate = governedScopeCandidates.find(
        (item) =>
          (item.candidate_id === nodeId || getGraphReviewBindTargetNodeId(item) === nodeId) &&
          (item.graph_scope ?? "unknown") === scope,
      );
      if (candidate) onChange(buildObjectRefFromInspectedNode(canonicalInspectedNodeForCandidate(candidate)));
      return;
    }
    if (rawValue.startsWith("existing_node:")) {
      const nodeId = rawValue.slice("existing_node:".length);
      const node = allExistingNodes.find((candidate) => candidate.node_id === nodeId);
      if (node) onChange(buildObjectRefFromInspectedNode(node));
      return;
    }
    onChange(null);
  };

  const handleInputChange = (rawValue: string) => {
    const encodedOption = pickerOptions.some((option) => option.encodedValue === rawValue);
    if (rawValue === "manual" || encodedOption) {
      handleSelectChange(rawValue);
      setQuery("");
      setOpen(false);
      setShowAll(false);
      return;
    }
    setQuery(rawValue);
    setOpen(true);
    setShowAll(false);
  };

  const handleOptionSelect = (option: PickerOption) => {
    onChange(option.ref);
    setQuery("");
    setOpen(false);
    setShowAll(false);
  };

  return (
    <div className="graph-object-authoring-ref-picker" ref={pickerRef}>
      <label>
        {label}
        <input
          type="search"
          aria-label={label}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          placeholder={`Search ${label.toLocaleLowerCase()}…`}
          value={inputValue}
          onFocus={() => {
            setQuery("");
            setOpen(true);
          }}
          onChange={(event) => handleInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
              setQuery("");
            } else if (event.key === "Enter" && open && visibleOptions[0]) {
              event.preventDefault();
              handleOptionSelect(visibleOptions[0].item);
            }
          }}
        />
      </label>
      <div className="graph-object-authoring-ref-picker-actions">
        {value ? (
          <button
            type="button"
            className="graph-object-authoring-ref-picker-clear"
            aria-label={`Clear ${label}`}
            onClick={() => {
              onChange(null);
              setQuery("");
              setOpen(false);
            }}
          >
            Clear
          </button>
        ) : null}
        <button
          type="button"
          className="graph-object-authoring-ref-picker-manual"
          onClick={() => {
            handleSelectChange("manual");
            setOpen(false);
            setQuery("");
          }}
        >
          Enter manually
        </button>
      </div>
      {open ? (
        <div
          id={listboxId}
          className="graph-object-authoring-ref-picker-results"
          role="listbox"
          aria-label={`${label} search results`}
          data-testid="graph-object-authoring-search-results"
        >
          {visibleOptions.map(({ item }) => (
            <button
              key={item.key}
              type="button"
              role="option"
              aria-selected={item.encodedValue === selectedOptionValue}
              className="graph-object-authoring-ref-picker-option"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => handleOptionSelect(item)}
            >
              <span className="graph-object-authoring-ref-picker-option-label">{item.label}</span>
              <span className="graph-object-authoring-ref-picker-option-meta">
                {item.meta ?? item.group}
              </span>
            </button>
          ))}
          {!visibleOptions.length ? (
            <p className="graph-object-authoring-ref-picker-empty">
              No objects match “{query}”. Try an alias, kind, or source.
            </p>
          ) : null}
          {showAll || hasMoreOptions ? (
            <button
              type="button"
              className="graph-object-authoring-ref-picker-show-all"
              data-testid="graph-object-authoring-show-all-objects"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => setShowAll((current) => !current)}
            >
              {showAll
                ? "Show fewer objects"
                : query.trim()
                  ? `Show all matches (${rankedOptions.length})`
                  : `Show all objects (${rankedOptions.length})`}
            </button>
          ) : null}
        </div>
      ) : null}
      {value?.refKind === "manual_ref" ? (
        <input
          type="text"
          aria-label={`${label} manual label`}
          placeholder={manualPlaceholder}
          value={value.label}
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
