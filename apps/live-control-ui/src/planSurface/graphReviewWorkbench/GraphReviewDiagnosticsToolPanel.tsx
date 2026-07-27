import type { GraphReviewDiagnosticsProjectionPayload } from "../projection/projectionBindings";
import { GraphReviewDeltaInspectorPanel } from "./GraphReviewDeltaInspectorPanel";
import { GraphReviewDeltaSummaryPanel } from "./GraphReviewDeltaSummaryPanel";
import { GraphReviewEvidenceSplitPanel } from "./GraphReviewEvidenceSplitPanel";
import { GraphReviewMetricPanel } from "./GraphReviewMetricPanel";
import { GraphReviewSourceSpanInspectorPanel } from "./GraphReviewSourceSpanInspectorPanel";
import { GraphReviewSourceSpanRail } from "./GraphReviewSourceSpanRail";
import { GraphReviewVariantInventoryPanel } from "./GraphReviewVariantInventoryPanel";
import { GraphReviewVariantLanePanel } from "./GraphReviewVariantLanePanel";
import { GraphReviewVariantObjectInspectorPanel } from "./GraphReviewVariantObjectInspectorPanel";

export interface GraphReviewDiagnosticsToolPanelProps {
  payload: GraphReviewDiagnosticsProjectionPayload | null;
}

export function GraphReviewDiagnosticsToolPanel({
  payload,
}: GraphReviewDiagnosticsToolPanelProps) {
  if (!payload) {
    return (
      <p className="plan-projection-empty" data-testid="graph-review-diagnostics-unavailable">
        Graph Review diagnostics are unavailable for the current projection surface.
      </p>
    );
  }

  const {
    campaignId,
    sessionId,
    liveRun,
    projection,
    projectionStatus,
    compareStatus,
    compare,
    compareError,
    selection,
    onSelectSelection,
    deltaIndex,
    sourceSpanDeltaIndex,
    selectedDeltaNodeId,
    setSelectedEvidenceDeltaId,
    selectedEvidenceDeltaId,
    selectedSourceSpanId,
    setSelectedSourceSpanId,
    evidenceSelection,
    evidenceDiff,
    evidenceStatus,
    evidenceError,
    manualBeds,
    manualBedsStatus,
    manualBedsError,
    selectedManualBed,
    selectedVariantLaneView,
    selectedManualVariant,
    onSelectManualBedId,
    onSelectManualVariantName,
    variantInventoryIndex,
    selectedVariantInventoryRowId,
    setSelectedVariantInventoryRowId,
    selectedVariantInventoryRow,
  } = payload;

  if (projectionStatus !== "ready" || !projection || !liveRun) {
    return (
      <p className="plan-projection-empty">
        Select a live run with a projection to inspect diagnostics.
      </p>
    );
  }

  return (
    <section
      className="graph-review-diagnostics-tool-panel"
      aria-label="Graph review diagnostics"
    >
      <GraphReviewDeltaInspectorPanel
        selectedNodeId={selectedDeltaNodeId}
        selectedNode={
          selectedDeltaNodeId
            ? projection.node_views[selectedDeltaNodeId]
            : null
        }
        presentation={null}
        onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
        selectedEvidenceDeltaId={selectedEvidenceDeltaId}
      />
      <GraphReviewSourceSpanRail
        index={sourceSpanDeltaIndex}
        selectedSourceSpanId={selectedSourceSpanId}
        onSelectSourceSpan={setSelectedSourceSpanId}
      />
      <GraphReviewSourceSpanInspectorPanel
        selectedSourceSpanId={selectedSourceSpanId}
        presentation={
          selectedSourceSpanId
            ? sourceSpanDeltaIndex.spansById[selectedSourceSpanId]
            : null
        }
        onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
        selectedEvidenceDeltaId={selectedEvidenceDeltaId}
      />
      <GraphReviewEvidenceSplitPanel
        selection={evidenceSelection}
        evidence={evidenceDiff}
        status={evidenceStatus}
        errorMessage={evidenceError}
        onClearSelection={() => setSelectedEvidenceDeltaId(null)}
      />
      <GraphReviewVariantLanePanel
        campaignId={campaignId}
        sessionId={sessionId}
        beds={manualBeds ?? []}
        bedsStatus={manualBedsStatus ?? "idle"}
        bedsError={manualBedsError}
        selectedBed={selectedManualBed ?? null}
        selectedLaneView={selectedVariantLaneView ?? null}
        selectedVariant={selectedManualVariant ?? null}
        onSelectBedId={onSelectManualBedId}
        onSelectVariantName={onSelectManualVariantName}
      />
      <GraphReviewVariantInventoryPanel
        index={variantInventoryIndex}
        selectedRowId={selectedVariantInventoryRowId}
        onSelectRow={setSelectedVariantInventoryRowId}
      />
      <GraphReviewVariantObjectInspectorPanel
        selectedRow={selectedVariantInventoryRow}
      />
      <GraphReviewDeltaSummaryPanel
        deltaIndex={deltaIndex}
        compareReady={compareStatus === "ready"}
        projectionReady={projectionStatus === "ready"}
        onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
        selectedEvidenceDeltaId={selectedEvidenceDeltaId}
      />
      <GraphReviewMetricPanel
        compare={compare}
        compareStatus={compareStatus}
        compareError={compareError}
        selection={selection}
        onSelect={onSelectSelection}
      />
    </section>
  );
}
