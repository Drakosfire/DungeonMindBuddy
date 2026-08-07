/**
 * OPT-BENCH02: client-side World Graph surface experience marks.
 *
 * Opt-in only. When disabled (default production), every public entry point is a
 * no-op: no performance.mark, no window globals, no sessionStorage writes.
 *
 * Enable via any of:
 *   - `VITE_DMB_BENCH_SURFACE=1` (Vite build/dev)
 *   - `sessionStorage['dmb:bench-surface'] = '1'` (Playwright addInitScript)
 *   - `window.__DMB_BENCH_SURFACE__ = true`
 *   - `enableSurfaceLatencyInstrumentationForTests()` (unit tests)
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
  /** `performance.now()` in the recording document (not comparable across full reloads). */
  t: number;
  /**
   * Absolute wall clock: `performance.timeOrigin + performance.now()` (or Date.now()).
   * Comparable across full-document Plan↔Build navigations.
   */
  epochMs: number;
  durationMs?: number;
  meta?: Record<string, unknown>;
};

type SurfaceSwitchStartPersisted = {
  switchId: string;
  epochMs: number;
  from?: string;
  to?: string;
  href?: string;
};

const RING_MAX = 256;
const MARK_PREFIX = "dmb:wg-surface:";
/** Survives full-document Plan↔Build `<a href>` navigations (OPT-BENCH02). */
const SESSION_STORAGE_KEY = "dmb:wg-surface-latency-ring";
const ENABLE_SESSION_KEY = "dmb:bench-surface";
const SWITCH_START_SESSION_KEY = "dmb:wg-surface-switch-start";

let ring: SurfaceLatencyRecord[] = [];
let firstChipPainted = false;
let dogfoodInstalled = false;
let hydratedFromSession = false;
/** Unit-test force enable (does not affect production). */
let forceEnabledForTests = false;

function readViteBenchFlag(): boolean {
  try {
    return import.meta.env?.VITE_DMB_BENCH_SURFACE === "1";
  } catch {
    return false;
  }
}

/** True only when an explicit bench/dev enablement signal is present. */
export function isSurfaceLatencyInstrumentationEnabled(): boolean {
  if (forceEnabledForTests) return true;
  if (readViteBenchFlag()) return true;
  if (typeof window !== "undefined") {
    const w = window as Window & { __DMB_BENCH_SURFACE__?: boolean };
    if (w.__DMB_BENCH_SURFACE__ === true) return true;
  }
  if (typeof sessionStorage !== "undefined") {
    try {
      if (sessionStorage.getItem(ENABLE_SESSION_KEY) === "1") return true;
    } catch {
      // private mode
    }
  }
  return false;
}

/** Vitest helper — enable recording without Vite/session flags. */
export function enableSurfaceLatencyInstrumentationForTests(): void {
  forceEnabledForTests = true;
}

function nowMs(): number {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

/** Cross-document absolute clock (survives performance time-origin reset). */
export function surfaceLatencyWallEpochMs(): number {
  if (
    typeof performance !== "undefined"
    && typeof performance.now === "function"
    && typeof performance.timeOrigin === "number"
  ) {
    return performance.timeOrigin + performance.now();
  }
  return Date.now();
}

function syncWindowMirror(): void {
  if (!isSurfaceLatencyInstrumentationEnabled()) return;
  const g = globalThis as typeof globalThis & {
    __DMB_WG_SURFACE_LATENCY__?: SurfaceLatencyRecord[];
  };
  if (typeof g !== "undefined") {
    g.__DMB_WG_SURFACE_LATENCY__ = ring;
  }
}

function persistRing(): void {
  if (!isSurfaceLatencyInstrumentationEnabled()) return;
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(ring));
  } catch {
    // quota / private mode — keep in-memory only
  }
}

function hydrateRingFromSession(): void {
  if (!isSurfaceLatencyInstrumentationEnabled()) return;
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

function persistSwitchStart(start: SurfaceSwitchStartPersisted): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.setItem(SWITCH_START_SESSION_KEY, JSON.stringify(start));
  } catch {
    // ignore
  }
}

function readPersistedSwitchStart(): SurfaceSwitchStartPersisted | null {
  if (typeof sessionStorage === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SWITCH_START_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SurfaceSwitchStartPersisted;
    if (
      parsed
      && typeof parsed.switchId === "string"
      && typeof parsed.epochMs === "number"
    ) {
      return parsed;
    }
  } catch {
    // ignore
  }
  return null;
}

function clearPersistedSwitchStart(): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.removeItem(SWITCH_START_SESSION_KEY);
  } catch {
    // ignore
  }
}

function pushRecord(record: SurfaceLatencyRecord): void {
  if (!isSurfaceLatencyInstrumentationEnabled()) return;
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
  if (!isSurfaceLatencyInstrumentationEnabled()) return;

  const epochMs = surfaceLatencyWallEpochMs();
  const t = nowMs();
  let nextMeta = meta;
  let nextDuration = durationMs;

  if (stage === "surface_switch_start") {
    const switchId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `switch-${epochMs}`;
    const start: SurfaceSwitchStartPersisted = {
      switchId,
      epochMs,
      from: typeof meta?.from === "string" ? meta.from : undefined,
      to: typeof meta?.to === "string" ? meta.to : undefined,
      href: typeof meta?.href === "string" ? meta.href : undefined,
    };
    persistSwitchStart(start);
    nextMeta = { ...meta, switchId, epochMs };
  }

  if (stage === "surface_switch_end") {
    const start = readPersistedSwitchStart();
    if (start) {
      nextDuration = Math.round(epochMs - start.epochMs);
      nextMeta = {
        ...meta,
        switchId: start.switchId,
        startEpochMs: start.epochMs,
        endEpochMs: epochMs,
        clock: "wall_epoch",
        from: start.from,
        to: start.to,
        href: start.href,
      };
      clearPersistedSwitchStart();
    } else {
      nextMeta = {
        ...meta,
        clock: "wall_epoch",
        endEpochMs: epochMs,
        missingSwitchStart: true,
      };
      nextDuration = undefined;
    }
  }

  const markName = surfaceLatencyMarkName(stage);
  if (typeof performance !== "undefined" && typeof performance.mark === "function") {
    try {
      performance.mark(markName, {
        detail: nextMeta ?? null,
      } as PerformanceMarkOptions);
    } catch {
      performance.mark(markName);
    }
  }
  pushRecord({
    stage,
    t,
    epochMs,
    durationMs: nextDuration,
    meta: nextMeta,
  });
}

/**
 * Measure duration between two previously recorded mark names and emit a stage row.
 * Returns rounded duration ms, or null if measurement fails / instrumentation off.
 */
export function measureSurfaceLatencyStage(
  stage: SurfaceLatencyStage,
  startMark: string,
  endMark: string,
  meta?: Record<string, unknown>,
): number | null {
  if (!isSurfaceLatencyInstrumentationEnabled()) return null;
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
  if (!isSurfaceLatencyInstrumentationEnabled()) return false;
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
      sessionStorage.removeItem(SWITCH_START_SESSION_KEY);
    } catch {
      // ignore
    }
  }
  if (isSurfaceLatencyInstrumentationEnabled()) {
    syncWindowMirror();
  }
}

export function getSurfaceLatencyRecords(): readonly SurfaceLatencyRecord[] {
  if (!isSurfaceLatencyInstrumentationEnabled()) return [];
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
 * No-ops (does not touch window) when instrumentation is disabled.
 */
export function installSurfaceLatencyDogfoodHooks(options: {
  clearProjectionCache: () => void;
}): SurfaceLatencyDogfoodApi | null {
  const api: SurfaceLatencyDogfoodApi = {
    getRecords: () => (isSurfaceLatencyInstrumentationEnabled() ? [...ring] : []),
    reset: () => {
      resetSurfaceLatencySession();
    },
    clearProjectionCache: () => {
      options.clearProjectionCache();
    },
  };

  if (!isSurfaceLatencyInstrumentationEnabled()) {
    return null;
  }

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
  forceEnabledForTests = false;
  if (typeof window !== "undefined") {
    const w = window as Window & {
      __DMB_WG_SURFACE_LATENCY__?: SurfaceLatencyRecord[];
      __DMB_WG_SURFACE_LATENCY_API__?: SurfaceLatencyDogfoodApi;
      __DMB_BENCH_SURFACE__?: boolean;
    };
    delete w.__DMB_WG_SURFACE_LATENCY__;
    delete w.__DMB_WG_SURFACE_LATENCY_API__;
    delete w.__DMB_BENCH_SURFACE__;
  }
  resetSurfaceLatencySession();
  hydratedFromSession = false;
}
