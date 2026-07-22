import { useCallback, useEffect, useState } from "react";

import {
  getExtractionRun,
  getWorkspaceDocument,
  launchExtractionRun,
} from "../api/liveApi";
import type {
  ExtractionRunLaunchResponse,
  ExtractionRunRecord,
  GraphReviewHandoffPayload,
  WorkspaceDocumentRecord,
} from "../api/types";

const RUN_STORAGE_PREFIX = "dmb.buildExtractionRun.";

function documentIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("documentId");
  return value?.trim() || null;
}

function runIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("extractionRunId");
  return value?.trim() || null;
}

function setRunIdInLocation(runId: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("extractionRunId", runId);
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
}

function readStoredRunId(documentId: string): string | null {
  try {
    return window.localStorage.getItem(`${RUN_STORAGE_PREFIX}${documentId}`);
  } catch {
    return null;
  }
}

function writeStoredRunId(documentId: string, runId: string): void {
  try {
    window.localStorage.setItem(`${RUN_STORAGE_PREFIX}${documentId}`, runId);
  } catch {
    // ignore quota
  }
}

export interface BuildExtractionState {
  document: WorkspaceDocumentRecord | null;
  run: ExtractionRunRecord | null;
  handoff: GraphReviewHandoffPayload | null;
  statusLabel: string;
  error: string | null;
  launching: boolean;
  canLaunch: boolean;
  canOpenGraphReview: boolean;
  refresh: () => Promise<void>;
  launch: () => Promise<void>;
}

export function useBuildExtraction(): BuildExtractionState {
  const [document, setDocument] = useState<WorkspaceDocumentRecord | null>(null);
  const [run, setRun] = useState<ExtractionRunRecord | null>(null);
  const [handoff, setHandoff] = useState<GraphReviewHandoffPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  const refresh = useCallback(async () => {
    setError(null);
    const documentId = documentIdFromLocation();
    if (!documentId) {
      setDocument(null);
      setRun(null);
      setHandoff(null);
      return;
    }
    try {
      const record = await getWorkspaceDocument(documentId);
      setDocument(record);
      const exactRunId = runIdFromLocation() ?? readStoredRunId(documentId);
      if (!exactRunId) {
        setRun(null);
        setHandoff(null);
        return;
      }
      const exactRun = await getExtractionRun(exactRunId);
      setRun(exactRun);
      writeStoredRunId(documentId, exactRun.run_id);
      setHandoff({
        href: `/ingest?extractionRunId=${exactRun.run_id}&sourceArtifactId=${encodeURIComponent(exactRun.source_artifact_id)}&documentId=${documentId}&revision=${record.revision}`,
        extraction_run_id: exactRun.run_id,
        source_artifact_id: exactRun.source_artifact_id,
        document_id: documentId,
        document_revision: record.revision,
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load extraction state");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const launch = useCallback(async () => {
    const documentId = documentIdFromLocation();
    if (!documentId || !document) {
      setError("Save and commit a source before extraction.");
      return;
    }
    if (document.content_status !== "committed") {
      setError("Source must be committed before extraction.");
      return;
    }
    setLaunching(true);
    setError(null);
    try {
      const response: ExtractionRunLaunchResponse = await launchExtractionRun({
        document_id: documentId,
        expected_revision: document.revision,
      });
      setRun(response.run);
      setHandoff(response.graph_review_handoff);
      setRunIdInLocation(response.run.run_id);
      writeStoredRunId(documentId, response.run.run_id);
      if (response.failure_kind) {
        setError(response.diagnostics.join("; ") || `Extraction ${response.failure_kind}`);
      }
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : "Extraction launch failed");
    } finally {
      setLaunching(false);
    }
  }, [document]);

  const canLaunch = Boolean(
    document
    && document.content_status === "committed"
    && !launching,
  );
  const canOpenGraphReview = Boolean(run && handoff && run.status === "reviewable");

  let statusLabel = "No extraction run";
  if (launching) statusLabel = "Launching extraction…";
  else if (run) statusLabel = `Run ${run.run_id} · ${run.status}`;
  else if (document?.content_status !== "committed") statusLabel = "Commit source to enable extraction";

  return {
    document,
    run,
    handoff,
    statusLabel,
    error,
    launching,
    canLaunch,
    canOpenGraphReview,
    refresh,
    launch,
  };
}
