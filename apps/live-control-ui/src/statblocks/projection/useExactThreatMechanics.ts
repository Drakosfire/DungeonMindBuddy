import { useEffect, useMemo, useState } from "react";

import { LiveApiError, postThreatQueryHydration } from "../../api/liveApi";
import type { ThreatQueryHydrationHitV1, ThreatQueryHydrationResponseV1 } from "../../api/types";
import type { GraphReferenceResolution } from "../../graphReference/types";
import {
  buildThreatQueryHydrationRequest,
  mapHydrationResultLabelToLoadStatus,
  selectExactThreatHit,
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
  const selectionTuple = useMemo(
    () => (enabled ? threatSelectionTupleFromResolution(resolution) : null),
    [enabled, resolution],
  );
  const selectionKey = selectionTuple ? threatSelectionTupleKey(selectionTuple) : null;

  const [hit, setHit] = useState<ThreatQueryHydrationHitV1 | null>(null);
  const [loadStatus, setLoadStatus] = useState<ThreatSheetLoadStatus>(
    enabled ? "loading" : "ready",
  );
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      setLoadStatus("ready");
      setMessage(null);
      setHit(null);
      return;
    }

    if (!selectionTuple || !selectionKey) {
      setLoadStatus("integrity_failure");
      setMessage("Exact graph scope is required for Threat Sheet projection.");
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
    loadStatus,
    hit,
    message,
  };
}
