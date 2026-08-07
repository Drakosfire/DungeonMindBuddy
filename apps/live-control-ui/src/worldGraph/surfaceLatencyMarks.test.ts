import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  enableSurfaceLatencyInstrumentationForTests,
  getSurfaceLatencyRecords,
  installSurfaceLatencyDogfoodHooks,
  isSurfaceLatencyInstrumentationEnabled,
  measureSurfaceLatencyStage,
  noteFirstChipPaint,
  recordSurfaceLatencyStage,
  resetSurfaceLatencyDogfoodInstallForTests,
  resetSurfaceLatencySession,
  surfaceLatencyMarkName,
  surfaceLatencyWallEpochMs,
} from "./surfaceLatencyMarks";

beforeEach(() => {
  enableSurfaceLatencyInstrumentationForTests();
});

afterEach(() => {
  resetSurfaceLatencyDogfoodInstallForTests();
  vi.restoreAllMocks();
});

describe("surfaceLatencyMarks", () => {
  it("is disabled by default after test reset (no force / vite / session flag)", () => {
    resetSurfaceLatencyDogfoodInstallForTests();
    expect(isSurfaceLatencyInstrumentationEnabled()).toBe(false);
    recordSurfaceLatencyStage("client_cache_miss");
    expect(getSurfaceLatencyRecords()).toHaveLength(0);
    expect(sessionStorage.getItem("dmb:wg-surface-latency-ring")).toBeNull();
    expect(
      (window as Window & { __DMB_WG_SURFACE_LATENCY_API__?: unknown }).__DMB_WG_SURFACE_LATENCY_API__,
    ).toBeUndefined();
  });

  it("records stages onto the ring buffer and performance.mark when enabled", () => {
    const marks: string[] = [];
    vi.spyOn(performance, "mark").mockImplementation((name: string) => {
      marks.push(String(name));
      return {} as PerformanceMark;
    });

    recordSurfaceLatencyStage("projection_ready", { surface: "plan" }, 42);

    const records = getSurfaceLatencyRecords();
    expect(records).toHaveLength(1);
    expect(records[0]).toMatchObject({
      stage: "projection_ready",
      durationMs: 42,
      meta: { surface: "plan" },
    });
    expect(typeof records[0]?.epochMs).toBe("number");
    expect(marks).toContain(surfaceLatencyMarkName("projection_ready"));
  });

  it("notes first chip paint only once until reset", async () => {
    vi.stubGlobal(
      "requestAnimationFrame",
      (cb: FrameRequestCallback) => {
        cb(0);
        return 1;
      },
    );
    expect(noteFirstChipPaint({ nodeId: "a" })).toBe(true);
    expect(noteFirstChipPaint({ nodeId: "b" })).toBe(false);
    expect(getSurfaceLatencyRecords().filter((r) => r.stage === "first_chip_paint")).toHaveLength(1);

    resetSurfaceLatencySession();
    expect(noteFirstChipPaint({ nodeId: "c" })).toBe(true);
    expect(getSurfaceLatencyRecords().filter((r) => r.stage === "first_chip_paint")).toHaveLength(1);
  });

  it("measureSurfaceLatencyStage returns rounded duration when performance.measure works", () => {
    vi.spyOn(performance, "mark").mockImplementation(() => ({} as PerformanceMark));
    vi.spyOn(performance, "measure").mockImplementation(() => ({ duration: 12.6 } as PerformanceMeasure));
    vi.spyOn(performance, "getEntriesByName").mockReturnValue([{ duration: 12.6 } as PerformanceEntry]);

    const ms = measureSurfaceLatencyStage(
      "projection_ready",
      "start",
      "end",
      { outcome: "ready" },
    );
    expect(ms).toBe(13);
    expect(getSurfaceLatencyRecords().at(-1)?.durationMs).toBe(13);
  });

  it("installs dogfood API on window only when enabled", () => {
    const clear = vi.fn();
    const api = installSurfaceLatencyDogfoodHooks({ clearProjectionCache: clear });
    expect(api).not.toBeNull();
    recordSurfaceLatencyStage("client_cache_miss");
    expect(api!.getRecords()).toHaveLength(1);
    api!.clearProjectionCache();
    expect(clear).toHaveBeenCalledOnce();
    api!.reset();
    expect(api!.getRecords()).toHaveLength(0);
    expect(
      (window as Window & { __DMB_WG_SURFACE_LATENCY_API__?: unknown }).__DMB_WG_SURFACE_LATENCY_API__,
    ).toBeDefined();
  });

  it("does not install dogfood hooks when instrumentation is disabled", () => {
    resetSurfaceLatencyDogfoodInstallForTests();
    const api = installSurfaceLatencyDogfoodHooks({ clearProjectionCache: () => undefined });
    expect(api).toBeNull();
    expect(
      (window as Window & { __DMB_WG_SURFACE_LATENCY_API__?: unknown }).__DMB_WG_SURFACE_LATENCY_API__,
    ).toBeUndefined();
  });

  it("persists the ring across resetSurfaceLatencyDogfoodInstallForTests + rehydrate", () => {
    recordSurfaceLatencyStage("projection_fetch", { surface: "plan" });
    expect(sessionStorage.getItem("dmb:wg-surface-latency-ring")).toBeTruthy();
    const rawBefore = sessionStorage.getItem("dmb:wg-surface-latency-ring");
    resetSurfaceLatencyDogfoodInstallForTests();
    // After full reset, storage is cleared — re-enable and prove install hydrates prior ring.
    enableSurfaceLatencyInstrumentationForTests();
    sessionStorage.setItem("dmb:wg-surface-latency-ring", rawBefore!);
    installSurfaceLatencyDogfoodHooks({ clearProjectionCache: () => undefined });
    expect(getSurfaceLatencyRecords().some((r) => r.stage === "projection_fetch")).toBe(true);
  });

  it("computes surface_switch_end from wall-epoch delta, not caller durationMs", () => {
    const startEpoch = surfaceLatencyWallEpochMs() - 1500;
    sessionStorage.setItem(
      "dmb:wg-surface-switch-start",
      JSON.stringify({
        switchId: "sw-1",
        epochMs: startEpoch,
        from: "plan",
        to: "build",
        href: "/build",
      }),
    );

    recordSurfaceLatencyStage("surface_switch_end", { surface: "build", outcome: "ready" }, 27);

    const end = getSurfaceLatencyRecords().find((r) => r.stage === "surface_switch_end");
    expect(end).toBeDefined();
    expect(end!.durationMs).toBeGreaterThanOrEqual(1400);
    expect(end!.durationMs).toBeLessThan(5000);
    expect(end!.meta).toMatchObject({
      switchId: "sw-1",
      clock: "wall_epoch",
      from: "plan",
      to: "build",
    });
    // Caller-supplied 27 must not win over wall-epoch delta.
    expect(end!.durationMs).not.toBe(27);
    expect(sessionStorage.getItem("dmb:wg-surface-switch-start")).toBeNull();
  });

  it("persists switch start identity on surface_switch_start", () => {
    recordSurfaceLatencyStage("surface_switch_start", {
      from: "plan",
      to: "build",
      href: "/build",
      navigation: "full_document_anchor",
    });
    const raw = sessionStorage.getItem("dmb:wg-surface-switch-start");
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!) as { switchId: string; epochMs: number; from: string };
    expect(parsed.from).toBe("plan");
    expect(typeof parsed.switchId).toBe("string");
    expect(typeof parsed.epochMs).toBe("number");
  });
});
