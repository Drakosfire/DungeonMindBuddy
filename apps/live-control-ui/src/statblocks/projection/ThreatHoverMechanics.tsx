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
  type ThreatSheetBindingViewModel,
  type ThreatSheetLoadStatus,
} from "./threatSheetViewModel";

export interface ThreatHoverMechanicsState {
  loadStatus: ThreatSheetLoadStatus | "idle";
  compactBinding: ThreatSheetBindingViewModel | null;
  availableCount: number;
  bindingCount: number;
}

/**
 * Hydrates exact Threat mechanics for chip hover when the Plan graph scope is known.
 * No-op without an exact scope; never invents latest-revision fallbacks.
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
    setLoadStatus("loading");
    setBindings([]);

    const request = buildThreatQueryHydrationRequest(scope, threatNodeId);
    void postThreatQueryHydration(request)
      .then((response) => {
        if (cancelled) return;
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
        setLoadStatus(status);
        if (selection.status !== "ready") {
          setBindings([]);
          return;
        }
        setBindings(sortThreatSheetBindings(selection.hit.bindings.map(mapBindingHydration)));
      })
      .catch(() => {
        if (cancelled) return;
        setLoadStatus("unavailable");
        setBindings([]);
      });

    return () => {
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
