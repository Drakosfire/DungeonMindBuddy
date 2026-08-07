/**
 * OPT-BENCH02: client-side World Graph surface experience marks.
 *
 * Dogfood / Playwright only — no product UI. Records a ring buffer on
 * `window.__DMB_WG_SURFACE_LATENCY__` and mirrors stages via performance.mark.
 */

export type SurfaceLatencyStage =
  | "projection_fetch"
  | "projection_ready"
  | "first_chip_paint"
  | "detail_glance_open"
  | "detail_full_open"
  | "surface_switch_start"
  | "surface_switch_end"
  | "build_projection_fetch"
  | "build_projection_ready"
  | "build_detail_open"
  | "client_cache_hit"
  | "client_cache_miss"
  | "client_cache_coalesced";

export type SurfaceLatencyRecord = {
  stage: SurfaceLatencyStage;
  /** `performance.now()` at record time. */
  t: number;
  durationMs?: number;
  meta?: Record<string, unknown>;
};

const RING_MAX = 256;
const MARK_PREFIX = "dmb:wg-surface:";
/** Survives full-document Plan↔Build `<a href>` navigations (OPT-BENCH02). */
const SESSION_STORAGE_KEY = "dmb:wg-surface-latency-ring";

let ring: SurfaceLatencyRecord[] = [];
let firstChipPainted = false;
let dogfoodInstalled = false;
let hydratedFromSession = false;

function nowMs(): number {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

function syncWindowMirror(): void {
  const g = globalThis as typeof globalThis & {
    __DMB_WG_SURFACE_LATENCY__?: SurfaceLatencyRecord[];
  };
  if (typeof g !== "undefined") {
    g.__DMB_WG_SURFACE_LATENCY__ = ring;
  }
}

function persistRing(): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(ring));
  } catch {
    // quota / private mode — keep in-memory only
  }
}

function hydrateRingFromSession(): void {
  if (hydratedFromSession || typeof sessionStorage === "undefined") return;
  hydratedFromSession = true;
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as SurfaceLatencyRecord[];
    if (Array.isArray(parsed)) {
      ring = parsed.slice(-RING_MAX);
      if (ring.some((row) => row.stage === "first_chip_paint")) {
        firstChipPainted = true;
      }
    }
  } catch {
    // ignore corrupt storage
  }
  syncWindowMirror();
}

function pushRecord(record: SurfaceLatencyRecord): void {
  hydrateRingFromSession();
  ring.push(record);
  if (ring.length > RING_MAX) {
    ring = ring.slice(ring.length - RING_MAX);
  }
  syncWindowMirror();
  persistRing();
}

/** Stable performance.mark name for a stage (+ optional generation suffix). */
export function surfaceLatencyMarkName(stage: SurfaceLatencyStage, suffix?: string | number): string {
  return suffix == null ? `${MARK_PREFIX}${stage}` : `${MARK_PREFIX}${stage}:${suffix}`;
}

export function recordSurfaceLatencyStage(
  stage: SurfaceLatencyStage,
  meta?: Record<string, unknown>,
  durationMs?: number,
): void {
  const markName = surfaceLatencyMarkName(stage);
  if (typeof performance !== "undefined" && typeof performance.mark === "function") {
    try {
      performance.mark(markName, {
        detail: meta ?? null,
      } as PerformanceMarkOptions);
    } catch {
      performance.mark(markName);
    }
  }
  pushRecord({
    stage,
    t: nowMs(),
    durationMs,
    meta,
  });
}

/**
 * Measure duration between two previously recorded mark names and emit a stage row.
 * Returns rounded duration ms, or null if measurement fails.
 */
export function measureSurfaceLatencyStage(
  stage: SurfaceLatencyStage,
  startMark: string,
  endMark: string,
  meta?: Record<string, unknown>,
): number | null {
  let durationMs: number | null = null;
  if (
    typeof performance !== "undefined"
    && typeof performance.mark === "function"
    && typeof performance.measure === "function"
  ) {
    const measureName = surfaceLatencyMarkName(stage, "measure");
    try {
      performance.mark(endMark);
      performance.measure(measureName, startMark, endMark);
      const entries = performance.getEntriesByName(measureName);
      const last = entries[entries.length - 1];
      if (last) {
        durationMs = Math.round(last.duration);
      }
    } catch {
      durationMs = null;
    }
  }
  recordSurfaceLatencyStage(stage, meta, durationMs ?? undefined);
  return durationMs;
}

/** First graph chip paint after cold/reset (once until `resetSurfaceLatencySession`). */
export function noteFirstChipPaint(meta?: Record<string, unknown>): boolean {
  if (firstChipPainted) return false;
  firstChipPainted = true;
  // Defer to next frame so layout/paint has a chance to commit.
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(() => {
      recordSurfaceLatencyStage("first_chip_paint", meta);
    });
  } else {
    recordSurfaceLatencyStage("first_chip_paint", meta);
  }
  return true;
}

export function resetSurfaceLatencySession(): void {
  ring = [];
  firstChipPainted = false;
  hydratedFromSession = true;
  if (typeof sessionStorage !== "undefined") {
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // ignore
    }
  }
  syncWindowMirror();
}

export function getSurfaceLatencyRecords(): readonly SurfaceLatencyRecord[] {
  hydrateRingFromSession();
  return ring;
}

export type SurfaceLatencyDogfoodApi = {
  getRecords: () => SurfaceLatencyRecord[];
  reset: () => void;
  clearProjectionCache: () => void;
};

/**
 * Install Playwright/dogfood hooks on `window`. Idempotent.
 * `clearProjectionCache` is injected to avoid a hard import cycle with the cache module.
 */
export function installSurfaceLatencyDogfoodHooks(options: {
  clearProjectionCache: () => void;
}): SurfaceLatencyDogfoodApi {
  const api: SurfaceLatencyDogfoodApi = {
    getRecords: () => [...ring],
    reset: () => {
      resetSurfaceLatencySession();
    },
    clearProjectionCache: () => {
      options.clearProjectionCache();
    },
  };

  if (dogfoodInstalled || typeof window === "undefined") {
    hydrateRingFromSession();
    syncWindowMirror();
    return api;
  }
  dogfoodInstalled = true;
  hydrateRingFromSession();

  const w = window as Window & {
    __DMB_WG_SURFACE_LATENCY__?: SurfaceLatencyRecord[];
    __DMB_WG_SURFACE_LATENCY_API__?: SurfaceLatencyDogfoodApi;
  };
  w.__DMB_WG_SURFACE_LATENCY__ = ring;
  w.__DMB_WG_SURFACE_LATENCY_API__ = api;
  return api;
}

/** Test-only: clear install flag so hooks can be reinstalled. */
export function resetSurfaceLatencyDogfoodInstallForTests(): void {
  dogfoodInstalled = false;
  hydratedFromSession = false;
  resetSurfaceLatencySession();
  hydratedFromSession = false;
}
