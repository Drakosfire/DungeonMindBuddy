import { describe, expect, it, vi } from "vitest";

import type { SurfaceInteractionEditCommandContribution } from "../types";
import { groupEditCommands } from "./groupEditCommands";

function makeEdit(
  overrides: Partial<SurfaceInteractionEditCommandContribution> &
    Pick<SurfaceInteractionEditCommandContribution, "id" | "label">,
): SurfaceInteractionEditCommandContribution {
  return {
    placement: {
      groupId: null,
      groupLabel: null,
      groupOrder: 0,
      itemOrder: 0,
    },
    availability: { status: "enabled" },
    target: { kind: "document", id: "doc-1" },
    invoke: vi.fn(),
    ...overrides,
  };
}

describe("groupEditCommands", () => {
  it("puts pinned groups first, then sorts by groupOrder, groupId, itemOrder, id", () => {
    const commands = [
      makeEdit({
        id: "z-cmd",
        label: "Zebra",
        placement: {
          groupId: "alpha",
          groupLabel: "Alpha",
          groupOrder: 1,
          itemOrder: 1,
          groupDefaultOpen: true,
        },
      }),
      makeEdit({
        id: "a-cmd",
        label: "Apple",
        placement: {
          groupId: "alpha",
          groupLabel: "Alpha",
          groupOrder: 1,
          itemOrder: 0,
          groupDefaultOpen: true,
        },
      }),
      makeEdit({
        id: "pinned",
        label: "Pinned late label",
        placement: {
          groupId: null,
          groupLabel: null,
          groupOrder: 99,
          itemOrder: 99,
        },
      }),
      makeEdit({
        id: "beta-cmd",
        label: "Beta",
        placement: {
          groupId: "beta",
          groupLabel: "Beta",
          groupOrder: 2,
          itemOrder: 0,
        },
      }),
    ];

    const groups = groupEditCommands(commands);
    expect(groups.map((group) => group.groupId)).toEqual([null, "alpha", "beta"]);
    expect(groups[0]?.commands.map((command) => command.id)).toEqual(["pinned"]);
    expect(groups[0]?.groupDefaultOpen).toBe(true);
    expect(groups[1]?.commands.map((command) => command.id)).toEqual(["a-cmd", "z-cmd"]);
    expect(groups[1]?.groupDefaultOpen).toBe(true);
    expect(groups[2]?.groupDefaultOpen).toBe(false);
  });

  it("resolves groupDefaultOpen from the first command in the group metadata", () => {
    const commands = [
      makeEdit({
        id: "first",
        label: "First",
        placement: {
          groupId: "fold",
          groupLabel: "Fold",
          groupOrder: 0,
          itemOrder: 0,
          groupDefaultOpen: false,
        },
      }),
      makeEdit({
        id: "second",
        label: "Second",
        placement: {
          groupId: "fold",
          groupLabel: "Fold",
          groupOrder: 0,
          itemOrder: 1,
          groupDefaultOpen: false,
        },
      }),
    ];
    const groups = groupEditCommands(commands);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.groupDefaultOpen).toBe(false);
  });

  it("uses stable id tie-breakers when placement fields collide", () => {
    const commands = [
      makeEdit({
        id: "a\u001fb",
        label: "Later label",
        placement: {
          groupId: "tie",
          groupLabel: "Tie",
          groupOrder: 0,
          itemOrder: 0,
        },
      }),
      makeEdit({
        id: "a:b",
        label: "Earlier label",
        placement: {
          groupId: "tie",
          groupLabel: "Tie",
          groupOrder: 0,
          itemOrder: 0,
        },
      }),
    ];

    const groups = groupEditCommands(commands);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.commands.map((command) => command.id)).toEqual(["a\u001fb", "a:b"]);
  });
});
