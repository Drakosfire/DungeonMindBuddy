import { useEffect, useMemo, useRef, useState } from "react";

import { postRecapIngest } from "../api/recapIngestApi";
import type { RecapIngestStatus } from "../api/types";
import { AuthorityTransitionPanel } from "./AuthorityTransitionPanel";
import { IngestionStatusPanel } from "./IngestionStatusPanel";
import { SpellingAuditPanel } from "./SpellingAuditPanel";

interface IngestionModuleProps {
  campaignId: string;
  session: number;
}

const INGESTION_DRAFT_STORAGE_VERSION = 3;

const SESSION_22_CANONICAL_SLUG = "Mireward Road and Lysandro";
const SESSION_22_CANONICAL_TITLE = "Session 22 - Mireward Road and Lysandro";

interface IngestionModuleDraft {
  version: number;
  activeStep: number;
  rawText: string;
  recapSession: number;
  slug: string;
  title: string;
  showAdvanced: boolean;
  forceStage: boolean;
  forceRecap: boolean;
  latestResult: RecapIngestStatus | null;
  previewSignature: string | null;
  state: IngestionPaneState;
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

type IngestionPaneState =
  | { status: "idle" }
  | { status: "previewing" }
  | { status: "preview_ready"; result: RecapIngestStatus }
  | { status: "applying" }
  | { status: "applied"; result: RecapIngestStatus }
  | { status: "breadcrumb_required"; result: RecapIngestStatus }
  | { status: "materializing" }
  | { status: "ready_for_planning_activation"; result: RecapIngestStatus }
  | { status: "error"; result?: RecapIngestStatus; message?: string };

function isNonGenericSlugOrTitle(slug: string, title: string): boolean {
  const normalizedSlug = slug.trim().toLowerCase().replace(/:$/, "");
  if (normalizedSlug && normalizedSlug !== "recap") {
    return true;
  }
  const normalizedTitle = title.trim();
  if (!normalizedTitle) {
    return false;
  }
  const match = normalizedTitle.match(/^Session\s+\d+\s*-\s*(.+)$/i);
  const tail = (match ? match[1] : normalizedTitle).trim().toLowerCase().replace(/:$/, "");
  return tail !== "" && tail !== "recap";
}

function hasState(result: RecapIngestStatus | null, state: string): boolean {
  return Boolean(result && result.states.includes(state));
}

function slugFromCanonicalPath(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  const match = path.match(/Session \d+ - (.+)\.md$/);
  return match?.[1] ?? null;
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

function session22CanonicalPaths(): RecapIngestStatus["paths"] {
  const base = "Longmont Campaign/Campaign 2/Session Recaps";
  const basename = `Session 22 - ${SESSION_22_CANONICAL_SLUG}`;
  return {
    staged_raw_notes: "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md",
    canonical_recap: `${base}/${basename}.md`,
    normalized_recap: `${base}/_normalized/Session 22 - ${SESSION_22_CANONICAL_SLUG}.md`,
    breadcrumbed_recap: `${base}/_breadcrumbed/${basename}.breadcrumbed.md`,
    session_memory_jsonl: `${base}/_session_memory/${basename}.records_meta.jsonl`,
    session_memory_meta: `${base}/_session_memory/${basename}.records_meta.json`,
  };
}

function canonicalSlugTitleForRecapSession(
  recapSession: number,
  paths?: RecapIngestStatus["paths"],
): { slug: string; title: string } | null {
  if (recapSession === 22) {
    return { slug: SESSION_22_CANONICAL_SLUG, title: SESSION_22_CANONICAL_TITLE };
  }
  const fromPath = slugFromCanonicalPath(paths?.canonical_recap ?? undefined);
  if (fromPath) {
    return { slug: fromPath, title: `Session ${recapSession} - ${fromPath}` };
  }
  return null;
}

function sanitizeLatestResult(result: RecapIngestStatus | null): RecapIngestStatus | null {
  if (!result || result.session !== 22) {
    return result;
  }
  const pathSlug = slugFromCanonicalPath(result.paths?.canonical_recap ?? undefined);
  if (!pathSlug || !isStaleSession22Slug(pathSlug)) {
    return result;
  }
  return {
    ...result,
    paths: session22CanonicalPaths(),
    status:
      result.status === "breadcrumb_required" && result.states.includes("session_memory_materialized")
        ? "ready_for_planning_activation"
        : result.status,
  };
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

function normalizeRestoredState(state: IngestionPaneState): IngestionPaneState {
  if (state.status === "previewing" || state.status === "applying" || state.status === "materializing") {
    return { status: "idle" };
  }
  return state;
}

function deriveStepFromResult(result: RecapIngestStatus | null): number {
  if (!result) {
    return 1;
  }
  if (
    result.status === "ready_for_planning_activation" ||
    hasState(result, "session_memory_materialized")
  ) {
    return 3;
  }
  if (
    hasState(result, "breadcrumb_found") ||
    hasState(result, "normalized_created") ||
    hasState(result, "normalized_reused") ||
    hasState(result, "recap_applied") ||
    hasState(result, "recap_reused")
  ) {
    return 3;
  }
  if (hasState(result, "recap_preview_created") || hasState(result, "staged_raw_notes_reused")) {
    return 2;
  }
  return 1;
}

function derivePaneStateFromResult(result: RecapIngestStatus): IngestionPaneState {
  if (result.status === "ready_for_planning_activation") {
    return { status: "ready_for_planning_activation", result };
  }
  if (result.status === "breadcrumb_required") {
    return { status: "breadcrumb_required", result };
  }
  if (result.status === "error") {
    return {
      status: "error",
      result,
      message: result.errors.length > 0 ? result.errors.join("; ") : "Ingestion error",
    };
  }
  if (
    hasState(result, "recap_applied") ||
    hasState(result, "recap_reused") ||
    hasState(result, "normalized_created") ||
    hasState(result, "normalized_reused")
  ) {
    return { status: "applied", result };
  }
  if (hasState(result, "recap_preview_created")) {
    return { status: "preview_ready", result };
  }
  return { status: "idle" };
}

function mergeInspectResult(
  draftResult: RecapIngestStatus | null,
  inspected: RecapIngestStatus,
): RecapIngestStatus {
  if (!draftResult) {
    return inspected;
  }
  const mergedStates = [...new Set([...draftResult.states, ...inspected.states])];
  const progressRank = (status: string): number => {
    switch (status) {
      case "ready_for_planning_activation":
        return 5;
      case "breadcrumb_required":
        return 4;
      case "recap_applied":
        return 3;
      case "recap_preview_created":
        return 2;
      default:
        return 1;
    }
  };
  const status =
    progressRank(draftResult.status) >= progressRank(inspected.status)
      ? draftResult.status
      : inspected.status;
  return sanitizeLatestResult({
    ...inspected,
    status,
    states: mergedStates,
    paths: { ...inspected.paths, ...draftResult.paths },
    warnings: [...new Set([...draftResult.warnings, ...inspected.warnings])],
    next_actions:
      draftResult.next_actions.length > 0 ? draftResult.next_actions : inspected.next_actions,
    ingest_report: { ...inspected.ingest_report, ...draftResult.ingest_report },
    entity_spelling_audit:
      draftResult.entity_spelling_audit.length > 0
        ? draftResult.entity_spelling_audit
        : inspected.entity_spelling_audit,
  }) ?? inspected;
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
    const latestResult = sanitizeLatestResult(parsed.latestResult ?? null);
    const sanitized = sanitizeSlugTitle(parsed.recapSession, parsed.slug, parsed.title);
    return {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      activeStep:
        typeof parsed.activeStep === "number" && parsed.activeStep >= 1 && parsed.activeStep <= 3
          ? parsed.activeStep
          : 1,
      rawText: parsed.rawText,
      recapSession: parsed.recapSession,
      slug: sanitized.slug,
      title: sanitized.title,
      showAdvanced: Boolean(parsed.showAdvanced),
      forceStage: Boolean(parsed.forceStage),
      forceRecap: Boolean(parsed.forceRecap),
      latestResult,
      previewSignature:
        typeof parsed.previewSignature === "string" || parsed.previewSignature === null
          ? parsed.previewSignature
          : null,
      state: parsed.state ? normalizeRestoredState(parsed.state) : { status: "idle" },
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

function hasReviewOnlySpellingVariants(result: RecapIngestStatus): boolean {
  return Array.isArray(result.entity_spelling_audit) && result.entity_spelling_audit.length > 0;
}

function buildToastForResult(
  result: RecapIngestStatus | null,
  {
    fallbackErrorMessage,
    forceStage,
    forceRecap,
    genericGuardPass,
    allowInspectResume,
  }: {
    fallbackErrorMessage?: string;
    forceStage: boolean;
    forceRecap: boolean;
    genericGuardPass: boolean;
    allowInspectResume?: boolean;
  },
): IngestionToast | null {
  if (!result) {
    if (!fallbackErrorMessage) {
      return null;
    }
    return {
      tone: "error",
      title: "Ingestion failed",
      detail: fallbackErrorMessage,
      nextSteps: ["Retry Stage + Preview."],
      sticky: true,
    };
  }

  if (
    !allowInspectResume &&
    result.states.includes("ingest_status_inspected") &&
    (result.status === "ready_for_planning_activation" || result.status === "recap_applied")
  ) {
    return null;
  }

  const warningSet = new Set(result.warnings);
  const nextSteps = [...result.next_actions];

  if (result.status === "error") {
    const joinedErrors = result.errors.join(" | ");
    if (joinedErrors.includes("staged raw notes already exists")) {
      nextSteps.unshift(
        forceStage
          ? "Click Stage + Preview again (force stage is enabled)."
          : "Enable overwrite staged raw notes (--force-stage), then rerun Stage + Preview.",
      );
    }
    if (joinedErrors.includes("canonical recap already exists")) {
      nextSteps.unshift(
        forceRecap
          ? "Click Apply + Normalize again (force recap is enabled)."
          : "Enable overwrite canonical recap (--force-recap), then rerun Apply + Normalize.",
      );
    }
  }

  if (warningSet.has("slug_mismatch_used_disk_breadcrumb")) {
    nextSteps.unshift("Slug in the form did not match canon on disk; fields were synced to the canonical recap slug.");
  }

  if (warningSet.has("slug_required_for_apply") || !genericGuardPass) {
    nextSteps.push("Set a non-generic slug/title before Apply + Normalize.");
  }

  if (hasReviewOnlySpellingVariants(result)) {
    nextSteps.push("Review obvious spelling/chat-noise artifacts before canonizing.");
  }

  if (result.status === "breadcrumb_required") {
    nextSteps.unshift(
      "Canonical + normalized recap exist on disk.",
      "Breadcrumb + session memory are not retrieval-ready yet.",
      "Bless the frontmatter seed and breadcrumb artifact, then inspect status before materializing session memory.",
    );
  }

  if (result.status === "ready_for_planning_activation") {
    nextSteps.unshift("Ingest complete. Proceed with Session 23 planning.");
  }

  if (result.states.includes("recap_reused")) {
    nextSteps.unshift("Canonical recap already on disk — reused without overwrite.");
  }
  if (result.states.includes("normalized_reused")) {
    nextSteps.unshift("Normalized recap already on disk — reused without overwrite.");
  }

  const uniqueNextSteps = [...new Set(nextSteps)].filter(Boolean);

  const tone: IngestionToastTone =
    result.status === "ready_for_planning_activation"
      ? "success"
      : result.status === "error"
        ? "error"
        : "info";

  const detail =
    result.status === "breadcrumb_required"
      ? "Expected v1 stop: canonical recap and normalized recap are prepared; retrieval activation waits for breadcrumb + session memory."
      : result.errors.length > 0
        ? result.errors.join("; ")
        : result.warnings.length > 0
          ? result.warnings.join("; ")
          : "Operation completed.";

  return {
    tone,
    title:
      result.status === "breadcrumb_required"
        ? "Breadcrumb required before retrieval"
        : `Ingestion ${result.status}`,
    detail,
    nextSteps: uniqueNextSteps.slice(0, 4),
    sticky: tone === "error",
  };
}

function previewSourceSignature(recapSession: number, rawText: string, slug: string): string {
  return JSON.stringify({
    recapSession,
    rawText: rawText.trim(),
    slug: slug.trim(),
  });
}

export function IngestionModule({ campaignId, session }: IngestionModuleProps) {
  const storageKey = useMemo(() => draftStorageKey(campaignId, session), [campaignId, session]);
  const [activeStep, setActiveStep] = useState<number>(1);
  const [rawText, setRawText] = useState("");
  const [recapSession, setRecapSession] = useState<number>(() => defaultRecapSession(session));
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [forceStage, setForceStage] = useState(false);
  const [forceRecap, setForceRecap] = useState(false);
  const [state, setState] = useState<IngestionPaneState>({ status: "idle" });
  const [latestResult, setLatestResult] = useState<RecapIngestStatus | null>(null);
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [toast, setToast] = useState<IngestionToast | null>(null);
  const lastToastKeyRef = useRef<string | null>(null);
  const hydrateInspectGenerationRef = useRef(0);
  const validRecapSession = Number.isInteger(recapSession) && recapSession > 0;

  function invalidateInFlightHydrateInspect() {
    hydrateInspectGenerationRef.current += 1;
  }

  const currentPreviewSignature = useMemo(
    () => previewSourceSignature(recapSession, rawText, slug),
    [recapSession, rawText, slug],
  );
  const previewInvalidated =
    previewSignature != null && previewSignature !== currentPreviewSignature;
  const busy = ["previewing", "applying", "materializing"].includes(state.status);
  const hasPreview =
    (hasState(latestResult, "recap_preview_created") &&
      !previewInvalidated &&
      previewSignature === currentPreviewSignature) ||
    hasState(latestResult, "staged_raw_notes_reused");
  const genericGuardPass = isNonGenericSlugOrTitle(slug, title);
  const canMaterialize =
    !busy &&
    !!latestResult &&
    hasState(latestResult, "breadcrumb_found");
  const hasApplied =
    hasState(latestResult, "recap_applied") ||
    hasState(latestResult, "recap_reused") ||
    hasState(latestResult, "normalized_created") ||
    hasState(latestResult, "normalized_reused");
  const hasMaterialized =
    hasState(latestResult, "session_memory_materialized") ||
    state.status === "ready_for_planning_activation";
  const isMaterializing = state.status === "materializing";

  useEffect(() => {
    let cancelled = false;

    async function hydrateFromStorageAndDisk() {
      const draft = readDraft(storageKey);
      const defaultRecap = draft?.recapSession ?? defaultRecapSession(session);
      const initialSlug = draft?.slug ?? canonicalSlugTitleForRecapSession(defaultRecap)?.slug ?? "";
      const initialTitle = draft?.title ?? canonicalSlugTitleForRecapSession(defaultRecap)?.title ?? "";

      if (!draft) {
        setActiveStep(1);
        setRawText("");
        setRecapSession(defaultRecap);
        setSlug(initialSlug);
        setTitle(initialTitle);
        setShowAdvanced(false);
        setForceStage(false);
        setForceRecap(false);
        setState({ status: "idle" });
        setLatestResult(null);
        setPreviewSignature(null);
      } else {
        setActiveStep(draft.activeStep);
        setRawText(draft.rawText);
        setRecapSession(draft.recapSession);
        setSlug(draft.slug);
        setTitle(draft.title);
        setShowAdvanced(draft.showAdvanced);
        setForceStage(draft.forceStage);
        setForceRecap(draft.forceRecap);
        setState(draft.state);
        setLatestResult(draft.latestResult);
        setPreviewSignature(draft.previewSignature);
      }

      try {
        const inspectGeneration = hydrateInspectGenerationRef.current;
        const inspected = await postRecapIngest({
          operation: "inspect_status",
          campaign_id: campaignId,
          session: defaultRecap,
          slug: initialSlug.trim() || undefined,
          title: initialTitle.trim() || undefined,
        });
        if (cancelled || inspectGeneration !== hydrateInspectGenerationRef.current) {
          return;
        }
        const mergedWithDraft = mergeInspectResult(draft?.latestResult ?? null, inspected);
        const sanitizedResult = sanitizeLatestResult(mergedWithDraft) ?? mergedWithDraft;
        setLatestResult((prev) => {
          const merged = mergeInspectResult(prev ?? draft?.latestResult ?? null, inspected);
          return sanitizeLatestResult(merged) ?? merged;
        });
        const synced = syncSlugTitleFromResult(sanitizedResult);
        if (synced) {
          setSlug(synced.slug);
          setTitle(synced.title);
          if (previewSignature != null && hasState(sanitizedResult, "recap_preview_created")) {
            setPreviewSignature(
              previewSourceSignature(recapSession, rawText, synced.slug),
            );
          }
        }
        setActiveStep((prev) => Math.max(prev, deriveStepFromResult(sanitizedResult)));
        setState((prev) => {
          if (
            prev.status === "previewing" ||
            prev.status === "applying" ||
            prev.status === "materializing" ||
            prev.status === "preview_ready" ||
            prev.status === "applied" ||
            prev.status === "ready_for_planning_activation"
          ) {
            return prev;
          }
          return derivePaneStateFromResult(sanitizedResult);
        });
      } catch {
        // Disk probe is best-effort; local draft still applies.
      }

      if (!cancelled) {
        setHydrated(true);
      }
    }

    setHydrated(false);
    void hydrateFromStorageAndDisk();

    return () => {
      cancelled = true;
    };
  }, [storageKey, session, campaignId]);

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
    if (!hydrated) {
      return;
    }
    writeDraft(storageKey, {
      version: INGESTION_DRAFT_STORAGE_VERSION,
      activeStep,
      rawText,
      recapSession,
      slug,
      title,
      showAdvanced,
      forceStage,
      forceRecap,
      latestResult,
      previewSignature,
      state,
    });
  }, [
    hydrated,
    storageKey,
    activeStep,
    rawText,
    recapSession,
    slug,
    title,
    showAdvanced,
    forceStage,
    forceRecap,
    latestResult,
    previewSignature,
    state,
  ]);

  useEffect(() => {
    const maybeToast = buildToastForResult(latestResult, {
      fallbackErrorMessage: state.status === "error" ? state.message : undefined,
      forceStage,
      forceRecap,
      genericGuardPass,
      allowInspectResume: false,
    });
    if (!maybeToast) {
      return;
    }
    const key = JSON.stringify({
      tone: maybeToast.tone,
      title: maybeToast.title,
      detail: maybeToast.detail,
      nextSteps: maybeToast.nextSteps,
      sticky: Boolean(maybeToast.sticky),
    });
    if (key === lastToastKeyRef.current) {
      return;
    }
    lastToastKeyRef.current = key;
    setToast(maybeToast);
  }, [latestResult, state, forceStage, forceRecap, genericGuardPass]);

  useEffect(() => {
    if (!toast || toast.sticky) {
      return;
    }
    const timeout = window.setTimeout(() => setToast(null), 9000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function jumpToStep(step: number) {
    setActiveStep(Math.min(3, Math.max(1, step)));
  }

  function resetWizardFlow(nextStep = 1) {
    lastToastKeyRef.current = null;
    setState({ status: "idle" });
    setLatestResult(null);
    setPreviewSignature(null);
    const canonicalDefaults = canonicalSlugTitleForRecapSession(recapSession);
    if (canonicalDefaults) {
      setSlug(canonicalDefaults.slug);
      setTitle(canonicalDefaults.title);
    }
    jumpToStep(nextStep);
  }

  function applyResultAndSyncSlug(result: RecapIngestStatus) {
    const sanitizedResult = sanitizeLatestResult(result) ?? result;
    setLatestResult(sanitizedResult);
    const synced = syncSlugTitleFromResult(sanitizedResult);
    if (synced) {
      setSlug(synced.slug);
      setTitle(synced.title);
    }
  }

  async function stagePreview() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "previewing" });
    try {
      const result = await postRecapIngest({
        operation: "stage_preview",
        campaign_id: campaignId,
        session: recapSession,
        raw_text: rawText,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
        force_stage: forceStage || undefined,
      });
      applyResultAndSyncSlug(result);
      const synced = syncSlugTitleFromResult(sanitizeLatestResult(result) ?? result);
      setPreviewSignature(
        previewSourceSignature(recapSession, rawText, synced?.slug ?? slug),
      );
      if (result.status === "error") {
        setState({
          status: "error",
          result,
          message:
            result.errors.length > 0 ? result.errors.join("; ") : "Stage + Preview failed",
        });
        jumpToStep(1);
        return;
      }
      if (result.status === "breadcrumb_required") {
        setState({ status: "breadcrumb_required", result });
      } else {
        setState({ status: "preview_ready", result });
      }
      jumpToStep(2);
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Stage + Preview failed",
      });
    }
  }

  async function applyNormalize() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "applying" });
    try {
      const result = await postRecapIngest({
        operation: "apply_normalize",
        campaign_id: campaignId,
        session: recapSession,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
        force_recap: forceRecap || undefined,
      });
      applyResultAndSyncSlug(result);
      if (result.status === "error") {
        setState({
          status: "error",
          result,
          message:
            result.errors.length > 0 ? result.errors.join("; ") : "Apply + Normalize failed",
        });
        jumpToStep(2);
        return;
      }
      if (result.status === "breadcrumb_required") {
        setState({ status: "breadcrumb_required", result });
      } else {
        setState({ status: "applied", result });
      }
      jumpToStep(3);
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Apply + Normalize failed",
      });
    }
  }

  async function materializeSessionMemory() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "materializing" });
    setToast({
      tone: "info",
      title: "Materialization started",
      detail: "Materializing session memory now. This can take a moment.",
      nextSteps: [],
    });
    try {
      const result = await postRecapIngest({
        operation: "materialize_session_memory",
        campaign_id: campaignId,
        session: recapSession,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
        check: true,
      });
      applyResultAndSyncSlug(result);
      if (result.status === "error") {
        setState({
          status: "error",
          result,
          message:
            result.errors.length > 0
              ? result.errors.join("; ")
              : "Session memory materialization failed",
        });
        jumpToStep(3);
        return;
      }
      if (result.status === "ready_for_planning_activation") {
        setState({ status: "ready_for_planning_activation", result });
      } else if (result.status === "breadcrumb_required") {
        setState({ status: "breadcrumb_required", result });
      } else {
        setState({ status: "applied", result });
      }
      jumpToStep(3);
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Session memory materialization failed",
      });
    }
  }

  return (
    <div className="module-panel ingestion-module" data-module-id="ingestion">
      {toast ? (
        <section className={`ingestion-toast ingestion-toast-${toast.tone}`} role="alert" aria-live="polite">
          <div className="ingestion-toast-header">
            <strong>{toast.title}</strong>
            <button type="button" onClick={() => setToast(null)} aria-label="Dismiss ingestion toast">
              Dismiss
            </button>
          </div>
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
        </section>
      ) : null}
      <h2 className="module-title">Raw Recap Ingestion</h2>
      <p className="module-muted">Operator prep tool over the PR92 ingestion orchestrator.</p>
      <p className="module-muted">
        Campaign: <strong>{campaignId}</strong> · Live workspace session: <strong>{session}</strong>
      </p>

      <div className="ingestion-wizard-nav" role="navigation" aria-label="Ingestion steps">
        <button
          type="button"
          className={`wizard-step-chip ${activeStep === 1 ? "active" : ""}`}
          onClick={() => jumpToStep(1)}
        >
          1. Source {hasPreview ? "✓" : ""}
        </button>
        <button
          type="button"
          className={`wizard-step-chip ${activeStep === 2 ? "active" : ""}`}
          onClick={() => jumpToStep(2)}
        >
          2. Preview + Apply {hasApplied ? "✓" : ""}
        </button>
        <button
          type="button"
          className={`wizard-step-chip ${activeStep === 3 ? "active" : ""}`}
          onClick={() => jumpToStep(3)}
        >
          3. Materialize {hasMaterialized ? "✓" : ""}
        </button>
        <button type="button" className="wizard-step-chip" onClick={() => resetWizardFlow(1)}>
          Reset flow
        </button>
      </div>

      <section className={`ingestion-step ${activeStep === 1 ? "is-active" : ""}`} aria-label="Ingestion step 1">
        <h3 className="ingestion-step-title">Step 1 — source recap details</h3>
        <div className="ingestion-source-grid">
          <div>
            <label htmlFor="ingestion-recap-session">Recap/source session</label>
            <input
              id="ingestion-recap-session"
              type="number"
              min={1}
              step={1}
              value={recapSession}
              onChange={(event) => {
                const nextValue = Number.parseInt(event.target.value, 10);
                setRecapSession(Number.isNaN(nextValue) ? 0 : nextValue);
              }}
            />
          </div>
          <div>
            <label htmlFor="ingestion-slug">Slug</label>
            <input
              id="ingestion-slug"
              value={slug}
              onChange={(event) => setSlug(event.target.value)}
              placeholder="Mireward Road and Lysandro"
            />
          </div>
          <div>
            <label htmlFor="ingestion-title">Title (optional)</label>
            <input
              id="ingestion-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Session 22 - Mireward Road and Lysandro"
            />
          </div>
          <div className="ingestion-raw-block">
            <label htmlFor="ingestion-raw-text">Raw recap text</label>
            <textarea
              id="ingestion-raw-text"
              value={rawText}
              onChange={(event) => setRawText(event.target.value)}
              rows={12}
              placeholder="Session 22 Recap&#10;&#10;The group turns their focus..."
            />
          </div>
        </div>
        <details>
          <summary>Advanced overwrite controls</summary>
          <label>
            <input
              type="checkbox"
              checked={showAdvanced}
              onChange={(event) => setShowAdvanced(event.target.checked)}
            />{" "}
            Enable overwrite toggles
          </label>
          {showAdvanced ? (
            <div className="ingestion-advanced-options">
              <label>
                <input
                  type="checkbox"
                  checked={forceStage}
                  onChange={(event) => {
                    setForceStage(event.target.checked);
                    resetWizardFlow(2);
                  }}
                />{" "}
                Overwrite staged raw notes (`--force-stage`)
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={forceRecap}
                  onChange={(event) => {
                    setForceRecap(event.target.checked);
                    resetWizardFlow(2);
                  }}
                />{" "}
                Overwrite existing canonical recap (`--force-recap`)
              </label>
            </div>
          ) : null}
        </details>
        {showAdvanced ? (
          <p className="module-muted">
            Changing overwrite toggles resets flow to Step 2 so you can rerun Stage + Preview.
          </p>
        ) : null}
        <div className="ingestion-step-actions">
          <button type="button" onClick={() => jumpToStep(2)} disabled={!validRecapSession || rawText.trim().length === 0}>
            Next: Preview
          </button>
        </div>
      </section>

      <section className={`ingestion-step ${activeStep === 2 ? "is-active" : ""}`} aria-label="Ingestion step 2">
        <h3 className="ingestion-step-title">Step 2 — stage preview and apply</h3>
        <div className="ingestion-actions">
          <button
            type="button"
            onClick={stagePreview}
            disabled={busy || rawText.trim().length === 0 || !validRecapSession}
          >
            Stage + Preview
          </button>
          <button
            type="button"
            onClick={applyNormalize}
            disabled={busy || !hasPreview || !genericGuardPass || !validRecapSession}
          >
            Apply + Normalize
          </button>
        </div>
        <div className="ingestion-step-actions">
          <button type="button" onClick={() => jumpToStep(1)}>
            Back
          </button>
          <button type="button" onClick={() => jumpToStep(3)} disabled={!hasPreview}>
            Next: Materialize
          </button>
        </div>
      </section>

      <section className={`ingestion-step ${activeStep === 3 ? "is-active" : ""}`} aria-label="Ingestion step 3">
        <h3 className="ingestion-step-title">Step 3 — breadcrumb and session memory readiness</h3>
        {latestResult?.status === "breadcrumb_required" ? (
          <div className="ingestion-boundary-card" role="status">
            <strong>Expected v1 boundary: breadcrumb required</strong>
            <p>Canonical recap and normalized recap are on disk. Retrieval is not ready until a blessed breadcrumb and session memory records exist.</p>
            <p>Use the established content-ops path for `frontmatter_seed.md` and breadcrumb tagging, then inspect status again before materializing session memory.</p>
          </div>
        ) : null}
        <div className="ingestion-actions">
          <button
            type="button"
            onClick={materializeSessionMemory}
            disabled={!canMaterialize || !validRecapSession}
          >
            {isMaterializing ? (
              <>
                <span className="button-inline-spinner" aria-hidden="true" />
                Materializing Session Memory...
              </>
            ) : (
              "Materialize Session Memory"
            )}
          </button>
        </div>
        <p className="module-muted ingestion-live-status" role="status" aria-live="polite">
          {isMaterializing ? "Materialization in progress..." : ""}
        </p>
        {!canMaterialize ? (
          <p className="module-muted">Materialize is disabled until disk status reports `breadcrumb_found`.</p>
        ) : null}
        <div className="ingestion-step-actions">
          <button type="button" onClick={() => jumpToStep(2)}>
            Back
          </button>
        </div>
      </section>

      {previewInvalidated ? (
        <p className="module-muted">Preview invalidated by raw text/slug/title edits. Re-run Stage + Preview.</p>
      ) : null}
      {!genericGuardPass ? (
        <p className="module-muted">Apply is disabled until slug/title is non-generic.</p>
      ) : null}
      {!validRecapSession ? (
        <p className="module-muted">Enter a valid recap/source session number (1+).</p>
      ) : null}

      <IngestionStatusPanel result={latestResult} />
      <AuthorityTransitionPanel result={latestResult} />
      <SpellingAuditPanel result={latestResult} />

      {state.status === "error" ? (
        <p className="module-error">{state.message ?? "Ingestion operation failed."}</p>
      ) : null}
      {state.status === "ready_for_planning_activation" ? (
        <p className="module-success">ready_for_planning_activation</p>
      ) : null}
    </div>
  );
}
