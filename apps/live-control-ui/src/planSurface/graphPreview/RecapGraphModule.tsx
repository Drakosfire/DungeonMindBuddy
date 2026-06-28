import { useCallback, useEffect, useMemo, useState } from "react";

import {
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

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

const DOGFOOD_SESSION_OPTIONS = ["session-21", "session-22", "session-23"];

export function RecapGraphModule({ context }: RecapGraphModuleProps) {
  const defaultSessionId = `session-${context.ingestSession}`;
  const sessionOptions = useMemo(() => {
    const options = new Set(DOGFOOD_SESSION_OPTIONS);
    options.add(defaultSessionId);
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [defaultSessionId]);

  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<RecapMode>("union-supergraph");
  const [unionPayload, setUnionPayload] = useState<UnionSupergraphProjectionResponse | null>(null);
  const [legacyPayload, setLegacyPayload] = useState<RecapGraphPresentationResponse | null>(null);
  const [runs, setRuns] = useState<GraphPreviewRunSummary[]>([]);
  const [selectedRunDir, setSelectedRunDir] = useState("");
  const [pinnedNodeId, setPinnedNodeId] = useState<string | null>(null);
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState(defaultSessionId);

  const loadUnionProjection = useCallback(async (sessionId = selectedSessionId) => {
    setStatus("loading");
    setError(null);
    try {
      const projection = await getUnionSupergraphProjection(sessionId);
      setUnionPayload(projection);
      setMode("union-supergraph");
      setStatus("ready");
    } catch (loadError) {
      setUnionPayload(null);
      setError(loadError instanceof Error ? loadError.message : "Failed to load union supergraph projection");
      setStatus("error");
    }
  }, [selectedSessionId]);

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
        const preferred = records.find((record) => record.session_id === defaultSessionId);
        setSelectedSessionId(preferred?.session_id ?? defaultSessionId);
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
          {error ?? "Union supergraph projection unavailable."}
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
