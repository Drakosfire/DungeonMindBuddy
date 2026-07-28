import { useEffect, useMemo } from "react";

import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "../projection/projectionBindings";
import { useProjection } from "../projection/projectionContext";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

/**
 * Publishes the diagnostics fields consumed by GraphReviewDiagnosticsToolPanel.
 * Must mount under GraphReviewLiveStateProvider and the app projection host.
 */
export function GraphReviewDiagnosticsProjectionBinding() {
  const { projectionSurface, registerToolProjectionPayload } = useProjection();
  const live = useGraphReviewLiveState();
  const payload = useMemo(
    () => ({
      campaignId: live.campaignId,
      sessionId: live.sessionId,
      liveRun: live.liveRun,
      projection: live.projection,
      projectionStatus: live.projectionStatus,
      compareStatus: live.compareStatus,
      compare: live.compare,
      compareError: live.compareError,
      selection: live.selection,
      onSelectSelection: live.onSelectSelection,
      deltaIndex: live.deltaIndex,
      sourceSpanDeltaIndex: live.sourceSpanDeltaIndex,
      selectedDeltaNodeId: live.selectedDeltaNodeId,
      setSelectedEvidenceDeltaId: live.setSelectedEvidenceDeltaId,
      selectedEvidenceDeltaId: live.selectedEvidenceDeltaId,
      selectedSourceSpanId: live.selectedSourceSpanId,
      setSelectedSourceSpanId: live.setSelectedSourceSpanId,
      evidenceSelection: live.evidenceSelection,
      evidenceDiff: live.evidenceDiff,
      evidenceStatus: live.evidenceStatus,
      evidenceError: live.evidenceError,
      manualBeds: live.manualBeds,
      manualBedsStatus: live.manualBedsStatus,
      manualBedsError: live.manualBedsError,
      selectedManualBed: live.selectedManualBed,
      selectedVariantLaneView: live.selectedVariantLaneView,
      selectedManualVariant: live.selectedManualVariant,
      onSelectManualBedId: live.onSelectManualBedId,
      onSelectManualVariantName: live.onSelectManualVariantName,
      variantInventoryIndex: live.variantInventoryIndex,
      selectedVariantInventoryRowId: live.selectedVariantInventoryRowId,
      setSelectedVariantInventoryRowId: live.setSelectedVariantInventoryRowId,
      selectedVariantInventoryRow: live.selectedVariantInventoryRow,
    }),
    [
      live.campaignId,
      live.sessionId,
      live.liveRun,
      live.projection,
      live.projectionStatus,
      live.compareStatus,
      live.compare,
      live.compareError,
      live.selection,
      live.onSelectSelection,
      live.deltaIndex,
      live.sourceSpanDeltaIndex,
      live.selectedDeltaNodeId,
      live.setSelectedEvidenceDeltaId,
      live.selectedEvidenceDeltaId,
      live.selectedSourceSpanId,
      live.setSelectedSourceSpanId,
      live.evidenceSelection,
      live.evidenceDiff,
      live.evidenceStatus,
      live.evidenceError,
      live.manualBeds,
      live.manualBedsStatus,
      live.manualBedsError,
      live.selectedManualBed,
      live.selectedVariantLaneView,
      live.selectedManualVariant,
      live.onSelectManualBedId,
      live.onSelectManualVariantName,
      live.variantInventoryIndex,
      live.selectedVariantInventoryRowId,
      live.setSelectedVariantInventoryRowId,
      live.selectedVariantInventoryRow,
    ],
  );

  useEffect(() => {
    return registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, payload);
  }, [payload, projectionSurface, registerToolProjectionPayload]);

  return null;
}
