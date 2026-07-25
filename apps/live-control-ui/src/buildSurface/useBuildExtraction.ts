import { useCallback, useEffect, useRef, useState } from "react";

import {
  getExtractionRunStatus,
  getWorkspaceDocumentSnapshot,
  launchExtractionRun,
} from "../api/liveApi";
import type {
  ExtractionRunLaunchResponse,
  ExtractionRunRecord,
  ExtractionRunStatusResponse,
  GraphReviewHandoffPayload,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../api/types";
import { readWorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";

const RUN_STORAGE_PREFIX = "dmb.buildExtractionRun.";

/** Bounded BLD-08 worldbuilding profile (Build product default). */
export const BUILD_WORLDBUILDING_PROFILE_ID = "worldbuilding_shepherds_flock_v0";
export const BUILD_WORLDBUILDING_PROFILE_VERSION = "0.1";

function runIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("extractionRunId");
  return value?.trim() || null;
}

function documentIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("documentId");
  return value?.trim() || null;
}

/** Mutate URL only while the selected document still owns the page. */
function setRunIdInLocationForDocument(documentId: string, runId: string): void {
  if (documentIdFromLocation() !== documentId) return;
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

function diagnosticRun(runId: string, sourceArtifactId = ""): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: runId,
    source_artifact_id: sourceArtifactId,
    source_domain: "worldbuilding",
    status: "failed",
  };
}

export type ExactRunIdentityValidation =
  | { ok: true; handoff: GraphReviewHandoffPayload }
  | { ok: false; reason: string };

function singleQueryValue(params: URLSearchParams, key: string): string | null {
  const values = params.getAll(key);
  if (values.length !== 1) return null;
  const value = values[0]?.trim() ?? "";
  return value || null;
}

/** Require handoff.href query identities to equal the handoff payload fields. */
export function validateHandoffHref(handoff: GraphReviewHandoffPayload): ExactRunIdentityValidation {
  if (!handoff.href?.trim()) {
    return { ok: false, reason: "Handoff href is missing." };
  }
  if (/\blatest\b/i.test(handoff.href)) {
    return { ok: false, reason: "Handoff href substitutes latest." };
  }
  let url: URL;
  try {
    url = new URL(handoff.href, "https://dmb.invalid");
  } catch {
    return { ok: false, reason: "Handoff href is malformed." };
  }
  const params = url.searchParams;
  const extractionRunId = singleQueryValue(params, "extractionRunId");
  const sourceArtifactId = singleQueryValue(params, "sourceArtifactId");
  const documentId = singleQueryValue(params, "documentId");
  const revision = singleQueryValue(params, "revision");
  if (
    extractionRunId !== handoff.extraction_run_id
    || sourceArtifactId !== handoff.source_artifact_id
    || documentId !== handoff.document_id
    || revision !== String(handoff.document_revision)
  ) {
    return {
      ok: false,
      reason: "Handoff href query identities do not match the handoff payload fields.",
    };
  }
  return { ok: true, handoff };
}

/** Shared identity matrix for launch and status envelopes. */
export function validateExactRunIdentity(args: {
  selectedDocumentId: string;
  requestedRunId: string;
  response: Pick<
    ExtractionRunStatusResponse,
    | "run"
    | "source_artifact_id"
    | "document_id"
    | "document_revision"
    | "source_content_sha256"
    | "graph_review_handoff"
  >;
  /** When set (launch path), response must equal the snapshot submitted with the request. */
  expectedDocumentRevision?: number;
  expectedContentSha256?: string;
}): ExactRunIdentityValidation {
  const {
    selectedDocumentId,
    requestedRunId,
    response,
    expectedDocumentRevision,
    expectedContentSha256,
  } = args;
  const handoff = response.graph_review_handoff;
  if (!handoff) {
    return { ok: false, reason: "Exact-run response is missing graph_review_handoff." };
  }
  if (response.run.run_id !== requestedRunId) {
    return { ok: false, reason: "Response run ID does not match the requested exact run." };
  }
  if (response.run.source_artifact_id !== response.source_artifact_id) {
    return { ok: false, reason: "Run source artifact does not match response source artifact." };
  }
  if (response.source_artifact_id !== handoff.source_artifact_id) {
    return { ok: false, reason: "Handoff source artifact does not match response source artifact." };
  }
  if (handoff.extraction_run_id !== response.run.run_id) {
    return { ok: false, reason: "Handoff run ID does not match response run." };
  }
  if (response.document_id !== selectedDocumentId || handoff.document_id !== selectedDocumentId) {
    return {
      ok: false,
      reason: "Exact run belongs to a different workspace document than the selected Build source.",
    };
  }
  if (handoff.document_revision !== response.document_revision) {
    return { ok: false, reason: "Handoff revision does not match server-resolved source revision." };
  }
  if (!response.source_content_sha256?.trim()) {
    return { ok: false, reason: "Exact-run response is missing source_content_sha256." };
  }
  if (
    expectedDocumentRevision !== undefined
    && response.document_revision !== expectedDocumentRevision
  ) {
    return {
      ok: false,
      reason: "Launch response revision does not match the requested snapshot revision.",
    };
  }
  if (
    expectedContentSha256 !== undefined
    && response.source_content_sha256 !== expectedContentSha256
  ) {
    return {
      ok: false,
      reason: "Launch response digest does not match the requested snapshot digest.",
    };
  }
  return validateHandoffHref(handoff);
}

export interface UseBuildExtractionArgs {
  documentId: string;
}

export interface BuildExtractionState {
  document: WorkspaceDocumentRecord | null;
  snapshot: WorkspaceDocumentSnapshot | null;
  run: ExtractionRunRecord | null;
  handoff: GraphReviewHandoffPayload | null;
  statusLabel: string;
  error: string | null;
  launching: boolean;
  canLaunch: boolean;
  canRefresh: boolean;
  canOpenGraphReview: boolean;
  refresh: () => Promise<void>;
  launch: () => Promise<void>;
}

function admitLaunchFromLocalAndSnapshot(args: {
  documentId: string;
  snapshot: WorkspaceDocumentSnapshot;
}): { ok: true } | { ok: false; reason: string } {
  const local = readWorkspaceDocumentLocalState(window.localStorage, args.documentId);
  if (!local) {
    return { ok: false, reason: "Open and save this Build source before extraction." };
  }
  if (local.document_id !== args.documentId || local.surface !== "build") {
    return { ok: false, reason: "Local draft does not belong to this Build document." };
  }
  if (local.dirty) {
    return { ok: false, reason: "Save and commit local changes before extraction." };
  }
  if (args.snapshot.record.content_status !== "committed") {
    return { ok: false, reason: "Source must be committed before extraction." };
  }
  if (local.base_revision !== args.snapshot.loaded_revision) {
    return {
      ok: false,
      reason: `Local base revision ${local.base_revision} does not match snapshot revision ${args.snapshot.loaded_revision}.`,
    };
  }
  if (local.base_content_sha256 !== args.snapshot.content_sha256) {
    return {
      ok: false,
      reason: "Local base content hash does not match the authoritative snapshot digest.",
    };
  }
  return { ok: true };
}

export function useBuildExtraction(args: UseBuildExtractionArgs): BuildExtractionState {
  const { documentId } = args;
  const [document, setDocument] = useState<WorkspaceDocumentRecord | null>(null);
  const [snapshot, setSnapshot] = useState<WorkspaceDocumentSnapshot | null>(null);
  const [run, setRun] = useState<ExtractionRunRecord | null>(null);
  const [handoff, setHandoff] = useState<GraphReviewHandoffPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);
  const [localCleanMatch, setLocalCleanMatch] = useState(false);

  // Separate generations so Refresh cannot cancel an in-flight Extract adoption.
  const launchGenerationRef = useRef(0);
  const refreshGenerationRef = useRef(0);
  // Synchronous mirror of launching so refresh can no-op before any await.
  const launchingRef = useRef(false);

  const clearAdoptedState = useCallback(() => {
    setDocument(null);
    setSnapshot(null);
    setRun(null);
    setHandoff(null);
    setError(null);
    launchingRef.current = false;
    setLaunching(false);
    setLocalCleanMatch(false);
  }, []);

  const refresh = useCallback(async () => {
    // Refresh must not supersede an active launch generation or clear a pending
    // Extract before its exact run ID is known.
    if (launchingRef.current) return;

    const generation = ++refreshGenerationRef.current;
    const selectedDocumentId = documentId;
    setError(null);
    setHandoff(null);

    if (!selectedDocumentId) {
      clearAdoptedState();
      return;
    }

    const exactRunId = runIdFromLocation() ?? readStoredRunId(selectedDocumentId);

    try {
      const nextSnapshot = await getWorkspaceDocumentSnapshot(selectedDocumentId);
      if (generation !== refreshGenerationRef.current) return;
      if (launchingRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId) return;

      setSnapshot(nextSnapshot);
      setDocument(nextSnapshot.record);
      const admission = admitLaunchFromLocalAndSnapshot({
        documentId: selectedDocumentId,
        snapshot: nextSnapshot,
      });
      setLocalCleanMatch(admission.ok);

      if (!exactRunId) {
        setRun(null);
        setHandoff(null);
        return;
      }

      const status: ExtractionRunStatusResponse = await getExtractionRunStatus(exactRunId);
      if (generation !== refreshGenerationRef.current) return;
      if (launchingRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId) return;

      const validation = validateExactRunIdentity({
        selectedDocumentId,
        requestedRunId: exactRunId,
        response: status,
      });
      setRun(status.run);
      if (!validation.ok) {
        setHandoff(null);
        setError(validation.reason);
        return;
      }
      writeStoredRunId(selectedDocumentId, status.run.run_id);
      setHandoff(validation.handoff);
      setError(null);
    } catch (loadError) {
      if (generation !== refreshGenerationRef.current) return;
      if (launchingRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId) return;
      setHandoff(null);
      setError(loadError instanceof Error ? loadError.message : "Failed to load extraction state");
      setRun((current) => {
        if (current) return current;
        return exactRunId ? diagnosticRun(exactRunId) : null;
      });
    }
  }, [clearAdoptedState, documentId]);

  useEffect(() => {
    // Invalidate any in-flight refresh/launch belonging to a prior selection.
    launchGenerationRef.current += 1;
    refreshGenerationRef.current += 1;
    clearAdoptedState();
    void refresh();
    return () => {
      launchGenerationRef.current += 1;
      refreshGenerationRef.current += 1;
      launchingRef.current = false;
    };
    // refresh is recreated when documentId changes; keying the effect on documentId is enough.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  const launch = useCallback(async () => {
    const selectedDocumentId = documentId;
    // Reject synchronous re-entry before React re-renders the disabled button.
    if (launchingRef.current) return;

    // Invalidate every pre-existing refresh before the first await so a stale
    // refresh cannot adopt R1 after this launch adopts R2.
    refreshGenerationRef.current += 1;
    const generation = ++launchGenerationRef.current;
    launchingRef.current = true;
    setLaunching(true);
    setError(null);
    setHandoff(null);

    try {
      const nextSnapshot = await getWorkspaceDocumentSnapshot(selectedDocumentId);
      if (generation !== launchGenerationRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId) return;

      setSnapshot(nextSnapshot);
      setDocument(nextSnapshot.record);
      const admission = admitLaunchFromLocalAndSnapshot({
        documentId: selectedDocumentId,
        snapshot: nextSnapshot,
      });
      setLocalCleanMatch(admission.ok);
      if (!admission.ok) {
        setError(admission.reason);
        return;
      }

      const response: ExtractionRunLaunchResponse = await launchExtractionRun({
        document_id: selectedDocumentId,
        expected_revision: nextSnapshot.loaded_revision,
        expected_content_sha256: nextSnapshot.content_sha256,
        profile_id: BUILD_WORLDBUILDING_PROFILE_ID,
        profile_version: BUILD_WORLDBUILDING_PROFILE_VERSION,
      });
      if (generation !== launchGenerationRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId) return;

      const validation = validateExactRunIdentity({
        selectedDocumentId,
        requestedRunId: response.run.run_id,
        response,
        expectedDocumentRevision: nextSnapshot.loaded_revision,
        expectedContentSha256: nextSnapshot.content_sha256,
      });
      if (!validation.ok) {
        setRun(response.run);
        setHandoff(null);
        setError(validation.reason);
        return;
      }

      setRun(response.run);
      setHandoff(validation.handoff);
      setRunIdInLocationForDocument(selectedDocumentId, response.run.run_id);
      writeStoredRunId(selectedDocumentId, response.run.run_id);
      if (response.failure_kind) {
        setError(response.diagnostics.join("; ") || `Extraction ${response.failure_kind}`);
      }
    } catch (launchError) {
      if (generation !== launchGenerationRef.current) return;
      if (documentIdFromLocation() !== selectedDocumentId) return;
      setHandoff(null);
      setError(launchError instanceof Error ? launchError.message : "Extraction launch failed");
    } finally {
      if (generation === launchGenerationRef.current) {
        launchingRef.current = false;
        setLaunching(false);
      }
    }
  }, [documentId]);

  const canLaunch = Boolean(
    snapshot
    && snapshot.record.content_status === "committed"
    && localCleanMatch
    && !launching,
  );
  const canRefresh = !launching;
  const canOpenGraphReview = Boolean(
    !launching
    && run
    && handoff
    && run.status === "reviewable",
  );

  let statusLabel = "No extraction run";
  if (launching) statusLabel = "Launching extraction…";
  else if (run && !handoff && error) statusLabel = `Run ${run.run_id} · identity unresolved`;
  else if (run) statusLabel = `Run ${run.run_id} · ${run.status}`;
  else if (!localCleanMatch) statusLabel = "Commit a clean matching source to enable extraction";
  else if (document?.content_status !== "committed") statusLabel = "Commit source to enable extraction";

  return {
    document,
    snapshot,
    run,
    handoff,
    statusLabel,
    error,
    launching,
    canLaunch,
    canRefresh,
    canOpenGraphReview,
    refresh,
    launch,
  };
}
