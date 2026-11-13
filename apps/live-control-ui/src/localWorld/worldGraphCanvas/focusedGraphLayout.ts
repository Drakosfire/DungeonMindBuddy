export interface FocusPoint { readonly x: number; readonly y: number; readonly radius?: number }
/** A disposable view projection. Never persisted to the World or saved layout. */
export function focusedGraphLayout(points: ReadonlyMap<string, FocusPoint>, focusId: string): Map<string, FocusPoint> {
  const hub = points.get(focusId);
  if (!hub || points.size < 2) return new Map(points);
  const hubRadius = hub.radius ?? 56;
  const neighbors = [...points].filter(([id]) => id !== focusId).sort(([a, pa], [b, pb]) =>
    Math.atan2(pa.y - hub.y, pa.x - hub.x) - Math.atan2(pb.y - hub.y, pb.x - hub.x) || a.localeCompare(b));
  const largest = Math.max(...neighbors.map(([, p]) => p.radius ?? 56));
  const arranged = new Map<string, FocusPoint>();
  let remaining = neighbors.length, cursor = 0, ring = hubRadius + largest + 200, maxExtent = 0, ringIndex = 0;
  while (remaining) {
    const count = Math.min(remaining, Math.max(3, Math.floor(2 * Math.PI * ring / (2 * largest + 64))));
    for (let i = 0; i < count; i++) {
      const [id, point] = neighbors[cursor++];
      const angle = -Math.PI / 2 + 2 * Math.PI * i / count + ringIndex * .31;
      arranged.set(id, { ...point, x: Math.cos(angle) * ring, y: Math.sin(angle) * ring });
    }
    maxExtent = ring + largest + 80;
    remaining -= count; ring += 2 * largest + 200; ringIndex++;
  }
  arranged.set(focusId, { ...hub, x: 0, y: 0 });
  for (const [id, point] of arranged) arranged.set(id, { ...point, x: point.x + maxExtent, y: point.y + maxExtent });
  return arranged;
}
