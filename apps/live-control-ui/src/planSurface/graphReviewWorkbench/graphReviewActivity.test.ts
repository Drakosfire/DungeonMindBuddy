import { describe, expect, it } from "vitest";

import {
  formatGraphReviewActivityTarget,
  resolveGraphReviewActivity,
} from "./graphReviewActivity";

describe("formatGraphReviewActivityTarget", () => {
  it("joins campaign and session labels", () => {
    expect(formatGraphReviewActivityTarget("Longmont C1", "session-6")).toBe(
      "Longmont C1 · Session 6",
    );
  });
});

describe("resolveGraphReviewActivity", () => {
  it("prioritizes catalog loading", () => {
    expect(
      resolveGraphReviewActivity({
        sessionsLoaded: false,
        hasAppliedLoad: false,
        warmupStatus: "warming",
        warmupTargetLabel: "Longmont C1 · Session 6",
        projectionStatus: "loading",
      }),
    ).toEqual({
      phase: "catalog",
      message: "Loading sessions…",
      busy: true,
    });
  });

  it("prioritizes applied session projection loading over warm-up", () => {
    expect(
      resolveGraphReviewActivity({
        sessionsLoaded: true,
        hasAppliedLoad: true,
        warmupStatus: "ready",
        warmupTargetLabel: "Longmont C1 · Session 6",
        projectionStatus: "loading",
        appliedTargetLabel: "Longmont C1 · Session 6",
      }),
    ).toEqual({
      phase: "loading-session",
      message: "Loading Longmont C1 · Session 6…",
      busy: true,
    });
  });

  it("shows warming then warm-ready on the blank landing", () => {
    expect(
      resolveGraphReviewActivity({
        sessionsLoaded: true,
        hasAppliedLoad: false,
        warmupStatus: "warming",
        warmupTargetLabel: "Longmont C2 · Session 23",
      }),
    ).toEqual({
      phase: "warming",
      message: "Warming Longmont C2 · Session 23…",
      busy: true,
    });

    expect(
      resolveGraphReviewActivity({
        sessionsLoaded: true,
        hasAppliedLoad: false,
        warmupStatus: "ready",
        warmupTargetLabel: "Longmont C2 · Session 23",
      }),
    ).toEqual({
      phase: "warm",
      message: "Longmont C2 · Session 23 ready",
      busy: false,
    });
  });

  it("returns null when idle after load is ready", () => {
    expect(
      resolveGraphReviewActivity({
        sessionsLoaded: true,
        hasAppliedLoad: true,
        warmupStatus: "ready",
        warmupTargetLabel: "Longmont C1 · Session 6",
        projectionStatus: "ready",
        appliedTargetLabel: "Longmont C1 · Session 6",
      }),
    ).toBeNull();
  });
});
