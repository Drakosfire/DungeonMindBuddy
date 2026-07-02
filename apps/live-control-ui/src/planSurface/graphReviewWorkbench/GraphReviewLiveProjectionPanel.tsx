import { useEffect, useMemo, useState } from "react";

import { getUnionSupergraphProjection, LiveApiError } from "../../api/liveApi";
import type { GoldReviewCompareResponse, GraphIngestRunSummary, GraphReviewLane, UnionSupergraphProjectionResponse } from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { GraphReviewDeltaInspectorPanel } from "./GraphReviewDeltaInspectorPanel";
import { GraphReviewDeltaSummaryPanel } from "./GraphReviewDeltaSummaryPanel";
import { buildGraphReviewDeltaIndex } from "./graphReviewDeltaUtils";
import { buildLiveNodeDeltaPresentationIndex, statusLabelForPill } from "./graphReviewPillOverlayUtils";

interface GraphReviewLiveProjectionPanelProps {
  campaignId: string;
  sessionId: string;
  liveRun: GraphIngestRunSummary | null;
  compare?: GoldReviewCompareResponse | null;
  compareStatus?: "idle" | "loading" | "ready" | "error";
  goldLane?: GraphReviewLane | null;
  liveLane?: GraphReviewLane | null;
}

type ProjectionStatus = "idle" | "loading" | "ready" | "error" | "unavailable";

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
  compare = null,
  compareStatus = "idle",
  goldLane = null,
  liveLane = null,
}: GraphReviewLiveProjectionPanelProps) {
  const [projection, setProjection] = useState<UnionSupergraphProjectionResponse | null>(null);
  const [projectionStatus, setProjectionStatus] = useState<ProjectionStatus>("idle");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [selectedDeltaNodeId, setSelectedDeltaNodeId] = useState<string | null>(null);

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

  const runIdentity = liveRun?.run_label || liveRun?.manifest_path || "selected run";

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
            onActiveNodeChange={setSelectedDeltaNodeId}
          />
          <GraphReviewDeltaInspectorPanel
            selectedNodeId={selectedDeltaNodeId}
            selectedNode={selectedDeltaNodeId ? projection.node_views[selectedDeltaNodeId] : null}
            presentation={selectedDeltaNodeId ? nodeDeltaPresentations[selectedDeltaNodeId] : null}
          />
        </>
      ) : null}

      {(compareStatus === "ready" || projectionStatus === "ready" || projectionStatus === "error" || projectionStatus === "unavailable") ? (
        <GraphReviewDeltaSummaryPanel
          deltaIndex={deltaIndex}
          compareReady={compareStatus === "ready"}
          projectionReady={projectionStatus === "ready"}
        />
      ) : null}
    </section>
  );
}
