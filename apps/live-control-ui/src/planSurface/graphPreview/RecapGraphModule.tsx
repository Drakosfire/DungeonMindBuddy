import { useCallback, useEffect, useState } from "react";

import { getGraphPreviewRuns, getRecapArtifacts, getRecapGraphPresentation } from "../../api/liveApi";
import type {
  GraphPreviewRunSummary,
  RecapArtifactRecord,
  RecapGraphPresentationResponse,
} from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { RecapGraphProjection } from "./RecapGraphProjection";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";

type LoadStatus = "loading" | "ready" | "error";

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

export function RecapGraphModule({ context }: RecapGraphModuleProps) {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<RecapGraphPresentationResponse | null>(null);
  const [runs, setRuns] = useState<GraphPreviewRunSummary[]>([]);
  const [selectedRunDir, setSelectedRunDir] = useState("");
  const [pinnedNodeId, setPinnedNodeId] = useState<string | null>(null);
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState(`session-${context.ingestSession}`);
  const [artifactsReady, setArtifactsReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setArtifactsReady(false);

    void getRecapArtifacts(context.campaignId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
        setSessionRecords(records);
        const preferredSessionId = `session-${context.ingestSession}`;
        const preferred = records.find((record) => record.session_id === preferredSessionId);
        setSelectedSessionId(preferred?.session_id ?? records.at(-1)?.session_id ?? preferredSessionId);
        setArtifactsReady(true);
      })
      .catch((loadError) => {
        if (cancelled) {
          return;
        }
        setSessionRecords([]);
        setSelectedSessionId(`session-${context.ingestSession}`);
        setError(loadError instanceof Error ? loadError.message : "Failed to load recap sessions");
        setStatus("error");
        setArtifactsReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, [context.campaignId, context.ingestSession]);

  const loadRun = useCallback(async (runDir?: string, sessionId = selectedSessionId) => {
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
      setPayload(recap);
      setSelectedRunDir(recap.run_dir);
      setPinnedNodeId((current) => {
        if (current && recap.nodes[current]) {
          return current;
        }
        return Object.keys(recap.nodes)[0] ?? null;
      });
      setStatus("ready");
    } catch (loadError) {
      setStatus("error");
      setError(loadError instanceof Error ? loadError.message : "Failed to load recap graph");
    }
  }, [context.campaignId, selectedSessionId]);

  useEffect(() => {
    if (!artifactsReady) {
      return;
    }
    void loadRun();
  }, [loadRun, artifactsReady]);

  if (status === "loading") {
    return <p className="plan-projection-empty">Loading recap graph…</p>;
  }

  if (status === "error" || !payload) {
    return (
      <div className="recap-reader-root">
        <p className="graph-preview-error" role="alert">{error ?? "Recap graph unavailable."}</p>
        <button type="button" onClick={() => loadRun(selectedRunDir || undefined)}>Retry</button>
      </div>
    );
  }

  return (
    <RecapGraphProjection
      payload={payload}
      runs={runs}
      sessionRecords={sessionRecords}
      selectedSessionId={selectedSessionId}
      onSelectSession={(sessionId) => {
        setSelectedSessionId(sessionId);
        setSelectedRunDir("");
        void loadRun(undefined, sessionId);
      }}
      selectedRunDir={selectedRunDir}
      onSelectRun={(runDir) => {
        setSelectedRunDir(runDir);
        void loadRun(runDir);
      }}
      pinnedNodeId={pinnedNodeId}
      onPinNode={setPinnedNodeId}
    />
  );
}
