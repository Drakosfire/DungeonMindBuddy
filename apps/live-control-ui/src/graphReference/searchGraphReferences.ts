import type { GraphReferenceSearchItem } from "./types";

function normalizeSearchText(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function itemSearchHaystack(item: GraphReferenceSearchItem): string {
  const parts = [
    item.label,
    item.nodeId,
    item.kind,
    item.role,
    ...item.aliases,
    item.summary ?? "",
    item.scopeLabel,
  ];
  return normalizeSearchText(parts.filter(Boolean).join(" "));
}

/**
 * Client-side search over graph reference search items.
 * Matches label, aliases, kind, role, node id, summary, and scope label.
 * Empty query returns all items (caller may still sort/limit).
 */
export function searchGraphReferences(
  items: Iterable<GraphReferenceSearchItem>,
  query: string,
  options?: { limit?: number },
): GraphReferenceSearchItem[] {
  const normalizedQuery = normalizeSearchText(query);
  const tokens = normalizedQuery ? normalizedQuery.split(" ").filter(Boolean) : [];
  const limit = options?.limit;

  const matched: GraphReferenceSearchItem[] = [];
  for (const item of items) {
    if (tokens.length === 0) {
      matched.push(item);
    } else {
      const haystack = itemSearchHaystack(item);
      if (tokens.every((token) => haystack.includes(token))) {
        matched.push(item);
      }
    }
    if (limit != null && matched.length >= limit) break;
  }

  return matched;
}

export function sortGraphReferenceItems(
  items: GraphReferenceSearchItem[],
): GraphReferenceSearchItem[] {
  return [...items].sort((a, b) => {
    const kindCmp = String(a.kind).localeCompare(String(b.kind));
    if (kindCmp !== 0) return kindCmp;
    return String(a.label).localeCompare(String(b.label));
  });
}
