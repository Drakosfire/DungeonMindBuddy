import { useCallback, useEffect, useState } from "react";

import { getGraphPreviewRuns, getRecapGraphPresentation } from "../../api/liveApi";
import type { GraphPreviewRunSummary, RecapGraphPresentationResponse } from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { RecapGraphProjection } from "./RecapGraphProjection";

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

  const loadRun = useCallback(async (runDir?: string) => {
    setStatus("loading");
    setError(null);
    try {
      const [runList, recap] = await Promise.all([
        getGraphPreviewRuns(),
        getRecapGraphPresentation(runDir),
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
  }, []);

  useEffect(() => {
    void loadRun();
  }, [loadRun, context.campaignId, context.ingestSession]);

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
