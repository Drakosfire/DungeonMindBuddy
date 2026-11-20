// Session-local view state only. Current draft membership remains authoritative.
export function planScenePositionKey(worldId: string, documentId: string): string {
  return `dmb:plan-scene-position:v1:${JSON.stringify([worldId, documentId])}`;
}

export function readPlanScenePosition(worldId: string, documentId: string): string | null {
  try {
    const raw = sessionStorage.getItem(planScenePositionKey(worldId, documentId));
    const value: unknown = raw === null ? null : JSON.parse(raw);
    return typeof value === "string" && value.trim() ? value : null;
  } catch { return null; }
}

export function writePlanScenePosition(worldId: string, documentId: string, sceneId: string | null): void {
  try {
    const key = planScenePositionKey(worldId, documentId);
    if (sceneId === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(sceneId));
  } catch {
    // Optional navigation memory must never block the owning document writer.
  }
}
