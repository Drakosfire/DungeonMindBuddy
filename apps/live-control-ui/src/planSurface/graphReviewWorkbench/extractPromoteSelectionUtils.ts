import type { ExtractPromotionReviewItem } from "../../api/types";

export function initialPromoteSelection(
  items: ExtractPromotionReviewItem[],
): Set<string> {
  return new Set(
    items
      .filter((item) => item.selectable && item.selectedByDefault)
      .map((item) => item.assertionId),
  );
}

/**
 * Toggle selection while preserving Kernel edge-endpoint invariants:
 * selecting a relationship also selects its newly created endpoint nodes;
 * deselecting a node also deselects dependent relationships.
 */
export function togglePromoteSelection(
  items: ExtractPromotionReviewItem[],
  selected: Set<string>,
  assertionId: string,
): Set<string> {
  const item = items.find((candidate) => candidate.assertionId === assertionId);
  if (!item || !item.selectable) {
    return selected;
  }

  const next = new Set(selected);
  if (next.has(assertionId)) {
    next.delete(assertionId);
    for (const other of items) {
      const deps = other.dependsOnAssertionIds ?? [];
      if (deps.includes(assertionId)) {
        next.delete(other.assertionId);
      }
    }
    return next;
  }

  for (const depId of item.dependsOnAssertionIds ?? []) {
    const dep = items.find((candidate) => candidate.assertionId === depId);
    if (dep?.selectable) {
      next.add(depId);
    }
  }
  next.add(assertionId);
  return next;
}

export function countSelectableSelected(
  items: ExtractPromotionReviewItem[],
  selected: Set<string>,
): number {
  let count = 0;
  for (const item of items) {
    if (item.selectable && selected.has(item.assertionId)) {
      count += 1;
    }
  }
  return count;
}
