import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getSurfaceLatencyRecords,
  installSurfaceLatencyDogfoodHooks,
  measureSurfaceLatencyStage,
  noteFirstChipPaint,
  recordSurfaceLatencyStage,
  resetSurfaceLatencyDogfoodInstallForTests,
  resetSurfaceLatencySession,
  surfaceLatencyMarkName,
} from "./surfaceLatencyMarks";

afterEach(() => {
  resetSurfaceLatencyDogfoodInstallForTests();
  vi.restoreAllMocks();
});

describe("surfaceLatencyMarks", () => {
  it("records stages onto the ring buffer and performance.mark", () => {
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

  it("installs dogfood API on window", () => {
    const clear = vi.fn();
    const api = installSurfaceLatencyDogfoodHooks({ clearProjectionCache: clear });
    recordSurfaceLatencyStage("client_cache_miss");
    expect(api.getRecords()).toHaveLength(1);
    api.clearProjectionCache();
    expect(clear).toHaveBeenCalledOnce();
    api.reset();
    expect(api.getRecords()).toHaveLength(0);
    expect(
      (window as Window & { __DMB_WG_SURFACE_LATENCY_API__?: unknown }).__DMB_WG_SURFACE_LATENCY_API__,
    ).toBeDefined();
  });

  it("persists the ring across resetSurfaceLatencyDogfoodInstallForTests + rehydrate", () => {
    recordSurfaceLatencyStage("projection_fetch", { surface: "plan" });
    expect(sessionStorage.getItem("dmb:wg-surface-latency-ring")).toBeTruthy();
    // Simulate a full document navigation: module state is new, storage remains.
    resetSurfaceLatencyDogfoodInstallForTests();
    // After test reset, storage is cleared — re-seed and prove install hydrates.
    recordSurfaceLatencyStage("projection_ready", { surface: "plan" }, 12);
    const raw = sessionStorage.getItem("dmb:wg-surface-latency-ring");
    expect(raw).toContain("projection_ready");
    resetSurfaceLatencyDogfoodInstallForTests();
    // Manually put storage back (as a navigation would leave it) then install.
    sessionStorage.setItem("dmb:wg-surface-latency-ring", raw!);
    installSurfaceLatencyDogfoodHooks({ clearProjectionCache: () => undefined });
    expect(getSurfaceLatencyRecords().some((r) => r.stage === "projection_ready")).toBe(true);
  });
});
