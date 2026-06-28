import { useCallback, useEffect, useState } from "react";

import { getGraphPreviewLatest, getGraphPreviewRuns } from "../../api/liveApi";
import type { GraphPreviewSurfaceResponse, GraphPreviewRunSummary } from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { GraphIngestProjectionPanel } from "./GraphIngestProjectionPanel";
import { GraphPreviewProjection } from "./GraphPreviewProjection";

type LoadStatus = "loading" | "ready" | "error";

interface GraphPreviewModuleProps {
  context: PlanContextDescriptor;
}

export function GraphPreviewModule({ context }: GraphPreviewModuleProps) {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<GraphPreviewSurfaceResponse | null>(null);
  const [runs, setRuns] = useState<GraphPreviewRunSummary[]>([]);
  const [selectedRunDir, setSelectedRunDir] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  const loadRun = useCallback(async (runDir?: string) => {
    setStatus("loading");
    setError(null);
    try {
      const [runList, surface] = await Promise.all([
        getGraphPreviewRuns(),
        getGraphPreviewLatest(runDir),
      ]);
      setRuns(runList.runs);
      setPayload(surface);
      setSelectedRunDir(surface.run_dir);
      setSelectedCandidateId((current) => {
        if (current && surface.candidates.some((row) => row.object_id === current)) {
          return current;
        }
        return surface.candidates[0]?.object_id ?? null;
      });
      setStatus("ready");
    } catch (loadError) {
      setStatus("error");
      setError(loadError instanceof Error ? loadError.message : "Failed to load graph preview");
    }
  }, []);

  useEffect(() => {
    void loadRun();
  }, [loadRun, context.campaignId, context.ingestSession]);

  if (status === "loading") {
    return <p className="plan-projection-empty">Loading graph preview…</p>;
  }

  if (status === "error" || !payload) {
    return (
      <div className="graph-preview-root">
        <p className="graph-preview-error" role="alert">{error ?? "Graph preview unavailable."}</p>
        <button type="button" onClick={() => loadRun(selectedRunDir || undefined)}>Retry</button>
      </div>
    );
  }

  return (
    <div className="graph-preview-root">
      <GraphIngestProjectionPanel context={context} />
      <GraphPreviewProjection
        payload={payload}
        runs={runs}
        selectedRunDir={selectedRunDir}
        onSelectRun={(runDir) => {
          setSelectedRunDir(runDir);
          void loadRun(runDir);
        }}
        selectedCandidateId={selectedCandidateId}
        onSelectCandidate={setSelectedCandidateId}
      />
    </div>
  );
}
