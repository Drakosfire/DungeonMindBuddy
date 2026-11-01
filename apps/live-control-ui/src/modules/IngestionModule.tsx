import {SessionEvidencePicker} from "../playSurface/review/SessionEvidencePicker";
import type {SessionEvidenceRef} from "../playSurface/review/sessionEvidenceApi";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { getHistoricalRecapWorldProjection } from "../api/liveApi";
import { getSavedRecapRuns, getSavedRecapSource, type SavedRecapRun, type SavedRecapRuns, type SavedRecapSource } from "../api/savedRecapRunsApi";
import { WorldPlanAgentAnswer } from "../planSurface/components/WorldPlanAgentAnswer";
import { postRecapIngest } from "../api/recapIngestApi";
import type {
  RecapGraphPreviewReport,
  RecapIngestStatus,
  HistoricalRecapWorldProjectionResponse,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../api/types";
import {
  recapSessionNumber,
} from "../planSurface/graphPreview/recapSessionLabels";
import { useOptionalProjection } from "../planSurface/projection/projectionContext";
import { ReviewCampaignPicker } from "../planSurface/ReviewCampaignPicker";
import {
  resolveInitialReviewCampaignId,
  syncReviewCampaignUrl,
} from "../graphLens/sessionCampaignContext";
import { GraphReviewHistoricalRecapProjection } from "../planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection";
import { GraphReviewCandidateRecapProjection } from "../planSurface/graphReviewWorkbench/GraphReviewCandidateRecapProjection";
import { getExactRunCandidateProjection, type ExactRunCandidateProjection } from "../api/exactRunCandidateProjectionApi";

import { verifyWorldGraphProjectionResponse } from "../worldGraph/verifyWorldGraphProjectionResponse";

import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";

import { NativeGraphAccessControl } from "../chrome/NativeGraphAccessControl";

interface IngestionModuleProps {
  campaignId: string;
  session: number;
  managedWorldId?: string;
  initialSourceSession?: number;
}

const INGESTION_DRAFT_STORAGE_VERSION = 3;
const INGESTION_GRAPH_MODEL_ID = "deepseek/deepseek-v4.1-flash-1017";

type IngestionSourceMode = "raw" | "saved";

function isIngestSurfacePath(): boolean {
  if (typeof window === "undefined") return false;
  return window.location.pathname.replace(/\/+$/, "") === "/ingest";
}

function ingestRoutePath(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/ingest";
}

function isFreshRecapEntryRoute(): boolean {
  if (!isIngestSurfacePath()) return false;
  const params = new URLSearchParams(window.location.search);
  return params.has("world") && params.get("view") !== "recap" && !params.has("campaign") && !params.has("session");
}


interface IngestionModuleDraft {
  version: number;
  rawText: string;
  recapSession: number;
  slug: string;
  title: string;
}

interface ReturnableIngestionDraft {
  storageKey: string;
  campaignId: string;
  draft: IngestionModuleDraft;
}

type IngestionToastTone = "info" | "warning" | "error" | "success";

interface IngestionToast {
  tone: IngestionToastTone;
  title: string;
  detail: string;
  nextSteps: string[];
  sticky?: boolean;
}

function defaultRecapSession(liveSession: number): number {
  return Math.max(1, liveSession - 1);
}

function requestedRecapSessionFromLocation(): number | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("session")?.trim();
  const match = raw?.match(/^session-(\d+)$/i);
  if (!match) return null;
  const session = Number.parseInt(match[1], 10);
  return Number.isFinite(session) && session > 0 ? session : null;
}

type IngestionPaneState =
  | { status: "idle" }
  | { status: "running_full_ingest" }
  | { status: "error"; result?: RecapIngestStatus; message?: string };

function draftStorageKey(campaignId: string, session: number): string {
  return `dmb.ingestion.${campaignId}.session.${session}`;
}

function derivePaneStateFromResult(result: RecapIngestStatus): IngestionPaneState {
  if (result.status === "error") {
    return {
      status: "error",
      result,
      message: result.errors.length > 0 ? result.errors.join("; ") : "Ingestion error",
    };
  }
  return { status: "idle" };
}

function graphPreviewIsBlocked(graphPreview?: RecapGraphPreviewReport): boolean {
  if (!graphPreview) return false;
  if (graphPreview.extraction_mode === "llm_blocked") return true;
  if (graphPreview.status === "missing" || graphPreview.status === "source_unverified") return false;
  const reason = graphPreview.blocked_reason?.trim();
  return Boolean(
    reason &&
      !(graphPreview.status === "source_span_bundle_ready" &&
        reason === "Graph source bundle ready. Candidate graph extraction has not run yet."),
  );
}

function graphPreviewIsReviewable(graphPreview?: RecapGraphPreviewReport): boolean {
  return Boolean(
    graphPreview?.status === "candidate_validation_ready" &&
    !graphPreviewIsBlocked(graphPreview),
  );
}

function readDraft(storageKey: string): IngestionModuleDraft | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<IngestionModuleDraft>;
    if (parsed.version !== INGESTION_DRAFT_STORAGE_VERSION) {
      return null;
    }
    if (
      typeof parsed.rawText !== "string" ||
      typeof parsed.recapSession !== "number" ||
      typeof parsed.slug !== "string" ||
      typeof parsed.title !== "string"
    ) {
      return null;
    }
    return {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      rawText: parsed.rawText,
      recapSession: parsed.recapSession,
      slug: parsed.slug,
      title: parsed.title,
    };
  } catch {
    return null;
  }
}

function writeDraft(storageKey: string, draft: IngestionModuleDraft): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(draft));
  } catch {
    // Best effort persistence only.
  }
}

function evidenceRows(values: string[]): ReactNode {
  if (values.length === 0) {
    return <li className="module-muted">None</li>;
  }
  return values.map((value) => <li key={value}>{value}</li>);
}

function RequiredBadge({ satisfied }: { satisfied: boolean }): ReactNode {
  if (satisfied) {
    return null;
  }
  return (
    <span className="field-required" aria-hidden="true">
      Required
    </span>
  );
}

function buildToastForResult(
  result: RecapIngestStatus | null,
  {
    fallbackErrorMessage,
  }: {
    fallbackErrorMessage?: string;
  },
): IngestionToast | null {
  if (!result) {
    if (!fallbackErrorMessage) {
      return null;
    }
    return {
      tone: "error",
      title: "Processing failed",
      detail: fallbackErrorMessage,
      nextSteps: ["Try Process again."],
      sticky: true,
    };
  }

  const graphPreview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const graphReady = graphPreviewIsReviewable(graphPreview);
  const graphBlocked = graphPreviewIsBlocked(graphPreview);
  if (result.status === "error" || result.errors.length > 0) {
    return {
      tone: "error",
      title: "Processing failed",
      detail: result.errors.join("; ") || result.warnings.join("; ") || `The server returned ${result.status}.`,
      nextSteps: ["Inspect the exact saved attempt."],
      sticky: true,
    };
  }
  if (graphBlocked) {
    return {
      tone: "warning",
      title: "Graph enrichment needs attention",
      detail: graphPreview?.blocked_reason || "The recap was saved, but graph extraction did not complete.",
      nextSteps: [],
      sticky: true,
    };
  }
  if (graphReady) {
    return {
      tone: "success",
      title: "Recap processed",
      detail: "The enriched recap is ready. Extracted facts still need Graph Review before admission.",
      nextSteps: [],
    };
  }
  return null;
}

export function IngestionModule({ campaignId: planCampaignId, session, managedWorldId: providedWorldId, initialSourceSession }: IngestionModuleProps) {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed"
    ? (!providedWorldId || providedWorldId === selectedWorld.worldId ? selectedWorld.worldId : undefined)
    : selectedWorld.kind === "legacy" ? providedWorldId : undefined;
  const projection = useOptionalProjection();
  const freshRecapEntry = isFreshRecapEntryRoute();
  const requestedRecapSession = requestedRecapSessionFromLocation();
  const routeCampaignId = resolveInitialReviewCampaignId(planCampaignId);
  const routeTargetSession = requestedRecapSession ?? (freshRecapEntry ? 0 : initialSourceSession ?? defaultRecapSession(session));
  const routeParams = new URLSearchParams(typeof window === "undefined" ? "" : window.location.search);
  const routeView = routeParams.get("view");
  const routeCampaign = routeParams.get("campaign");
  const routeSession = routeParams.get("session");
  const routeRunId = routeParams.get("recapReviewRunId");
  const routeTargetIdentity = JSON.stringify([
    managedWorldId ?? null,
    routeCampaignId,
    routeTargetSession,
    freshRecapEntry,
  ]);
  const routeStateIdentity = JSON.stringify([
    routeTargetIdentity,
    routeView,
    routeCampaign,
    routeSession,
    routeRunId,
  ]);
  const [ingestCampaignId, setIngestCampaignId] = useState(() =>
    routeCampaignId,
  );
  const routeTargetGenerationRef = useRef(0);
  function getIngestTargetIdentity(campaignId: string, sessionNumber: number): string {
    return JSON.stringify([managedWorldId ?? null, routeTargetGenerationRef.current, campaignId, sessionNumber]);
  }
  const storageKey = useMemo(
    () => draftStorageKey(ingestCampaignId, session),
    [ingestCampaignId, session],
  );
  const initialRecapSession = requestedRecapSession ?? (freshRecapEntry ? 0 : initialSourceSession ?? defaultRecapSession(session));
  const [rawText, setRawText] = useState("");
  const rawRecapTextAreaRef = useRef<HTMLTextAreaElement | null>(null);
  const [recapSession, setRecapSession] = useState<number>(() => initialRecapSession);
  const selectedIngestTarget = getIngestTargetIdentity(ingestCampaignId, recapSession);
  const [sessionSupplements,setSessionSupplements]=useState<{identity:string;refs:SessionEvidenceRef[]}>({identity:"",refs:[]});
  const evidenceTargetKey=JSON.stringify([managedWorldId??null,ingestCampaignId,recapSession]);
  const selectedIngestTargetRef = useRef(selectedIngestTarget);
  selectedIngestTargetRef.current = selectedIngestTarget;
  const previousRouteTargetIdentityRef = useRef(routeTargetIdentity);
  const previousManagedWorldIdRef = useRef(managedWorldId ?? null);
  const previousRouteStateIdentityRef = useRef(routeStateIdentity);
  const targetSelectionTransitionRef = useRef<{
    identity: string;
    campaignId: string;
    session: number;
  } | null>(null);
  const [hydratedIngestTargetIdentity, setHydratedIngestTargetIdentity] = useState<string | null>(null);
  const ingestCampaignIdRef = useRef(ingestCampaignId);
  ingestCampaignIdRef.current = ingestCampaignId;
  const recapSessionRef = useRef(recapSession);
  recapSessionRef.current = recapSession;
  const recapDraftEpochRef = useRef(0);
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [reviewSource, setReviewSource] = useState<{ identity: string; session: number; nodes: number; edges: number; projection: HistoricalRecapWorldProjectionResponse | ExactRunCandidateProjection | null; runId?: string } | null>(null);
  const [readerMode, setReaderMode] = useState(() => new URLSearchParams(window.location.search).get("view") === "recap");
  const readerAttempt = useRef<string | null>(null);
  const restoreReaderRoute = useRef(true);
  const evidenceDetailsRef = useRef<HTMLDetailsElement>(null);
  const [readerRun, setReaderRun] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("view") === "recap" && params.get("recapReviewRunId")
      ? { campaign: params.get("campaign"), session: params.get("session"), runId: params.get("recapReviewRunId")! } : null;
  });
  const reviewEpoch = useRef(0);
  const currentReviewIdentity = useRef("");
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [forceGraphRun, setForceGraphRun] = useState(false);
  /** Which primary action is in flight — drives spinner / status copy. */
  const [primaryOp, setPrimaryOp] = useState<"process" | null>(null);
  const [state, setState] = useState<IngestionPaneState>({ status: "idle" });
  const [latestResult, setLatestResult] = useState<RecapIngestStatus | null>(null);
  // Retain the operation result separately from the selected saved reader.
  const [latestOperationResult, setLatestOperationResult] = useState<{
    targetIdentity: string;
    draftEpoch: number;
    result: RecapIngestStatus;
  } | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [toast, setToast] = useState<IngestionToast | null>(null);
  const [sourceMode, setSourceMode] = useState<IngestionSourceMode>("raw");
  const [loadedRun, setLoadedRun] = useState<SavedRecapRun | null>(null);
  const [returnableDraft, setReturnableDraft] = useState<ReturnableIngestionDraft | null>(null);
  const preservedRouteDraftRef = useRef<ReturnableIngestionDraft | null>(null);
  const [savedRuns, setSavedRuns] = useState<SavedRecapRun[]>([]);
  const [savedRunScope, setSavedRunScope] = useState<SavedRecapRuns | null>(null);
  const [savedSource, setSavedSource] = useState<{identity: string; source: SavedRecapSource} | null>(null);
  const [savedRunRefresh, setSavedRunRefresh] = useState(0);
  const savedCatalogEpoch = useRef(0);
  const savedRunKey = JSON.stringify([managedWorldId ?? "", ingestCampaignId, savedRunRefresh]);
  const [savedRunLookup, setSavedRunLookup] = useState<{
    key: string;
    status: "loading" | "loaded" | "failed";
  } | null>(null);
  const [selectedSavedRunId, setSelectedSavedRunId] = useState("");
  const lastToastKeyRef = useRef<string | null>(null);
  /** When set, the result→toast effect leaves the Process result's message in charge. */
  const suppressResultToastRef = useRef(false);
  const draftHydrationEpochRef = useRef(0);
  const initialHydrationRef = useRef(true);
  const validRecapSession = Number.isInteger(recapSession) && recapSession > 0;
  const selectionHydrated = hydrated && hydratedIngestTargetIdentity === selectedIngestTarget;

  function advanceIngestTarget(campaignId: string, sessionNumber: number): string {
    routeTargetGenerationRef.current += 1;
    const identity = getIngestTargetIdentity(campaignId, sessionNumber);
    selectedIngestTargetRef.current = identity;
    targetSelectionTransitionRef.current = { identity, campaignId, session: sessionNumber };
    setHydratedIngestTargetIdentity(null);
    return identity;
  }

  function preserveCurrentDraftForTargetChange() {
    if (!rawText.trim()) return;
    const draft = {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      rawText,
      recapSession,
      slug,
      title,


    } satisfies IngestionModuleDraft;
    writeDraft(storageKey, draft);
    const preserved = { storageKey, campaignId: ingestCampaignId, draft };
    preservedRouteDraftRef.current = preserved;
    setReturnableDraft(preserved);
  }

  function handleIngestCampaignSelect(nextCampaignId: string) {
    if (nextCampaignId === ingestCampaignId) return;
    preserveCurrentDraftForTargetChange();
    invalidateInFlightRecapOperations();
    advanceIngestTarget(nextCampaignId, recapSession);
    ingestCampaignIdRef.current = nextCampaignId;
    invalidateDraftHydration();
    setIngestCampaignId(nextCampaignId);
    syncReviewCampaignUrl(nextCampaignId);
    setHydrated(false);

    setLatestResult(null);
    setState({ status: "idle" });
    setSourceMode("raw");
    setLoadedRun(null);
    setRawText("");
    setSlug("");
    setTitle("");


    setSelectedSavedRunId("");
    setSavedRuns([]);
    setPrimaryOp(null);

    setToast(null);
    lastToastKeyRef.current = null;
  }

  function handleRecapSessionChange(nextSession: number) {
    if (nextSession === recapSession) return;
    preserveCurrentDraftForTargetChange();
    invalidateInFlightRecapOperations();
    advanceIngestTarget(ingestCampaignId, nextSession);
    recapSessionRef.current = nextSession;
    invalidateDraftHydration();
    setRecapSession(nextSession);
    setLatestResult(null);
    setState({ status: "idle" });
    setSourceMode("raw");
    setLoadedRun(null);
    setRawText("");
    setSlug("");
    setTitle("");


    setSelectedSavedRunId("");

    setPrimaryOp(null);

    setToast(null);
    lastToastKeyRef.current = null;
  }

  function invalidateDraftHydration() {
    draftHydrationEpochRef.current += 1;
    // The selected-target identity prevents old hydration from unlocking the
    // new target while its local draft is being restored.
  }

  function invalidateInFlightRecapOperations() {
    recapDraftEpochRef.current += 1;
  }

  useLayoutEffect(() => {
    if (previousRouteStateIdentityRef.current === routeStateIdentity) return;
    previousRouteStateIdentityRef.current = routeStateIdentity;
    const routeSelectionChanged = previousRouteTargetIdentityRef.current !== routeTargetIdentity;
    previousRouteTargetIdentityRef.current = routeTargetIdentity;
    const managedWorldChanged = previousManagedWorldIdRef.current !== (managedWorldId ?? null);
    previousManagedWorldIdRef.current = managedWorldId ?? null;
    const selectionChanged = routeSelectionChanged && (
      ingestCampaignId !== routeCampaignId || recapSession !== routeTargetSession
    );
    const ingestTargetChanged = selectionChanged || (routeSelectionChanged && managedWorldChanged);

    if (ingestTargetChanged) {
      preserveCurrentDraftForTargetChange();
    }

    if (ingestTargetChanged) {
      routeTargetGenerationRef.current += 1;
      invalidateInFlightRecapOperations();
      draftHydrationEpochRef.current += 1;
      const identity = getIngestTargetIdentity(routeCampaignId, routeTargetSession);
      selectedIngestTargetRef.current = identity;
      targetSelectionTransitionRef.current = { identity, campaignId: routeCampaignId, session: routeTargetSession };
      setHydrated(false);
      setHydratedIngestTargetIdentity(null);
      setPrimaryOp(null);
      setLatestResult(null);
      setLoadedRun(null);
      if (managedWorldChanged || ingestCampaignId !== routeCampaignId) {
        setSavedRuns([]);
        setSavedRunScope(null);
      }
      setSourceMode("raw");
      setState({ status: "idle" });
      setToast(null);
        }
    if (selectionChanged) {
      ingestCampaignIdRef.current = routeCampaignId;
      recapSessionRef.current = routeTargetSession;
      setIngestCampaignId(routeCampaignId);
      setRecapSession(routeTargetSession);
      setHydrated(false);
      setRawText("");
      setSlug("");
      setTitle("");


      setLatestResult(null);
      setState({ status: "idle" });
      setSourceMode("raw");
      setLoadedRun(null);

      setPrimaryOp(null);

      setToast(null);
      lastToastKeyRef.current = null;
        setSelectedSavedRunId("");
      if (ingestCampaignId !== routeCampaignId) {
        setSavedRuns([]);
      }
    }

    const readerModeFromRoute = routeView === "recap";
    const readerCampaign = routeCampaign;
    const readerSession = routeSession;
    const readerRunId = routeRunId;
    const readerRouteMatchesSelection =
      readerCampaign === routeCampaignId && readerSession === `session-${routeTargetSession}`;
    const shouldRestoreReader = readerModeFromRoute && readerRouteMatchesSelection;
    setReaderMode(shouldRestoreReader);
    setReaderRun(shouldRestoreReader && readerRunId
      ? { campaign: routeCampaignId, session: readerSession, runId: readerRunId }
      : null);
    restoreReaderRoute.current = shouldRestoreReader;
    readerAttempt.current = null;

  }, [
    routeTargetIdentity,
    routeStateIdentity,
    routeCampaignId,
    routeTargetSession,
    routeView,
    routeCampaign,
    routeSession,
    routeRunId,
    ingestCampaignId,
    recapSession,
    rawText,
    slug,
    title,


    storageKey,
  ]);

  async function postForSelectedIngestTarget(
    request: Parameters<typeof postRecapIngest>[0],
    targetIdentity: string,
  ): Promise<RecapIngestStatus | null> {
    const draftEpoch = recapDraftEpochRef.current;
    let result: RecapIngestStatus;
    try {
      const refs=sessionSupplements.identity===evidenceTargetKey?sessionSupplements.refs:[];
      result = await postRecapIngest({...request,...(refs.length&&request.operation==="generate_recap_memory"?{session_evidence:refs}:{})});
    } catch (error) {
      // Resetting the draft invalidates pending responses and their failures.
      // Do not let an older request publish an error into the new draft.
      if (recapDraftEpochRef.current !== draftEpoch) return null;
      throw error;
    }
    if (
      recapDraftEpochRef.current !== draftEpoch ||
      selectedIngestTargetRef.current !== targetIdentity
    ) return null;
    if (result.campaign_id !== request.campaign_id || result.session !== request.session) {
      const message = "The service returned a result for a different campaign or session. Inspect this recap before retrying.";
      setState({ status: "error", message });
      setToast({
        tone: "error",
        title: "Response did not match this recap",
        detail: message,
        nextSteps: [],
        sticky: true,
      });
      return null;
    }
    return result;
  }

  const rawTextSatisfied = rawText.trim().length > 0;
  const matchingResult =
    latestResult?.campaign_id === ingestCampaignId && latestResult.session === recapSession
      ? latestResult
      : null;
  const resultOwnsSelection =
    selectionHydrated &&
    matchingResult !== null;
  // Only an acknowledged operation result can describe this raw draft.
  const proofResult = resultOwnsSelection ? matchingResult : null;
  const acknowledgedOperationResult =
    latestOperationResult?.targetIdentity === selectedIngestTarget &&
    latestOperationResult.draftEpoch === recapDraftEpochRef.current
      ? latestOperationResult.result
      : null;
  const evidenceResult = acknowledgedOperationResult ?? proofResult;
  const evidenceResultOwnsSelection = evidenceResult !== null;
  const busy = state.status === "running_full_ingest";
  const sourceInputSatisfied = rawTextSatisfied;
  const graphPreviewFromEvidence = evidenceResult?.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const graphPreview = graphPreviewFromEvidence;
  const currentSavedRunLookup = savedRunLookup?.key === savedRunKey ? savedRunLookup : null;
  const exactGraphReviewRunId = loadedRun?.runId ?? (evidenceResultOwnsSelection
    ? graphPreviewFromEvidence?.extraction_run_id?.trim() || null
    : null);
  const graphReviewable = loadedRun ? ["reviewable", "promoted"].includes(loadedRun.runStatus) : graphPreviewIsReviewable(graphPreview);
  const canOpenGraphReview = Boolean(
    isIngestSurfacePath()
    && managedWorldId
    && exactGraphReviewRunId
    && graphReviewable
    && (sourceMode === "raw" || currentSavedRunLookup?.status === "loaded"),
  );
  const graphReviewUnavailableReason = !managedWorldId
    ? "selected World"
    : "exact extraction run";
  const selectedReaderRun = readerRun?.campaign === ingestCampaignId && readerRun.session === `session-${recapSession}` ? readerRun.runId : null;
  const reviewIdentity = JSON.stringify([
    managedWorldId ?? null,
    ingestCampaignId,
    recapSession,
    selectedIngestTarget,
    savedRunRefresh,
    selectedReaderRun ?? (evidenceResultOwnsSelection ? graphPreview?.extraction_run_id : null) ?? null,
  ]);
  useLayoutEffect(() => {
    currentReviewIdentity.current = reviewIdentity;
    reviewEpoch.current += 1;
    readerAttempt.current = null;
    setReviewSource(null);
    setSavedSource(null);
    setReviewError(null);
    setReviewLoading(false);
    return () => { reviewEpoch.current += 1; };
  }, [reviewIdentity]);
  useEffect(() => {
    if (!readerMode || !selectionHydrated || readerAttempt.current === reviewIdentity) return;
    // An exact saved route waits for its scoped catalogue; never infer a
    // source from a session label or the another draft.
    if (currentSavedRunLookup?.status !== "loaded" && currentSavedRunLookup?.status !== "failed") return;
    const restore = restoreReaderRoute.current;
    restoreReaderRoute.current = false;
    readerAttempt.current = reviewIdentity;
    if (currentSavedRunLookup?.status === "failed") {
      setReviewError(managedWorldId ? "Saved extraction work could not be checked. Retry saved work." : "Select a World to read saved extraction work.");
      return;
    }
    void reviewSavedSource(restore, true);
  }, [readerMode, selectionHydrated, reviewIdentity, latestResult?.session, latestResult?.campaign_id, savedRuns, currentSavedRunLookup?.status]);
  const hasLoadedRecapContent =
    sourceMode !== "raw" ||
    loadedRun !== null ||
    Boolean(rawText.trim()) ||
    resultOwnsSelection;
  const showRecapWelcome =
    selectionHydrated &&
    !readerMode &&
    !returnableDraft &&
    !hasLoadedRecapContent &&
    !busy &&
    state.status !== "error" &&
    !matchingResult?.errors?.length;
  const hasPriorIngestWork = resultOwnsSelection;
  const workflowNextAction = (() => {
    if (state.status === "running_full_ingest") {
      return "Processing recap and building World Graph context.";
    }
    if (readerMode) {
      if (savedSource?.identity === reviewIdentity) return `Viewing saved source · ${savedSource.source.run.runStatus}.`;
      if (reviewLoading) return `Opening saved recap · Session ${recapSession}…`;
      if (reviewError) return "Saved recap could not be opened. See the message on the recap surface.";
      if (reviewSource?.projection) return `Viewing saved recap · Session ${reviewSource.session}.`;
      return `Opening saved recap · Session ${recapSession}…`;
    }
    if (!managedWorldId) return "Select a World before processing.";
    if (!validRecapSession) return "Choose a session number before processing.";
    if (canOpenGraphReview) return "Candidates are ready for review; publication is a separate step.";
    return "Write or paste a recap, then choose Process.";
  })();
  const canProcessRecap = !busy && sourceMode === "raw" && !readerMode && validRecapSession && rawTextSatisfied && !!managedWorldId;
  useEffect(() => {
    if (selectionHydrated) return;
    let cancelled = false;

    async function hydrateDraft() {
      const hydrationEpoch = draftHydrationEpochRef.current;
      const draft = readDraft(storageKey);
      const routeTransition = targetSelectionTransitionRef.current?.identity === selectedIngestTarget
        ? targetSelectionTransitionRef.current
        : null;
      const routeSessionTarget = routeTransition?.session ?? routeTargetSession;
      const forcedRouteSelection = routeTransition !== null || (
        initialHydrationRef.current && requestedRecapSession != null
      );
      const mismatchedStoredDraft = Boolean(
        forcedRouteSelection &&
        draft &&
        draft.recapSession !== routeSessionTarget,
      );
      const storedRouteDraft = mismatchedStoredDraft && draft?.rawText.trim()
        ? { storageKey, campaignId: ingestCampaignId, draft }
        : null;
      const preservedRouteDraft = preservedRouteDraftRef.current;
      const preservedMismatchedDraft = preservedRouteDraft && (
        preservedRouteDraft.campaignId !== ingestCampaignId ||
        preservedRouteDraft.draft.recapSession !== routeSessionTarget
      ) ? preservedRouteDraft : null;
      const routeDraft = storedRouteDraft ?? preservedMismatchedDraft;
      setReturnableDraft(routeDraft);
      const usableDraft = mismatchedStoredDraft
        ? null
        : draft ?? (
            preservedRouteDraft?.campaignId === ingestCampaignId &&
            preservedRouteDraft.draft.recapSession === routeSessionTarget
              ? preservedRouteDraft.draft
              : null
          );
      const defaultRecap = forcedRouteSelection
        ? routeSessionTarget
        : usableDraft?.recapSession ?? routeSessionTarget;
      if (recapSessionRef.current !== defaultRecap) {
        routeTargetGenerationRef.current += 1;
        const identity = getIngestTargetIdentity(ingestCampaignId, defaultRecap);
        selectedIngestTargetRef.current = identity;
        recapSessionRef.current = defaultRecap;
        targetSelectionTransitionRef.current = {
          identity,
          campaignId: ingestCampaignId,
          session: defaultRecap,
        };
        setRecapSession(defaultRecap);
        setHydrated(false);
        setHydratedIngestTargetIdentity(null);
        return;
      }
      const initialSlug = usableDraft?.slug ?? "";
      const initialTitle = usableDraft?.title ?? "";

      if (!usableDraft) {
        setRawText("");
        setRecapSession(defaultRecap);
        setSlug(initialSlug);
        setTitle(initialTitle);


        setState({ status: "idle" });
        setLatestResult(null);

      } else {
        setRawText(usableDraft.rawText);
        setRecapSession(usableDraft.recapSession);
        setSlug(usableDraft.slug);
        setTitle(usableDraft.title);


        setState({ status: "idle" });
        setLatestResult(null);

      }

      if (!cancelled && hydrationEpoch === draftHydrationEpochRef.current) {
        setHydrated(true);
        setHydratedIngestTargetIdentity(selectedIngestTarget);
        initialHydrationRef.current = false;
        if (targetSelectionTransitionRef.current?.identity === selectedIngestTarget) {
          targetSelectionTransitionRef.current = null;
        }
        if (routeDraft && preservedRouteDraftRef.current === routeDraft) {
          preservedRouteDraftRef.current = routeDraft;
        } else if (usableDraft && preservedRouteDraftRef.current?.draft === usableDraft) {
          preservedRouteDraftRef.current = null;
        }
      }
    }

    setToast(null);
    lastToastKeyRef.current = null;
    void hydrateDraft();

    return () => {
      cancelled = true;
    };
  }, [
    storageKey,
    session,
    ingestCampaignId,
    requestedRecapSession,
    initialSourceSession,
    freshRecapEntry,
    routeTargetIdentity,
    routeTargetSession,
    hydrated,
    selectedIngestTarget,
  ]);

  useEffect(() => {
    if (!hydrated) return;
    const controller = new AbortController();
    const catalogEpoch = ++savedCatalogEpoch.current;
    let cancelled = false;
    const worldId = managedWorldId ?? "";
    setSavedRuns([]);
    setSavedRunScope(null);
    setSavedRunLookup({key: savedRunKey, status: "loading"});
    if (!worldId) {
      setSavedRunLookup({key: savedRunKey, status: "failed"});
      return;
    }
    void getSavedRecapRuns(worldId, ingestCampaignId, controller.signal).then(scope => {
      if (cancelled || catalogEpoch !== savedCatalogEpoch.current || ingestCampaignIdRef.current !== ingestCampaignId) return;
      setSavedRunScope(scope);
      setSavedRuns(scope.runs);
      setSavedRunLookup({key: savedRunKey, status: "loaded"});
      setSelectedSavedRunId(current => scope.runs.some(row => row.runId === current) ? current : "");
    }).catch(() => {
      if (!cancelled && catalogEpoch === savedCatalogEpoch.current) setSavedRunLookup({key: savedRunKey, status: "failed"});
    });
    return () => {cancelled = true; controller.abort();};
  }, [ingestCampaignId, managedWorldId, hydrated, savedRunRefresh, savedRunKey]);

  useEffect(() => {
    if (!selectionHydrated || readerMode || returnableDraft) {
      return;
    }
    writeDraft(storageKey, {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      rawText,
      recapSession,
      slug,
      title,


    });
  }, [
    selectionHydrated,
    readerMode,
    returnableDraft,
    storageKey,
    rawText,
    recapSession,
    slug,
    title,


  ]);

  useEffect(() => {
    if (!selectionHydrated) {
      return;
    }
    const maybeToast = buildToastForResult(latestResult, {
      fallbackErrorMessage: state.status === "error" ? state.message : undefined,
    });
    if (!maybeToast) {
      if (suppressResultToastRef.current) {
        suppressResultToastRef.current = false;
      }
      return;
    }
    const key = JSON.stringify({
      tone: maybeToast.tone,
      title: maybeToast.title,
      detail: maybeToast.detail,
      nextSteps: maybeToast.nextSteps,
      sticky: Boolean(maybeToast.sticky),
    });
    if (suppressResultToastRef.current) {
      // Process already set an explicit toast; adopt the auto-toast key so
      // Strict Mode remounts / later effect passes do not overwrite it.
      suppressResultToastRef.current = false;
      lastToastKeyRef.current = key;
      return;
    }
    if (key === lastToastKeyRef.current) {
      return;
    }
    lastToastKeyRef.current = key;
    setToast(maybeToast);
  }, [selectionHydrated, latestResult, state]);

  useEffect(() => {
    if (!toast || toast.sticky) {
      return;
    }
    const timeout = window.setTimeout(() => setToast(null), 9000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function closeSavedReader() {
    reviewEpoch.current += 1;
    setSavedSource(null);
    setLoadedRun(null);
    setSourceMode("raw");
    setReviewSource(null);
    setReviewError(null);
    setReviewLoading(false);
    setReaderMode(false);
    setReaderRun(null);
    readerAttempt.current = null;
    const params = new URLSearchParams(window.location.search);
    params.delete("view");
    params.delete("recapReviewRunId");
    window.history.replaceState({}, "", `${ingestRoutePath()}?${params.toString()}`);
  }

  function returnToDraft() {
    const candidate = returnableDraft;
    if (!candidate) {
      closeSavedReader();
      return;
    }

    invalidateInFlightRecapOperations();
    draftHydrationEpochRef.current += 1;
    closeSavedReader();
    const { draft, campaignId } = candidate;
    advanceIngestTarget(campaignId, draft.recapSession);
    ingestCampaignIdRef.current = campaignId;
    recapSessionRef.current = draft.recapSession;
    setIngestCampaignId(campaignId);
    setRecapSession(draft.recapSession);
    setRawText(draft.rawText);
    setSlug(draft.slug);
    setTitle(draft.title);


    setSourceMode("raw");
    setLoadedRun(null);
    setLatestResult(null);
    setState({ status: "idle" });
    setToast(null);
    setReturnableDraft(null);
    setHydrated(false);
    setHydratedIngestTargetIdentity(null);

    const params = new URLSearchParams(window.location.search);
    params.set("campaign", campaignId);
    params.set("session", `session-${draft.recapSession}`);
    params.delete("view");
    params.delete("recapReviewRunId");
    window.history.replaceState({}, "", `${ingestRoutePath()}?${params.toString()}`);
  }

  function resetIngestionDraft() {
    invalidateInFlightRecapOperations();
    draftHydrationEpochRef.current += 1;
    closeSavedReader();
    lastToastKeyRef.current = null;
    window.localStorage.removeItem(storageKey);
    setRawText("");
    setSlug("");
    setTitle("");


    setForceGraphRun(false);
    setSourceMode("raw");
    setLoadedRun(null);
    setReturnableDraft(null);
    setSelectedSavedRunId("");
    setToast(null);
    setState({ status: "idle" });
    setLatestResult(null);
    setPrimaryOp(null);

  }

  function startNewRecap() {

    resetIngestionDraft();
  }

  function applyOperationResult(
    result: RecapIngestStatus,
    targetIdentity: string,
    draftEpoch: number,
  ): RecapIngestStatus {
    setLatestResult(result);
    setLatestOperationResult({ targetIdentity, draftEpoch, result });
    return result;
  }

  function resultErrorMessage(result: RecapIngestStatus, fallback: string): string {
    return result.errors.length > 0 ? result.errors.join("; ") : fallback;
  }

  async function loadPriorIngestion(record: SavedRecapRun) {
    const sessionNumber = recapSessionNumber(record.sessionId ?? "");
    if (sessionNumber == null || sessionNumber <= 0 || record.campaignId !== ingestCampaignId) {
      setToast({tone: "error", title: "Saved work cannot be opened", detail: "This run has no matching campaign and numeric session.", nextSteps: [], sticky: true});
      return;
    }
    preserveCurrentDraftForTargetChange();
    invalidateInFlightRecapOperations();
    invalidateDraftHydration();
    const identity = advanceIngestTarget(ingestCampaignId, sessionNumber);
    recapSessionRef.current = sessionNumber;
    targetSelectionTransitionRef.current = null;
    setHydrated(true);
    setHydratedIngestTargetIdentity(identity);
    setRecapSession(sessionNumber);
    setSourceMode("saved");
    setLoadedRun(record);
    setReaderRun({campaign: ingestCampaignId, session: record.sessionId!, runId: record.runId});
    setRawText("");
    setTitle("");
    setSlug("");
    setLatestResult(null);
    setState({status: "idle"});
    setToast(null);
    const route = new URLSearchParams(window.location.search);
    route.set("campaign", ingestCampaignId);
    route.set("session", record.sessionId!);
    route.set("view", "recap");
    route.set("recapReviewRunId", record.runId);
    route.set("recapProjection", "source");
    window.history.replaceState({}, "", `${ingestRoutePath()}?${route}`);
    restoreReaderRoute.current = false;
    setReaderMode(true);
  }

  async function loadSelectedPriorIngestion() {
    const record = savedRuns.find((row) => row.runId === selectedSavedRunId);
    if (!record) {
      setToast({
        tone: "warning",
        title: "Select saved extraction work",
        detail: "Choose an exact extraction run first.",
        nextSteps: [],
      });
      return;
    }
    await loadPriorIngestion(record);
  }

  function publishPrimaryToast(next: IngestionToast) {
    suppressResultToastRef.current = true;
    const key = JSON.stringify({
      tone: next.tone,
      title: next.title,
      detail: next.detail,
      nextSteps: next.nextSteps,
      sticky: Boolean(next.sticky),
    });
    lastToastKeyRef.current = key;
    setToast(next);
  }

  async function processRecap() {
    if (!canProcessRecap) return;
    const targetIdentity = selectedIngestTarget;
    const draftEpoch = recapDraftEpochRef.current;
    setReaderRun(null);
    invalidateDraftHydration();
    lastToastKeyRef.current = null;
    setPrimaryOp("process");
    publishPrimaryToast({
      tone: "info",
      title: "Processing recap",
      detail: "Saving the recap and building its World Graph context.",
      nextSteps: [],
    });
    setState({ status: "running_full_ingest" });

    try {
      const response = await postForSelectedIngestTarget({
          operation: "generate_recap_memory",
          campaign_id: ingestCampaignId,
          managed_world_id: managedWorldId,
          session: recapSession,
          raw_text: sourceMode === "raw" ? rawText : undefined,
          include_graph_extraction: true,
          graph_model_id: INGESTION_GRAPH_MODEL_ID,
          force_graph_run: forceGraphRun || undefined,
        }, targetIdentity);
      if (!response) return;
      const result = applyOperationResult(response, targetIdentity, draftEpoch);
      setSavedRunRefresh(value => value + 1);
      setHydrated(true);
      setHydratedIngestTargetIdentity(targetIdentity);
      if (targetSelectionTransitionRef.current?.identity === targetIdentity) {
        targetSelectionTransitionRef.current = null;
      }

      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Ingest failed") });
        return;
      }

      const freshReaderParams = new URLSearchParams(window.location.search);
      freshReaderParams.set("view", "recap");
      freshReaderParams.set("campaign", ingestCampaignId);
      freshReaderParams.set("session", `session-${recapSession}`);
      const processedRunId = (result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined)?.extraction_run_id;
      if (!processedRunId) throw new Error("The service did not return an exact extraction run. Your draft is preserved.");
      if (processedRunId) freshReaderParams.set("recapReviewRunId", processedRunId);
      else freshReaderParams.delete("recapReviewRunId");
      freshReaderParams.set("recapProjection", "candidate");
      window.history.replaceState({}, "", `${window.location.pathname}?${freshReaderParams}`);
      preserveCurrentDraftForTargetChange();
      setSourceMode("saved");
      setRawText("");
      readerAttempt.current = null;
      restoreReaderRoute.current = false;
      setReaderMode(true);

      const candidate = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
      if (candidate?.status === "candidate_validation_ready" && !candidate.blocked_reason) {
        setState(derivePaneStateFromResult(result));
        publishPrimaryToast({
          tone: "success",
          title: "Recap processed",
          detail: "The extracted candidates are ready for review. Nothing has been published to the World Graph.",
          nextSteps: ["Review graph candidate"],
          sticky: true,
        });
        return;
      }

      setState(derivePaneStateFromResult(result));
      publishPrimaryToast({tone:"warning",title:"Extraction needs attention",detail:"Inspect the exact saved attempt before retrying.",nextSteps:[],sticky:true});
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setHydrated(true);
      setHydratedIngestTargetIdentity(targetIdentity);
      if (targetSelectionTransitionRef.current?.identity === targetIdentity) {
        targetSelectionTransitionRef.current = null;
      }
      const message = error instanceof Error ? error.message : "Processing failed";
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message,
      });
      publishPrimaryToast({
        tone: "error",
        title: "Processing failed",
        detail: message,
        nextSteps: ["Retry Process", "Open Advanced → Evidence for details"],
        sticky: true,
      });
    } finally {
      if (
        recapDraftEpochRef.current === draftEpoch &&
        selectedIngestTargetRef.current === targetIdentity
      ) setPrimaryOp(null);
    }
  }

  async function reviewSavedSource(restore = false, preserveSelection = false, admittedMemory?: boolean) {
    restoreReaderRoute.current = false;
    const params = new URLSearchParams(window.location.search);
    // A queued restore must not reopen a reader the user has just left.
    if ((restore || preserveSelection) && params.get("view") !== "recap") return;
    const sameSelection = params.get("campaign") === ingestCampaignId && params.get("session") === `session-${recapSession}`;
    const currentRun = loadedRun?.runId ?? (resultOwnsSelection ? graphPreview?.extraction_run_id : undefined);
    const runId = ((preserveSelection || restore) && selectedReaderRun ? selectedReaderRun : currentRun) ?? undefined;
    if (restore && (!sameSelection || !requestedRecapSessionFromLocation())) {
      setReviewError("Saved recap route has an invalid campaign or session.");
      return;
    }
    if (!preserveSelection && !restore) setReaderRun(runId ? { campaign: ingestCampaignId, session: `session-${recapSession}`, runId } : null);
    params.set("campaign", ingestCampaignId);
    params.set("session", `session-${recapSession}`);
    params.set("view", "recap");
    const projectionMode = admittedMemory === undefined ? params.get("recapProjection") ?? "source" : admittedMemory ? "admitted" : "candidate";
    const readAdmitted = projectionMode === "admitted";
    params.set("recapProjection", projectionMode);
    if (runId) params.set("recapReviewRunId", runId); else params.delete("recapReviewRunId");
    window.history.replaceState({}, "", `${ingestRoutePath()}?${params.toString()}`);
    readerAttempt.current = reviewIdentity;
    setReaderMode(true);
    const identity = reviewIdentity;
    const epoch = ++reviewEpoch.current;
    const capturedSession = recapSession;
    const capturedManagedWorldId = managedWorldId?.trim() ?? "";
    const nodes = graphPreview?.candidate_node_count ?? 0;
    const edges = graphPreview?.candidate_edge_count ?? 0;
    const isCurrent = () => epoch === reviewEpoch.current && identity === currentReviewIdentity.current;
    setReviewLoading(true);
    setReviewError(null);
    setReviewSource(null);
    setSavedSource(null);
    try {
      const record = runId ? savedRuns.find(item => item.runId === runId) : undefined;
      if (currentSavedRunLookup?.status !== "loaded" || !runId || !record || !savedRunScope || savedRunScope.managedWorldId !== capturedManagedWorldId
        || record.campaignId !== ingestCampaignId || record.sessionId !== `session-${capturedSession}`) {
        throw new Error("The exact saved extraction run is not available for this World, campaign and session. Choose an exact run from saved work.");
      }
      setLoadedRun(record);
      setSourceMode("saved");
      if (projectionMode === "source") {
        if (record.unavailableReason) throw new Error(record.unavailableReason);
        const source = await getSavedRecapSource(savedRunScope, record);
        if (!isCurrent()) return;
        setSavedSource({identity, source});
        setReviewSource({identity,session:capturedSession,nodes:0,edges:0,runId,projection:null});
        return;
      }
      setReviewSource({ identity, session: capturedSession, nodes, edges, runId, projection: null });
      if (!readAdmitted) {
        if (!capturedManagedWorldId) throw new Error("Select a managed World before opening this exact candidate.");
        const candidate = await getExactRunCandidateProjection(runId,capturedManagedWorldId);
        if (!isCurrent()) return;
        if (candidate.runId !== runId || candidate.sourceDomain !== "recap" || candidate.campaignId !== ingestCampaignId
          || candidate.sessionId !== `session-${capturedSession}` || candidate.managedWorldId !== capturedManagedWorldId
          || candidate.runRevision !== record.runRevision || candidate.sourceArtifactId !== record.sourceArtifactId
          || candidate.sourceSha256 !== `sha256:${record.sourceSha256}` || candidate.nativeWorldId !== savedRunScope.nativeWorldId
          || candidate.bindingVersion !== savedRunScope.bindingVersion) {
          throw new Error("Exact candidate does not match the selected managed World binding, source campaign or session.");
        }
        setReviewSource({identity,session:capturedSession,nodes:candidate.nodes.length,edges:candidate.edges.length,runId,projection:candidate});
      } else {
        // A selected extraction run is an exact source identity. Never replace
        // it with the another source for the same session.
        if (!capturedManagedWorldId) {
          throw new Error("Select a managed World before opening this exact recap projection.");
        }
        const historical = await getHistoricalRecapWorldProjection(runId, capturedManagedWorldId);
        if (!isCurrent()) return;
        if (
          historical.runId !== runId ||
          historical.sourceDomain !== "recap" ||
          historical.campaignId !== ingestCampaignId ||
          historical.sessionId !== `session-${capturedSession}` || historical.sourceArtifactId !== record.sourceArtifactId
          || historical.sourceSha256 !== `sha256:${record.sourceSha256}`
        ) {
          throw new Error("Historical recap projection does not match the selected extraction run.");
        }
        if (historical.sourceStatus !== "available" || historical.graphStatus !== "available") {
          throw new Error("The exact extraction run does not have both a durable source and a World Graph projection.");
        }
        if (
          !historical.sourceArtifactId ||
          !historical.sourceRevisionId ||
          !historical.sourceSha256.startsWith("sha256:")
        ) {
          throw new Error("The exact extraction run is missing its source revision or content digest.");
        }
        if (
          historical.managedWorldId !== capturedManagedWorldId ||
          historical.worldId !== savedRunScope.nativeWorldId ||
          historical.bindingVersion !== savedRunScope.bindingVersion
        ) {
          throw new Error("Historical recap projection does not match the selected managed World binding.");
        }
        const request: WorldGraphProjectionRequest = {
          schema: "dmb_world_graph_projection_request_v1",
          worldId: historical.worldId,
          campaignId: ingestCampaignId,
          scopeMode: "campaign",
          focus: {
            kind: "session",
            sessionId: `session-${capturedSession}`,
            campaignId: ingestCampaignId,
          },
          admissibility: "gm",
        };
        if (historical.snapshot.worldId !== historical.worldId) {
          throw new Error("Historical recap projection does not match the selected World.");
        }
        if (!historical.snapshot.revisionId || !historical.snapshot.headRevisionId) {
          throw new Error("Historical recap projection has no verified World revision identity.");
        }
        const integrityError = verifyWorldGraphProjectionResponse({
          request,
          response: historical as unknown as WorldGraphProjection,
          revisionKind: "head",
        });
        if (integrityError) throw new Error(integrityError);
        setReviewSource({ identity, session: capturedSession, nodes, edges, runId, projection: historical });
      }
    } catch (error) {
      if (isCurrent()) setReviewError(error instanceof Error ? error.message : "Unable to open saved source.");
    } finally {
      if (isCurrent()) setReviewLoading(false);
    }
  }

  function handleNativeGraphAccessChanged(available: boolean) {
    savedCatalogEpoch.current += 1;
    reviewEpoch.current += 1;
    readerAttempt.current = null;
    setReviewSource(null);
    setSavedSource(null);
    setReviewLoading(false);
    if (available) {
      setReviewError(null);
      setSavedRunRefresh(value => value + 1);
    } else {
      setSavedRuns([]);
      setSavedRunScope(null);
      setSavedRunLookup({key: savedRunKey, status: "failed"});
      if (readerMode) setReviewError("Reconnect local Graph access, then refresh saved work.");
    }
  }

  function openGraphReviewWorkbench() {
    if (typeof window === "undefined" || !canOpenGraphReview || !exactGraphReviewRunId || !managedWorldId) return;
    const params = new URLSearchParams(window.location.search);
    params.set("world", managedWorldId);
    params.set("session", `session-${recapSession}`);
    params.set("campaign", ingestCampaignId);
    params.set("extractionRunId", exactGraphReviewRunId);
    params.delete("recapReviewRunId");
    params.delete("sourceArtifactId");
    params.delete("documentId");
    params.delete("revision");
    const sourceArtifactId = reviewSource?.runId === exactGraphReviewRunId
      && (reviewSource.projection?.schema === "dmb_historical_recap_world_projection_v1"
        || reviewSource.projection?.schema === "dmb_exact_run_candidate_projection_v1")
      ? reviewSource.projection.sourceArtifactId
      : currentSavedRunLookup?.status === "loaded" ? savedRuns.find(run => run.runId === exactGraphReviewRunId)?.sourceArtifactId ?? null : null;
    if (sourceArtifactId) params.set("sourceArtifactId", sourceArtifactId);
    window.history.pushState({}, "", `${ingestRoutePath()}?${params.toString()}${window.location.hash}`);
    window.dispatchEvent(new Event("popstate"));
    projection?.close();
  }

  const showSourceActions = true;
  const showEvidenceShortcut = evidenceResult !== null;
  const showWorkflowActions = sourceMode === "raw" && !readerMode && (sourceInputSatisfied || busy);
  const showGraphReviewAction = isIngestSurfacePath() && graphReviewable;
  const showWorkflowFeedback = showWorkflowActions || showGraphReviewAction || Boolean(toast) || state.status === "error";
  const canReturnToDraft = Boolean(returnableDraft || (readerMode && rawText.trim()));

  return (
    <div className="module-panel ingestion-module" data-module-id="ingestion">
      <nav className="ingest-local-nav" aria-label="Ingest workspace navigation">
        <div className="ingest-local-nav__identity">
          <ReviewCampaignPicker
            selectedCampaignId={ingestCampaignId}
            onSelect={handleIngestCampaignSelect}
            className="graph-preview-run-picker ingestion-campaign-picker"
          />
          <label className="ingest-local-nav__field" htmlFor="ingestion-recap-session">
            <span>Session</span>
            <span className="ingest-local-nav__session-control">
              <input
                id="ingestion-recap-session"
                aria-label="Recap/source session"
                type="number"
                min={1}
                step={1}
                value={recapSession > 0 ? recapSession : ""}
                onChange={(event) => {
                  const nextValue = Number.parseInt(event.target.value, 10);
                  handleRecapSessionChange(Number.isNaN(nextValue) ? 0 : nextValue);
                }}
              />
              <RequiredBadge satisfied={validRecapSession} />
            </span>
          </label>
          {!readerMode ? <label className="ingest-local-nav__field ingest-local-nav__title">
            <span>Draft title (optional)</span>
            <input aria-label="Draft title (optional)" value={title} onChange={event=>setTitle(event.target.value)}/>
          </label> : null}
          {selectionHydrated ? (
            <>
              {canReturnToDraft ? (
                <button
                  type="button"
                  className="ingest-local-nav__primary-action"
                  onClick={returnToDraft}
                >
                  Return to draft
                </button>
              ) : null}
              {canReturnToDraft && !returnableDraft ? (
                <button
                  type="button"
                  onClick={() => showRecapWelcome ? rawRecapTextAreaRef.current?.focus() : startNewRecap()}
                >
                  {showRecapWelcome ? "Paste recap" : "New recap"}
                </button>
              ) : !canReturnToDraft ? (
                <button
                  type="button"
                  className="ingest-local-nav__primary-action"
                  onClick={() => showRecapWelcome ? rawRecapTextAreaRef.current?.focus() : startNewRecap()}
                >
                  {showRecapWelcome ? "Paste recap" : "New recap"}
                </button>
              ) : null}
            </>
          ) : null}
        </div>

        {showSourceActions || showWorkflowActions || showGraphReviewAction || showEvidenceShortcut ? (
          <div className="ingest-local-nav__workflow">
            {showSourceActions ? (
              <div className="ingest-local-nav__source" role="group" aria-label="Source actions">
                <label className="ingest-local-nav__prior" htmlFor="ingestion-prior-artifact">
                  <span className="sr-only">Saved extraction work</span>
                  <select
                    id="ingestion-prior-artifact"
                    aria-label="Saved extraction work"
                    value={selectedSavedRunId}
                    onChange={(event) => setSelectedSavedRunId(event.target.value)}
                    disabled={currentSavedRunLookup?.status !== "loaded"}
                  >
                    <option value="">Choose saved extraction work…</option>
                    {savedRuns.map((record) => (
                      <option key={record.runId} value={record.runId}>
                        {record.sessionId ?? "No session"} · {record.runStatus} · {record.runId}
                      </option>
                    ))}
                  </select>
                </label>
                {selectedSavedRunId ? (
                  <button
                    type="button"
                    aria-label="Open saved extraction"
                    onClick={() => void loadSelectedPriorIngestion()}
                    disabled={currentSavedRunLookup?.status !== "loaded"}
                  >
                    Open
                  </button>
                ) : null}
                <button type="button" onClick={() => {readerAttempt.current = null; setSavedRunRefresh(value => value + 1);}} disabled={!managedWorldId}>Refresh saved work</button>
                {!managedWorldId ? <span>Select a World to read saved extraction work.</span> : savedRunLookup?.status === "failed" ? <span role="alert">Saved extraction work could not be checked.</span> : null}
              </div>
            ) : null}

            {showEvidenceShortcut ? (
              <a
                className="ingest-local-nav__evidence"
                href="#ingestion-evidence-details"
                onClick={() => {
                  if (evidenceDetailsRef.current) evidenceDetailsRef.current.open = true;
                }}
              >
                Evidence
              </a>
            ) : null}

            {showWorkflowActions || showGraphReviewAction ? (
              <div className="ingest-local-nav__stages" role="group" aria-label="Recap processing">
                {showWorkflowActions ? (
                  <>
                      <label className="ingestion-checkbox-row ingestion-replace-graph-row ingest-local-nav__replace">
                        <input
                          type="checkbox"
                          checked={forceGraphRun}
                          onChange={(event) => setForceGraphRun(event.target.checked)}
                        />
                        Run fresh extraction
                      </label>
                    <button
                      type="button"
                      aria-label={primaryOp === "process" ? "Processing recap" : "Process recap"}
                      className="primary"
                      onClick={() => void processRecap()}
                      disabled={!canProcessRecap}
                    >
                      {primaryOp === "process" ? <><span className="button-inline-spinner" aria-hidden="true" /> Processing…</> : "Process"}
                    </button>
                  </>
                ) : null}
                {showGraphReviewAction ? (
                  <>
                    <button
                      type="button"
                      aria-label={canOpenGraphReview ? "Open Graph Review" : `Graph Review unavailable: ${graphReviewUnavailableReason} required`}
                      onClick={openGraphReviewWorkbench}
                      disabled={!canOpenGraphReview}
                    >
                      Graph Review
                    </button>
                    {!canOpenGraphReview ? (
                      <span className="ingest-local-nav__action-hint" role="status">
                        Graph Review needs {graphReviewUnavailableReason === "exact extraction run" ? "an exact extraction run for this session" : "a selected World"}.
                      </span>
                    ) : null}
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
        {showWorkflowFeedback ? (
          <div className={`ingest-local-nav__feedback ingest-local-nav__feedback--${toast?.tone ?? "neutral"}`}>
            <p
              className="ingest-local-nav__status"
              role={toast?.tone === "error" || toast?.tone === "warning" ? "alert" : "status"}
              aria-live={toast?.tone === "error" || toast?.tone === "warning" ? "assertive" : "polite"}
              aria-atomic="true"
            >
              {state.status === "error"
                ? <span className="ingest-local-nav__status-title">{toast?.title ?? "Needs attention"}</span>
                : primaryOp === "process"
                  ? "Processing recap and building World Graph context…"
                : !selectionHydrated
                        ? "Restoring draft…"
                      : toast
                        ? <>
                            <span className="ingest-local-nav__status-title">{toast.title}</span>
                            {sourceInputSatisfied ? (
                              <>
                                <span aria-hidden="true"> · </span>
                                <span>{workflowNextAction}</span>
                              </>
                            ) : null}
                          </>
                        : workflowNextAction}
            </p>
            {toast ? (
              <>
                <details className="ingest-local-nav__feedback-details" aria-label="Ingestion feedback details">
                  <summary>Details</summary>
                  <div className="ingest-local-nav__feedback-popover">
                    <p>{toast.detail}</p>
                    {toast.nextSteps.length > 0 ? (
                      <>
                        <p className="ingestion-toast-next-label">Next steps</p>
                        <ul>
                          {toast.nextSteps.map((step) => (
                            <li key={step}>{step}</li>
                          ))}
                        </ul>
                      </>
                    ) : null}
                  </div>
                </details>
                <button
                  type="button"
                  className="ingest-local-nav__dismiss"
                  onClick={() => setToast(null)}
                  aria-label="Dismiss ingestion toast"
                >
                  <span aria-hidden="true">×</span>
                </button>
              </>
            ) : null}
          </div>
        ) : null}
      </nav>

      {showRecapWelcome ? (
        <section className="ingest-welcome-card ingest-welcome-card--world" aria-labelledby="ingest-first-recap-title">
          <p className="ingest-welcome-kicker">
            {hasPriorIngestWork ? "YOUR SESSION CANVAS" : "A NEW STORY STARTS HERE"}
          </p>
          <h2 id="ingest-first-recap-title">
            Bring your table’s story into the World.
          </h2>
          <p className="ingest-welcome-intro">
            Your recap will become a growing map of the people, places, events, and ties that shape your World.
          </p>
        </section>
      ) : null}

      <div className={`ingestion-command-grid${readerMode ? " ingestion-command-grid--reading" : ""}`}>
        <section className={`ingestion-controls-pane${readerMode ? " ingestion-controls-pane--reading" : ""}`} aria-label={readerMode ? "Recap surface" : "Recap editor"}>
          {readerMode ? (
            <section className="ingest-enriched-recap" aria-label="Saved recap reader">
              {reviewLoading ? <p role="status">Opening saved extraction…</p> : null}
              {reviewError ? (
                <p role="alert" className="module-error">
                  {reviewError} {reviewError.includes("credential") || reviewError.includes("graph_auth_required") ? "Open Advanced → Evidence to connect the local Graph session." : ""}
                </p>
              ) : null}
              {sourceMode === "saved" || selectedReaderRun ? <p>Saved extraction{loadedRun ? ` · ${loadedRun.runStatus}` : ""}. To process new text, choose New recap or Return to draft.</p> : null}
              {reviewSource?.runId ? <div aria-label="Recap projection choice">
                    <button type="button" disabled={reviewLoading || savedSource?.identity === reviewIdentity} onClick={() => {
                      const route = new URLSearchParams(window.location.search); route.set("recapProjection", "source");
                      window.history.replaceState({}, "", `${ingestRoutePath()}?${route}`); void reviewSavedSource(false,true);
                    }}>View saved source</button>
                    <button type="button" disabled={reviewLoading || !loadedRun || !["reviewable", "promoted"].includes(loadedRun.runStatus) || reviewSource.projection?.schema === "dmb_exact_run_candidate_projection_v1"}
                      onClick={() => void reviewSavedSource(false,true,false)}>View extracted candidates</button>
                    <button type="button" disabled={reviewLoading || reviewSource.projection?.schema === "dmb_historical_recap_world_projection_v1"}
                      onClick={() => void reviewSavedSource(false,true,true)}>View admitted memory</button>
              </div> : null}
              {savedSource?.identity === reviewIdentity ? <WorldPlanAgentAnswer answer={savedSource.source.sourceProse} /> : reviewSource?.projection ? (
                <>
                  {reviewSource.projection.schema === "dmb_exact_run_candidate_projection_v1" ? (
                    <GraphReviewCandidateRecapProjection projection={reviewSource.projection}/>
                  ) : (
                    <>
                      <p className="ingest-enriched-recap__status">Exact extraction run · {reviewSource.projection.runId}. Linked facts use the current admitted World Graph; candidates remain unpublished.</p>
                      <GraphReviewHistoricalRecapProjection projection={reviewSource.projection} />
                    </>
                  )}
                </>
              ) : !reviewLoading && !reviewError ? (
                <p role="status" className="module-muted">Choose an exact saved extraction to read.</p>
              ) : null}
            </section>
          ) : returnableDraft ? (
            <div className="ingestion-prepared-source-notice" role="status">
              <strong>Draft preserved · Session {returnableDraft.draft.recapSession}</strong>
              <p>Return to this draft to continue editing under its original session.</p>
            </div>
          ) : (
            <div className="ingestion-source-grid">
              <div className="ingestion-raw-block">
                <label htmlFor="ingestion-raw-text">
                  Write or paste a recap <RequiredBadge satisfied={rawTextSatisfied} />
                </label>
                <textarea
                  id="ingestion-raw-text"
                  aria-label="Write or paste a recap"
                  ref={rawRecapTextAreaRef}
                  value={rawText}
                  onChange={(event) => {
                    setRawText(event.target.value);
                    setSourceMode("raw");
                  }}
                  rows={18}
                  placeholder="Write or paste a session recap here…"
                />
              </div>
            </div>
          )}

          {managedWorldId?<SessionEvidencePicker key={evidenceTargetKey} worldId={managedWorldId} targetKey={evidenceTargetKey} disabled={primaryOp!==null} onChange={refs=>setSessionSupplements({identity:evidenceTargetKey,refs})}/>:null}
        </section>

        <aside className="ingestion-evidence-pane" aria-label="Ingestion evidence and proof">
          <details ref={evidenceDetailsRef} id="ingestion-evidence-details">
            <summary>Evidence &amp; details</summary>
            <NativeGraphAccessControl onChanged={handleNativeGraphAccessChanged}/>
            {evidenceResult ? <>
              <p>Source and extraction are saved in the database. Candidates require reviewed publication.</p>
              <p>Status: {evidenceResult.status}</p>
              {graphPreview?.extraction_run_id ? <p>Extraction run: <code>{graphPreview.extraction_run_id}</code></p> : null}
              {graphPreview?.blocked_reason ? <p role="alert">{graphPreview.blocked_reason}</p> : null}
              {evidenceResult.errors.length ? <ul>{evidenceRows(evidenceResult.errors)}</ul> : null}
            </> : <p>No extraction result yet. Choose exact saved work or submit a recap.</p>}
          </details>
        </aside>
      </div>
    </div>
  );
}
