import {
  formatPlayableElementMarker,
  validatePlayableOptionItemAttrs,
} from "../playable/playableElementIdentity";

type JsonNodeLike = {
  type?: unknown;
  attrs?: Record<string, unknown> | null;
  content?: unknown;
};

function firstListItem(listNode: JsonNodeLike): JsonNodeLike | null {
  const content = listNode.content;
  if (!Array.isArray(content) || content.length === 0) return null;
  const first = content[0];
  if (first === null || typeof first !== "object") return null;
  const item = first as JsonNodeLike;
  return item.type === "listItem" ? item : null;
}

/**
 * Canonical v2 Option marker line for a list whose first item carries option
 * identity, or null when the list is not a marked Option. Emission is keyed
 * to the first list item because Markdown admission binds a preceding option
 * marker to exactly that position; emitting for any other item would rebind
 * identity on re-import.
 */
export function formatPlayableOptionListMarker(listNode: JsonNodeLike): string | null {
  const item = firstListItem(listNode);
  if (item === null) return null;
  const validated = validatePlayableOptionItemAttrs(item.attrs);
  if (validated.status !== "canonical") return null;
  return formatPlayableElementMarker(validated.identity);
}
