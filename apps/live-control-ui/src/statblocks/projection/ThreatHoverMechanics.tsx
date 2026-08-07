import { useEffect, useMemo, useState } from "react";

import { postThreatQueryHydration } from "../../api/liveApi";
import type { ExactGraphReferenceScope } from "../../graphReference/types";
import {
  availableBindingCount,
  buildThreatQueryHydrationRequest,
  mapBindingHydration,
  mapHydrationResultLabelToLoadStatus,
  selectExactThreatHit,
  sortThreatSheetBindings,
  threatSelectionTupleKey,
  type ThreatSheetBindingViewModel,
  type ThreatSheetLoadStatus,
} from "./threatSheetViewModel";

export interface ThreatHoverMechanicsState {
  loadStatus: ThreatSheetLoadStatus | "idle";
  compactBinding: ThreatSheetBindingViewModel | null;
  availableCount: number;
  bindingCount: number;
}

type CachedThreatHoverHydration = {
  loadStatus: ThreatSheetLoadStatus;
  bindings: ThreatSheetBindingViewModel[];
};

/** Exact world/campaign/scope/revision/Threat → last successful (or terminal) hydration. */
const threatHoverHydrationCache = new Map<string, CachedThreatHoverHydration>();
/** In-flight POSTs coalesced by the same exact tuple. */
const threatHoverHydrationInflight = new Map<string, Promise<CachedThreatHoverHydration>>();

/** Vitest seam — clears module cache between cases. */
export function resetThreatHoverHydrationCacheForTests(): void {
  threatHoverHydrationCache.clear();
  threatHoverHydrationInflight.clear();
}

function loadThreatHoverHydration(
  scope: ExactGraphReferenceScope,
  threatNodeId: string,
): Promise<CachedThreatHoverHydration> {
  const cacheKey = threatSelectionTupleKey({
    worldId: scope.worldId,
    campaignId: scope.campaignId,
    scopeMode: scope.scopeMode,
    revisionId: scope.revisionId,
    threatNodeId,
  });

  const cached = threatHoverHydrationCache.get(cacheKey);
  if (cached) {
    return Promise.resolve(cached);
  }

  const existing = threatHoverHydrationInflight.get(cacheKey);
  if (existing) {
    return existing;
  }

  const request = buildThreatQueryHydrationRequest(scope, threatNodeId);
  const pending = postThreatQueryHydration(request)
    .then((response): CachedThreatHoverHydration => {
      const selection = selectExactThreatHit(
        response,
        {
          worldId: scope.worldId,
          campaignId: scope.campaignId,
          scopeMode: scope.scopeMode,
          revisionId: scope.revisionId,
          threatNodeId,
        },
        threatNodeId,
      );
      const status = mapHydrationResultLabelToLoadStatus(response.resultLabel, selection);
      if (selection.status !== "ready") {
        return { loadStatus: status, bindings: [] };
      }
      return {
        loadStatus: status,
        bindings: sortThreatSheetBindings(selection.hit.bindings.map(mapBindingHydration)),
      };
    })
    .catch((): CachedThreatHoverHydration => ({
      loadStatus: "unavailable",
      bindings: [],
    }))
    .then((result) => {
      // Keep in-flight coalescing, but do not sticky-cache transient unavailability
      // (DMS down, timeout, rate limit). Successful / terminal immutable results persist.
      if (shouldPersistThreatHoverResult(result)) {
        threatHoverHydrationCache.set(cacheKey, result);
      }
      threatHoverHydrationInflight.delete(cacheKey);
      return result;
    });

  threatHoverHydrationInflight.set(cacheKey, pending);
  return pending;
}

function shouldPersistThreatHoverResult(result: CachedThreatHoverHydration): boolean {
  if (result.loadStatus === "unavailable") return false;
  // Any unavailable binding may recover later (partial DMS/integration outage).
  if (result.bindings.some((binding) => binding.hydrationStatus === "unavailable")) {
    return false;
  }
  return true;
}

/**
 * Hydrates exact Threat mechanics for chip hover when the Plan graph scope is known.
 * No-op without an exact scope; never invents latest-revision fallbacks.
 * Coalesces and caches by the exact world/campaign/scope/revision/Threat tuple so
 * leave/re-enter does not re-POST identical DungeonMind requests.
 */
export function useThreatHoverMechanics(
  enabled: boolean,
  threatNodeId: string,
  scope: ExactGraphReferenceScope | null | undefined,
): ThreatHoverMechanicsState {
  const [loadStatus, setLoadStatus] = useState<ThreatSheetLoadStatus | "idle">("idle");
  const [bindings, setBindings] = useState<ThreatSheetBindingViewModel[]>([]);

  const scopeKey = scope
    ? `${scope.worldId}\0${scope.campaignId}\0${scope.scopeMode}\0${scope.revisionId}`
    : null;

  useEffect(() => {
    if (!enabled || !scope || !scopeKey) {
      setLoadStatus("idle");
      setBindings([]);
      return;
    }

    let cancelled = false;
    const cacheKey = threatSelectionTupleKey({
      worldId: scope.worldId,
      campaignId: scope.campaignId,
      scopeMode: scope.scopeMode,
      revisionId: scope.revisionId,
      threatNodeId,
    });
    const cached = threatHoverHydrationCache.get(cacheKey);
    if (cached) {
      setLoadStatus(cached.loadStatus);
      setBindings(cached.bindings);
      return;
    }

    setLoadStatus("loading");
    setBindings([]);

    void loadThreatHoverHydration(scope, threatNodeId).then((result) => {
      if (cancelled) return;
      setLoadStatus(result.loadStatus);
      setBindings(result.bindings);
    });

    return () => {
      // Ignore outstanding UI updates only — do not abort the shared inflight POST.
      cancelled = true;
    };
  }, [enabled, scope, scopeKey, threatNodeId]);

  return useMemo(() => {
    const availableCount = availableBindingCount(bindings);
    const compactBinding =
      availableCount === 1
        ? bindings.find((binding) => binding.hydrationStatus === "available") ?? null
        : null;
    return {
      loadStatus,
      compactBinding,
      availableCount,
      bindingCount: bindings.length,
    };
  }, [bindings, loadStatus]);
}
