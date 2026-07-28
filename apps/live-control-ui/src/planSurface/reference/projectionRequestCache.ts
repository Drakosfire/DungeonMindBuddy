/**
 * Module-level warm cache for World Graph projection HTTP requests.
 *
 * Survives React remounts and /plan ↔ /ingest route swaps within the same SPA
 * session. Coalesces in-flight duplicates and keeps a short TTL so Load after
 * warm-up feels warm without inventing per-hook caches.
 */

import { WORLD_GRAPH_REVISION_COMMITTED_EVENT } from "./planGraphContextRequest";

export type ProjectionCacheEndpoint = "projection" | "recap-projection";

const DEFAULT_TTL_MS = 120_000;
const DEFAULT_MAX_ENTRIES = 8;

type CacheEntry<T> = {
  value: T;
  expiresAt: number;
};

type InFlightEntry<T> = {
  promise: Promise<T>;
};

const settled = new Map<string, CacheEntry<unknown>>();
const inFlight = new Map<string, InFlightEntry<unknown>>();

let ttlMs = DEFAULT_TTL_MS;
let maxEntries = DEFAULT_MAX_ENTRIES;
let revisionListenerBound = false;

function ensureRevisionInvalidation(): void {
  if (revisionListenerBound || typeof window === "undefined") return;
  revisionListenerBound = true;
  window.addEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, () => {
    clearProjectionRequestCache();
  });
}

/** Stable key from endpoint + request body (insertion-order JSON). */
export function projectionRequestCacheKey(
  endpoint: ProjectionCacheEndpoint,
  request: unknown,
): string {
  return `${endpoint}:${JSON.stringify(request)}`;
}

export function clearProjectionRequestCache(): void {
  settled.clear();
  inFlight.clear();
}

/** Test/harness knobs. */
export function configureProjectionRequestCache(options: {
  ttlMs?: number;
  maxEntries?: number;
}): void {
  if (options.ttlMs != null) ttlMs = Math.max(0, options.ttlMs);
  if (options.maxEntries != null) maxEntries = Math.max(1, options.maxEntries);
}

export function projectionRequestCacheStats(): {
  settled: number;
  inFlight: number;
} {
  return { settled: settled.size, inFlight: inFlight.size };
}

function pruneExpired(now: number): void {
  for (const [key, entry] of settled) {
    if (entry.expiresAt <= now) {
      settled.delete(key);
    }
  }
}

function enforceMaxEntries(): void {
  while (settled.size > maxEntries) {
    const oldest = settled.keys().next().value;
    if (oldest == null) break;
    settled.delete(oldest);
  }
}

/**
 * Return a cached value, coalesce with an in-flight fetch, or run `loader`.
 */
export async function withProjectionRequestCache<T>(
  endpoint: ProjectionCacheEndpoint,
  request: unknown,
  loader: () => Promise<T>,
): Promise<T> {
  ensureRevisionInvalidation();
  const key = projectionRequestCacheKey(endpoint, request);
  const now = Date.now();
  pruneExpired(now);

  const hit = settled.get(key) as CacheEntry<T> | undefined;
  if (hit && hit.expiresAt > now) {
    // Refresh LRU order.
    settled.delete(key);
    settled.set(key, hit);
    return hit.value;
  }

  const pending = inFlight.get(key) as InFlightEntry<T> | undefined;
  if (pending) {
    return pending.promise;
  }

  const promise = loader()
    .then((value) => {
      settled.set(key, { value, expiresAt: Date.now() + ttlMs });
      enforceMaxEntries();
      inFlight.delete(key);
      return value;
    })
    .catch((error) => {
      inFlight.delete(key);
      throw error;
    });

  inFlight.set(key, { promise });
  return promise;
}
