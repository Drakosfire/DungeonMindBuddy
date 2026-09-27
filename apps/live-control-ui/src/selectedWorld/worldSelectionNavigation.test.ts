import { beforeEach, describe, expect, it, vi } from "vitest";

import { selectWorldFromLocation, worldSelectionHref, worldScopedSurfaceHref } from "./worldSelectionNavigation";

describe("World selection navigation", () => {
  beforeEach(() => window.history.replaceState({}, "", "/"));

  it("clears every scope-bound identity on same-path selection", () => {
    expect(worldSelectionHref(
      "/ingest?world=a&campaign=a&session=session-25&extractionRunId=run-a&documentId=doc-a&revision=2",
      "b",
    )).toBe("/ingest?world=b");
    expect(worldSelectionHref("/play?world=a&run=run-a", "b")).toBe("/play?world=b");
    expect(worldSelectionHref("/plan?world=a&documentId=plan-a", "b")).toBe("/plan?world=b");
  });

  it("carries selection across ordinary surface navigation without stale Plan IDs", () => {
    expect(worldScopedSurfaceHref("/build", "world-a")).toBe("/build?world=world-a");
    expect(worldScopedSurfaceHref("/play", "world-a")).toBe("/play?world=world-a");
  });

  it("pushes the same route when its World changes and exposes back navigation", () => {
    window.history.replaceState({}, "", "/plan?world=a&documentId=plan-a");
    const push = vi.spyOn(window.history, "pushState");
    selectWorldFromLocation("b");
    expect(window.location.href).toContain("/plan?world=b");
    expect(push).toHaveBeenCalledOnce();
    push.mockRestore();
  });
});
