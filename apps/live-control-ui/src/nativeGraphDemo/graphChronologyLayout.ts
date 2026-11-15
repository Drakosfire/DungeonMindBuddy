import type { NativeGraph } from "./nativeGraphDemoApi";
import type { buildGraphChronology } from "./graphChronologyModel";

export type ChronologyLayout = "line" | "spiral";
type Point = { x: number; y: number };
type EventRow = ReturnType<typeof buildGraphChronology>[number];

export function layoutGraphChronology(events: readonly EventRow[], mode: ChronologyLayout, graph: NativeGraph) {
  const campaigns = new Map<string, Map<number, string[]>>();
  const unplaced: string[] = [];
  for (const event of events) {
    const placements = [...event.placementSessions].flatMap(([campaign, sessions]) =>
      [...sessions].map(session => ({ campaign, session })));
    // A node can occupy one position. Conflicting placements remain inspectable.
    if (placements.length !== 1) {
      unplaced.push(event.node.id);
      continue;
    }
    const { campaign, session } = placements[0];
    const sessions = campaigns.get(campaign) ?? new Map<number, string[]>();
    const ids = sessions.get(session) ?? [];
    ids.push(event.node.id);
    sessions.set(session, ids);
    campaigns.set(campaign, sessions);
  }

  const positions = new Map<string, Point>();
  const markers: { campaign: string; session: number; point: Point }[] = [];
  let laneTop = 0;
  for (const [campaign, sessions] of [...campaigns].sort(([a], [b]) => a.localeCompare(b))) {
    const ordered = [...sessions].sort(([a], [b]) => a - b);
    const spread = Math.max(...ordered.map(([, ids]) => Math.ceil(ids.length / 8))) * 80;
    const pitch = Math.max(760, spread * 2 + 180);
    const outerRadius = pitch * ordered.length / (2 * Math.PI);
    const center = { x: outerRadius + pitch, y: laneTop + outerRadius + pitch };
    ordered.forEach(([session, ids], index) => {
      const angle = index * 0.8;
      const radius = pitch * angle / (2 * Math.PI);
      const point = mode === "line"
        ? { x: pitch * index + 80, y: laneTop + 80 }
        : { x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius };
      markers.push({ campaign, session, point });
      ids.sort().forEach((id, slot) => {
        positions.set(id, {
          x: point.x + slot % 8 * 80,
          y: point.y + (Math.floor(slot / 8) + 1) * 80,
        });
      });
    });
    laneTop += mode === "line" ? spread + 240 : 2 * (outerRadius + pitch) + spread;
  }
  const unplacedMarker = unplaced.length ? { x: 80, y: laneTop + 80 } : null;
  unplaced.sort().forEach((id, slot) => {
    positions.set(id, { x: 80 + slot % 8 * 80, y: laneTop + 160 + Math.floor(slot / 8) * 80 });
  });

  const anchors = new Map<string, Point[]>();
  for (const edge of graph.edges) {
    const source = positions.get(edge.source_id);
    const target = positions.get(edge.target_id);
    if (Boolean(source) === Boolean(target)) continue;
    const id = source ? edge.target_id : edge.source_id;
    const points = anchors.get(id) ?? [];
    points.push((source ?? target)!);
    anchors.set(id, points);
  }

  const counts = new Map<string, number>();
  let detachedSlot = 0;
  const detachedY = laneTop + Math.ceil(unplaced.length / 8) * 80 + 440;
  for (const node of [...graph.nodes].sort((a, b) => a.id.localeCompare(b.id))) {
    if (positions.has(node.id)) continue;
    const points = anchors.get(node.id);
    if (!points) {
      positions.set(node.id, { x: 80 + detachedSlot % 16 * 100, y: detachedY + Math.floor(detachedSlot / 16) * 100 });
      detachedSlot += 1;
      continue;
    }
    const anchor = points[0];
    const key = `${anchor.x}:${anchor.y}`;
    const slot = counts.get(key) ?? 0;
    counts.set(key, slot + 1);
    positions.set(node.id, {
      x: anchor.x + (slot % 5 - 2) * 72,
      y: anchor.y - 100 - Math.floor(slot / 5) * 72,
    });
  }

  return { positions, markers, unplacedMarker, eventIds: events.map(event => event.node.id) };
}
