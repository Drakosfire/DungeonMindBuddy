import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WORLD_GRAPH_REVISION_COMMITTED_EVENT } from "./planGraphContextRequest";
import {
  clearProjectionRequestCache,
  configureProjectionRequestCache,
  projectionRequestCacheStats,
  withProjectionRequestCache,
} from "./projectionRequestCache";

describe("projectionRequestCache", () => {
  beforeEach(() => {
    clearProjectionRequestCache();
    configureProjectionRequestCache({ ttlMs: 120_000, maxEntries: 8 });
  });

  afterEach(() => {
    clearProjectionRequestCache();
    vi.useRealTimers();
  });

  it("coalesces in-flight duplicate requests", async () => {
    let resolveLoader!: (value: string) => void;
    const loader = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          resolveLoader = resolve;
        }),
    );

    const request = { schema: "test", worldId: "eldyrwild" };
    const a = withProjectionRequestCache("recap-projection", request, loader);
    const b = withProjectionRequestCache("recap-projection", request, loader);

    expect(loader).toHaveBeenCalledTimes(1);
    expect(projectionRequestCacheStats().inFlight).toBe(1);

    resolveLoader("warm");
    await expect(Promise.all([a, b])).resolves.toEqual(["warm", "warm"]);
    expect(projectionRequestCacheStats().settled).toBe(1);
  });

  it("returns settled cache hits without reloading", async () => {
    const loader = vi.fn(async () => "cached");
    const request = { campaignId: "longmont-c1", sessionId: "session-6" };

    await expect(
      withProjectionRequestCache("projection", request, loader),
    ).resolves.toBe("cached");
    await expect(
      withProjectionRequestCache("projection", request, loader),
    ).resolves.toBe("cached");

    expect(loader).toHaveBeenCalledTimes(1);
  });

  it("misses after TTL expiry", async () => {
    vi.useFakeTimers();
    configureProjectionRequestCache({ ttlMs: 1_000 });
    const loader = vi.fn(async () => "v1");
    const request = { worldId: "eldyrwild" };

    await withProjectionRequestCache("projection", request, loader);
    await vi.advanceTimersByTimeAsync(1_001);
    loader.mockResolvedValueOnce("v2");
    await expect(
      withProjectionRequestCache("projection", request, loader),
    ).resolves.toBe("v2");
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it("clears on world graph revision committed", async () => {
    const loader = vi.fn(async () => "before");
    const request = { worldId: "eldyrwild" };
    await withProjectionRequestCache("recap-projection", request, loader);
    expect(projectionRequestCacheStats().settled).toBe(1);

    window.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));
    expect(projectionRequestCacheStats().settled).toBe(0);

    loader.mockResolvedValueOnce("after");
    await expect(
      withProjectionRequestCache("recap-projection", request, loader),
    ).resolves.toBe("after");
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it("keeps projection and recap-projection endpoints on separate keys", async () => {
    const projectionLoader = vi.fn(async () => "projection");
    const recapLoader = vi.fn(async () => "recap");
    const request = { worldId: "eldyrwild" };

    await withProjectionRequestCache("projection", request, projectionLoader);
    await withProjectionRequestCache("recap-projection", request, recapLoader);

    expect(projectionLoader).toHaveBeenCalledTimes(1);
    expect(recapLoader).toHaveBeenCalledTimes(1);
    expect(projectionRequestCacheStats().settled).toBe(2);
  });
});
