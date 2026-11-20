import { useEffect, useMemo, useState } from "react";

import { useOptionalWorldGraphLensProjection } from "../../graphLens/useWorldGraphLensProjection";
import { LiveApiError, postThreatQueryHydration } from "../../api/liveApi";
import type { ThreatQueryHydrationHitV1, ThreatQueryHydrationResponseV1 } from "../../api/types";
import type { GraphReferenceResolution } from "../../graphReference/types";
import {
  buildThreatQueryHydrationRequest,
  mapHydrationResultLabelToLoadStatus,
  selectExactThreatHit,
  resolveManagedThreatScope,
  threatSelectionTupleFromResolution,
  threatSelectionTupleKey,
  type ThreatSelectionTuple,
  type ThreatSheetLoadStatus,
} from "./threatSheetViewModel";

export interface ExactThreatMechanicsState {
  selectionTuple: ThreatSelectionTuple | null;
  selectionKey: string | null;
  loadStatus: ThreatSheetLoadStatus;
  hit: ThreatQueryHydrationHitV1 | null;
  message: string | null;
}

/**
 * Surface-neutral exact Threat mechanics hydration.
 * Callers own Plan/Play presentation. This hook never imports Plan or Play policy.
 */
export function useExactThreatMechanics(
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>,
  options?: { enabled?: boolean },
): ExactThreatMechanicsState {
  const enabled = options?.enabled ?? true;
  const binding = useOptionalWorldGraphLensProjection()?.managedBinding;
  const selectionTuple = useMemo(() => {
    const tuple = enabled ? threatSelectionTupleFromResolution(resolution) : null;
    const scope = resolveManagedThreatScope(tuple, binding);
    return tuple && scope ? { ...scope, threatNodeId: tuple.threatNodeId } : null;
  }, [enabled, resolution, binding]);
  const selectionKey = selectionTuple && binding
    ? JSON.stringify([binding.nativeWorldId, binding.bindingVersion, threatSelectionTupleKey(selectionTuple)])
    : null;

  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [hit, setHit] = useState<ThreatQueryHydrationHitV1 | null>(null);
  const [loadStatus, setLoadStatus] = useState<ThreatSheetLoadStatus>(
    enabled ? "loading" : "ready",
  );
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setLoadedKey(selectionKey);
    if (!enabled) {
      setLoadStatus("ready");
      setMessage(null);
      setHit(null);
      return;
    }

    if (!selectionTuple || !selectionKey) {
      setLoadStatus("integrity_failure");
      setMessage("A verified managed World binding is required for Threat mechanics.");
      setHit(null);
      return;
    }

    let cancelled = false;
    setLoadStatus("loading");
    setMessage(null);
    setHit(null);

    const request = buildThreatQueryHydrationRequest(
      {
        worldId: selectionTuple.worldId,
        campaignId: selectionTuple.campaignId,
        scopeMode: selectionTuple.scopeMode,
        revisionId: selectionTuple.revisionId,
      },
      selectionTuple.threatNodeId,
    );

    void postThreatQueryHydration(request)
      .then((response: ThreatQueryHydrationResponseV1) => {
        if (cancelled) return;
        const selection = selectExactThreatHit(
          response,
          selectionTuple,
          selectionTuple.threatNodeId,
        );
        setLoadStatus(mapHydrationResultLabelToLoadStatus(response.resultLabel, selection));
        if (selection.status === "ready") {
          setHit(selection.hit);
          setMessage(response.message);
          return;
        }
        setHit(null);
        if (selection.status === "not_found") {
          setMessage(selection.message ?? "Exact Threat mechanics not found.");
          return;
        }
        setMessage(selection.message);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setHit(null);
        if (error instanceof LiveApiError) {
          if (error.status === 404) {
            setLoadStatus("not_found");
            setMessage(error.message);
            return;
          }
          if (error.status === 503) {
            setLoadStatus("unavailable");
            setMessage(error.message);
            return;
          }
          if (error.status >= 500) {
            setLoadStatus("integrity_failure");
            setMessage(error.message);
            return;
          }
        }
        setLoadStatus("unavailable");
        setMessage(error instanceof Error ? error.message : "Threat mechanics unavailable.");
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, selectionKey, selectionTuple]);

  return {
    selectionTuple,
    selectionKey,
    loadStatus: loadedKey === selectionKey ? loadStatus : "loading",
    hit: enabled && selectionKey !== null && loadedKey === selectionKey ? hit : null,
    message: loadedKey === selectionKey ? message : null,
  };
}
