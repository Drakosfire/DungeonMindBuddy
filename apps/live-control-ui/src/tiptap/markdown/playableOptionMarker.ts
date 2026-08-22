import {
  formatPlayableElementMarker,
  validatePlayableOptionItemAttrs,
} from "../playable/playableElementIdentity";

type JsonNodeLike = {
  type?: unknown;
  attrs?: Record<string, unknown> | null;
  content?: unknown;
};

/**
 * Canonical v2 Option marker line for one list item, or null when the item
 * carries no canonical option identity.
 *
 * Emission is per item: a marked first item emits its marker immediately
 * before the list (the canonical authored shape), and a marked later item —
 * reachable through ordinary list editing such as merging two option lists —
 * emits its marker immediately before its own item. On re-import the marker
 * interrupts the list and binds to the first item of the following list, so
 * every marked Option keeps its identity and edges through Save/reload even
 * when several marked Options share one editor list.
 */
export function formatPlayableOptionListItemMarker(itemNode: JsonNodeLike): string | null {
  if (itemNode.type !== "listItem") return null;
  const validated = validatePlayableOptionItemAttrs(itemNode.attrs);
  if (validated.status !== "canonical") return null;
  return formatPlayableElementMarker(validated.identity);
}
