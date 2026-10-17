import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { getHistoricalRecapWorldProjection, getRecapArtifacts, postWorldGraphRecapProjection } from "../api/liveApi";
import { postRecapIngest } from "../api/recapIngestApi";
import type {
  NormalizedRecapCandidate,
  RecapArtifactRecord,
  RecapGraphPreviewReport,
  RecapIngestStatus,
  HistoricalRecapWorldProjectionResponse,
  WorldGraphRecapProjection,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../api/types";
import {
  filterNumericRecapArtifactRecords,
  recapArtifactSessionLabel,
  recapSessionNumber,
  sortRecapArtifactRecords,
} from "../planSurface/graphPreview/recapSessionLabels";
import { useOptionalProjection } from "../planSurface/projection/projectionContext";
import { ReviewCampaignPicker } from "../planSurface/ReviewCampaignPicker";
import {
  resolveInitialReviewCampaignId,
  syncReviewCampaignUrl,
} from "../planSurface/sessionCampaignContext";
import { GRAPH_REVIEW_RUNS_CHANGED_EVENT } from "../planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils";
import { GraphReviewHistoricalRecapProjection } from "../planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection";

import { WorldGraphRecapProjectionView } from "../planSurface/graphPreview/WorldGraphRecapProjection";
import { verifyWorldGraphProjectionResponse } from "../worldGraph/verifyWorldGraphProjectionResponse";
import { buildWorldGraphRecapProjectionRequest } from "../worldGraph/worldGraphSurfaceContext";

import { NativeGraphAccessControl } from "../chrome/NativeGraphAccessControl";

interface IngestionModuleProps {
  campaignId: string;
  session: number;
  managedWorldId?: string;
  initialSourceSession?: number;
}

const INGESTION_DRAFT_STORAGE_VERSION = 3;

type IngestionSourceMode = "raw" | "processed";

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

function titleFromArtifact(record: RecapArtifactRecord): string {
  const fileName = record.source_recap_path.split("/").pop()?.replace(/\.md$/i, "") ?? "";
  return fileName.trim();
}

const SESSION_22_CANONICAL_SLUG = "Mireward Road and Lysandro";
const SESSION_22_CANONICAL_TITLE = "Session 22 - Mireward Road and Lysandro";
const GENERIC_RECAP_TAILS = new Set([
  "",
  "ingest",
  "ingestion",
  "raw recap",
  "raw recap ingest",
  "raw recap ingestion",
  "recap",
  "recap ingest",
  "recap ingestion",
  "session recap",
]);

interface IngestionModuleDraft {
  version: number;
  rawText: string;
  recapSession: number;
  slug: string;
  title: string;
  showAdvanced: boolean;
  forceStage: boolean;
  forceRecap: boolean;
  ignoreDiskResume?: boolean;
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

interface CorpusImpactRow {
  key: string;
  relpath: string | null;
  exists: boolean | null;
  size_bytes?: number;
  modified_at?: string;
  record_count?: number;
  preview?: string;
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
  | { status: "building_graph_preview" }
  | { status: "materializing_preview_supergraph" }
  | { status: "preview_supergraph_ready"; result: RecapIngestStatus }
  | { status: "ready_for_planning_activation"; result: RecapIngestStatus }
  | { status: "error"; result?: RecapIngestStatus; message?: string };

function isNonGenericSlugOrTitle(slug: string, title: string): boolean {
  const normalizedSlug = slug.trim().toLowerCase().replace(/:$/, "");
  if (normalizedSlug) {
    return !GENERIC_RECAP_TAILS.has(normalizedSlug);
  }
  const normalizedTitle = title.trim();
  if (!normalizedTitle) {
    return false;
  }
  const match = normalizedTitle.match(/^Session\s+\d+\s*(?:-\s*)?(.+)$/i);
  const tail = (match ? match[1] : normalizedTitle).trim().toLowerCase().replace(/:$/, "");
  return !GENERIC_RECAP_TAILS.has(tail);
}

function inferTitleFromRawText(rawText: string, session: number): string {
  const firstMeaningfulLine = rawText
    .split(/\r?\n/)
    .map((line) => line.trim().replace(/^#+\s*/, ""))
    .find((line) => line.length > 0);
  if (!firstMeaningfulLine) {
    return "";
  }
  if (!isNonGenericSlugOrTitle("", firstMeaningfulLine)) {
    return "";
  }
  return /^Session\s+\d+\s*-/i.test(firstMeaningfulLine)
    ? firstMeaningfulLine
    : `Session ${session} - ${firstMeaningfulLine}`;
}

function hasState(result: RecapIngestStatus | null, state: string): boolean {
  return Boolean(result && result.states.includes(state));
}

function slugFromCanonicalPath(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  const filename = path.split("/").pop() ?? "";
  const withoutKnownSuffix = filename
    .replace(/\.md$/i, "");
  const match = withoutKnownSuffix.match(/^Session\s+\d+\s*-\s*(.+)$/i);
  if (!match) {
    return null;
  }
  const tail = match[1].trim();
  const cleaned = tail
    .replace(/^session[-_\s]*\d+[-_\s]*/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!cleaned) {
    return tail;
  }
  return /[-_]/.test(tail)
    ? cleaned.replace(/\b[a-z]/g, (char) => char.toUpperCase())
    : cleaned;
}

function isStaleSession22Slug(slug: string): boolean {
  const normalized = slug.trim().toLowerCase();
  if (!normalized) {
    return true;
  }
  if (normalized.includes("lysadnro")) {
    return true;
  }
  if (normalized.includes("mireward gate")) {
    return true;
  }
  if (normalized !== SESSION_22_CANONICAL_SLUG.toLowerCase() && normalized.includes("mireward road and lysandro")) {
    return true;
  }
  return false;
}

function canonicalSlugTitleForRecapSession(
  recapSession: number,
  paths?: RecapIngestStatus["paths"],
): { slug: string; title: string } | null {
  if (recapSession === 22) {
    return { slug: SESSION_22_CANONICAL_SLUG, title: SESSION_22_CANONICAL_TITLE };
  }
  const pathKeys = [
    "canonical_recap",
    "normalized_recap",
  ];
  for (const key of pathKeys) {
    const fromPath = slugFromCanonicalPath(paths?.[key] ?? undefined);
    if (fromPath && isNonGenericSlugOrTitle(fromPath, "")) {
      return { slug: fromPath, title: `Session ${recapSession} - ${fromPath}` };
    }
  }
  return null;
}

function sanitizeSlugTitle(
  recapSession: number,
  slug: string,
  title: string,
): { slug: string; title: string } {
  if (recapSession === 22 && (isStaleSession22Slug(slug) || isStaleSession22Slug(title))) {
    return { slug: SESSION_22_CANONICAL_SLUG, title: SESSION_22_CANONICAL_TITLE };
  }
  return { slug, title };
}

function syncSlugTitleFromResult(result: RecapIngestStatus): { slug: string; title: string } | null {
  return canonicalSlugTitleForRecapSession(result.session, result.paths);
}

function draftStorageKey(campaignId: string, session: number): string {
  return `dmb.ingestion.${campaignId}.session.${session}`;
}

function derivePaneStateFromResult(result: RecapIngestStatus): IngestionPaneState {
  if (result.status === "ready_for_planning_activation") {
    return { status: "ready_for_planning_activation", result };
  }
  if (result.status === "error") {
    return {
      status: "error",
      result,
      message: result.errors.length > 0 ? result.errors.join("; ") : "Ingestion error",
    };
  }
  return { status: "idle" };
}

type IngestionStatusBadge = {
  label: string;
  tone: "neutral" | "success" | "warning";
};

function graphPreviewIsBlocked(graphPreview?: RecapGraphPreviewReport): boolean {
  return Boolean(graphPreview?.blocked_reason || graphPreview?.extraction_mode === "llm_blocked");
}

function ingestionStatusBadge(
  paneStatus: IngestionPaneState["status"],
  result: RecapIngestStatus | null,
  graphPreview?: RecapGraphPreviewReport,
): IngestionStatusBadge {
  const processing =
    paneStatus === "running_full_ingest" ||
    paneStatus === "building_graph_preview" ||
    paneStatus === "materializing_preview_supergraph";
  const graphReady =
    graphPreview?.status === "candidate_validation_ready" ||
    graphPreview?.status === "preview_union_store_ready";

  if (paneStatus === "error") {
    return { label: "Failed", tone: "warning" };
  }
  if (processing) {
    return { label: "Processing", tone: "neutral" };
  }
  if (result?.status === "error") {
    return { label: "Failed", tone: "warning" };
  }
  if (
    graphPreview?.status === "source_unverified" ||
    result?.status === "source_unverified" ||
    result?.states.includes("source_unverified")
  ) {
    return { label: "Source unverified", tone: "warning" };
  }
  if (graphPreviewIsBlocked(graphPreview)) {
    return { label: "Blocked", tone: "warning" };
  }
  if (graphReady) {
    return { label: "Graph ready", tone: "success" };
  }
  if (graphPreview) {
    return { label: "Graph incomplete", tone: "warning" };
  }

  const hasProcessedResult =
    result !== null &&
    (result.status !== "initialized" ||
      result.states.some((state) => state !== "ingest_status_inspected"));
  return hasProcessedResult
    ? { label: "Graph unavailable", tone: "warning" }
    : { label: "Not run", tone: "neutral" };
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
    const sanitized = sanitizeSlugTitle(parsed.recapSession, parsed.slug, parsed.title);
    return {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      rawText: parsed.rawText,
      recapSession: parsed.recapSession,
      slug: sanitized.slug,
      title: sanitized.title,
      showAdvanced: Boolean(parsed.showAdvanced),
      forceStage: Boolean(parsed.forceStage),
      forceRecap: Boolean(parsed.forceRecap),
      ignoreDiskResume: Boolean(parsed.ignoreDiskResume),
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

function pathLabel(key: string): string {
  return key.replace(/_/g, " ");
}

function normalizedRecapCandidates(result: RecapIngestStatus | null): NormalizedRecapCandidate[] {
  const raw = result?.ingest_report?.normalized_recap_candidates;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((row): row is Record<string, unknown> => typeof row === "object" && row !== null)
    .map((row) => ({
      basename: String(row.basename ?? ""),
      relpath: String(row.relpath ?? ""),
      size_bytes: Number(row.size_bytes ?? 0),
      modified_at: String(row.modified_at ?? ""),
      is_generic: Boolean(row.is_generic),
      recommended: Boolean(row.recommended),
    }))
    .filter((row) => row.basename.length > 0);
}

function corpusImpactRows(result: RecapIngestStatus | null): CorpusImpactRow[] {
  const raw = result?.ingest_report?.corpus_impact;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((row): row is Record<string, unknown> => typeof row === "object" && row !== null)
    .filter(
      (row) =>
        typeof row.key === "string" &&
        row.key.trim().length > 0 &&
        typeof row.relpath === "string" &&
        row.relpath.trim().length > 0,
    )
    .map((row) => ({
      key: (row.key as string).trim(),
      relpath: row.relpath as string,
      exists: typeof row.exists === "boolean" ? row.exists : null,
      size_bytes: typeof row.size_bytes === "number" ? row.size_bytes : undefined,
      modified_at: typeof row.modified_at === "string" ? row.modified_at : undefined,
      record_count: typeof row.record_count === "number" ? row.record_count : undefined,
      preview: typeof row.preview === "string" ? row.preview : undefined,
    }));
}

function recapSourceProof(result: RecapIngestStatus | null): {
  confirmed: boolean;
  missing: boolean;
  hasProofRows: boolean;
  actionStateConfirmed: boolean;
  normalizedCurrent: boolean;
} {
  const sourceRows = corpusImpactRows(result).filter(
    (row) => row.key === "canonical_recap" || row.key === "normalized_recap",
  );
  const canonical = sourceRows.filter((row) => row.key === "canonical_recap");
  const normalized = sourceRows.filter((row) => row.key === "normalized_recap");
  return {
    confirmed:
      canonical.length === 1 &&
      canonical[0].exists === true &&
      normalized.length === 1 &&
      normalized[0].exists === true,
    missing: sourceRows.some((row) => row.exists === false),
    hasProofRows: sourceRows.length > 0,
    actionStateConfirmed: Boolean(
      result &&
        (result.states.includes("recap_reused") || result.states.includes("recap_applied")) &&
        (result.states.includes("normalized_reused") || result.states.includes("normalized_created")),
    ),
    normalizedCurrent: Boolean(
      result?.states.includes("normalized_current") &&
        !result.states.includes("normalized_stale") &&
        !result.states.includes("normalized_provenance_unknown"),
    ),
  };
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
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

function proofPathKeys(result: RecapIngestStatus | null): string[] {
  const preferred = ["canonical_recap", "normalized_recap"];
  if (!result) return preferred;
  const extra = Object.keys(result.paths).filter((key) => !preferred.includes(key));
  return [...preferred, ...extra];
}

function buildToastForResult(
  result: RecapIngestStatus | null,
  {
    fallbackErrorMessage,
    allowInspectResume,
  }: {
    fallbackErrorMessage?: string;
    allowInspectResume?: boolean;
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

  if (!allowInspectResume && result.states.includes("ingest_status_inspected") && result.errors.length === 0) return null;
  const graphPreview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const graphReady = graphPreview?.status === "candidate_validation_ready" || graphPreview?.status === "preview_union_store_ready";
  const graphBlocked = graphPreviewIsBlocked(graphPreview);
  const stagedConflict = result.states.includes("staged_raw_notes_conflict");
  if (stagedConflict) {
    return {
      tone: "warning",
      title: "Saved recap needs your attention",
      detail: "Different source text is already saved for this session, so nothing was processed. Open Evidence & details → Advanced file controls to replace it, then choose Process again.",
      nextSteps: [],
      sticky: true,
    };
  }
  if (result.status === "error" || result.errors.length > 0) {
    return {
      tone: "error",
      title: "Processing failed",
      detail: result.errors.join("; ") || result.warnings.join("; ") || `The server returned ${result.status}.`,
      nextSteps: ["Open Evidence & details for the source and graph error."],
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
  if (result.status === "needs_reconciliation") {
    return {
      tone: "warning",
      title: "Source needs attention",
      detail: result.warnings.join("; ") || "Resolve the source issue before building graph context.",
      nextSteps: [],
      sticky: true,
    };
  }
  return null;
}

export function IngestionModule({ campaignId: planCampaignId, session, managedWorldId, initialSourceSession }: IngestionModuleProps) {
  const projection = useOptionalProjection();
  const [freshRecapEntry] = useState(isFreshRecapEntryRoute);
  const [ingestCampaignId, setIngestCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(planCampaignId),
  );
  const storageKey = useMemo(
    () => draftStorageKey(ingestCampaignId, session),
    [ingestCampaignId, session],
  );
  const [requestedRecapSession] = useState(requestedRecapSessionFromLocation);
  const initialRecapSession = requestedRecapSession ?? (freshRecapEntry ? 0 : initialSourceSession ?? defaultRecapSession(session));
  const [rawText, setRawText] = useState("");
  const rawRecapTextAreaRef = useRef<HTMLTextAreaElement | null>(null);
  const [recapSession, setRecapSession] = useState<number>(() => initialRecapSession);
  const selectedIngestTarget = JSON.stringify([ingestCampaignId, recapSession]);
  const selectedIngestTargetRef = useRef(selectedIngestTarget);
  selectedIngestTargetRef.current = selectedIngestTarget;
  const ingestCampaignIdRef = useRef(ingestCampaignId);
  ingestCampaignIdRef.current = ingestCampaignId;
  const recapSessionRef = useRef(recapSession);
  recapSessionRef.current = recapSession;
  const recapDraftEpochRef = useRef(0);
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [reviewSource, setReviewSource] = useState<{ identity: string; session: number; nodes: number; edges: number; projection: WorldGraphRecapProjection | HistoricalRecapWorldProjectionResponse | null; runId?: string } | null>(null);
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
  const [forceStage, setForceStage] = useState(false);
  const [forceRecap, setForceRecap] = useState(false);
  const [forceGraphRun, setForceGraphRun] = useState(false);
  /** Which primary action is in flight — drives spinner / status copy. */
  const [primaryOp, setPrimaryOp] = useState<"process" | null>(null);
  const [candidateGraphPath, setCandidateGraphPath] = useState("");
  const [extractGraphWithModel, setExtractGraphWithModel] = useState(false);
  const [state, setState] = useState<IngestionPaneState>({ status: "idle" });
  const [latestResult, setLatestResult] = useState<RecapIngestStatus | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [toast, setToast] = useState<IngestionToast | null>(null);
  const [reconcileChoice, setReconcileChoice] = useState<string | null>(null);
  const [reconciling, setReconciling] = useState(false);
  const [sourceMode, setSourceMode] = useState<IngestionSourceMode>("raw");
  const [loadedArtifact, setLoadedArtifact] = useState<RecapArtifactRecord | null>(null);
  const [returnableDraft, setReturnableDraft] = useState<ReturnableIngestionDraft | null>(null);
  const [priorIngestionArtifacts, setPriorIngestionArtifacts] = useState<RecapArtifactRecord[]>([]);
  const [selectedPriorArtifactId, setSelectedPriorArtifactId] = useState("");
  const [loadingPriorIngestion, setLoadingPriorIngestion] = useState(false);
  const [priorSourceReadFailed, setPriorSourceReadFailed] = useState(false);
  const [ignoreDiskResume, setIgnoreDiskResume] = useState(false);
  const inspectedTargetRef = useRef("");
  const lastToastKeyRef = useRef<string | null>(null);
  /** When set, the result→toast effect leaves the Process result's message in charge. */
  const suppressResultToastRef = useRef(false);
  const hydrateInspectGenerationRef = useRef(0);
  const validRecapSession = Number.isInteger(recapSession) && recapSession > 0;

  function handleIngestCampaignSelect(nextCampaignId: string) {
    if (nextCampaignId === ingestCampaignId) return;
    invalidateInFlightRecapOperations();
    selectedIngestTargetRef.current = JSON.stringify([nextCampaignId, recapSession]);
    ingestCampaignIdRef.current = nextCampaignId;
    invalidateInFlightHydrateInspect();
    setIngestCampaignId(nextCampaignId);
    syncReviewCampaignUrl(nextCampaignId);
    setHydrated(false);
    setIgnoreDiskResume(false);
    setLatestResult(null);
    setState({ status: "idle" });
    setSourceMode("raw");
    setLoadedArtifact(null);
    setSelectedPriorArtifactId("");
    setPriorIngestionArtifacts([]);
    setPriorSourceReadFailed(false);
    setPrimaryOp(null);
    setLoadingPriorIngestion(false);
    setReconciling(false);
    setToast(null);
    lastToastKeyRef.current = null;
    inspectedTargetRef.current = "";
    window.dispatchEvent(new Event(GRAPH_REVIEW_RUNS_CHANGED_EVENT));
  }

  function handleRecapSessionChange(nextSession: number) {
    if (nextSession === recapSession) return;
    invalidateInFlightRecapOperations();
    selectedIngestTargetRef.current = JSON.stringify([ingestCampaignId, nextSession]);
    recapSessionRef.current = nextSession;
    invalidateInFlightHydrateInspect();
    setRecapSession(nextSession);
    setLatestResult(null);
    setState({ status: "idle" });
    setSourceMode("raw");
    setLoadedArtifact(null);
    const targetSessionId = nextSession > 0 ? `session-${nextSession}` : "";
    const exactTarget = priorIngestionArtifacts.find(
      (record) => record.campaign_id === ingestCampaignId && record.session_id === targetSessionId,
    );
    setSelectedPriorArtifactId(exactTarget?.artifact_id || "");
    setPriorSourceReadFailed(false);
    setIgnoreDiskResume(false);
    setPrimaryOp(null);
    setLoadingPriorIngestion(false);
    setReconciling(false);
    setToast(null);
    lastToastKeyRef.current = null;
    inspectedTargetRef.current = "";
  }

  function invalidateInFlightHydrateInspect() {
    hydrateInspectGenerationRef.current += 1;
    // The operator's newer action now owns this draft; do not keep it behind
    // the stale disk-inspection request's hydration gate.
    setHydrated(true);
  }

  function invalidateInFlightRecapOperations() {
    recapDraftEpochRef.current += 1;
  }

  async function postForSelectedIngestTarget(
    request: Parameters<typeof postRecapIngest>[0],
    targetIdentity: string,
  ): Promise<RecapIngestStatus | null> {
    const draftEpoch = recapDraftEpochRef.current;
    let result: RecapIngestStatus;
    try {
      result = await postRecapIngest(request);
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

  async function inspectSelectedRecapStatus(
    campaignId = ingestCampaignId,
    sessionNumber = recapSession,
  ) {
    if (!Number.isInteger(sessionNumber) || sessionNumber <= 0 || ignoreDiskResume) return;
    const identity = JSON.stringify([campaignId, sessionNumber]);
    if (inspectedTargetRef.current === identity) return;
    const inspectGeneration = ++hydrateInspectGenerationRef.current;
    setToast(null);
    try {
      const inspected = await postRecapIngest({
        operation: "inspect_status",
        campaign_id: campaignId,
        session: sessionNumber,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
      });
      if (
        inspectGeneration !== hydrateInspectGenerationRef.current ||
        selectedIngestTargetRef.current !== identity ||
        inspected.campaign_id !== campaignId ||
        inspected.session !== sessionNumber
      ) return;
      setLatestResult(inspected);
      inspectedTargetRef.current = identity;
      const synced = syncSlugTitleFromResult(inspected);
      if (synced) {
        setSlug(synced.slug);
        setTitle(synced.title);
      }
      setState(derivePaneStateFromResult(inspected));
    } catch {
      if (
        inspectGeneration === hydrateInspectGenerationRef.current &&
        selectedIngestTargetRef.current === identity
      ) {
        setLatestResult(null);
        setState({ status: "idle" });
        setToast({
          tone: "warning",
          title: "Could not verify saved ingest status",
          detail: "The current recap files could not be checked. This browser's saved status may be out of date.",
          nextSteps: ["Refresh the page to check the saved files again before continuing."],
          sticky: true,
        });
      }
    } finally {
      if (
        inspectGeneration === hydrateInspectGenerationRef.current &&
        selectedIngestTargetRef.current === identity
      ) setHydrated(true);
    }
  }

  const inferredTitle = useMemo(
    () => inferTitleFromRawText(rawText, recapSession),
    [rawText, recapSession],
  );
  const effectiveTitle = title.trim() || inferredTitle;
  const slugOverrideIsSpecific = slug.trim().length > 0 && isNonGenericSlugOrTitle(slug, "");
  const ignoredFileNameOverride = showAdvanced && slug.trim().length > 0 && !slugOverrideIsSpecific;
  const effectiveSlug = showAdvanced && slugOverrideIsSpecific ? slug.trim() : "";
  const rawTextSatisfied = rawText.trim().length > 0;
  const matchingResult =
    latestResult?.campaign_id === ingestCampaignId && latestResult.session === recapSession
      ? latestResult
      : null;
  const resultOwnsSelection =
    hydrated &&
    matchingResult !== null;
  // Saved-file proof requires a status result for the current selection.
  const proofResult = resultOwnsSelection ? matchingResult : null;
  const busy = [
    "running_full_ingest",
    "building_graph_preview",
    "materializing_preview_supergraph",
  ].includes(state.status);
  const genericGuardPass = isNonGenericSlugOrTitle(effectiveSlug, effectiveTitle);
  const hasApplied =
    hasState(matchingResult, "recap_applied") ||
    hasState(matchingResult, "recap_reused") ||
    hasState(matchingResult, "normalized_created") ||
    hasState(matchingResult, "normalized_reused");
  const recapSourceNavigationProof = recapSourceProof(proofResult);
  const hasCurrentNormalizedSource =
    resultOwnsSelection &&
    hasApplied &&
    recapSourceNavigationProof.confirmed &&
    recapSourceNavigationProof.normalizedCurrent;
  const processedSourceReady =
    sourceMode === "processed" &&
    loadedArtifact !== null &&
    hasCurrentNormalizedSource;
  const sourceInputSatisfied =
    rawTextSatisfied ||
    processedSourceReady ||
    hasCurrentNormalizedSource;
  const isRunningFullIngest = state.status === "running_full_ingest";
  const isBuildingGraphPreview = state.status === "building_graph_preview";
  const isMaterializingPreviewSupergraph = state.status === "materializing_preview_supergraph";
  const graphPreview = proofResult?.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const statusBadge = ingestionStatusBadge(state.status, proofResult, graphPreview);
  const selectedReaderRun = readerRun?.campaign === ingestCampaignId && readerRun.session === `session-${recapSession}` ? readerRun.runId : null;
  const reviewIdentity = JSON.stringify([
    managedWorldId ?? null,
    ingestCampaignId,
    recapSession,
    selectedReaderRun ?? (resultOwnsSelection ? graphPreview?.extraction_run_id : null) ?? null,
  ]);
  useLayoutEffect(() => {
    currentReviewIdentity.current = reviewIdentity;
    reviewEpoch.current += 1;
    readerAttempt.current = null;
    setReviewSource(null);
    setReviewError(null);
    setReviewLoading(false);
    return () => { reviewEpoch.current += 1; };
  }, [reviewIdentity]);
  useEffect(() => {
    if (!readerMode || !hydrated || loadingPriorIngestion || readerAttempt.current === reviewIdentity) return;
    if (!resultOwnsSelection && !priorIngestionArtifacts.some((item) => item.campaign_id === ingestCampaignId && item.session_id === `session-${recapSession}`)) return;
    const restore = restoreReaderRoute.current;
    restoreReaderRoute.current = false;
    readerAttempt.current = reviewIdentity;
    void reviewSavedSource(restore, true);
  }, [readerMode, hydrated, loadingPriorIngestion, reviewIdentity, latestResult?.session, latestResult?.campaign_id, priorIngestionArtifacts]);
  // Trust live graph_preview.status only — draft states must not claim materialized.
  const hasPreviewUnionStore = graphPreview?.status === "preview_union_store_ready";
  const hasNormalizedRecap = hasApplied;
  const sourcePresentButUnverified =
    sourceMode === "raw" &&
    !rawTextSatisfied &&
    hasNormalizedRecap &&
    !hasCurrentNormalizedSource;
  const showPreparedSourceNotice =
    sourceMode === "raw" &&
    !rawTextSatisfied &&
    hasNormalizedRecap &&
    hasCurrentNormalizedSource &&
    recapSession > 0 &&
    !priorSourceReadFailed;
  const hasLoadedRecapContent =
    sourceMode !== "raw" ||
    loadedArtifact !== null ||
    Boolean(rawText.trim()) ||
    (resultOwnsSelection && hasCurrentNormalizedSource);
  useEffect(() => {
    if (!hydrated || loadingPriorIngestion || rawTextSatisfied || !hasCurrentNormalizedSource || readerMode) return;
    restoreReaderRoute.current = false;
    setReaderMode(true);
  }, [hydrated, loadingPriorIngestion, rawTextSatisfied, hasCurrentNormalizedSource, readerMode]);
  const showRecapWelcome =
    hydrated &&
    !readerMode &&
    !returnableDraft &&
    !hasLoadedRecapContent &&
    !busy &&
    state.status !== "error" &&
    !matchingResult?.errors?.length;
  const hasPriorIngestWork = Boolean(
    resultOwnsSelection && matchingResult?.states.some((item) => item !== "ingest_status_inspected"),
  );
  const canBuildGraphPreview = hasCurrentNormalizedSource && !busy && (!hasPreviewUnionStore || forceGraphRun);
  const canMaterializePreviewSupergraph = hasCurrentNormalizedSource && !busy && (!hasPreviewUnionStore || forceGraphRun) && Boolean(
    extractGraphWithModel ||
    candidateGraphPath.trim() ||
    graphPreview?.candidate_graph_path ||
    graphPreview?.status === "candidate_validation_ready",
  );
  const workflowNextAction = (() => {
    if (state.status === "running_full_ingest") {
      return "Processing recap and building World Graph context.";
    }
    if (state.status === "building_graph_preview") return "Working: building the graph source-span preview bundle.";
    if (state.status === "materializing_preview_supergraph") return "Working: materializing the preview union supergraph.";
    if (readerMode) {
      if (reviewLoading) return `Opening saved recap · Session ${recapSession}…`;
      if (reviewError) return "Saved recap could not be opened. See the message on the recap surface.";
      if (reviewSource?.projection) return `Viewing saved recap · Session ${reviewSource.session}.`;
      return `Opening saved recap · Session ${recapSession}…`;
    }
    if (rawTextSatisfied && hasCurrentNormalizedSource) {
      return `Unsaved draft open · Session ${recapSession}. The saved recap is available to read.`;
    }
    if (!sourceInputSatisfied && !hasNormalizedRecap) {
      return "Write or paste a recap, then choose Process.";
    }
    if (!validRecapSession) return "Choose a session number before processing.";
    if (!genericGuardPass) return "Add a specific session title before processing.";
    if (hasPreviewUnionStore && forceGraphRun) {
      return "Ready to replace the existing graph. Choose Process to refresh it.";
    }
    if (hasPreviewUnionStore) {
      return "Graph exists · choose Replace graph to run a fresh extraction.";
    }
    if (sourcePresentButUnverified) {
      return recapSourceNavigationProof.missing
        ? "Recap files are reported missing. Inspect Evidence or load/paste the source to continue."
        : recapSourceNavigationProof.confirmed && !recapSourceNavigationProof.normalizedCurrent
          ? "The normalized recap is stale or its source lineage is unverified. Inspect Evidence or load the source to continue."
          : "Recap file presence is unverified. Inspect Evidence or load the recap to continue.";
    }
    if (graphPreview?.status === "candidate_validation_ready") return "Graph candidate ready for review; World admission is a separate step.";
    return "Choose Process to build the enriched recap and graph context.";
  })();
  const graphDisabledReason = !hasNormalizedRecap
    ? "Build Graph Preview waits for a processed recap."
    : !hasCurrentNormalizedSource
      ? "Build Graph Preview waits for confirmed recap files and current normalized lineage."
      : null;
  const previewUnionSizeHint =
    typeof graphPreview?.node_count === "number"
      ? ` (${graphPreview.node_count} nodes${
          typeof graphPreview.edge_count === "number" ? `, ${graphPreview.edge_count} edges` : ""
        })`
      : "";
  const previewSupergraphDisabledReason = hasPreviewUnionStore && !forceGraphRun
    ? `Preview union on disk${previewUnionSizeHint}. Choose Replace graph before processing again.`
    : !hasNormalizedRecap
      ? "Materialize Preview Supergraph waits for a normalized recap."
      : !hasCurrentNormalizedSource
        ? "Materialize Preview Supergraph waits for confirmed recap files and current normalized lineage."
      : !canMaterializePreviewSupergraph
        ? "Choose a candidate graph source or Process the recap before materializing a preview."
        : null;
  // One visible Process action accepts composer text or verified saved source.
  const canProcessRecap =
    !busy &&
    validRecapSession &&
    sourceInputSatisfied &&
    (!hasPreviewUnionStore || forceGraphRun) &&
    genericGuardPass;
  useEffect(() => {
    let cancelled = false;

    async function hydrateFromStorageAndDisk() {
      const inspectGeneration = hydrateInspectGenerationRef.current;
      const draft = readDraft(storageKey);
      const routeDraft =
        requestedRecapSession != null &&
        draft?.recapSession !== requestedRecapSession &&
        Boolean(draft?.rawText.trim())
          ? { storageKey, campaignId: ingestCampaignId, draft: draft! }
          : null;
      setReturnableDraft(routeDraft);
      const usableDraft =
        requestedRecapSession != null && draft?.recapSession !== requestedRecapSession
          ? null
          : draft;
      const defaultRecap = requestedRecapSession ?? usableDraft?.recapSession ?? (freshRecapEntry ? 0 : initialSourceSession ?? defaultRecapSession(session));
      const restoredSlug = usableDraft?.slug ?? canonicalSlugTitleForRecapSession(defaultRecap)?.slug ?? "";
      const initialSlug =
        usableDraft?.showAdvanced && isNonGenericSlugOrTitle(restoredSlug, "") ? restoredSlug : "";
      const initialTitle = usableDraft?.title ?? canonicalSlugTitleForRecapSession(defaultRecap)?.title ?? "";

      const restoredIgnoreDiskResume = Boolean(usableDraft?.ignoreDiskResume);

      if (!usableDraft) {
        setRawText("");
        setRecapSession(defaultRecap);
        setSlug(initialSlug);
        setTitle(initialTitle);
        setShowAdvanced(false);
        setForceStage(false);
        setForceRecap(false);
        setState({ status: "idle" });
        setLatestResult(null);
        setIgnoreDiskResume(false);
      } else {
        setRawText(usableDraft.rawText);
        setRecapSession(usableDraft.recapSession);
        setSlug(usableDraft.slug);
        setTitle(usableDraft.title);
        setShowAdvanced(usableDraft.showAdvanced);
        setForceStage(usableDraft.forceStage);
        setForceRecap(usableDraft.forceRecap);
        setState({ status: "idle" });
        setLatestResult(null);
        setIgnoreDiskResume(restoredIgnoreDiskResume);
      }

      if (!freshRecapEntry || usableDraft) {
        try {
          const inspected = await postRecapIngest({
            operation: "inspect_status",
            campaign_id: ingestCampaignId,
            session: defaultRecap,
            slug: initialSlug.trim() || undefined,
            title: initialTitle.trim() || undefined,
          });
          if (cancelled || inspectGeneration !== hydrateInspectGenerationRef.current) {
            return;
          }
          if (!restoredIgnoreDiskResume) {
            const currentResult = inspected;
            setLatestResult(currentResult);
            if (inspected.campaign_id === ingestCampaignId && inspected.session === defaultRecap) {
              inspectedTargetRef.current = JSON.stringify([ingestCampaignId, defaultRecap]);
            }
            const synced = currentResult.session === recapSession ? syncSlugTitleFromResult(currentResult) : null;
            if (synced) {
              setSlug(synced.slug);
              setTitle(synced.title);
            }
            setState((prev) => {
              if (prev.status === "running_full_ingest") {
                return prev;
              }
              return derivePaneStateFromResult(currentResult);
            });
          }
        } catch {
          if (
            !cancelled &&
            inspectGeneration === hydrateInspectGenerationRef.current &&
            usableDraft &&
            !restoredIgnoreDiskResume
          ) {
            setLatestResult(null);
            setState({ status: "idle" });
            setToast({
              tone: "warning",
              title: "Could not verify saved ingest status",
              detail: "The current recap files could not be checked. This browser's saved status may be out of date.",
              nextSteps: ["Refresh the page to check the saved files again before continuing."],
              sticky: true,
            });
          }
        }
      }

      if (!cancelled && inspectGeneration === hydrateInspectGenerationRef.current) {
        setHydrated(true);
      }
    }

    setHydrated(false);
    setToast(null);
    lastToastKeyRef.current = null;
    void hydrateFromStorageAndDisk();

    return () => {
      cancelled = true;
    };
  }, [storageKey, session, ingestCampaignId, requestedRecapSession, initialSourceSession, freshRecapEntry]);

  useEffect(() => {
    if (!hydrated || recapSession !== 22) {
      return;
    }
    if (isStaleSession22Slug(slug) || isStaleSession22Slug(title)) {
      setSlug(SESSION_22_CANONICAL_SLUG);
      setTitle(SESSION_22_CANONICAL_TITLE);
    }
  }, [hydrated, recapSession, slug, title]);

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    void getRecapArtifacts(ingestCampaignId)
      .then((response) => {
        if (cancelled || ingestCampaignIdRef.current !== ingestCampaignId) return;
        const records = sortRecapArtifactRecords(
          filterNumericRecapArtifactRecords(response.records).filter(
            (record) => record.campaign_id === ingestCampaignId,
          ),
        );
        setPriorIngestionArtifacts(records);
        const currentSession = recapSessionRef.current;
        const targetSessionId = currentSession > 0 ? `session-${currentSession}` : "";
        const exactTarget = records.find(
          (record) => record.campaign_id === ingestCampaignId && record.session_id === targetSessionId,
        );
        setSelectedPriorArtifactId((current) => current || exactTarget?.artifact_id || "");
      })
      .catch(() => {
        if (!cancelled && ingestCampaignIdRef.current === ingestCampaignId) {
          setPriorIngestionArtifacts([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [ingestCampaignId, hydrated]);

  useEffect(() => {
    if (!hydrated || loadingPriorIngestion || readerMode || returnableDraft) {
      return;
    }
    writeDraft(storageKey, {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      rawText,
      recapSession,
      slug,
      title,
      showAdvanced,
      forceStage,
      forceRecap,
      ignoreDiskResume,
    });
  }, [
    hydrated,
    loadingPriorIngestion,
    readerMode,
    returnableDraft,
    storageKey,
    rawText,
    recapSession,
    slug,
    title,
    showAdvanced,
    forceStage,
    forceRecap,
    ignoreDiskResume,
  ]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    const maybeToast = buildToastForResult(latestResult, {
      fallbackErrorMessage: state.status === "error" ? state.message : undefined,
      allowInspectResume: false,
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
  }, [hydrated, latestResult, state]);

  useEffect(() => {
    if (!toast || toast.sticky) {
      return;
    }
    const timeout = window.setTimeout(() => setToast(null), 9000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function closeSavedReader() {
    reviewEpoch.current += 1;
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
    hydrateInspectGenerationRef.current += 1;
    closeSavedReader();
    setLoadingPriorIngestion(false);
    const { draft, campaignId } = candidate;
    setIngestCampaignId(campaignId);
    selectedIngestTargetRef.current = JSON.stringify([campaignId, draft.recapSession]);
    inspectedTargetRef.current = "";
    setRecapSession(draft.recapSession);
    setRawText(draft.rawText);
    setSlug(draft.slug);
    setTitle(draft.title);
    setShowAdvanced(draft.showAdvanced);
    setForceStage(draft.forceStage);
    setForceRecap(draft.forceRecap);
    setIgnoreDiskResume(Boolean(draft.ignoreDiskResume));
    setSourceMode("raw");
    setLoadedArtifact(null);
    setLatestResult(null);
    setState({ status: "idle" });
    setToast(null);
    setReturnableDraft(null);
    setHydrated(true);

    const params = new URLSearchParams(window.location.search);
    params.set("campaign", campaignId);
    params.set("session", `session-${draft.recapSession}`);
    params.delete("view");
    params.delete("recapReviewRunId");
    window.history.replaceState({}, "", `${ingestRoutePath()}?${params.toString()}`);
  }

  function resetIngestionDraft() {
    invalidateInFlightRecapOperations();
    hydrateInspectGenerationRef.current += 1;
    closeSavedReader();
    lastToastKeyRef.current = null;
    window.localStorage.removeItem(storageKey);
    setRawText("");
    setSlug("");
    setTitle("");
    setShowAdvanced(false);
    setForceStage(false);
    setForceRecap(false);
    setForceGraphRun(false);
    setSourceMode("raw");
    setPriorSourceReadFailed(false);
    setLoadedArtifact(null);
    setReturnableDraft(null);
    setSelectedPriorArtifactId("");
    setToast(null);
    setState({ status: "idle" });
    setLatestResult(null);
    setPrimaryOp(null);
    setReconciling(false);
    setLoadingPriorIngestion(false);
  }

  function startNewRecap() {
    setIgnoreDiskResume(true);
    resetIngestionDraft();
  }

  function applyResultAndSyncSlug(result: RecapIngestStatus) {
    setLatestResult(result);
    const synced = result.session === recapSession ? syncSlugTitleFromResult(result) : null;
    if (synced) {
      setSlug(synced.slug);
      setTitle(synced.title);
    }
  }

  function applyAutomatedResult(result: RecapIngestStatus): RecapIngestStatus {
    setLatestResult(result);
    const synced = syncSlugTitleFromResult(result);
    if (synced) {
      setSlug(synced.slug);
      setTitle(synced.title);
    }
    return result;
  }

  function resultErrorMessage(result: RecapIngestStatus, fallback: string): string {
    return result.errors.length > 0 ? result.errors.join("; ") : fallback;
  }

  async function loadPriorIngestion(record: RecapArtifactRecord) {
    const sessionNumber = recapSessionNumber(record.session_id);
    if (sessionNumber == null || sessionNumber <= 0) {
      setPriorSourceReadFailed(true);
      setToast({
        tone: "error",
        title: "Could not load ingestion",
        detail: "Selected artifact has no numeric session id.",
        nextSteps: [],
        sticky: true,
      });
      return;
    }

    const targetIdentity = JSON.stringify([record.campaign_id, sessionNumber]);
    if (rawText.trim()) {
      const draft = {
        version: INGESTION_DRAFT_STORAGE_VERSION,
        rawText,
        recapSession,
        slug,
        title,
        showAdvanced,
        forceStage,
        forceRecap,
        ignoreDiskResume,
      } satisfies IngestionModuleDraft;
      writeDraft(storageKey, draft);
      setReturnableDraft({ storageKey, campaignId: ingestCampaignId, draft });
    }
    invalidateInFlightRecapOperations();
    selectedIngestTargetRef.current = targetIdentity;
    invalidateInFlightHydrateInspect();
    const requestGeneration = hydrateInspectGenerationRef.current;
    setLoadingPriorIngestion(true);
    setPriorSourceReadFailed(false);
    setSourceMode("processed");
    setLoadedArtifact(record);
    setRawText("");
    setRecapSession(sessionNumber);
    setLatestResult(null);
    setState({ status: "idle" });
    inspectedTargetRef.current = "";
    setTitle(titleFromArtifact(record));
    setSlug("");
    lastToastKeyRef.current = null;

    try {
      const inspected = await postRecapIngest({
        operation: "inspect_status",
        campaign_id: record.campaign_id,
        session: sessionNumber,
        title: titleFromArtifact(record) || undefined,
      });
      if (
        requestGeneration !== hydrateInspectGenerationRef.current ||
        selectedIngestTargetRef.current !== targetIdentity ||
        inspected.campaign_id !== record.campaign_id ||
        inspected.session !== sessionNumber
      ) return;
      applyResultAndSyncSlug(inspected);
      inspectedTargetRef.current = targetIdentity;
      setState(derivePaneStateFromResult(inspected));

      const route = new URLSearchParams(window.location.search);
      route.set("campaign", record.campaign_id);
      route.set("session", record.session_id);
      route.set("view", "recap");
      route.delete("recapReviewRunId");
      window.history.replaceState({}, "", `${ingestRoutePath()}?${route.toString()}`);
      setIgnoreDiskResume(false);
      readerAttempt.current = null;
      restoreReaderRoute.current = false;
      setReaderMode(true);
      setToast({
        tone: "info",
        title: "Loaded processed recap",
        detail: `Reading the saved recap for Session ${sessionNumber}.`,
        nextSteps: [],
      });
    } catch (error) {
      if (
        requestGeneration !== hydrateInspectGenerationRef.current ||
        selectedIngestTargetRef.current !== targetIdentity
      ) return;
      closeSavedReader();
      setSourceMode("raw");
      setLoadedArtifact(null);
        setPriorSourceReadFailed(true);
      setToast({
        tone: "error",
        title: "Could not load prior ingestion",
        detail: error instanceof Error ? error.message : "Load failed",
        nextSteps: [],
        sticky: true,
      });
    } finally {
      if (
        requestGeneration === hydrateInspectGenerationRef.current &&
        selectedIngestTargetRef.current === targetIdentity
      ) setLoadingPriorIngestion(false);
    }
  }

  async function loadSelectedPriorIngestion() {
    const record = priorIngestionArtifacts.find((row) => row.artifact_id === selectedPriorArtifactId);
    if (!record) {
      setToast({
        tone: "warning",
        title: "Select a prior ingestion",
        detail: "Choose a session from the dropdown first.",
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
    invalidateInFlightHydrateInspect();
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
          slug: effectiveSlug || undefined,
          title: effectiveTitle || undefined,
          force_stage: forceStage || undefined,
          force_recap: forceRecap || undefined,
          include_graph_extraction: true,
          graph_model_id: "deepseek/deepseek-v4.1-flash",
          force_graph_run: forceGraphRun || undefined,
        }, targetIdentity);
      if (!response) return;
      const result = applyAutomatedResult(response);

      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Ingest failed") });
        return;
      }

      if (result.states.includes("staged_raw_notes_conflict") && !forceStage) {
        setState({ status: "idle" });
        publishPrimaryToast({
          tone: "warning",
          title: "Saved recap needs your attention",
          detail: "Different source text is already saved for this session. Nothing was processed. Replace the saved source in Advanced, then try Process again.",
          nextSteps: [],
          sticky: true,
        });
        return;
      }

      if (
        result.status === "needs_reconciliation" ||
        result.states.some((state) =>
          ["canonical_recap_conflict", "normalized_stale", "normalized_provenance_unknown"].includes(state),
        )
      ) {
        // Do not switch to the reader or clear the composer until the source
        // chain is durably current. The operator needs the draft to resolve it.
        setState(derivePaneStateFromResult(result));
        publishPrimaryToast({
          tone: "warning",
          title: "Source needs attention",
          detail: result.warnings.join("; ") || "The saved source is not current, so this draft remains in the editor.",
          nextSteps: ["Resolve the source conflict, then Process again."],
          sticky: true,
        });
        return;
      }

      setSourceMode("processed");
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
          detail: "The graph-enriched recap is ready. Candidate facts still need Graph Review before admission.",
          nextSteps: ["Review graph candidate"],
          sticky: true,
        });
        return;
      }

      if (result.status === "ready_for_planning_activation" || result.ingest_report?.graph_preview) {
        const preview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
        const graphBlocked = graphPreviewIsBlocked(preview);
        const graphMaterialized = preview?.status === "preview_union_store_ready";
        const resultError = result.errors[0]?.trim() || "";
        const blockedReason = preview?.blocked_reason?.trim() || "";
        const ok = graphMaterialized && !graphBlocked && !resultError;
        setState({ status: "ready_for_planning_activation", result });
        publishPrimaryToast({
          tone: ok ? "success" : "warning",
          title: ok ? "Recap processed" : "Processing finished with warnings",
          detail: resultError
            ? resultError
            : graphBlocked
              ? `Graph extract was blocked: ${blockedReason || "unknown reason"}`
            : graphMaterialized
              ? forceGraphRun
                ? "The graph preview reflects a fresh extraction from this recap."
                : "The graph preview is ready for Graph Review."
              : "The recap is saved, but the graph projection is not ready yet.",
          nextSteps: ok
            ? ["Review graph candidate"]
            : ["Open Advanced → Evidence for details"],
          sticky: true,
        });
      } else {
        setState(derivePaneStateFromResult(result));
        publishPrimaryToast({
          tone: "warning",
          title: "Processing finished with warnings",
          detail:
            result.errors[0]?.trim() ||
            `The server returned ${result.status}. Open Advanced → Evidence for details.`,
          nextSteps: ["Open Advanced → Evidence for details"],
          sticky: true,
        });
      }
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
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

  async function buildGraphPreview() {
    if (!canBuildGraphPreview) return;
    const targetIdentity = selectedIngestTarget;
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "building_graph_preview" });
    try {
      const result = await postForSelectedIngestTarget({
        operation: "build_graph_preview_bundle",
        campaign_id: ingestCampaignId,
        managed_world_id: managedWorldId,
        session: recapSession,
        candidate_graph_path: extractGraphWithModel ? undefined : candidateGraphPath.trim() || undefined,
        extract_graph: extractGraphWithModel,
        graph_model_id: extractGraphWithModel ? "deepseek/deepseek-v4.1-flash" : undefined,
        force_graph_run: forceGraphRun || undefined,
      }, targetIdentity);
      if (!result) return;
      applyResultAndSyncSlug(result);
      setState(derivePaneStateFromResult(result));
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Graph preview bundle build failed",
      });
    }
  }

  async function materializePreviewSupergraph() {
    if (!canMaterializePreviewSupergraph) return;
    const targetIdentity = selectedIngestTarget;
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "materializing_preview_supergraph" });
    try {
      const result = await postForSelectedIngestTarget({
        operation: "materialize_preview_supergraph",
        campaign_id: ingestCampaignId,
        managed_world_id: managedWorldId,
        session: recapSession,
        candidate_graph_path: extractGraphWithModel ? undefined : candidateGraphPath.trim() || undefined,
        extract_graph: extractGraphWithModel,
        graph_model_id: extractGraphWithModel ? "deepseek/deepseek-v4.1-flash" : undefined,
        materialize_after_extract: extractGraphWithModel,
        force_graph_run: forceGraphRun || undefined,
      }, targetIdentity);
      if (!result) return;
      applyResultAndSyncSlug(result);
      if (result.states.includes("preview_union_store_ready")) {
        setState({ status: "preview_supergraph_ready", result });
      } else {
        setState(derivePaneStateFromResult(result));
      }
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Preview supergraph materialization failed",
      });
    }
  }

  function openGraphPreview() {
    if (typeof window !== "undefined") {
      window.location.assign(`/plan?tool=graph-preview&session=session-${recapSession}`);
    }
  }

  async function reviewSavedSource(restore = false, preserveSelection = false) {
    restoreReaderRoute.current = false;
    const params = new URLSearchParams(window.location.search);
    const sameSelection = params.get("campaign") === ingestCampaignId && params.get("session") === `session-${recapSession}`;
    const currentRun = resultOwnsSelection ? graphPreview?.extraction_run_id : undefined;
    const runId = ((preserveSelection || restore) && selectedReaderRun ? selectedReaderRun : currentRun) ?? undefined;
    if (restore && (!sameSelection || !requestedRecapSessionFromLocation())) {
      setReviewError("Saved recap route has an invalid campaign or session.");
      return;
    }
    if (!preserveSelection && !restore) setReaderRun(runId ? { campaign: ingestCampaignId, session: `session-${recapSession}`, runId } : null);
    params.set("campaign", ingestCampaignId);
    params.set("session", `session-${recapSession}`);
    params.set("view", "recap");
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
    try {
      const record = priorIngestionArtifacts.find((item) => item.campaign_id === ingestCampaignId && item.session_id === `session-${capturedSession}`);
      const path = resultOwnsSelection ? latestResult?.paths?.normalized_recap : null;
      if (!record && !path && !runId) throw new Error("No saved recap is available for this session.");
      setReviewSource({ identity, session: capturedSession, nodes, edges, runId, projection: null });
      if (runId) {
        // A selected extraction run is an exact source identity. Never replace
        // it with the current normalized recap for the same session.
        if (!capturedManagedWorldId) {
          throw new Error("Select a managed World before opening this exact recap projection.");
        }
        const historical = await getHistoricalRecapWorldProjection(runId, capturedManagedWorldId);
        if (!isCurrent()) return;
        if (
          historical.runId !== runId ||
          historical.sourceDomain !== "recap" ||
          historical.campaignId !== ingestCampaignId ||
          historical.sessionId !== `session-${capturedSession}`
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
          !Number.isInteger(historical.bindingVersion) ||
          (historical.bindingVersion ?? 0) < 1
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
      } else {
        const request = buildWorldGraphRecapProjectionRequest({ campaignId: ingestCampaignId, sessionId: `session-${capturedSession}` });
        if (!request) throw new Error("World Graph mapping is unavailable for this recap.");
        const projection = await postWorldGraphRecapProjection(request);
        if (!isCurrent()) return;
        if (projection.campaignId !== ingestCampaignId || projection.sessionId !== `session-${capturedSession}` || projection.snapshot.worldId !== request.worldId) {
          throw new Error("Recap projection does not match the selected World and session.");
        }
        if (!projection.snapshot.revisionId || !projection.snapshot.headRevisionId) throw new Error("Recap projection has no verified revision identity.");
        const integrityError = verifyWorldGraphProjectionResponse({
          request,
          response: projection as unknown as WorldGraphProjection,
          revisionKind: "head",
        });
        if (integrityError) throw new Error(integrityError);
        setReviewSource({ identity, session: capturedSession, nodes, edges, projection });
      }
    } catch (error) {
      if (isCurrent()) setReviewError(error instanceof Error ? error.message : "Unable to open saved source.");
    } finally {
      if (isCurrent()) setReviewLoading(false);
    }
  }

  function openGraphReviewWorkbench() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    params.set("session", `session-${recapSession}`);
    params.set("campaign", ingestCampaignId);
    window.history.replaceState({}, "", `/ingest?${params.toString()}`);
    window.dispatchEvent(new Event(GRAPH_REVIEW_RUNS_CHANGED_EVENT));
    projection?.close();
  }

  async function reconcileNormalizedRecap(keepBasename: string) {
    const targetIdentity = selectedIngestTarget;
    const draftEpoch = recapDraftEpochRef.current;
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setReconciling(true);
    setToast({
      tone: "info",
      title: "Reconciling duplicate recaps",
      detail: `Keeping "${keepBasename}" and archiving the rest, then re-checking on disk.`,
      nextSteps: [],
    });
    try {
      const result = await postForSelectedIngestTarget({
        operation: "reconcile_normalized_recap",
        campaign_id: ingestCampaignId,
        session: recapSession,
        keep_basename: keepBasename,
      }, targetIdentity);
      if (!result) return;
      applyResultAndSyncSlug(result);
      setReconcileChoice(null);
      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Reconcile failed") });
        return;
      }
      setState(derivePaneStateFromResult(result));
      const archivedRows = result.ingest_report?.reconciled_archived;
      const archivedCount = Array.isArray(archivedRows) ? archivedRows.length : 0;
      setToast({
        tone: "success",
        title: "Duplicate recaps reconciled",
        detail: `Kept "${keepBasename}". Archived ${archivedCount} artifact${
          archivedCount === 1 ? "" : "s"
        } under _archive. Exactly one normalized recap remains.`,
        nextSteps: ["Process the recap to rebuild its World Graph context."],
        sticky: true,
      });
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      const message = error instanceof Error ? error.message : "Reconcile failed";
      setState({ status: "error", result: latestResult ?? undefined, message });
      setToast({
        tone: "error",
        title: "Reconcile failed",
        detail: message,
        nextSteps: ["Inspect the corpus _normalized folder and retry."],
        sticky: true,
      });
    } finally {
      if (recapDraftEpochRef.current === draftEpoch) setReconciling(false);
    }
  }

  const report = latestResult?.ingest_report ?? {};
  const previewDiff = typeof report.preview_diff === "string" ? report.preview_diff : "";
  const titlePlaceholder = freshRecapEntry
    ? "e.g., Mireward Gate Battle"
    : inferredTitle || `Session ${recapSession || defaultRecapSession(session)} - Mireward Gate Battle`;
  const normalizedDuplicates = normalizedRecapCandidates(latestResult);
  const corpusImpact = corpusImpactRows(latestResult);
  const {
    confirmed: recapSourceConfirmed,
    missing: recapSourceMissing,
    hasProofRows: hasRecapSourceProofRows,
    actionStateConfirmed: recapSourceActionConfirmed,
    normalizedCurrent: recapSourceNormalizedCurrent,
  } = recapSourceProof(latestResult);
  const recapSourceActionsUnverified = Boolean(
    hasNormalizedRecap &&
      (!recapSourceConfirmed || !recapSourceNormalizedCurrent),
  );
  const recapSourceUnconfirmed = Boolean(
    recapSourceMissing ||
      ((latestResult?.states.includes("ingest_status_inspected") || hasRecapSourceProofRows) &&
        !recapSourceConfirmed) ||
      (!recapSourceConfirmed && !recapSourceActionConfirmed) ||
      recapSourceActionsUnverified,
  );
  const proofRows: CorpusImpactRow[] = latestResult
    ? [
        ...corpusImpact,
        ...proofPathKeys(latestResult)
          .filter((key) => !corpusImpact.some((row) => row.key === key))
          .map((key) => ({
          key,
          relpath: latestResult?.paths?.[key] ?? null,
          exists: null,
          record_count: undefined as number | undefined,
          })),
      ]
    : [];
  const hasNormalizedDuplicates = normalizedDuplicates.length > 1;
  const recommendedKeep =
    normalizedDuplicates.find((row) => row.recommended)?.basename ?? null;
  const selectableKeep = normalizedDuplicates.filter((row) => !row.is_generic);
  const selectedKeep =
    (reconcileChoice && normalizedDuplicates.some((row) => row.basename === reconcileChoice)
      ? reconcileChoice
      : null) ??
    recommendedKeep ??
    (selectableKeep.length === 1 ? selectableKeep[0].basename : null);
  const canReconcile = hasNormalizedDuplicates && !reconciling && Boolean(selectedKeep);
  const showSourceActions = priorIngestionArtifacts.length > 0 || loadingPriorIngestion;
  const showEvidenceShortcut = latestResult !== null;
  const showWorkflowActions = sourceInputSatisfied || busy;
  const showSourceProofRecovery = Boolean(
    hydrated &&
      showRecapWelcome &&
      sourcePresentButUnverified &&
      recapSourceUnconfirmed,
  );
  const showSavedWorkRecovery = showSourceProofRecovery && hasPriorIngestWork && recapSourceMissing;
  const showWorkflowFeedback =
    showWorkflowActions ||
    Boolean(toast) ||
    state.status === "error" ||
    showSourceProofRecovery;
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
                onBlur={() => void inspectSelectedRecapStatus()}
              />
              <RequiredBadge satisfied={validRecapSession} />
            </span>
          </label>
          <label className="ingest-local-nav__field ingest-local-nav__title" htmlFor="ingestion-title">
            <span>Session title</span>
            <span className="ingest-local-nav__title-control">
              <input
                id="ingestion-title"
                aria-label="Session title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder={titlePlaceholder}
              />
              <RequiredBadge satisfied={genericGuardPass} />
            </span>
          </label>
          {hydrated ? (
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
              {!readerMode && rawText.trim() && hasCurrentNormalizedSource ? (
                <button type="button" onClick={() => void reviewSavedSource()}>
                  View saved recap
                </button>
              ) : null}
            </>
          ) : null}
        </div>

        {showSourceActions || showWorkflowActions || showEvidenceShortcut ? (
          <div className="ingest-local-nav__workflow">
            {showSourceActions ? (
              <div className="ingest-local-nav__source" role="group" aria-label="Source actions">
                <label className="ingest-local-nav__prior" htmlFor="ingestion-prior-artifact">
                  <span className="sr-only">Prior processed recap</span>
                  <select
                    id="ingestion-prior-artifact"
                    aria-label="Prior processed recap"
                    value={selectedPriorArtifactId}
                    onChange={(event) => setSelectedPriorArtifactId(event.target.value)}
                    disabled={loadingPriorIngestion}
                  >
                    <option value="">Load a processed recap…</option>
                    {priorIngestionArtifacts.map((record) => (
                      <option key={record.artifact_id} value={record.artifact_id}>
                        {recapArtifactSessionLabel(record)}
                      </option>
                    ))}
                  </select>
                </label>
                {selectedPriorArtifactId ? (
                  <button
                    type="button"
                    aria-label="Load processed recap"
                    onClick={() => void loadSelectedPriorIngestion()}
                    disabled={loadingPriorIngestion}
                  >
                    {loadingPriorIngestion ? "Loading…" : "Load"}
                  </button>
                ) : null}
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

            {showWorkflowActions ? (
              <div className="ingest-local-nav__stages" role="group" aria-label="Recap processing">
                {hasPreviewUnionStore ? (
                  <label className="ingestion-checkbox-row ingestion-replace-graph-row ingest-local-nav__replace">
                    <input
                      type="checkbox"
                      checked={forceGraphRun}
                      onChange={(event) => setForceGraphRun(event.target.checked)}
                    />
                    Replace graph
                  </label>
                ) : null}
                <button
                  type="button"
                  aria-label={primaryOp === "process" ? "Processing recap" : "Process recap"}
                  className="primary"
                  onClick={() => void processRecap()}
                  disabled={!canProcessRecap}
                >
                  {primaryOp === "process" ? <><span className="button-inline-spinner" aria-hidden="true" /> Processing…</> : "Process"}
                </button>
                {isIngestSurfacePath() && (hasPreviewUnionStore || graphPreview?.status === "candidate_validation_ready") ? (
                  <button type="button" onClick={openGraphReviewWorkbench}>Graph Review</button>
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
                : !hydrated
                        ? "Checking saved recap status…"
                      : toast
                        ? <>
                            <span className="ingest-local-nav__status-title">{toast.title}</span>
                            {sourceInputSatisfied || hasNormalizedRecap ? (
                              <>
                                <span aria-hidden="true"> · </span>
                                <span>{workflowNextAction}</span>
                              </>
                            ) : null}
                          </>
                        : showSavedWorkRecovery
                          ? "Saved ingest work is preserved. No graph changes were written; load a recap or paste the verified source to continue."
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
            <section className="ingest-enriched-recap" aria-label="Graph-enriched recap">
              {reviewLoading ? <p role="status">Opening the graph-enriched recap…</p> : null}
              {reviewError ? (
                <p role="alert" className="module-error">
                  {reviewError} {reviewError.includes("credential") || reviewError.includes("graph_auth_required") ? "Open Advanced → Evidence to connect the local Graph session." : ""}
                </p>
              ) : null}
              {reviewSource?.projection ? (
                <>
                  {reviewSource.projection.schema === "dmb_historical_recap_world_projection_v1" ? (
                    <>
                      <p className="ingest-enriched-recap__status">
                        Exact extraction run · {reviewSource.projection.runId} · source bound by digest. Linked facts use the current admitted World Graph; new candidates remain in Graph Review.
                      </p>
                      <GraphReviewHistoricalRecapProjection projection={reviewSource.projection} />
                    </>
                  ) : (
                    <WorldGraphRecapProjectionView
                      payload={{ ...reviewSource.projection, markdown: reviewSource.projection.markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "") }}
                      selectedSessionId={`session-${reviewSource.session}`}
                      sessionOptions={Array.from(new Set([`session-${reviewSource.session}`, ...priorIngestionArtifacts.filter((item) => item.campaign_id === ingestCampaignId).map((item) => item.session_id)])).sort((a, b) => Number(a.replace("session-", "")) - Number(b.replace("session-", "")))}
                      onSelectSession={(value) => {
                        const nextSession = Number(value.replace("session-", ""));
                        handleRecapSessionChange(nextSession);
                        void inspectSelectedRecapStatus(ingestCampaignId, nextSession);
                      }}
                      selectedCampaignId={ingestCampaignId}
                      onSelectCampaign={handleIngestCampaignSelect}
                    />
                  )}
                </>
              ) : !reviewLoading && !reviewError ? (
                <p role="status" className="module-muted">Preparing the graph-enriched view…</p>
              ) : null}
            </section>
          ) : returnableDraft ? (
            <div className="ingestion-prepared-source-notice" role="status">
              <strong>Draft preserved · Session {returnableDraft.draft.recapSession}</strong>
              <p>Return to this draft to continue editing under its original session.</p>
            </div>
          ) : sourceMode === "processed" ? (
            <div className="ingestion-prepared-source-notice" role="status">
              <strong>Graph-enriched recap</strong>
              <p>Opening the linked World view…</p>
            </div>
          ) : showPreparedSourceNotice ? (
            <div className="ingestion-prepared-source-notice" role="note" aria-label="Prepared recap source">
              <strong>Prepared recap · Session {recapSession}</strong>
              <p>Opening the linked World view…</p>
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
                    setPriorSourceReadFailed(false);
                  }}
                  rows={18}
                  placeholder="Write or paste a session recap here…"
                />
              </div>
            </div>
          )}

        </section>

        <aside className="ingestion-evidence-pane" aria-label="Ingestion evidence and proof">
          <details id="ingestion-evidence-details" ref={evidenceDetailsRef}><summary>Evidence &amp; details</summary>
          <NativeGraphAccessControl onChanged={(available) => {
            reviewEpoch.current += 1;
            setReviewSource(null);
            setReviewError(null);
            setReviewLoading(false);
            if (available && readerMode) void reviewSavedSource(true);
          }} />
          <details className="ingestion-advanced-fold">
            <summary>Advanced file controls</summary>
            <label>
              <input
                type="checkbox"
                checked={showAdvanced}
                onChange={(event) => setShowAdvanced(event.target.checked)}
              />{" "}
              Show file replacement and filename override controls
            </label>
            {showAdvanced ? (
              <div className="ingestion-advanced-options">
                <label htmlFor="ingestion-slug">Canonical file name override</label>
                <input
                  id="ingestion-slug"
                  value={slug}
                  onChange={(event) => setSlug(event.target.value)}
                  placeholder="Mireward Gate Battle"
                />
                <p className="module-muted">
                  Usually leave this blank. The session title already chooses the saved filename.
                </p>
                {ignoredFileNameOverride ? (
                  <p className="module-muted">
                    This override looks like a tool label, so the session title will be used instead.
                  </p>
                ) : null}
                <label>
                  <input
                    type="checkbox"
                    checked={forceStage}
                    onChange={(event) => setForceStage(event.target.checked)}
                  />{" "}
                  Replace saved raw notes with the pasted text
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={forceRecap}
                    onChange={(event) => setForceRecap(event.target.checked)}
                  />{" "}
                  Replace existing canonical recap file
                </label>
                <p className="module-muted">
                  These controls are only for correcting prior saved files. The normal path does not need them.
                </p>
              </div>
            ) : null}
          </details>

          <details className="ingestion-advanced-fold">
            <summary>Advanced graph tools</summary>
            <p className="module-muted">Manual graph artifact controls for inspection and recovery.</p>
            <label htmlFor="ingestion-candidate-graph-path">Candidate graph path</label>
            <input
              id="ingestion-candidate-graph-path"
              value={candidateGraphPath}
              onChange={(event) => setCandidateGraphPath(event.target.value)}
              placeholder="out/graph_memory/fixtures/candidate_graph.json"
              disabled={extractGraphWithModel}
            />
            <label className="ingestion-checkbox-row">
              <input
                type="checkbox"
                checked={extractGraphWithModel}
                onChange={(event) => {
                  const checked = event.target.checked;
                  setExtractGraphWithModel(checked);
                  if (checked) setCandidateGraphPath("");
                }}
              />
              Extract graph from recap with category extraction (DeepSeek)
            </label>
            <p className="module-muted">
              Optional preview-only candidate graph artifact. When category extraction is enabled, the backend extracts source-backed nodes and relationships from the saved recap.
            </p>
            <div className="ingestion-actions ingestion-manual-actions">
              <button type="button" onClick={buildGraphPreview} disabled={!canBuildGraphPreview}>
                {isBuildingGraphPreview ? "Building Graph Preview..." : "Build Graph Preview"}
              </button>
              <button type="button" onClick={materializePreviewSupergraph} disabled={!canMaterializePreviewSupergraph}>
                {isMaterializingPreviewSupergraph ? "Materializing Preview Supergraph..." : "Materialize Preview Supergraph"}
              </button>
              {!isIngestSurfacePath() ? (
                <button type="button" onClick={openGraphPreview} disabled={!hasPreviewUnionStore}>
                  Open Graph Preview
                </button>
              ) : null}
            </div>
            <div className="ingestion-action-explainer">
              {graphDisabledReason ? <p>{graphDisabledReason}</p> : null}
              {previewSupergraphDisabledReason && !(hasPreviewUnionStore && !forceGraphRun) ? (
                <p>{previewSupergraphDisabledReason}</p>
              ) : null}
            </div>
          </details>

          <div className="ingestion-evidence-header">
            <div>
              <p className="ingestion-flow-kicker">Evidence / Details</p>
              <strong>Ingestion status</strong>
            </div>
            <span className={`pill pill-${statusBadge.tone}`} aria-live="polite">
              {statusBadge.label}
            </span>
          </div>
          {graphPreview?.status === "candidate_validation_ready" || graphPreview?.status === "preview_union_store_ready" ? (
            <p className="module-muted">
              Rendered recap ready: <code>{latestResult?.paths?.normalized_recap ?? latestResult?.paths?.canonical_recap ?? "recap path not reported"}</code>
            </p>
          ) : null}

          {hasNormalizedDuplicates ? (
            <div className="ingestion-reconcile-card" role="alert">
              <strong>Resolve duplicate normalized recaps</strong>
              <p>
                Found {normalizedDuplicates.length} normalized recaps for this session. Retrieval
                expects exactly one canonical recap. Pick the one that represents canon; the rest are
                archived (moved to <code>_archive</code>, never deleted).
              </p>
              <ul className="ingestion-reconcile-options">
                {normalizedDuplicates.map((row) => {
                  const checked = selectedKeep === row.basename;
                  return (
                    <li
                      key={row.basename}
                      className={`ingestion-reconcile-option${checked ? " is-selected" : ""}`}
                    >
                      <label>
                        <input
                          type="radio"
                          name="reconcile-keep"
                          value={row.basename}
                          checked={checked}
                          disabled={row.is_generic || reconciling}
                          onChange={() => setReconcileChoice(row.basename)}
                        />
                        <span className="ingestion-reconcile-option-main">
                          <code>{row.basename}</code>
                          {row.recommended ? <span className="pill pill-success">recommended</span> : null}
                          {row.is_generic ? <span className="pill pill-warning">tool-shaped</span> : null}
                        </span>
                        <span className="ingestion-reconcile-option-meta">
                          {formatBytes(row.size_bytes)}
                          {row.modified_at ? ` - ${new Date(row.modified_at).toLocaleString()}` : ""}
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
              <div className="ingestion-reconcile-actions">
                <button
                  type="button"
                  className="primary"
                  disabled={!canReconcile}
                  onClick={() => selectedKeep && reconcileNormalizedRecap(selectedKeep)}
                >
                  {reconciling ? "Repairing..." : "Repair and Prove"}
                </button>
                {selectedKeep ? (
                  <p className="ingestion-action-explainer">
                    Will keep <code>{selectedKeep}</code> and archive the other
                    {normalizedDuplicates.length > 2 ? " duplicates" : ""}.
                  </p>
                ) : (
                  <p className="ingestion-action-explainer">
                    No non-generic recap to keep automatically. Pick a canonical recap, or re-run
                    Process after correcting its session title first.
                  </p>
                )}
              </div>
            </div>
          ) : null}

          {latestResult?.states.includes("staged_raw_notes_conflict") ? (
            <div className="ingestion-boundary-card">
              <strong>Saved source conflict</strong>
              <p>
                Different raw notes are already staged for this session. This Process stopped without
                continuing against the older text. Confirm the replacement control in Advanced, then Process again.
              </p>
            </div>
          ) : null}

          <section className="ingestion-proof-card" aria-label="Graph preview status">
            <h4>Graph</h4>
            <p className="module-muted">Preview supergraph only. No canon graph write.</p>
            <p className="module-muted">
              Graph extraction:{" "}
              {graphPreview?.status === "preview_union_store_ready"
                ? "preview graph materialized"
                : graphPreview?.extraction_mode === "llm_blocked"
                  ? "blocked"
                  : graphPreview?.status === "candidate_validation_ready"
                    ? "candidate ready"
                    : graphPreview?.status === "source_span_bundle_ready"
                      ? "candidate pending"
                      : isRunningFullIngest
                        ? "extracting"
                        : graphPreview?.status ?? "pending"}
            </p>
            {state.status !== "error" && latestResult?.errors?.length ? (
              <p className="module-muted" role="status">
                Last ingest error: {latestResult.errors[0]}
              </p>
            ) : null}
            <div className="ingestion-proof-metrics">
              <span className="pill pill-neutral">status: {graphPreview?.status ?? "missing"}</span>
              <span className="pill pill-neutral">nodes: {graphPreview?.node_count ?? 0}</span>
              <span className="pill pill-neutral">edges: {graphPreview?.edge_count ?? 0}</span>
            </div>
            {Array.isArray(graphPreview?.extracted_nodes) && graphPreview.extracted_nodes.length > 0 ? (
              <div className="ingestion-extracted-nodes" aria-label="Extracted preview nodes">
                <p className="module-muted">
                  Nodes in this preview union ({graphPreview.extracted_nodes.length}):
                </p>
                <ul className="ingestion-extracted-node-list">
                  {Object.entries(
                    graphPreview.extracted_nodes.reduce<Record<string, string[]>>((acc, node) => {
                      const kind = node.kind?.trim() || "unknown";
                      (acc[kind] ??= []).push(node.label);
                      return acc;
                    }, {}),
                  )
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([kind, labels]) => (
                      <li key={kind}>
                        <strong>{kind}</strong>
                        <span>{labels.join(", ")}</span>
                      </li>
                    ))}
                </ul>
              </div>
            ) : hasPreviewUnionStore ? (
              <p className="module-muted">
                Preview union is on disk, but inspect did not return node labels. Open Graph Preview or
                re-inspect status.
              </p>
            ) : null}
            {graphPreview?.blocked_reason ? <p className="module-muted">{graphPreview.blocked_reason}</p> : null}
            {graphPreview?.manifest_path ? <p><code>{graphPreview.manifest_path}</code></p> : null}
            {graphPreview?.preview_union_store_path ? <p><code>{graphPreview.preview_union_store_path}</code></p> : null}
          </section>

          <section className="ingestion-proof-card" aria-label="Ingestion proof artifacts">
            <h4>Prove</h4>
            <p className="module-muted">
              On-disk existence from the latest inspect/status check (not path strings alone).
            </p>
            <div className="ingestion-proof-metrics">
              <span className="pill pill-neutral">{proofRows.filter((row) => row.exists === true).length} of {proofRows.length} recap files verified</span>
            </div>
            <ul className="ingestion-proof-paths">
              {proofRows.map((row) => {
                const statusLabel = row.exists === true ? "done" : row.exists === false ? "waiting" : "unverified";
                return (
                  <li key={row.key} className={`ingestion-proof-path ingestion-proof-path-${statusLabel}`}>
                    <details className="ingestion-proof-path__details">
                      <summary>
                        <span>{pathLabel(row.key)}</span>
                        <strong>{row.exists === true ? "Found" : row.exists === false ? "Missing" : "Unverified"}</strong>
                        {typeof row.record_count === "number" ? (
                          <span className="pill pill-neutral">records: {row.record_count}</span>
                        ) : null}
                      </summary>
                      <code>{row.relpath ?? "not reported yet"}</code>
                      {row.exists === true && (typeof row.size_bytes === "number" || row.modified_at) ? (
                        <p className="module-muted">
                          {typeof row.size_bytes === "number" ? formatBytes(row.size_bytes) : null}
                          {row.modified_at
                            ? `${typeof row.size_bytes === "number" ? " · " : ""}${new Date(row.modified_at).toLocaleString()}`
                            : null}
                        </p>
                      ) : null}
                      {row.preview ? <pre>{row.preview}</pre> : null}
                    </details>
                  </li>
                );
              })}
            </ul>
          </section>

          {latestResult ? (
            <section className="ingestion-status-panel">
              <h4>Status: <code>{latestResult.status}</code></h4>
              <div className="ingestion-status-columns">
                <div>
                  <h5>States</h5>
                  <ul>{evidenceRows(latestResult.states)}</ul>
                </div>
                <div>
                  <h5>Warnings</h5>
                  <ul>{evidenceRows(latestResult.warnings)}</ul>
                </div>
                <div>
                  {state.status === "error" ? (
                    <details>
                      <summary>Error details</summary>
                      <ul>{evidenceRows(latestResult.errors)}</ul>
                    </details>
                  ) : (
                    <>
                      <h5>Errors</h5>
                      <ul>{evidenceRows(latestResult.errors)}</ul>
                    </>
                  )}
                </div>
              </div>
              {latestResult.next_actions.length > 0 ? (
                <details className="ingestion-status-diagnostics">
                  <summary>Raw server recommendations</summary>
                  {recapSourceUnconfirmed ? (
                    <p className="module-muted">
                      These were returned by the status service. The recap-file check above did not
                      confirm both sources: restore or load the source before continuing.
                    </p>
                  ) : null}
                  <ul>{evidenceRows(latestResult.next_actions)}</ul>
                </details>
              ) : null}

              <details>
                <summary>Canonical preview</summary>
                <ul>
                  <li>title_line_stripped: {String(report.title_line_stripped ?? false)}</li>
                  <li>paragraph_count_in: {String(report.paragraph_count_in ?? "-")}</li>
                  <li>paragraph_count_out: {String(report.paragraph_count_out ?? "-")}</li>
                  <li>duplicates_detected: {String(report.duplicates_detected ?? "-")}</li>
                  <li>duplicates_removed: {String(report.duplicates_removed ?? "-")}</li>
                </ul>
                <h5>Preview diff</h5>
                <pre aria-label="Canonical preview diff">{previewDiff || "(no diff available)"}</pre>
              </details>

              <details>
                <summary>Authority transition</summary>
                <ul>
                  <li>raw notes -&gt; {latestResult.authority.staged_raw_notes}</li>
                  <li>canonical recap -&gt; {latestResult.authority.canonical_recap}</li>
                  <li>normalized recap -&gt; {latestResult.authority.normalized_recap}</li>
                </ul>
                <p className="module-muted">Raw notes are not normal retrieval evidence after a recap exists.</p>
                <p className="module-muted">Planning scaffold is not proof of what happened.</p>
                <p className="module-muted">Roll tables are reference tools, not play facts.</p>
              </details>

              <details>
                <summary>Spelling / Entity audit</summary>
                <p className="module-muted">Review only. No auto-corrections are applied.</p>
                {latestResult.entity_spelling_audit.length === 0 ? (
                  <p className="module-muted">No spelling variants detected.</p>
                ) : (
                  <ul>
                    {latestResult.entity_spelling_audit.map((row, idx) => {
                      const canonical = String(row.canonical_guess ?? "unknown");
                      const variants = Array.isArray(row.variants)
                        ? row.variants.map((v) => String(v)).join(", ")
                        : "unknown";
                      const action = String(row.action ?? "review_only");
                      return (
                        <li key={`${canonical}-${idx}`}>
                          <strong>{canonical}</strong> ← {variants} ({action})
                        </li>
                      );
                    })}
                  </ul>
                )}
              </details>
            </section>
          ) : (
            <p className="module-muted">No ingestion result yet.</p>
          )}
          </details>
        </aside>
      </div>
    </div>
  );
}
