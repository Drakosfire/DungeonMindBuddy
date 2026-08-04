import { describe, expect, it, vi } from "vitest";

import type { SurfaceInteractionToolContribution } from "../types";
import { groupToolContributions } from "./groupTools";

function makeTool(
  overrides: Partial<SurfaceInteractionToolContribution> &
    Pick<SurfaceInteractionToolContribution, "id" | "label">,
): SurfaceInteractionToolContribution {
  return {
    placement: {
      groupId: null,
      groupLabel: null,
      groupOrder: 0,
      itemOrder: 0,
    },
    availability: { status: "enabled" },
    activation: { kind: "command", invoke: vi.fn() },
    ...overrides,
  };
}

describe("groupToolContributions", () => {
  it("sorts by groupOrder, then groupId (pinned first), then itemOrder, then id — not by label", () => {
    const tools = [
      makeTool({
        id: "z-tool",
        label: "Zebra",
        placement: {
          groupId: "alpha",
          groupLabel: "Alpha",
          groupOrder: 1,
          itemOrder: 1,
        },
      }),
      makeTool({
        id: "a-tool",
        label: "Apple",
        placement: {
          groupId: "alpha",
          groupLabel: "Alpha",
          groupOrder: 1,
          itemOrder: 0,
        },
      }),
      makeTool({
        id: "pinned",
        label: "Pinned late label",
        placement: {
          groupId: null,
          groupLabel: null,
          groupOrder: 0,
          itemOrder: 99,
        },
      }),
      makeTool({
        id: "beta-tool",
        label: "Beta",
        placement: {
          groupId: "beta",
          groupLabel: "Beta",
          groupOrder: 2,
          itemOrder: 0,
        },
      }),
    ];

    const groups = groupToolContributions(tools);
    expect(groups.map((group) => group.groupId)).toEqual([null, "alpha", "beta"]);
    expect(groups[0]?.tools.map((tool) => tool.id)).toEqual(["pinned"]);
    expect(groups[1]?.tools.map((tool) => tool.id)).toEqual(["a-tool", "z-tool"]);
    expect(groups[2]?.tools.map((tool) => tool.id)).toEqual(["beta-tool"]);
  });

  it("keeps pinned tools in a null groupId bucket separate from labeled groups", () => {
    const tools = [
      makeTool({
        id: "pinned-a",
        label: "Pinned A",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
      }),
      makeTool({
        id: "group-a",
        label: "Group A",
        placement: {
          groupId: "tools",
          groupLabel: "Tools",
          groupOrder: 0,
          itemOrder: 0,
        },
      }),
    ];

    const groups = groupToolContributions(tools);
    expect(groups).toHaveLength(2);
    expect(groups[0]).toMatchObject({ groupId: null, groupLabel: null });
    expect(groups[1]).toMatchObject({ groupId: "tools", groupLabel: "Tools" });
  });

  it("uses stable id tie-breakers when placement fields collide", () => {
    const tools = [
      makeTool({
        id: "a\u001fb",
        label: "Later label",
        placement: {
          groupId: "tie",
          groupLabel: "Tie",
          groupOrder: 0,
          itemOrder: 0,
        },
      }),
      makeTool({
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

    const groups = groupToolContributions(tools);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.tools.map((tool) => tool.id)).toEqual(["a\u001fb", "a:b"]);
  });
});
