import { useMemo } from "react";

import {
  buildManualObjectRef,
  buildObjectRefFromInspectedNode,
  buildObjectRefFromObjectProposal,
  type GraphObjectAuthoringObjectProposal,
  type GraphObjectAuthoringObjectRef,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";

export interface GraphObjectAuthoringInspectedNode {
  node_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
}

type PickerOptionValue =
  | { source: "empty" }
  | { source: "manual" }
  | { source: "local_proposal"; localProposalId: string }
  | { source: "existing_node"; nodeId: string };

function encodeOptionValue(value: PickerOptionValue): string {
  if (value.source === "local_proposal") {
    return `local_proposal:${value.localProposalId}`;
  }
  if (value.source === "existing_node") {
    return `existing_node:${value.nodeId}`;
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

export function GraphObjectAuthoringObjectRefPicker({
  label,
  value,
  onChange,
  proposals,
  existingNodes = [],
  manualPlaceholder = "Type a label for an object not staged yet",
}: {
  label: string;
  value: GraphObjectAuthoringObjectRef | null;
  onChange: (ref: GraphObjectAuthoringObjectRef | null) => void;
  proposals: GraphObjectAuthoringProposal[];
  existingNodes?: GraphObjectAuthoringInspectedNode[];
  manualPlaceholder?: string;
}) {
  const objectProposals = stagedObjectProposals(proposals);
  const sortedExistingNodes = useMemo(() => dedupeAndSortNodes(existingNodes), [existingNodes]);
  const showManualInput = value?.refKind === "manual_ref";
  // Derived entirely from `value` (no local echo state) so a parent-driven reset
  // (e.g. after staging clears the form) can never leave stale manual input behind
  // in an always-mounted picker instance.
  const manualLabelValue = value?.refKind === "manual_ref" ? value.label : "";

  const selectedOptionValue: string = (() => {
    if (!value) return encodeOptionValue({ source: "empty" });
    if (value.refKind === "manual_ref") return encodeOptionValue({ source: "manual" });
    if (value.refKind === "local_proposal" && value.localProposalId) {
      return encodeOptionValue({ source: "local_proposal", localProposalId: value.localProposalId });
    }
    if (value.refKind === "existing_graph_node" && value.nodeId) {
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
    if (rawValue.startsWith("existing_node:")) {
      const nodeId = rawValue.slice("existing_node:".length);
      const node = sortedExistingNodes.find((candidate) => candidate.node_id === nodeId);
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
                  {proposal.objectRef.label}
                </option>
              ))}
            </optgroup>
          ) : null}
          {sortedExistingNodes.length ? (
            <optgroup label="Existing graph objects">
              {sortedExistingNodes.map((node) => (
                <option
                  key={node.node_id}
                  value={encodeOptionValue({ source: "existing_node", nodeId: node.node_id })}
                >
                  {node.kind ? `${node.label} (${node.kind})` : node.label}
                </option>
              ))}
            </optgroup>
          ) : null}
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
        </p>
      ) : null}
    </div>
  );
}
