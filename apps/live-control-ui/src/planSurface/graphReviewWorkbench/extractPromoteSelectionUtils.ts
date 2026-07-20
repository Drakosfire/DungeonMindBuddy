import type { ExtractPromotionReviewItem } from "../../api/types";

export function initialPromoteSelection(
  items: ExtractPromotionReviewItem[],
): Set<string> {
  return new Set(
    items
      .filter((item) => item.selectable && item.selectedByDefault)
      .map((item) => item.sliceQualifiedId),
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
  sliceQualifiedId: string,
): Set<string> {
  const item = items.find((candidate) => candidate.sliceQualifiedId === sliceQualifiedId);
  if (!item || !item.selectable) {
    return selected;
  }

  const next = new Set(selected);
  if (next.has(sliceQualifiedId)) {
    next.delete(sliceQualifiedId);
    for (const other of items) {
      const deps = other.dependsOnSliceQualifiedIds ?? [];
      if (deps.includes(sliceQualifiedId)) {
        next.delete(other.sliceQualifiedId);
      }
    }
    return next;
  }

  for (const depId of item.dependsOnSliceQualifiedIds ?? []) {
    const dep = items.find((candidate) => candidate.sliceQualifiedId === depId);
    if (dep?.selectable) {
      next.add(depId);
    }
  }
  next.add(sliceQualifiedId);
  return next;
}

export function countSelectableSelected(
  items: ExtractPromotionReviewItem[],
  selected: Set<string>,
): number {
  let count = 0;
  for (const item of items) {
    if (item.selectable && selected.has(item.sliceQualifiedId)) {
      count += 1;
    }
  }
  return count;
}

/** Slice-qualified selectors posted to confirm (assertionIds payload). */
export function selectedPromoteAssertionIds(
  items: ExtractPromotionReviewItem[],
  selected: Set<string>,
): string[] {
  return items
    .filter((item) => item.selectable && selected.has(item.sliceQualifiedId))
    .map((item) => item.sliceQualifiedId);
}
