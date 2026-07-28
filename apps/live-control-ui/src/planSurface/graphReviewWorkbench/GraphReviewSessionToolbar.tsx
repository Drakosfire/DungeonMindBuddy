import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  ExtractPromoteApiError,
  getExtractPromoteStatus,
  prepareExtractPromote,
} from "../../api/extractPromoteApi";
import type { ExtractPromotePrepareResponse } from "../../api/types";
import { GraphAuthoredOverlaySummary } from "./GraphAuthoredOverlaySummary";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

function promoteErrorMessage(error: unknown): string {
  if (error instanceof ExtractPromoteApiError) {
    if (error.code === "run_not_promotable") {
      return `This run cannot be promoted yet: ${error.message}`;
    }
    if (error.code === "world_not_initialized") {
      return "The World Graph is not initialized. Bootstrap it before merging.";
    }
    if (error.code === "run_not_found") {
      return "The selected ingest run was not found on the server.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Failed to prepare promotion.";
}

export function GraphReviewSessionToolbar() {
  const { projection, projectionStatus, liveRun } = useGraphReviewLiveState();
  const [worldInitialized, setWorldInitialized] = useState(false);
  const [worldStatusError, setWorldStatusError] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [prepared, setPrepared] = useState<ExtractPromotePrepareResponse | null>(null);
  const [confirmInFlight, setConfirmInFlight] = useState(false);
  const prepareGenerationRef = useRef(0);
  const liveRunIdRef = useRef<string | null>(liveRun?.run_id?.trim() || null);

  liveRunIdRef.current = liveRun?.run_id?.trim() || null;

  useEffect(() => {
    let cancelled = false;
    setWorldStatusError(null);
    void getExtractPromoteStatus()
      .then((status) => {
        if (cancelled) return;
        setWorldInitialized(status.initialized && status.worldState === "initialized");
      })
      .catch((error) => {
        if (cancelled) return;
        setWorldInitialized(false);
        setWorldStatusError(
          error instanceof Error ? error.message : "Could not read World Graph status.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [liveRun?.run_id, liveRun?.manifest_path]);

  // Clear a prior sheet when the selected run changes; bump generation so
  // in-flight prepare responses for the previous run cannot repopulate it.
  useEffect(() => {
    if (confirmInFlight) return;
    prepareGenerationRef.current += 1;
    setPrepared(null);
    setPrepareError(null);
    setPreparing(false);
  }, [confirmInFlight, liveRun?.run_id, liveRun?.manifest_path]);

  const canReviewAndMerge = useMemo(() => {
    if (projectionStatus !== "ready" || !projection) return false;
    if (!liveRun?.run_id || !liveRun.run_id.trim()) return false;
    if (liveRun.promotable !== true) return false;
    if (!worldInitialized) return false;
    if (confirmInFlight) return false;
    return true;
  }, [confirmInFlight, liveRun, projection, projectionStatus, worldInitialized]);

  const disabledReason = useMemo(() => {
    if (confirmInFlight) {
      return "Merge confirmation is in progress.";
    }
    if (projectionStatus !== "ready" || !projection) {
      return "Load a World Graph session first.";
    }
    if (!liveRun?.run_id || !liveRun.run_id.trim()) {
      return "Browse Load is read-only World Graph memory. Open an exact ExtractionRun to Review & merge.";
    }
    if (liveRun.promotable !== true) {
      return liveRun.promotable_reason?.trim() || "Selected run is not promotable.";
    }
    if (worldStatusError) {
      return worldStatusError;
    }
    if (!worldInitialized) {
      return "World Graph is not initialized.";
    }
    return null;
  }, [confirmInFlight, liveRun, projection, projectionStatus, worldInitialized, worldStatusError]);

  const onReviewAndMerge = useCallback(async () => {
    const runId = liveRun?.run_id?.trim();
    if (!runId || preparing || confirmInFlight) return;
    const generation = prepareGenerationRef.current;
    setPreparing(true);
    setPrepareError(null);
    try {
      const response = await prepareExtractPromote({ runId });
      const stillCurrent =
        generation === prepareGenerationRef.current &&
        liveRunIdRef.current === runId &&
        (response.runId == null || response.runId === runId);
      if (!stillCurrent) {
        return;
      }
      setPrepared(response);
    } catch (error) {
      const stillCurrent =
        generation === prepareGenerationRef.current && liveRunIdRef.current === runId;
      if (!stillCurrent) {
        return;
      }
      setPrepared(null);
      setPrepareError(promoteErrorMessage(error));
    } finally {
      if (generation === prepareGenerationRef.current) {
        setPreparing(false);
      }
    }
  }, [confirmInFlight, liveRun?.run_id, preparing]);

  if (projectionStatus !== "ready" || !projection) {
    return null;
  }

  return (
    <div className="graph-review-session-toolbar-stack">
      <div className="graph-review-session-toolbar" aria-label="Loaded session status">
        <GraphAuthoredOverlaySummary summary={projection.authored_overlay} variant="compact" />
        <div className="graph-review-extract-promote-actions">
          <button
            type="button"
            className="primary"
            disabled={!canReviewAndMerge || preparing}
            title={disabledReason ?? "Prepare a governed promotion proposal"}
            data-testid="graph-review-review-and-merge"
            onClick={() => void onReviewAndMerge()}
          >
            {preparing ? "Preparing…" : "Review & merge"}
          </button>
        </div>
      </div>
      {prepareError ? (
        <p
          className="graph-review-extract-promote-error"
          data-testid="graph-review-extract-promote-error"
          role="alert"
        >
          {prepareError}
        </p>
      ) : null}
      {prepared ? (
        <GraphReviewExtractPromoteSheet
          key={prepared.proposalDigest}
          prepared={prepared}
          onClose={() => {
            if (confirmInFlight) return;
            setPrepared(null);
          }}
          onConfirmInFlightChange={setConfirmInFlight}
        />
      ) : null}
    </div>
  );
}
