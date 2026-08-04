import type { SurfaceInteractionEditCommandContribution } from "../types";

export interface EditHostGroup {
  groupId: string | null;
  groupLabel: string | null;
  groupOrder: number;
  /** Resolved fold default: pinned always open; else first declared groupDefaultOpen or false. */
  groupDefaultOpen: boolean;
  commands: readonly SurfaceInteractionEditCommandContribution[];
}

/**
 * Deterministic Edit grouping for EditHost.
 * Pinned (groupId null) first, then by groupOrder, groupId, itemOrder, id —
 * never by label or insertion accident.
 */
export function groupEditCommands(
  commands: readonly SurfaceInteractionEditCommandContribution[],
): readonly EditHostGroup[] {
  const sorted = [...commands].sort((left, right) => {
    const leftPinned = left.placement.groupId === null;
    const rightPinned = right.placement.groupId === null;
    if (leftPinned !== rightPinned) return leftPinned ? -1 : 1;
    if (left.placement.groupOrder !== right.placement.groupOrder) {
      return left.placement.groupOrder - right.placement.groupOrder;
    }
    const leftGroup = left.placement.groupId ?? "";
    const rightGroup = right.placement.groupId ?? "";
    if (leftGroup !== rightGroup) {
      return leftGroup < rightGroup ? -1 : 1;
    }
    if (left.placement.itemOrder !== right.placement.itemOrder) {
      return left.placement.itemOrder - right.placement.itemOrder;
    }
    return left.id < right.id ? -1 : left.id > right.id ? 1 : 0;
  });

  const groups: EditHostGroup[] = [];
  for (const command of sorted) {
    const last = groups[groups.length - 1];
    if (
      last
      && last.groupId === command.placement.groupId
      && last.groupOrder === command.placement.groupOrder
    ) {
      (last.commands as SurfaceInteractionEditCommandContribution[]).push(command);
      continue;
    }
    const pinned = command.placement.groupId === null;
    groups.push({
      groupId: command.placement.groupId,
      groupLabel: command.placement.groupLabel,
      groupOrder: command.placement.groupOrder,
      groupDefaultOpen: pinned
        ? true
        : command.placement.groupDefaultOpen === true,
      commands: [command],
    });
  }
  return groups;
}
