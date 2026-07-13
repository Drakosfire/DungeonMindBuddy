import type { GraphProjectionNodeView } from "../../api/types";
import {
  RUNBOOK_REF_TYPES,
  type RunbookReferenceAttrs,
  type RunbookRefType,
} from "../../tiptap/references/runbookReferences";

const KIND_TO_REF_TYPE: Record<string, RunbookRefType> = {
  npc: "npc",
  actor: "npc",
  character: "npc",
  pc: "npc",
  location: "location",
  place: "location",
  landmark: "location",
  statblock: "statblock",
  "roll-table": "roll-table",
  roll_table: "roll-table",
  citation: "citation",
};

function normalizeKind(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/_/g, "-");
}

function sanitizeRefId(nodeId: string): string {
  const trimmed = String(nodeId || "").trim().toLowerCase();
  const sanitized = trimmed.replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  return sanitized || "graph-node";
}

/**
 * Build a Plan chip from a graph projection node.
 * Prefer exact node_id as refId so the graph-aware resolver hits by id.
 * Unknown graph kinds use refType "node" (not a corpus-index type).
 */
export function runbookReferenceFromGraphNode(
  node: GraphProjectionNodeView,
): RunbookReferenceAttrs {
  const normalizedKind = normalizeKind(node.kind);
  const mapped = KIND_TO_REF_TYPE[normalizedKind];
  const refType: RunbookRefType =
    mapped ??
    (RUNBOOK_REF_TYPES.includes(normalizedKind as RunbookRefType)
      ? (normalizedKind as RunbookRefType)
      : "node");

  const rawId = String(node.node_id || "").trim();
  const refId = /^[a-z0-9][a-z0-9_-]*$/i.test(rawId) ? rawId.toLowerCase() : sanitizeRefId(rawId);

  return {
    kind: "ref",
    refType,
    refId,
    label: String(node.label || node.node_id).trim() || node.node_id,
  };
}
