import type { GraphProjectionNodeView } from "../../api/types";

function normalizeSearchText(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function nodeSearchHaystack(node: GraphProjectionNodeView): string {
  const parts = [
    node.label,
    node.node_id,
    node.kind,
    node.role,
    ...(node.aliases ?? []),
    node.summary ?? "",
  ];
  return normalizeSearchText(parts.filter(Boolean).join(" "));
}

/**
 * Client-side search over Union Supergraph projection nodes.
 * Matches label, aliases, kind, role, node id, and summary.
 * Empty query returns all nodes (caller may still sort/limit).
 */
export function searchGraphProjectionNodes(
  nodes: Iterable<GraphProjectionNodeView>,
  query: string,
  options?: { limit?: number },
): GraphProjectionNodeView[] {
  const normalizedQuery = normalizeSearchText(query);
  const tokens = normalizedQuery ? normalizedQuery.split(" ").filter(Boolean) : [];
  const limit = options?.limit;

  const matched: GraphProjectionNodeView[] = [];
  for (const node of nodes) {
    if (tokens.length === 0) {
      matched.push(node);
    } else {
      const haystack = nodeSearchHaystack(node);
      if (tokens.every((token) => haystack.includes(token))) {
        matched.push(node);
      }
    }
    if (limit != null && matched.length >= limit) break;
  }

  return matched;
}

export function sortGraphProjectionNodes(
  nodes: GraphProjectionNodeView[],
): GraphProjectionNodeView[] {
  return [...nodes].sort((a, b) => {
    const kindCmp = String(a.kind).localeCompare(String(b.kind));
    if (kindCmp !== 0) return kindCmp;
    return String(a.label).localeCompare(String(b.label));
  });
}
