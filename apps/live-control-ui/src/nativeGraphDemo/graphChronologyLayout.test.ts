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
    const linked = Array.from({ length: 10 }, (_, i) => ({
      id: `person-${i}`, name: `Person ${i}`, kind: "character",
    }));
    const graph = {
      nodes: [...events.map(event => event.node), ...linked],
      edges: linked.map((node, i) => ({
        id: `link-${i}`, source_id: node.id, target_id: `event-${i < 5 ? 0 : 1}`, predicate: "participates",
      })),
    } as Parameters<typeof layoutGraphChronology>[2];
    const layout = layoutGraphChronology(events, mode, graph);

    expect(layout.markers.map(marker => marker.session)).toEqual([1, 2]);
    for (const [id, point] of layout.positions) {
      if (!id.startsWith("person-")) continue;
      for (const [otherId, other] of layout.positions) {
        if (id === otherId) continue;
        expect(Math.hypot(point.x - other.x, point.y - other.y)).toBeGreaterThanOrEqual(64);
      }
    }
    const adjacent = layout.positions.get("event-18")!;
    for (const event of events.slice(0, 18)) {
      const point = layout.positions.get(event.node.id)!;
      expect(Math.hypot(point.x - adjacent.x, point.y - adjacent.y)).toBeGreaterThan(64);
    }
  });
});
