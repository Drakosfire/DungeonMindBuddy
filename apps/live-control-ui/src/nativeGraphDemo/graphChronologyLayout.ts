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
    // Radial separation alone clears the diagonal of a session cluster.
    const pitch = Math.ceil(Math.hypot(760, spread + 180));
    const outerRadius = pitch * (ordered.length - 1);
    const center = { x: outerRadius + 80, y: laneTop + outerRadius + 80 };
    ordered.forEach(([session, ids], index) => {
      const angle = index * 0.8;
      const radius = pitch * index;
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
    laneTop += mode === "line" ? spread + 240 : 2 * (outerRadius + 80) + spread;
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

  // Use a shared grid for non-Events so adjacent anchors cannot place
  // objects on top of each other. Reserve cells near every Event first.
  const cellSize = 72;
  const occupied = new Set<string>();
  for (const point of positions.values()) {
    for (let x = Math.ceil((point.x - 64) / cellSize); x <= Math.floor((point.x + 64) / cellSize); x++) {
      for (let y = Math.ceil((point.y - 64) / cellSize); y <= Math.floor((point.y + 64) / cellSize); y++) {
        occupied.add(`${x}:${y}`);
      }
    }
  }
  const counts = new Map<string, number>();
  const detachedY = laneTop + Math.ceil(unplaced.length / 8) * 80 + 440;
  for (const node of [...graph.nodes].sort((a, b) => a.id.localeCompare(b.id))) {
    if (positions.has(node.id)) continue;
    const anchor = anchors.get(node.id)?.[0];
    const column = Math.round((anchor?.x ?? 80) / cellSize);
    const row = Math.round((anchor ? anchor.y - 100 : detachedY) / cellSize);
    const columns = anchor ? 5 : 16;
    const key = `${column}:${row}:${columns}`;
    let slot = counts.get(key) ?? 0;
    while (true) {
      const x = column + slot % columns - (anchor ? 2 : 0);
      const y = row + Math.floor(slot / columns) * (anchor ? -1 : 1);
      const cell = `${x}:${y}`;
      slot += 1;
      if (occupied.has(cell)) continue;
      occupied.add(cell);
      counts.set(key, slot);
      positions.set(node.id, { x: x * cellSize, y: y * cellSize });
      break;
    }
  }

  return { positions, markers, unplacedMarker, eventIds: events.map(event => event.node.id) };
}
