import { describe, expect, it } from "vitest";
import { layoutGraphChronology } from "./graphChronologyLayout";

describe("chronology canvas geometry", () => {
  it.each(["line", "spiral"] as const)("separates populated adjacent sessions in %s", mode => {
    const events = Array.from({ length: 19 }, (_, i) => ({
      node: { id: `event-${i}`, name: `Event ${i}`, kind: "event" },
      assertions: [],
      placements: [],
      placementSessions: new Map([["campaign", new Set([i < 18 ? 1 : 2])]]),
      campaignIds: ["campaign"],
      occurrences: [],
      sourceSessions: [],
    }));
    const graph = { nodes: events.map(event => event.node), edges: [] } as Parameters<typeof layoutGraphChronology>[2];
    const layout = layoutGraphChronology(events, mode, graph);

    expect(layout.markers.map(marker => marker.session)).toEqual([1, 2]);
    const adjacent = layout.positions.get("event-18")!;
    for (const event of events.slice(0, 18)) {
      const point = layout.positions.get(event.node.id)!;
      expect(Math.hypot(point.x - adjacent.x, point.y - adjacent.y)).toBeGreaterThan(64);
    }
  });
});
