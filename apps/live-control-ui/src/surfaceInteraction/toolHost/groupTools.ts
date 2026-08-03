import type { SurfaceInteractionToolContribution } from "../types";

export interface ToolHostGroup {
  groupId: string | null;
  groupLabel: string | null;
  groupOrder: number;
  tools: readonly SurfaceInteractionToolContribution[];
}

/**
 * Deterministic Tool grouping for ToolHost.
 * Sort by groupOrder, then groupId (null/pinned first within same order),
 * then itemOrder, then id — never by label or insertion accident.
 */
export function groupToolContributions(
  tools: readonly SurfaceInteractionToolContribution[],
): readonly ToolHostGroup[] {
  const sorted = [...tools].sort((left, right) => {
    if (left.placement.groupOrder !== right.placement.groupOrder) {
      return left.placement.groupOrder - right.placement.groupOrder;
    }
    const leftGroup = left.placement.groupId ?? "";
    const rightGroup = right.placement.groupId ?? "";
    if (leftGroup !== rightGroup) {
      if (left.placement.groupId === null) return -1;
      if (right.placement.groupId === null) return 1;
      return leftGroup < rightGroup ? -1 : 1;
    }
    if (left.placement.itemOrder !== right.placement.itemOrder) {
      return left.placement.itemOrder - right.placement.itemOrder;
    }
    return left.id < right.id ? -1 : left.id > right.id ? 1 : 0;
  });

  const groups: ToolHostGroup[] = [];
  for (const tool of sorted) {
    const last = groups[groups.length - 1];
    if (
      last
      && last.groupId === tool.placement.groupId
      && last.groupOrder === tool.placement.groupOrder
    ) {
      (last.tools as SurfaceInteractionToolContribution[]).push(tool);
      continue;
    }
    groups.push({
      groupId: tool.placement.groupId,
      groupLabel: tool.placement.groupLabel,
      groupOrder: tool.placement.groupOrder,
      tools: [tool],
    });
  }
  return groups;
}
