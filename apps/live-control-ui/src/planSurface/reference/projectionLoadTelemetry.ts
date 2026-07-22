/** Shared dogfood timing for World Graph / Recap / Graph Review projection loads. */

export type ProjectionLoadTelemetryMeta = {
  loader: string;
  campaignId?: string | null;
  sessionId?: string | null;
  /** Alias retained for Plan resolver dogfood logs. */
  focusSessionId?: string | null;
  scopeMode?: string | null;
  authority?: string | null;
  projectionSource?: string | null;
};

let projectionLoadGeneration = 0;

export function markProjectionLoadStart(loader = "projection"): string {
  projectionLoadGeneration += 1;
  const markName = `dmb:wg-projection:start:${loader}:${projectionLoadGeneration}`;
  if (typeof performance !== "undefined" && typeof performance.mark === "function") {
    performance.mark(markName);
  }
  return markName;
}

export function measureProjectionLoad(
  startMark: string,
  outcome: string,
  meta: ProjectionLoadTelemetryMeta,
): number | null {
  const endMark = `dmb:wg-projection:end:${projectionLoadGeneration}`;
  const measureName = `dmb:wg-projection:load:${meta.loader}:${projectionLoadGeneration}`;
  let durationMs: number | null = null;
  if (typeof performance !== "undefined" && typeof performance.mark === "function") {
    performance.mark(endMark);
    try {
      if (typeof performance.measure === "function") {
        performance.measure(measureName, startMark, endMark);
        const entries = performance.getEntriesByName(measureName);
        const last = entries[entries.length - 1];
        if (last) {
          durationMs = Math.round(last.duration);
        }
      }
    } catch {
      durationMs = null;
    }
  }
  const sessionId = meta.sessionId ?? meta.focusSessionId ?? null;
  // Never include corpus prose / markdown in this payload.
  console.debug("[dmb] world-graph projection", {
    loader: meta.loader,
    campaignId: meta.campaignId ?? null,
    sessionId,
    focusSessionId: meta.focusSessionId ?? sessionId,
    scopeMode: meta.scopeMode ?? null,
    authority: meta.authority ?? null,
    projectionSource: meta.projectionSource ?? null,
    outcome,
    durationMs,
  });
  return durationMs;
}
