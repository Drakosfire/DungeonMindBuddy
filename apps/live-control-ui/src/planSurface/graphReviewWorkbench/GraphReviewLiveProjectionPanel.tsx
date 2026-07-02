import { useEffect, useMemo, useState } from "react";

import { getGoldReviewEvidence, getUnionSupergraphProjection, LiveApiError } from "../../api/liveApi";
import type { GoldReviewCompareResponse, GoldReviewEvidenceDiffResponse, GoldReviewSessionSummary, GraphIngestRunSummary, GraphReviewLane, ManualReviewBedDetail, ManualReviewBedSummary, UnionSupergraphProjectionResponse } from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { GraphReviewDeltaInspectorPanel } from "./GraphReviewDeltaInspectorPanel";
import { GraphReviewDeltaSummaryPanel } from "./GraphReviewDeltaSummaryPanel";
import { GraphReviewReferenceLanePanel } from "./GraphReviewReferenceLanePanel";
import { GraphReviewEvidenceSplitPanel } from "./GraphReviewEvidenceSplitPanel";
import { GraphReviewSourceSpanInspectorPanel } from "./GraphReviewSourceSpanInspectorPanel";
import { GraphReviewSourceSpanRail } from "./GraphReviewSourceSpanRail";
import { GraphReviewVariantInventoryPanel } from "./GraphReviewVariantInventoryPanel";
import { GraphReviewVariantLanePanel } from "./GraphReviewVariantLanePanel";
import { GraphReviewVariantObjectInspectorPanel } from "./GraphReviewVariantObjectInspectorPanel";
import { GraphReviewTwoLaneShell, type GraphReviewTwoLaneLayoutMode } from "./GraphReviewTwoLaneShell";
import { buildGraphReviewDeltaIndex } from "./graphReviewDeltaUtils";
import { buildPrimaryLiveLaneView, buildReferenceLaneView } from "./graphReviewReferenceLaneUtils";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import { buildLiveNodeDeltaPresentationIndex, statusLabelForPill } from "./graphReviewPillOverlayUtils";
import { buildSourceSpanDeltaIndex, statusLabelForSourceSpan } from "./graphReviewSourceSpanOverlayUtils";
import type { GraphReviewManualVariantLaneView, GraphReviewManualVariantSelection } from "./graphReviewVariantReferenceUtils";
import { buildVariantLiveInventoryIndex } from "./graphReviewVariantReferenceUtils";

interface GraphReviewLiveProjectionPanelProps {
  campaignId: string;
  sessionId: string;
  liveRun: GraphIngestRunSummary | null;
  selectedSession?: GoldReviewSessionSummary | null;
  compare?: GoldReviewCompareResponse | null;
  compareStatus?: "idle" | "loading" | "ready" | "error";
  goldLane?: GraphReviewLane | null;
  liveLane?: GraphReviewLane | null;
  manualBeds?: ManualReviewBedSummary[];
  manualBedsStatus?: "idle" | "loading" | "ready" | "error";
  manualBedsError?: string | null;
  selectedManualBed?: ManualReviewBedDetail | null;
  selectedVariantLaneView?: GraphReviewManualVariantLaneView | null;
  selectedManualVariant?: GraphReviewManualVariantSelection | null;
  onSelectManualBedId?: (bedId: string | null) => void;
  onSelectManualVariantName?: (variantName: string | null) => void;
}

type ProjectionStatus = "idle" | "loading" | "ready" | "error" | "unavailable";
type EvidenceStatus = "idle" | "loading" | "ready" | "error" | "unavailable";

const FALLBACK_MARKDOWN = `# Projection unavailable\n\nThe selected live run did not return projected recap Markdown.`;

function friendlyProjectionError(error: unknown): string {
  if (error instanceof LiveApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Failed to load selected live lane projection.";
}

function metadataValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}

export function GraphReviewLiveProjectionPanel({
  campaignId,
  sessionId,
  liveRun,
  selectedSession = null,
  compare = null,
  compareStatus = "idle",
  goldLane = null,
  liveLane = null,
  manualBeds = [],
  manualBedsStatus = "idle",
  manualBedsError = null,
  selectedManualBed = null,
  selectedVariantLaneView = null,
  selectedManualVariant = null,
  onSelectManualBedId = () => undefined,
  onSelectManualVariantName = () => undefined,
}: GraphReviewLiveProjectionPanelProps) {
  const [projection, setProjection] = useState<UnionSupergraphProjectionResponse | null>(null);
  const [projectionStatus, setProjectionStatus] = useState<ProjectionStatus>("idle");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [selectedDeltaNodeId, setSelectedDeltaNodeId] = useState<string | null>(null);
  const [selectedSourceSpanId, setSelectedSourceSpanId] = useState<string | null>(null);
  const [selectedEvidenceDeltaId, setSelectedEvidenceDeltaId] = useState<string | null>(null);
  const [evidenceDiff, setEvidenceDiff] = useState<GoldReviewEvidenceDiffResponse | null>(null);
  const [evidenceStatus, setEvidenceStatus] = useState<EvidenceStatus>("idle");
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [selectedVariantInventoryRowId, setSelectedVariantInventoryRowId] = useState<string | null>(null);
  const [twoLaneLayoutMode, setTwoLaneLayoutMode] = useState<GraphReviewTwoLaneLayoutMode>("single");

  const liveRunKey = liveRun
    ? `${liveRun.manifest_path}:${liveRun.preview_union_store_path ?? ""}:${liveRun.preview_union_available}`
    : "";

  useEffect(() => {
    let cancelled = false;

    setProjection(null);
    setProjectionError(null);

    if (!liveRun) {
      setProjectionStatus("idle");
      return () => {
        cancelled = true;
      };
    }

    if (!liveRun.preview_union_available) {
      setProjectionStatus("unavailable");
      return () => {
        cancelled = true;
      };
    }

    setProjectionStatus("loading");

    void getUnionSupergraphProjection({
      campaignId,
      sessionId,
      graphRunManifestPath: liveRun.manifest_path,
      previewUnionStorePath: liveRun.preview_union_store_path ?? null,
    })
      .then((response) => {
        if (cancelled) return;
        setProjection(response);
        setProjectionStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setProjection(null);
        setProjectionStatus("error");
        setProjectionError(friendlyProjectionError(error));
      });

    return () => {
      cancelled = true;
    };
  }, [campaignId, sessionId, liveRun, liveRunKey]);

  useEffect(() => {
    setSelectedSourceSpanId(null);
    setSelectedEvidenceDeltaId(null);
  }, [liveRunKey, projection?.graph_id]);

  const paragraphSourceSpans = useMemo(
    () =>
      (projection?.source_spans ?? [])
        .filter((span) => span.kind === "paragraph")
        .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0)),
    [projection?.source_spans],
  );

  const deltaIndex = useMemo(
    () =>
      buildGraphReviewDeltaIndex({
        compare: compare ?? null,
        liveProjection: projection,
        goldLane: goldLane ?? null,
        liveLane: liveLane ?? null,
      }),
    [compare, projection, goldLane, liveLane],
  );

  const nodeDeltaPresentations = useMemo(
    () => buildLiveNodeDeltaPresentationIndex(deltaIndex.deltas),
    [deltaIndex.deltas],
  );

  const readerNodeDeltaPresentations = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(nodeDeltaPresentations).map(([nodeId, presentation]) => [
          nodeId,
          {
            status: presentation.status,
            label: statusLabelForPill(presentation.status),
            summary: presentation.primaryDelta?.summary ?? null,
          },
        ]),
      ),
    [nodeDeltaPresentations],
  );

  const sourceSpanDeltaIndex = useMemo(
    () =>
      buildSourceSpanDeltaIndex({
        sourceSpans: paragraphSourceSpans,
        deltas: deltaIndex.deltas,
      }),
    [paragraphSourceSpans, deltaIndex.deltas],
  );

  const variantInventoryIndex = useMemo(
    () => buildVariantLiveInventoryIndex({ variant: selectedVariantLaneView?.variant ?? null, compare: compare ?? null }),
    [selectedVariantLaneView?.variant, compare],
  );

  const selectedVariantInventoryRow = useMemo(
    () => variantInventoryIndex.rows.find((row) => row.rowId === selectedVariantInventoryRowId) ?? null,
    [variantInventoryIndex.rows, selectedVariantInventoryRowId],
  );

  useEffect(() => {
    setSelectedVariantInventoryRowId(null);
  }, [selectedVariantLaneView?.lane.laneId, liveRunKey]);

  const sourceSpanDeltaOverlays = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(sourceSpanDeltaIndex.spansById).map(([sourceSpanId, presentation]) => [
          sourceSpanId,
          {
            status: presentation.status,
            label: statusLabelForSourceSpan(presentation.status),
          },
        ]),
      ),
    [sourceSpanDeltaIndex],
  );


  const selectedEvidenceDelta = useMemo(
    () => deltaIndex.deltas.find((delta) => delta.deltaId === selectedEvidenceDeltaId) ?? null,
    [deltaIndex.deltas, selectedEvidenceDeltaId],
  );

  const evidenceSelection = useMemo(
    () => buildEvidenceSelectionForDelta(selectedEvidenceDelta),
    [selectedEvidenceDelta],
  );

  useEffect(() => {
    let cancelled = false;

    setEvidenceDiff(null);
    setEvidenceError(null);

    if (!selectedEvidenceDeltaId) {
      setEvidenceStatus("idle");
      return () => {
        cancelled = true;
      };
    }

    if (evidenceSelection.status !== "queryable") {
      setEvidenceStatus("unavailable");
      return () => {
        cancelled = true;
      };
    }

    if (!liveRun) {
      setEvidenceStatus("unavailable");
      return () => {
        cancelled = true;
      };
    }

    setEvidenceStatus("loading");

    void getGoldReviewEvidence({
      campaignId,
      sessionId,
      manifestPath: liveRun.manifest_path,
      objectKind: evidenceSelection.queryObjectKind!,
      objectId: evidenceSelection.queryObjectId!,
    })
      .then((response) => {
        if (cancelled) return;
        setEvidenceDiff(response);
        setEvidenceStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setEvidenceDiff(null);
        setEvidenceStatus("error");
        setEvidenceError(error instanceof Error ? error.message : "Failed to load gold/live evidence.");
      });

    return () => {
      cancelled = true;
    };
  }, [
    campaignId,
    sessionId,
    liveRun,
    liveRun?.manifest_path,
    selectedEvidenceDeltaId,
    evidenceSelection.status,
    evidenceSelection.queryObjectKind,
    evidenceSelection.queryObjectId,
  ]);

  const runIdentity = liveRun?.run_label || liveRun?.manifest_path || "selected run";

  const primaryLaneView = useMemo(
    () => buildPrimaryLiveLaneView(liveRun),
    [liveRun],
  );

  const referenceLaneView = useMemo(
    () =>
      buildReferenceLaneView({
        selectedSession: selectedSession ?? null,
        compare: compare ?? null,
        selectedVariantLaneView,
        preferredReference: "auto",
      }),
    [selectedSession, compare, selectedVariantLaneView],
  );

  return (
    <section className="graph-review-live-projection-panel" aria-label="Selected live lane source projection">
      <header className="graph-review-live-projection-header">
        <div>
          <p className="plan-surface-kicker">Selected live lane</p>
          <h3>Source projection</h3>
          <p>
            Read-only projected source Markdown for the selected graph-ingest run. Graph chips are candidate graph behavior;
            source text remains the review surface.
          </p>
        </div>
        {liveRun ? <span>{runIdentity}</span> : null}
      </header>

      {projectionStatus === "idle" ? (
        <p className="graph-review-live-projection-status">
          Select a live graph-ingest run to render its source projection.
        </p>
      ) : null}

      {projectionStatus === "unavailable" && liveRun ? (
        <div className="graph-review-live-projection-status" role="status">
          <p>Selected live run does not have a preview-union projection available yet.</p>
          <dl className="graph-review-lane-meta">
            <div>
              <dt>Run label</dt>
              <dd>{metadataValue(liveRun.run_label)}</dd>
            </div>
            <div>
              <dt>Run id</dt>
              <dd>{metadataValue(liveRun.run_id)}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{metadataValue(liveRun.status)}</dd>
            </div>
            <div>
              <dt>Manifest path</dt>
              <dd>{metadataValue(liveRun.manifest_path)}</dd>
            </div>
            <div>
              <dt>Preview union path</dt>
              <dd>{metadataValue(liveRun.preview_union_store_path)}</dd>
            </div>
            <div>
              <dt>Next actions</dt>
              <dd>{liveRun.next_actions.length ? liveRun.next_actions.join("; ") : "—"}</dd>
            </div>
          </dl>
        </div>
      ) : null}

      {projectionStatus === "loading" ? (
        <p className="graph-review-live-projection-status" role="status">Loading selected live lane projection…</p>
      ) : null}

      {projectionStatus === "error" && liveRun ? (
        <div className="graph-review-error" role="alert">
          <p>{projectionError ?? "Failed to load selected live lane projection."}</p>
          <p>Selected run: {runIdentity}</p>
        </div>
      ) : null}

      {projectionStatus === "ready" && projection && liveRun ? (
        <>
          <GraphReviewTwoLaneShell
            primaryLane={primaryLaneView}
            referenceLane={referenceLaneView}
            layoutMode={twoLaneLayoutMode}
            onLayoutModeChange={setTwoLaneLayoutMode}
            primary={(
              <GraphProjectionReader
                markdown={projection.markdown ?? FALLBACK_MARKDOWN}
                nodeViews={projection.node_views}
                sourceSpans={paragraphSourceSpans}
                mentionsCount={projection.mentions.length}
                graphId={projection.graph_id}
                title="Selected live lane projection"
                subtitle={`Projected source view for ${runIdentity}`}
                sourceNote={`Live lane · ${liveRun.vocabulary_mode ?? "unknown"} vocabulary · ${liveRun.extraction_profile ?? "unknown"} profile`}
                className="graph-review-live-projection-reader"
                documentLabel="Selected live lane projected source"
                resetKey={`${liveRun.manifest_path}:${liveRun.preview_union_store_path ?? ""}`}
                nodeDeltaPresentations={readerNodeDeltaPresentations}
                sourceSpanDeltaOverlays={sourceSpanDeltaOverlays}
                selectedSourceSpanId={selectedSourceSpanId}
                onActiveNodeChange={setSelectedDeltaNodeId}
              />
            )}
            reference={<GraphReviewReferenceLanePanel referenceLane={referenceLaneView} />}
          />
          <GraphReviewDeltaInspectorPanel
            selectedNodeId={selectedDeltaNodeId}
            selectedNode={selectedDeltaNodeId ? projection.node_views[selectedDeltaNodeId] : null}
            presentation={selectedDeltaNodeId ? nodeDeltaPresentations[selectedDeltaNodeId] : null}
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
            presentation={selectedSourceSpanId ? sourceSpanDeltaIndex.spansById[selectedSourceSpanId] : null}
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
            beds={manualBeds}
            bedsStatus={manualBedsStatus}
            bedsError={manualBedsError}
            selectedBed={selectedManualBed}
            selectedLaneView={selectedVariantLaneView}
            selectedVariant={selectedManualVariant}
            onSelectBedId={onSelectManualBedId}
            onSelectVariantName={onSelectManualVariantName}
          />
          <GraphReviewVariantInventoryPanel
            index={variantInventoryIndex}
            selectedRowId={selectedVariantInventoryRowId}
            onSelectRow={setSelectedVariantInventoryRowId}
          />
          <GraphReviewVariantObjectInspectorPanel selectedRow={selectedVariantInventoryRow} />
        </>
      ) : null}

      {projectionStatus !== "ready" ? (
        <>
          <GraphReviewVariantLanePanel
            campaignId={campaignId}
            sessionId={sessionId}
            beds={manualBeds}
            bedsStatus={manualBedsStatus}
            bedsError={manualBedsError}
            selectedBed={selectedManualBed}
            selectedLaneView={selectedVariantLaneView}
            selectedVariant={selectedManualVariant}
            onSelectBedId={onSelectManualBedId}
            onSelectVariantName={onSelectManualVariantName}
          />
          <GraphReviewVariantInventoryPanel
            index={variantInventoryIndex}
            selectedRowId={selectedVariantInventoryRowId}
            onSelectRow={setSelectedVariantInventoryRowId}
          />
          <GraphReviewVariantObjectInspectorPanel selectedRow={selectedVariantInventoryRow} />
        </>
      ) : null}

      {(compareStatus === "ready" || projectionStatus === "ready" || projectionStatus === "error" || projectionStatus === "unavailable") ? (
        <GraphReviewDeltaSummaryPanel
          deltaIndex={deltaIndex}
          compareReady={compareStatus === "ready"}
          projectionReady={projectionStatus === "ready"}
          onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
          selectedEvidenceDeltaId={selectedEvidenceDeltaId}
        />
      ) : null}
    </section>
  );
}
