import { useCallback, useEffect, useMemo, useState } from "react";

import {
  LiveApiError,
  getDefaultUnionSupergraphProjection,
  getGraphPreviewRuns,
  getRecapArtifacts,
  getRecapGraphPresentation,
  getUnionSupergraphProjection,
} from "../../api/liveApi";
import type {
  GraphPreviewRunSummary,
  RecapArtifactRecord,
  RecapGraphPresentationResponse,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { RecapGraphProjection } from "./RecapGraphProjection";
import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";

type LoadStatus = "loading" | "ready" | "error";
type RecapMode = "union-supergraph" | "legacy";
export type RecapProjectionSource =
  | "latest-graph-ingest"
  | "default-preview-source"
  | "legacy"
  | "unavailable";

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

const DOGFOOD_SESSION_OPTIONS = ["session-21", "session-22", "session-23"];

function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const session = new URLSearchParams(window.location.search).get("session")?.trim();
  return session || null;
}

function isExpectedProjectionMiss(error: unknown): boolean {
  return error instanceof LiveApiError && (error.status === 400 || error.status === 404);
}

export function RecapGraphModule({ context }: RecapGraphModuleProps) {
  const defaultSessionId = requestedSessionFromLocation() ?? `session-${context.ingestSession}`;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<RecapMode>("union-supergraph");
  const [unionPayload, setUnionPayload] = useState<UnionSupergraphProjectionResponse | null>(null);
  const [legacyPayload, setLegacyPayload] = useState<RecapGraphPresentationResponse | null>(null);
  const [projectionSource, setProjectionSource] = useState<RecapProjectionSource>("unavailable");
  const [runs, setRuns] = useState<GraphPreviewRunSummary[]>([]);
  const [selectedRunDir, setSelectedRunDir] = useState("");
  const [pinnedNodeId, setPinnedNodeId] = useState<string | null>(null);
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState(defaultSessionId);

  const sessionOptions = useMemo(() => {
    const options = new Set(sessionRecords.length > 0 ? [] : DOGFOOD_SESSION_OPTIONS);
    options.add(`session-${context.ingestSession}`);
    options.add(defaultSessionId);
    sessionRecords.forEach((record) => options.add(record.session_id));
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [context.ingestSession, defaultSessionId, sessionRecords]);


  const loadUnionProjection = useCallback(async (sessionId = selectedSessionId) => {
    setStatus("loading");
    setError(null);
    setPinnedNodeId(null);
    try {
      const projection = await getUnionSupergraphProjection({
        campaignId: context.campaignId,
        sessionId,
        useLatestGraphIngest: true,
      });
      setUnionPayload(projection);
      setProjectionSource("latest-graph-ingest");
      setMode("union-supergraph");
      setStatus("ready");
      return;
    } catch (latestError) {
      if (!isExpectedProjectionMiss(latestError)) {
        setUnionPayload(null);
        setProjectionSource("unavailable");
        setError(latestError instanceof Error ? latestError.message : "Failed to load latest graph-ingest projection");
        setStatus("error");
        return;
      }
    }

    try {
      const projection = await getDefaultUnionSupergraphProjection(sessionId);
      setUnionPayload(projection);
      setProjectionSource("default-preview-source");
      setMode("union-supergraph");
      setStatus("ready");
    } catch (fallbackError) {
      setUnionPayload(null);
      setProjectionSource("unavailable");
      setError(
        fallbackError instanceof Error
          ? `No union-supergraph projection is available for ${sessionId}. ${fallbackError.message}`
          : `No union-supergraph projection is available for ${sessionId}.`,
      );
      setStatus("error");
    }
  }, [context.campaignId, selectedSessionId]);

  const loadLegacyRun = useCallback(async (runDir?: string, sessionId = selectedSessionId) => {
    setStatus("loading");
    setError(null);
    try {
      const recapQuery = {
        campaign_id: context.campaignId,
        session_id: sessionId,
      };
      const [runList, recap] = await Promise.all([
        getGraphPreviewRuns(recapQuery),
        getRecapGraphPresentation({ ...recapQuery, run_dir: runDir }),
      ]);
      setRuns(runList.runs);
      setLegacyPayload(recap);
      setSelectedRunDir(recap.run_dir);
      setPinnedNodeId((current) => {
        if (current && recap.nodes[current]) {
          return current;
        }
        return Object.keys(recap.nodes)[0] ?? null;
      });
      setProjectionSource("legacy");
      setMode("legacy");
      setStatus("ready");
    } catch (loadError) {
      setStatus("error");
      setError(loadError instanceof Error ? loadError.message : "Failed to load legacy recap graph");
    }
  }, [context.campaignId, selectedSessionId]);

  useEffect(() => {
    let cancelled = false;

    void getRecapArtifacts(context.campaignId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
        setSessionRecords(records);
        setSelectedSessionId(defaultSessionId || records[0]?.session_id || `session-${context.ingestSession}`);
      })
      .catch(() => {
        if (!cancelled) {
          setSessionRecords([]);
          setSelectedSessionId(defaultSessionId);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [context.campaignId, defaultSessionId]);

  useEffect(() => {
    if (mode === "legacy") {
      return;
    }
    void loadUnionProjection(selectedSessionId);
  }, [loadUnionProjection, mode, selectedSessionId]);

  if (status === "loading") {
    return <p className="plan-projection-empty">Loading union supergraph projection…</p>;
  }

  if (status === "error" && mode === "union-supergraph") {
    return (
      <div className="recap-reader-root">
        <p className="graph-preview-error" role="alert">
          {error ?? `No union-supergraph projection is available for ${selectedSessionId}.`}
        </p>
        <button type="button" onClick={() => void loadUnionProjection(selectedSessionId)}>
          Retry
        </button>
        <button type="button" onClick={() => void loadLegacyRun()}>
          Open legacy recap preview
        </button>
      </div>
    );
  }

  if (mode === "union-supergraph" && unionPayload) {
    return (
      <UnionSupergraphRecapProjection
        payload={unionPayload}
        selectedSessionId={selectedSessionId}
        onSelectSession={(sessionId) => {
          setSelectedSessionId(sessionId);
        }}
        sessionOptions={sessionOptions}
        projectionSource={projectionSource}
        onOpenLegacy={() => {
          void loadLegacyRun(undefined, selectedSessionId);
        }}
      />
    );
  }

  if (status === "error" || !legacyPayload) {
    return (
      <div className="recap-reader-root">
        <p className="graph-preview-error" role="alert">{error ?? "Recap graph unavailable."}</p>
        <button type="button" onClick={() => void loadLegacyRun(selectedRunDir || undefined)}>
          Retry legacy preview
        </button>
        <button type="button" onClick={() => void loadUnionProjection(selectedSessionId)}>
          Back to union supergraph
        </button>
      </div>
    );
  }

  return (
    <RecapGraphProjection
      payload={legacyPayload}
      runs={runs}
      sessionRecords={sessionRecords}
      selectedSessionId={selectedSessionId}
      onSelectSession={(sessionId) => {
        setSelectedSessionId(sessionId);
        setSelectedRunDir("");
        void loadLegacyRun(undefined, sessionId);
      }}
      selectedRunDir={selectedRunDir}
      onSelectRun={(runDir) => {
        setSelectedRunDir(runDir);
        void loadLegacyRun(runDir);
      }}
      pinnedNodeId={pinnedNodeId}
      onPinNode={setPinnedNodeId}
    />
  );
}
