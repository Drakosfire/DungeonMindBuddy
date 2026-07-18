import { useCallback, useEffect, useMemo, useState } from "react";

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

  // Clear a prior sheet when the selected run changes.
  useEffect(() => {
    setPrepared(null);
    setPrepareError(null);
  }, [liveRun?.run_id, liveRun?.manifest_path]);

  const canReviewAndMerge = useMemo(() => {
    if (projectionStatus !== "ready" || !projection) return false;
    if (!liveRun?.preview_union_available) return false;
    if (!liveRun.run_id || !liveRun.run_id.trim()) return false;
    if (!worldInitialized) return false;
    return true;
  }, [liveRun, projection, projectionStatus, worldInitialized]);

  const disabledReason = useMemo(() => {
    if (projectionStatus !== "ready" || !projection) {
      return "Load a preview-ready run first.";
    }
    if (!liveRun?.preview_union_available) {
      return "Selected run is not preview-ready.";
    }
    if (!liveRun.run_id || !liveRun.run_id.trim()) {
      return "Selected run is missing a server run id.";
    }
    if (worldStatusError) {
      return worldStatusError;
    }
    if (!worldInitialized) {
      return "World Graph is not initialized.";
    }
    return null;
  }, [liveRun, projection, projectionStatus, worldInitialized, worldStatusError]);

  const onReviewAndMerge = useCallback(async () => {
    const runId = liveRun?.run_id?.trim();
    if (!runId || preparing) return;
    setPreparing(true);
    setPrepareError(null);
    try {
      const response = await prepareExtractPromote({ runId });
      setPrepared(response);
    } catch (error) {
      setPrepared(null);
      setPrepareError(promoteErrorMessage(error));
    } finally {
      setPreparing(false);
    }
  }, [liveRun?.run_id, preparing]);

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
          prepared={prepared}
          onClose={() => setPrepared(null)}
        />
      ) : null}
    </div>
  );
}
