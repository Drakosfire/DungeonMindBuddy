import { useEffect } from "react";

import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "../projection/projectionBindings";
import { useProjection } from "../projection/projectionContext";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

/**
 * Publishes the diagnostics fields consumed by GraphReviewDiagnosticsToolPanel.
 * Must mount under GraphReviewLiveStateProvider and ProjectionProvider.
 */
export function GraphReviewDiagnosticsProjectionBinding() {
  const { registerToolProjectionPayload } = useProjection();
  const live = useGraphReviewLiveState();

  useEffect(() => {
    return registerToolProjectionPayload(GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID, {
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
    });
  }, [live, registerToolProjectionPayload]);

  return null;
}
