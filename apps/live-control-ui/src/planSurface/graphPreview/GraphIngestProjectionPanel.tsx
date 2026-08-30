import { useCallback, useEffect, useState } from "react";

import {
  getLatestGraphIngestRun,
  getUnionSupergraphProjection,
  LiveApiError,
} from "../../api/liveApi";
import type {
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";

type LatestRunStatus = "loading" | "ready" | "unavailable" | "warning" | "error";
type ProjectionLoadStatus = "idle" | "loading" | "ready" | "error";

function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const session = new URLSearchParams(window.location.search).get("session")?.trim();
  return session || null;
}

function ingestSessionId(context: PlanContextDescriptor): string {
  return requestedSessionFromLocation() ?? `session-${context.ingestSession}`;
}

interface GraphIngestProjectionPanelProps {
  context: PlanContextDescriptor;
  sessionId?: string;
  sourceRecapPath?: string;
  sourceRecapSha256?: string;
}

function displayMetadataValue(value: string | null | undefined): string {
  return value?.trim() || "Unknown";
}

function displayBoolean(value: boolean): string {
  return value ? "Yes" : "No";
}

function friendlyProjectionError(error: unknown): string {
  if (error instanceof LiveApiError) {
    if (
      error.status === 410
      || error.code === "union_supergraph_preview_retired"
    ) {
      return (
        "UnionSupergraph store preview is retired. This is not a missing ingest artifact — "
        + "use retained gold/manual/recap graph-preview surfaces instead."
      );
    }
    if (error.status === 404) return "The latest graph-ingest run disappeared or its projection artifact is missing.";
    if (error.status === 400) return `The projection API rejected this manifest/store: ${error.message}`;
    if (error.status >= 500) return `Unexpected backend failure while loading projection: ${error.message}`;
  }
  return error instanceof Error ? error.message : "Failed to load union graph projection.";
}

export function GraphIngestProjectionPanel({
  context,
  sessionId: providedSessionId,
  sourceRecapPath,
  sourceRecapSha256,
}: GraphIngestProjectionPanelProps) {
  const sessionId = providedSessionId ?? ingestSessionId(context);
  const [latestStatus, setLatestStatus] = useState<LatestRunStatus>("loading");
  const [latestGraphRun, setLatestGraphRun] = useState<GraphIngestRunSummary | null>(null);
  const [latestGraphRunError, setLatestGraphRunError] = useState<string | null>(null);
  const [projectionStatus, setProjectionStatus] = useState<ProjectionLoadStatus>("idle");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [unionProjection, setUnionProjection] = useState<UnionSupergraphProjectionResponse | null>(null);

  const loadLatest = useCallback(async () => {
    setLatestStatus("loading");
    setLatestGraphRunError(null);
    setProjectionStatus("idle");
    setProjectionError(null);
    setUnionProjection(null);
    try {
      const response = await getLatestGraphIngestRun(
        context.campaignId,
        sessionId,
        sourceRecapPath,
        sourceRecapSha256,
      );
      setLatestGraphRun(response.run);
      setLatestStatus(response.run ? "ready" : "unavailable");
    } catch (error) {
      setLatestGraphRun(null);
      if (error instanceof LiveApiError && error.status === 404) {
        setLatestStatus("unavailable");
        return;
      }
      if (error instanceof LiveApiError && error.status === 422) {
        setLatestStatus("warning");
        setLatestGraphRunError(`Invalid graph-ingest configuration: ${error.message}`);
        return;
      }
      setLatestStatus("error");
      setLatestGraphRunError(error instanceof Error ? error.message : "Failed to load latest graph-ingest run.");
    }
  }, [context.campaignId, sessionId, sourceRecapPath, sourceRecapSha256]);

  useEffect(() => {
    void loadLatest();
  }, [loadLatest]);

  const openIngestRecap = () => {
    if (typeof window === "undefined") return;
    window.location.assign(`/plan?tool=ingest-recap&session=${encodeURIComponent(sessionId)}`);
  };

  const openUnionGraph = async () => {
    setProjectionStatus("loading");
    setProjectionError(null);
    try {
      const projection = await getUnionSupergraphProjection({
        campaignId: context.campaignId,
        sessionId,
        useLatestGraphIngest: true,
        sourceRecapPath,
        sourceRecapSha256,
      });
      setUnionProjection(projection);
      setProjectionStatus("ready");
    } catch (error) {
      setProjectionStatus("error");
      setProjectionError(friendlyProjectionError(error));
    }
  };

  return (
    <section className="graph-ingest-panel" aria-label="Latest Graph-Ingest Projection">
      <header className="graph-ingest-panel-header">
        <div>
          <p className="plan-surface-kicker">Latest Graph-Ingest Projection</p>
          <h2>Open latest union graph (retired)</h2>
          <p>
            Looks for the latest preview-union-ready graph-ingest run for {context.campaignId} / {sessionId}.
          </p>
        </div>
        <button type="button" onClick={loadLatest} disabled={latestStatus === "loading"}>
          Refresh
        </button>
      </header>

      {latestStatus === "loading" ? (
        <p className="graph-ingest-status-row">Loading latest graph-ingest run…</p>
      ) : null}

      {latestStatus === "unavailable" ? (
        <div className="graph-ingest-run-card" data-state="unavailable">
          <strong>Graph-rendered recap not ready yet</strong>
          <p>No lineage-matched graph projection exists for this ingested recap yet.</p>
          <p>
            Generate Recap Memory for this session, then refresh. That one button now creates the
            graph projection used by Recap View.
          </p>
          <button type="button" onClick={openIngestRecap}>
            Generate Recap Memory for {sessionId}
          </button>
        </div>
      ) : null}

      {latestStatus === "warning" || latestStatus === "error" ? (
        <div className="graph-ingest-run-card" data-state="error" role="alert">
          <strong>
            {latestStatus === "warning" ? "Graph-ingest configuration warning" : "Error: API/client failure"}
          </strong>
          <p>{latestGraphRunError ?? "Unable to load latest graph-ingest status."}</p>
        </div>
      ) : null}

      {latestStatus === "ready" && latestGraphRun ? (
        <div className="graph-ingest-run-card" data-state="ready">
          <strong>Ready: latest preview_union_store_ready run found</strong>
          <dl className="graph-ingest-status-row">
            <div>
              <dt>Status</dt>
              <dd>{latestGraphRun.status}</dd>
            </div>
            <div>
              <dt>Run label</dt>
              <dd>{displayMetadataValue(latestGraphRun.run_label)}</dd>
            </div>
            <div>
              <dt>Run ID</dt>
              <dd>{displayMetadataValue(latestGraphRun.run_id)}</dd>
            </div>
            <div>
              <dt>Generated at</dt>
              <dd>{displayMetadataValue(latestGraphRun.generated_at)}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>{displayMetadataValue(latestGraphRun.model_id)}</dd>
            </div>
            <div>
              <dt>Provider</dt>
              <dd>{displayMetadataValue(latestGraphRun.model_provider)}</dd>
            </div>
            <div>
              <dt>Extraction profile</dt>
              <dd>{displayMetadataValue(latestGraphRun.extraction_profile)}</dd>
            </div>
            <div>
              <dt>Extraction mode</dt>
              <dd>{displayMetadataValue(latestGraphRun.extraction_mode)}</dd>
            </div>
            <div>
              <dt>Vocabulary mode</dt>
              <dd>{displayMetadataValue(latestGraphRun.vocabulary_mode)}</dd>
            </div>
            <div>
              <dt>Preview union available</dt>
              <dd>{displayBoolean(latestGraphRun.preview_union_available)}</dd>
            </div>
            <div>
              <dt>Manifest path</dt>
              <dd>{latestGraphRun.manifest_path}</dd>
            </div>
            <div>
              <dt>Preview union store path</dt>
              <dd>{latestGraphRun.preview_union_store_path ?? "Not reported"}</dd>
            </div>
            <div>
              <dt>Nodes</dt>
              <dd>{latestGraphRun.node_count}</dd>
            </div>
            <div>
              <dt>Edges</dt>
              <dd>{latestGraphRun.edge_count}</dd>
            </div>
            <div>
              <dt>Evidence refs</dt>
              <dd>{latestGraphRun.evidence_ref_count}</dd>
            </div>
          </dl>
          {latestGraphRun.next_actions.length ? (
            <div className="graph-ingest-badge-row" aria-label="Next actions">
              {latestGraphRun.next_actions.map((action) => <span key={action}>{action}</span>)}
            </div>
          ) : null}
          <div className="graph-ingest-projection-actions">
            <button type="button" onClick={openUnionGraph} disabled={projectionStatus === "loading"}>
              {projectionStatus === "loading" ? "Opening Union Graph…" : "Open Union Graph"}
            </button>
            <button type="button" onClick={loadLatest}>
              Refresh
            </button>
          </div>
        </div>
      ) : null}

      {projectionStatus === "error" ? (
        <p className="graph-preview-error" role="alert">
          {projectionError}
        </p>
      ) : null}

      {projectionStatus === "ready" && unionProjection ? (
        <div className="graph-ingest-projection-layout">
          <UnionSupergraphRecapProjection
            payload={unionProjection}
            selectedSessionId={sessionId}
            onSelectSession={() => undefined}
            sessionOptions={[sessionId]}
            selectedCampaignId={context.campaignId}
            onSelectCampaign={() => undefined}
          />
        </div>
      ) : null}
    </section>
  );
}
