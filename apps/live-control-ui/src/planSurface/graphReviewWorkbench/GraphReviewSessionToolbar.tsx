import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  ExtractPromoteApiError,
  prepareExtractPromote,
} from "../../api/extractPromoteApi";
import type { ExtractPromotePrepareResponse } from "../../api/types";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import type { SelectedWorldState } from "../../selectedWorld/SelectedWorldContext";
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

function selectedWorldGuidance(selection: SelectedWorldState): string | null {
  switch (selection.kind) {
    case "managed":
      return null;
    case "loading":
      return "Wait for the selected World to finish verification before preparing this recap.";
    case "error":
      return `Selected World could not be verified: ${selection.message}`;
    case "legacy":
      return "Select a verified managed World before preparing this recap.";
  }
}

export function GraphReviewSessionToolbar({
  onConfirmInFlightChange,
}: {
  onConfirmInFlightChange?: (inFlight: boolean) => void;
} = {}) {
  const { projection, projectionStatus, liveRun, committedPhase, committedReceipt } =
    useGraphReviewLiveState();
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const targetGuidance = selectedWorldGuidance(selectedWorld);
  const [preparing, setPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [prepared, setPrepared] = useState<ExtractPromotePrepareResponse | null>(null);
  const [confirmInFlight, setConfirmInFlight] = useState(false);
  const prepareGenerationRef = useRef(0);
  const liveRunIdRef = useRef<string | null>(liveRun?.run_id?.trim() || null);
  const managedWorldIdRef = useRef<string | null>(managedWorldId);

  liveRunIdRef.current = liveRun?.run_id?.trim() || null;
  managedWorldIdRef.current = managedWorldId;
  const hasTerminalCommittedReceipt =
    committedPhase !== "candidate" && committedReceipt != null;

  const handleConfirmInFlightChange = useCallback(
    (inFlight: boolean) => {
      setConfirmInFlight(inFlight);
      onConfirmInFlightChange?.(inFlight);
    },
    [onConfirmInFlightChange],
  );

  // Clear a prior sheet when the selected run changes; bump generation so
  // in-flight prepare responses for the previous run cannot repopulate it.
  useEffect(() => {
    if (confirmInFlight) return;
    prepareGenerationRef.current += 1;
    setPrepared(null);
    setPrepareError(null);
    setPreparing(false);
  }, [confirmInFlight, liveRun?.run_id, liveRun?.manifest_path, managedWorldId]);

  const canReviewAndMerge = useMemo(() => {
    if (hasTerminalCommittedReceipt) return false;
    if (projectionStatus !== "ready" || !projection) return false;
    if (!liveRun?.run_id || !liveRun.run_id.trim()) return false;
    if (liveRun.promotable !== true) return false;
    if (!managedWorldId) return false;
    if (confirmInFlight) return false;
    return true;
  }, [
    confirmInFlight,
    hasTerminalCommittedReceipt,
    liveRun,
    managedWorldId,
    projection,
    projectionStatus,
  ]);

  const disabledReason = useMemo(() => {
    if (hasTerminalCommittedReceipt) {
      return "Committed World Graph authority is active for this binding. Reload the committed revision instead of preparing again.";
    }
    if (confirmInFlight) {
      return "Merge confirmation is in progress.";
    }
    if (targetGuidance) {
      return targetGuidance;
    }
    if (projectionStatus !== "ready" || !projection) {
      return "Load a preview-ready run first.";
    }
    if (!liveRun?.run_id || !liveRun.run_id.trim()) {
      return "Selected run is missing a server run id.";
    }
    if (liveRun.promotable !== true) {
      return liveRun.promotable_reason?.trim() || "Selected run is not promotable.";
    }
    return null;
  }, [
    confirmInFlight,
    hasTerminalCommittedReceipt,
    liveRun,
    targetGuidance,
    projection,
    projectionStatus,
  ]);

  const onReviewAndMerge = useCallback(async () => {
    const runId = liveRun?.run_id?.trim();
    if (!runId || !managedWorldId || preparing || confirmInFlight || hasTerminalCommittedReceipt) return;
    const generation = prepareGenerationRef.current;
    setPreparing(true);
    setPrepareError(null);
    try {
      const response = await prepareExtractPromote({ runId, managedWorldId });
      const stillCurrent =
        generation === prepareGenerationRef.current &&
        liveRunIdRef.current === runId &&
        managedWorldIdRef.current === managedWorldId &&
        (response.runId == null || response.runId === runId);
      if (!stillCurrent) {
        return;
      }
      setPrepared(response);
    } catch (error) {
      const stillCurrent =
        generation === prepareGenerationRef.current &&
        liveRunIdRef.current === runId &&
        managedWorldIdRef.current === managedWorldId;
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
  }, [confirmInFlight, hasTerminalCommittedReceipt, liveRun?.run_id, managedWorldId, preparing]);

  if (projectionStatus !== "ready" || !projection) {
    if (committedPhase === "candidate") {
      return null;
    }
  }

  return (
    <div className="graph-review-session-toolbar-stack">
      {projectionStatus === "ready" && projection ? (
        <div className="graph-review-session-toolbar" aria-label="Loaded session status">
          <GraphAuthoredOverlaySummary summary={projection.authored_overlay} variant="compact" />
          <div className="graph-review-extract-promote-actions">
            {!hasTerminalCommittedReceipt ? (
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
            ) : (
              <p
                className="module-muted"
                data-testid="graph-review-committed-prepare-suppressed"
              >
                Prepare/confirm hidden while committed World Graph authority is active.
              </p>
            )}
          </div>
        </div>
      ) : null}
      {targetGuidance ? (
        <p
          className="module-muted"
          data-testid="graph-review-selected-world-guidance"
          role="status"
        >
          {targetGuidance}
        </p>
      ) : null}
      {prepareError ? (
        <p
          className="graph-review-extract-promote-error"
          data-testid="graph-review-extract-promote-error"
          role="alert"
        >
          {prepareError}
        </p>
      ) : null}
      {prepared && !hasTerminalCommittedReceipt ? (
        <GraphReviewExtractPromoteSheet
          key={prepared.proposalDigest}
          prepared={prepared}
          onClose={() => {
            if (confirmInFlight) return;
            setPrepared(null);
          }}
          onConfirmInFlightChange={handleConfirmInFlightChange}
        />
      ) : null}
    </div>
  );
}
