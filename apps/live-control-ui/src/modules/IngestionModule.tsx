import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { postRecapIngest } from "../api/recapIngestApi";
import type { NormalizedRecapCandidate, RecapGraphPreviewReport, RecapIngestStatus } from "../api/types";

interface IngestionModuleProps {
  campaignId: string;
  session: number;
}

const INGESTION_DRAFT_STORAGE_VERSION = 3;

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

interface CorpusImpactRow {
  key: string;
  relpath: string;
  exists: boolean;
  size_bytes?: number;
  modified_at?: string;
  record_count?: number;
  preview?: string;
}

function defaultRecapSession(liveSession: number): number {
  return Math.max(1, liveSession - 1);
}

function campaignNumberFromId(campaignId: string): string {
  return campaignId.replace(/^longmont-c/i, "") || campaignId;
}

type IngestionPaneState =
  | { status: "idle" }
  | { status: "running_full_ingest" }
  | { status: "previewing" }
  | { status: "preview_ready"; result: RecapIngestStatus }
  | { status: "applying" }
  | { status: "applied"; result: RecapIngestStatus }
  | { status: "breadcrumb_required"; result: RecapIngestStatus }
  | { status: "building_frontmatter_seed" }
  | { status: "running_breadcrumb_ingest" }
  | { status: "materializing" }
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
    .replace(/\.records_meta\.jsonl$/i, "")
    .replace(/\.records_meta\.json$/i, "")
    .replace(/\.breadcrumbed\.md$/i, "")
    .replace(/\.frontmatter_seed\.md$/i, "")
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
  const pathKeys = [
    "canonical_recap",
    "normalized_recap",
    "breadcrumbed_recap",
    "session_memory_jsonl",
    "session_memory_meta",
  ];
  for (const key of pathKeys) {
    const fromPath = slugFromCanonicalPath(paths?.[key] ?? undefined);
    if (fromPath && isNonGenericSlugOrTitle(fromPath, "")) {
      return { slug: fromPath, title: `Session ${recapSession} - ${fromPath}` };
    }
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
  if (
    state.status === "previewing" ||
    state.status === "running_full_ingest" ||
    state.status === "applying" ||
    state.status === "building_frontmatter_seed" ||
    state.status === "running_breadcrumb_ingest" ||
    state.status === "materializing" ||
    state.status === "building_graph_preview" ||
    state.status === "materializing_preview_supergraph"
  ) {
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

function workflowStepState(done: boolean, active: boolean): "done" | "active" | "locked" {
  if (done) return "done";
  if (active) return "active";
  return "locked";
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderSimpleMarkdown(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return '<p class="module-muted">Paste raw notes to preview rendered markdown here.</p>';
  }

  return trimmed
    .split(/\n{2,}/)
    .map((block) => {
      const lines = block.split("\n").map((line) => line.trimEnd());
      const firstLine = lines[0]?.trim() ?? "";
      const heading = firstLine.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        return `<h${level}>${escapeHtml(heading[2])}</h${level}>`;
      }
      if (lines.every((line) => /^\s*[-*]\s+/.test(line))) {
        return `<ul>${lines
          .map((line) => `<li>${escapeHtml(line.replace(/^\s*[-*]\s+/, ""))}</li>`)
          .join("")}</ul>`;
      }
      return `<p>${lines.map((line) => escapeHtml(line)).join("<br />")}</p>`;
    })
    .join("");
}

function evidenceRows(values: string[]): ReactNode {
  if (values.length === 0) {
    return <li className="module-muted">None</li>;
  }
  return values.map((value) => <li key={value}>{value}</li>);
}

function pathStatus(result: RecapIngestStatus | null, key: string): "done" | "waiting" {
  return result?.paths?.[key] ? "done" : "waiting";
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
    .map((row) => ({
      key: String(row.key ?? ""),
      relpath: String(row.relpath ?? ""),
      exists: Boolean(row.exists),
      size_bytes: typeof row.size_bytes === "number" ? row.size_bytes : undefined,
      modified_at: typeof row.modified_at === "string" ? row.modified_at : undefined,
      record_count: typeof row.record_count === "number" ? row.record_count : undefined,
      preview: typeof row.preview === "string" ? row.preview : undefined,
    }))
    .filter((row) => row.key.length > 0 && row.relpath.length > 0);
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
  const preferred = [
    "canonical_recap",
    "normalized_recap",
    "frontmatter_seed",
    "breadcrumbed_recap",
    "session_memory_jsonl",
    "session_memory_meta",
  ];
  if (!result) return preferred;
  const extra = Object.keys(result.paths).filter((key) => !preferred.includes(key));
  return [...preferred, ...extra];
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
  const stagedRawConflict = result.states.includes("staged_raw_notes_conflict");
  const frontmatterSeedReady =
    result.states.includes("frontmatter_seed_built") ||
    result.states.includes("frontmatter_seed_reused");

  if (stagedRawConflict) {
    nextSteps.unshift(
      "Existing staged notes were reused for this preview.",
      forceStage
        ? "Click Stage + Preview again to overwrite the staged notes."
        : "Use Advanced only if the pasted text should replace the saved raw notes.",
    );
  }

  if (result.status === "error") {
    const joinedErrors = result.errors.join(" | ");
    if (joinedErrors.includes("staged raw notes already exists")) {
      nextSteps.unshift(
        forceStage
          ? "Click Stage + Preview again (force stage is enabled)."
          : "Use Advanced to replace the saved raw notes, then rerun Stage + Preview.",
      );
    }
    if (joinedErrors.includes("canonical recap already exists")) {
      nextSteps.unshift(
        forceRecap
          ? "Click Apply + Normalize again (force recap is enabled)."
          : "Use Advanced to replace the saved canonical recap, then rerun Apply + Normalize.",
      );
    }
  }

  if (warningSet.has("slug_mismatch_used_disk_breadcrumb")) {
    nextSteps.unshift("The saved canon on disk used a different recap title; fields were synced to the canonical recap.");
  }

  if (warningSet.has("slug_required_for_apply") || !genericGuardPass) {
    nextSteps.push("Session title is required before saving canon.");
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
    nextSteps.unshift("Open Recap View to read the recap and inspect graph chips.");
  }

  if (frontmatterSeedReady) {
    nextSteps.unshift("Review the frontmatter seed, then run breadcrumb ingest.");
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
      : frontmatterSeedReady
        ? "success"
      : stagedRawConflict
        ? "warning"
      : result.status === "error"
        ? "error"
        : "info";

  const detail =
    stagedRawConflict
      ? "Existing staged raw notes were found, so the preview uses those notes. The pasted text was not written."
      : frontmatterSeedReady
        ? "Frontmatter seed is ready for human review before breadcrumb ingest."
      : result.status === "ready_for_planning_activation"
        ? "Recap memory generated. Open Recap View to read the recap and inspect graph chips."
      : result.status === "breadcrumb_required"
      ? "Expected v1 stop: canonical recap and normalized recap are prepared; retrieval activation waits for breadcrumb + session memory."
      : result.errors.length > 0
        ? result.errors.join("; ")
        : result.warnings.length > 0
          ? result.warnings.join("; ")
          : "Operation completed.";

  return {
    tone,
    title:
      stagedRawConflict
        ? "Existing staged notes reused"
        : frontmatterSeedReady
          ? "Frontmatter seed ready"
        : result.status === "breadcrumb_required"
        ? "Breadcrumb required before retrieval"
        : `Ingestion ${result.status}`,
    detail,
    nextSteps: uniqueNextSteps.slice(0, 4),
    sticky: tone === "error" || stagedRawConflict,
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
  const [candidateGraphPath, setCandidateGraphPath] = useState("");
  const [state, setState] = useState<IngestionPaneState>({ status: "idle" });
  const [latestResult, setLatestResult] = useState<RecapIngestStatus | null>(null);
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [toast, setToast] = useState<IngestionToast | null>(null);
  const [reconcileChoice, setReconcileChoice] = useState<string | null>(null);
  const [reconciling, setReconciling] = useState(false);
  const lastToastKeyRef = useRef<string | null>(null);
  const hydrateInspectGenerationRef = useRef(0);
  const validRecapSession = Number.isInteger(recapSession) && recapSession > 0;
  const terminalCampaign = campaignNumberFromId(campaignId);

  function invalidateInFlightHydrateInspect() {
    hydrateInspectGenerationRef.current += 1;
  }

  const inferredTitle = useMemo(
    () => inferTitleFromRawText(rawText, recapSession),
    [rawText, recapSession],
  );
  const effectiveTitle = title.trim() || inferredTitle;
  const slugOverrideIsSpecific = slug.trim().length > 0 && isNonGenericSlugOrTitle(slug, "");
  const ignoredFileNameOverride = showAdvanced && slug.trim().length > 0 && !slugOverrideIsSpecific;
  const effectiveSlug = showAdvanced && slugOverrideIsSpecific ? slug.trim() : "";
  const currentPreviewSignature = useMemo(
    () => previewSourceSignature(recapSession, rawText, effectiveTitle || effectiveSlug),
    [recapSession, rawText, effectiveSlug, effectiveTitle],
  );
  const previewInvalidated =
    previewSignature != null && previewSignature !== currentPreviewSignature;
  const rawTextSatisfied = rawText.trim().length > 0;
  const busy = [
    "running_full_ingest",
    "previewing",
    "applying",
    "building_frontmatter_seed",
    "running_breadcrumb_ingest",
    "materializing",
    "building_graph_preview",
    "materializing_preview_supergraph",
  ].includes(state.status);
  const hasPreview =
    (hasState(latestResult, "recap_preview_created") &&
      !previewInvalidated &&
      previewSignature === currentPreviewSignature) ||
    hasState(latestResult, "staged_raw_notes_reused");
  const genericGuardPass = isNonGenericSlugOrTitle(effectiveSlug, effectiveTitle);
  const hasApplied =
    hasState(latestResult, "recap_applied") ||
    hasState(latestResult, "recap_reused") ||
    hasState(latestResult, "normalized_created") ||
    hasState(latestResult, "normalized_reused");
  const hasUsablePreview = hasPreview || hasApplied;
  const hasFrontmatterSeed = hasState(latestResult, "frontmatter_seed_found");
  const hasBreadcrumb = hasState(latestResult, "breadcrumb_found");
  const canMaterialize =
    !busy &&
    !!latestResult &&
    hasBreadcrumb;
  const canBuildFrontmatterSeed =
    !busy &&
    !!latestResult &&
    hasApplied &&
    !hasFrontmatterSeed;
  const canRunBreadcrumbIngest =
    !busy &&
    !!latestResult &&
    hasFrontmatterSeed &&
    !hasBreadcrumb;
  const hasMaterialized =
    hasState(latestResult, "session_memory_materialized") ||
    state.status === "ready_for_planning_activation";
  const isBuildingFrontmatterSeed = state.status === "building_frontmatter_seed";
  const isRunningBreadcrumbIngest = state.status === "running_breadcrumb_ingest";
  const isMaterializing = state.status === "materializing";
  const isRunningFullIngest = state.status === "running_full_ingest";
  const isBuildingGraphPreview = state.status === "building_graph_preview";
  const isMaterializingPreviewSupergraph = state.status === "materializing_preview_supergraph";
  const graphPreview = latestResult?.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const hasGraphSourceBundle = hasState(latestResult, "graph_source_bundle_ready");
  const hasPreviewUnionStore = hasState(latestResult, "preview_union_store_ready");
  const canBuildGraphPreview = hasMaterialized && !busy;
  const canMaterializePreviewSupergraph = hasMaterialized && !busy && Boolean(candidateGraphPath.trim() || graphPreview?.candidate_graph_path || graphPreview?.status === "candidate_validation_ready");
  const workflowSteps = [
    {
      id: "source",
      label: "Source",
      state: workflowStepState(validRecapSession && rawText.trim().length > 0, activeStep === 1),
    },
    {
      id: "preview",
      label: "Preview",
      state: workflowStepState(hasUsablePreview, activeStep === 2 && !hasUsablePreview),
    },
    {
      id: "apply",
      label: "Apply",
      state: workflowStepState(hasApplied, hasPreview && !hasApplied),
    },
    {
      id: "seed",
      label: "Seed",
      state: workflowStepState(hasFrontmatterSeed, hasApplied && !hasFrontmatterSeed),
    },
    {
      id: "breadcrumb",
      label: "Breadcrumb",
      state: workflowStepState(hasBreadcrumb, hasFrontmatterSeed && !hasBreadcrumb),
    },
    {
      id: "memory",
      label: "Memory",
      state: workflowStepState(hasMaterialized, hasBreadcrumb && !hasMaterialized),
    },
    {
      id: "graph",
      label: "Graph (advanced)",
      state: workflowStepState(hasPreviewUnionStore || hasGraphSourceBundle, false),
    },
    {
      id: "prove",
      label: "Prove",
      state: workflowStepState(hasMaterialized, hasMaterialized),
    },
  ];
  const workflowNextAction = (() => {
    if (state.status === "running_full_ingest") return "Working: running the full recap ingest pipeline.";
    if (state.status === "previewing") return "Working: staging raw notes and building the preview.";
    if (state.status === "applying") return "Working: writing canonical + normalized recap files.";
    if (state.status === "building_frontmatter_seed") return "Working: building the frontmatter seed.";
    if (state.status === "running_breadcrumb_ingest") return "Working: running breadcrumb ingest.";
    if (state.status === "materializing") return "Working: materializing session memory.";
    if (state.status === "building_graph_preview") return "Working: building the graph source-span preview bundle.";
    if (state.status === "materializing_preview_supergraph") return "Working: materializing the preview union supergraph.";
    if (hasMaterialized) return "Complete: recap memory is generated. Review the rendered recap and proof artifacts.";
    if (!validRecapSession) return "Enter a valid recap/source session number.";
    if (!rawTextSatisfied && !hasUsablePreview) return "Paste raw recap text, then continue to preview.";
    if (!hasUsablePreview) return "Next: click Generate Recap Memory. This stages, writes, breadcrumbs, and materializes in sequence.";
    if (!genericGuardPass) return "Session title is required before saving canon.";
    if (!hasApplied) return "Next: review the preview, then click Apply + Normalize.";
    if (!hasFrontmatterSeed) return "Next: click Build Frontmatter Seed, then review the generated seed.";
    if (!hasBreadcrumb) return "Next: after reviewing the seed, click Run Breadcrumb Ingest.";
    if (!hasMaterialized) return "Next: click Materialize Session Memory.";
    return "Complete: session memory is ready for planning activation.";
  })();
  const applyDisabledReason =
    hasApplied
      ? "Apply already completed or reused."
      : !hasPreview
        ? "Apply waits for Stage + Preview."
        : !genericGuardPass
          ? "Session title is required before Apply + Normalize."
          : null;
  const frontmatterDisabledReason =
    hasFrontmatterSeed
      ? "Frontmatter seed already exists."
      : !hasApplied
        ? "Build Frontmatter Seed waits for Apply + Normalize."
        : null;
  const breadcrumbDisabledReason =
    hasBreadcrumb
      ? "Breadcrumb artifact already exists."
      : !hasFrontmatterSeed
        ? "Run Breadcrumb Ingest waits for the reviewed frontmatter seed."
        : null;
  const materializeDisabledReason =
    hasMaterialized
      ? "Session memory already materialized."
      : !hasBreadcrumb
        ? "Materialize waits for breadcrumb_found."
        : null;
  const graphDisabledReason = !hasMaterialized
    ? "Build Graph Preview waits for session memory."
    : null;
  const previewSupergraphDisabledReason = hasPreviewUnionStore
    ? "Preview union store already materialized."
    : !hasMaterialized
      ? "Materialize Preview Supergraph waits for session memory."
      : !canMaterializePreviewSupergraph
        ? "Candidate graph path is required until live graph extraction is wired."
        : null;
  const canResumeFromDisk = hasApplied || hasFrontmatterSeed || hasBreadcrumb;
  const canRunFullIngest =
    !busy &&
    validRecapSession &&
    (rawTextSatisfied || canResumeFromDisk) &&
    genericGuardPass &&
    !hasMaterialized;
  const fullIngestDisabledReason =
    hasMaterialized
      ? "Session memory already materialized."
      : !rawTextSatisfied && !canResumeFromDisk
        ? "Raw recap text is required to start a new ingest."
        : !validRecapSession
          ? "Generate Recap Memory needs a valid recap/source session."
          : !genericGuardPass
            ? "Session title is required. Use a clear table title, like \"Mireward Gate Battle\"."
            : null;

  useEffect(() => {
    let cancelled = false;

    async function hydrateFromStorageAndDisk() {
      const draft = readDraft(storageKey);
      const defaultRecap = draft?.recapSession ?? defaultRecapSession(session);
      const restoredSlug = draft?.slug ?? canonicalSlugTitleForRecapSession(defaultRecap)?.slug ?? "";
      const initialSlug =
        draft?.showAdvanced && isNonGenericSlugOrTitle(restoredSlug, "") ? restoredSlug : "";
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
  const synced = sanitizedResult.session === recapSession ? syncSlugTitleFromResult(sanitizedResult) : null;
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
            prev.status === "running_full_ingest" ||
            prev.status === "applying" ||
            prev.status === "building_frontmatter_seed" ||
            prev.status === "running_breadcrumb_ingest" ||
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
    window.localStorage.removeItem(storageKey);
    setRawText("");
    setSlug("");
    setTitle("");
    setShowAdvanced(false);
    setForceStage(false);
    setForceRecap(false);
    setToast(null);
    setState({ status: "idle" });
    setLatestResult(null);
    setPreviewSignature(null);
    jumpToStep(nextStep);
  }

  function applyResultAndSyncSlug(result: RecapIngestStatus) {
    const sanitizedResult = sanitizeLatestResult(result) ?? result;
    setLatestResult(sanitizedResult);
    const synced = sanitizedResult.session === recapSession ? syncSlugTitleFromResult(sanitizedResult) : null;
    if (synced) {
      setSlug(synced.slug);
      setTitle(synced.title);
    }
  }

  function applyAutomatedResult(result: RecapIngestStatus): RecapIngestStatus {
    const sanitizedResult = sanitizeLatestResult(result) ?? result;
    setLatestResult(sanitizedResult);
    const synced = syncSlugTitleFromResult(sanitizedResult);
    if (synced) {
      setSlug(synced.slug);
      setTitle(synced.title);
    }
    return sanitizedResult;
  }

  function resultErrorMessage(result: RecapIngestStatus, fallback: string): string {
    return result.errors.length > 0 ? result.errors.join("; ") : fallback;
  }

  async function runFullIngest() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setToast({
      tone: "info",
      title: "Full ingest started",
      detail: "Running stage, apply, seed, breadcrumb, and session-memory materialization in sequence.",
      nextSteps: [],
    });
    setState({ status: "running_full_ingest" });
    jumpToStep(2);

    try {
      let currentSlug = effectiveSlug;
      let currentTitle = effectiveTitle;
      const syncFields = (result: RecapIngestStatus) => {
        const synced = result.session === recapSession ? syncSlugTitleFromResult(result) : null;
        if (synced) {
          currentSlug = synced.slug;
          currentTitle = synced.title;
        }
      };

      let result = latestResult ? applyAutomatedResult(latestResult) : null;
      if (rawTextSatisfied || !result) {
        result = applyAutomatedResult(
          await postRecapIngest({
            operation: "stage_preview",
            campaign_id: campaignId,
            session: recapSession,
            raw_text: rawText,
            slug: currentSlug.trim() || undefined,
            title: currentTitle.trim() || undefined,
            force_stage: forceStage || undefined,
          }),
        );
        syncFields(result);
        setPreviewSignature(previewSourceSignature(recapSession, rawText, currentTitle || currentSlug));
        if (result.status === "error") {
          setState({ status: "error", result, message: resultErrorMessage(result, "Stage + Preview failed") });
          return;
        }
        if (result.states.includes("staged_raw_notes_conflict") && !forceStage) {
          setState({ status: "preview_ready", result });
          setToast({
            tone: "warning",
            title: "Full ingest paused",
            detail: "Existing staged notes were reused, so the pasted text was not ingested. Use Advanced only if the pasted text should replace them.",
            nextSteps: ["Review the existing staged preview or use Advanced to replace saved raw notes and rerun full ingest."],
            sticky: true,
          });
          return;
        }
      }

      const applied =
        result.states.includes("recap_applied") ||
        result.states.includes("recap_reused") ||
        result.states.includes("normalized_created") ||
        result.states.includes("normalized_reused");
      if (!applied) {
        result = applyAutomatedResult(
          await postRecapIngest({
            operation: "apply_normalize",
            campaign_id: campaignId,
            session: recapSession,
            slug: currentSlug.trim() || undefined,
            title: currentTitle.trim() || undefined,
            force_recap: forceRecap || undefined,
          }),
        );
        syncFields(result);
        if (result.status === "error") {
          setState({ status: "error", result, message: resultErrorMessage(result, "Apply + Normalize failed") });
          return;
        }
      }

      if (!result.states.includes("frontmatter_seed_found")) {
        result = applyAutomatedResult(
          await postRecapIngest({
            operation: "build_frontmatter_seed",
            campaign_id: campaignId,
            session: recapSession,
            slug: currentSlug.trim() || undefined,
            title: currentTitle.trim() || undefined,
          }),
        );
        syncFields(result);
        if (result.status === "error") {
          setState({ status: "error", result, message: resultErrorMessage(result, "Frontmatter seed build failed") });
          return;
        }
      }

      if (!result.states.includes("breadcrumb_found")) {
        result = applyAutomatedResult(
          await postRecapIngest({
            operation: "run_breadcrumb_ingest",
            campaign_id: campaignId,
            session: recapSession,
            slug: currentSlug.trim() || undefined,
            title: currentTitle.trim() || undefined,
          }),
        );
        syncFields(result);
        if (result.status === "error") {
          setState({ status: "error", result, message: resultErrorMessage(result, "Breadcrumb ingest failed") });
          return;
        }
      }

      if (!result.states.includes("session_memory_materialized")) {
        result = applyAutomatedResult(
          await postRecapIngest({
            operation: "materialize_session_memory",
            campaign_id: campaignId,
            session: recapSession,
            slug: currentSlug.trim() || undefined,
            title: currentTitle.trim() || undefined,
            check: true,
          }),
        );
        syncFields(result);
        if (result.status === "error") {
          setState({ status: "error", result, message: resultErrorMessage(result, "Session memory materialization failed") });
          return;
        }
      }

      if (result.status === "ready_for_planning_activation" || result.states.includes("session_memory_materialized")) {
        setState({ status: "ready_for_planning_activation", result });
        setToast({
          tone: "success",
          title: "Full ingest complete",
          detail: "Recap memory generated. Open Recap View to read the recap and inspect graph chips.",
          nextSteps: [],
        });
        jumpToStep(3);
      } else {
        setState(derivePaneStateFromResult(result));
      }
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Full ingest failed",
      });
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
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
        force_stage: forceStage || undefined,
      });
      applyResultAndSyncSlug(result);
      const cleanResult = sanitizeLatestResult(result) ?? result;
      const synced = cleanResult.session === recapSession ? syncSlugTitleFromResult(cleanResult) : null;
      setPreviewSignature(
        previewSourceSignature(recapSession, rawText, synced?.title ?? (effectiveTitle || effectiveSlug)),
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
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
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

  async function buildFrontmatterSeed() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "building_frontmatter_seed" });
    setToast({
      tone: "info",
      title: "Building frontmatter seed",
      detail: "Creating the deterministic frontmatter seed for human review.",
      nextSteps: [],
    });
    try {
      const result = await postRecapIngest({
        operation: "build_frontmatter_seed",
        campaign_id: campaignId,
        session: recapSession,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
      });
      applyResultAndSyncSlug(result);
      if (result.status === "error") {
        setState({
          status: "error",
          result,
          message:
            result.errors.length > 0
              ? result.errors.join("; ")
              : "Frontmatter seed build failed",
        });
        jumpToStep(3);
        return;
      }
      setState(derivePaneStateFromResult(result));
      jumpToStep(3);
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Frontmatter seed build failed",
      });
    }
  }

  async function runBreadcrumbIngest() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "running_breadcrumb_ingest" });
    setToast({
      tone: "info",
      title: "Breadcrumb ingest started",
      detail: "Running routing-only breadcrumb tagging from the reviewed frontmatter seed.",
      nextSteps: [],
    });
    try {
      const result = await postRecapIngest({
        operation: "run_breadcrumb_ingest",
        campaign_id: campaignId,
        session: recapSession,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
      });
      applyResultAndSyncSlug(result);
      if (result.status === "error") {
        setState({
          status: "error",
          result,
          message:
            result.errors.length > 0
              ? result.errors.join("; ")
              : "Breadcrumb ingest failed",
        });
        jumpToStep(3);
        return;
      }
      setState(derivePaneStateFromResult(result));
      jumpToStep(3);
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Breadcrumb ingest failed",
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
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
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

  async function buildGraphPreview() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "building_graph_preview" });
    try {
      const result = await postRecapIngest({
        operation: "build_graph_preview_bundle",
        campaign_id: campaignId,
        session: recapSession,
        candidate_graph_path: candidateGraphPath.trim() || undefined,
      });
      applyResultAndSyncSlug(result);
      setState(derivePaneStateFromResult(result));
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Graph preview bundle build failed",
      });
    }
  }

  async function materializePreviewSupergraph() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "materializing_preview_supergraph" });
    try {
      const result = await postRecapIngest({
        operation: "materialize_preview_supergraph",
        campaign_id: campaignId,
        session: recapSession,
        candidate_graph_path: candidateGraphPath.trim() || undefined,
      });
      applyResultAndSyncSlug(result);
      if (result.states.includes("preview_union_store_ready")) {
        setState({ status: "preview_supergraph_ready", result });
      } else {
        setState(derivePaneStateFromResult(result));
      }
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Preview supergraph materialization failed",
      });
    }
  }

  function openGraphPreview() {
    if (typeof window !== "undefined") {
      window.location.assign("/plan?tool=graph-preview");
    }
  }

  function openRecapView() {
    if (typeof window !== "undefined") {
      window.location.assign(`/plan?tool=recap&session=session-${recapSession}`);
    }
  }

  async function reconcileNormalizedRecap(keepBasename: string) {
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
      const result = await postRecapIngest({
        operation: "reconcile_normalized_recap",
        campaign_id: campaignId,
        session: recapSession,
        keep_basename: keepBasename,
      });
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
        nextSteps: result.states.includes("session_memory_materialized")
          ? []
          : ["Generate Recap Memory to finish proving this session."],
        sticky: true,
      });
    } catch (error) {
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
      setReconciling(false);
    }
  }

  const report = latestResult?.ingest_report ?? {};
  const previewDiff = typeof report.preview_diff === "string" ? report.preview_diff : "";
  const proofPaths = proofPathKeys(latestResult);
  const sessionMemoryRecordCount = String(report.session_memory_record_count ?? "-");
  const sessionMemoryCheck = String(report.session_memory_check ?? "-");
  const titlePlaceholder =
    inferredTitle || `Session ${recapSession || defaultRecapSession(session)} - Mireward Gate Battle`;
  const normalizedDuplicates = normalizedRecapCandidates(latestResult);
  const corpusImpact = corpusImpactRows(latestResult);
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
  const canOpenRecapView = hasMaterialized && (state.status === "ready_for_planning_activation" || hasApplied);

  return (
    <div className="module-panel ingestion-module" data-module-id="ingestion">
      <header className="ingestion-module-header">
        <div>
          <h2 className="module-title">Raw Recap Ingestion</h2>
          <p className="module-muted">Operator prep tool over the PR92 ingestion orchestrator.</p>
          <p className="module-muted">
            Campaign: <strong>{campaignId}</strong> · Live workspace session:{" "}
            <strong>{session}</strong>
          </p>
        </div>
        <button type="button" className="wizard-step-chip" onClick={() => resetWizardFlow(1)}>
          Clear flow
        </button>
      </header>

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

      <section className="ingestion-flow-card" aria-label="Ingestion workflow progress">
        <div>
          <p className="ingestion-flow-kicker">Single workflow with human review gates</p>
          <h3>Current next action</h3>
          <p role="status" aria-live="polite">{workflowNextAction}</p>
        </div>
        <ol className="ingestion-flow-steps">
          {workflowSteps.map((step) => (
            <li key={step.id} className={`ingestion-flow-step ingestion-flow-step-${step.state}`}>
              <span>{step.label}</span>
              <strong>{step.state === "done" ? "Done" : step.state === "active" ? "Now" : "Waiting"}</strong>
            </li>
          ))}
        </ol>
      </section>

      <div className="ingestion-command-grid">
        <section className="ingestion-controls-pane" aria-label="Ingestion source and controls">
          <div className="ingestion-source-grid">
            <div>
              <label htmlFor="ingestion-recap-session">
                Recap/source session <RequiredBadge satisfied={validRecapSession} />
              </label>
              <input
                id="ingestion-recap-session"
                aria-label="Recap/source session"
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
              <label htmlFor="ingestion-title">
                Session title <RequiredBadge satisfied={genericGuardPass} />
              </label>
              <input
                id="ingestion-title"
                aria-label="Session title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder={titlePlaceholder}
              />
            </div>
            <div className="ingestion-raw-block">
              <label htmlFor="ingestion-raw-text">
                Raw recap text <RequiredBadge satisfied={rawTextSatisfied} />
              </label>
              <textarea
                id="ingestion-raw-text"
                aria-label="Raw recap text"
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                rows={18}
                placeholder="Session 22 Recap&#10;&#10;The group turns their focus..."
              />
            </div>
          </div>

          <div className="ingestion-actions ingestion-primary-actions">
            <button
              type="button"
              className="primary"
              onClick={runFullIngest}
              disabled={!canRunFullIngest}
            >
              {isRunningFullIngest ? (
                <>
                  <span className="button-inline-spinner" aria-hidden="true" />
                  Running full ingest...
                </>
              ) : (
                "Generate Recap Memory"
              )}
            </button>
          </div>

          <div className="ingestion-action-explainer">
            {fullIngestDisabledReason ? <p>{fullIngestDisabledReason}</p> : null}
            {previewInvalidated ? (
              <p>Preview invalidated by raw text/title edits. Re-run full ingest.</p>
            ) : null}
            <p className="ingestion-live-status" role="status" aria-live="polite">
              {isRunningFullIngest ? "Full ingest in progress..." : isMaterializing ? "Materialization in progress..." : ""}
            </p>
          </div>

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
                    onChange={(event) => {
                      setForceStage(event.target.checked);
                      resetWizardFlow(2);
                    }}
                  />{" "}
                  Replace saved raw notes with the pasted text
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
                  Replace existing canonical recap file
                </label>
                <p className="module-muted">
                  These controls are only for correcting prior saved files. The normal path does not need them.
                </p>
              </div>
            ) : null}
          </details>

          <details className="ingestion-advanced-fold">
            <summary>Advanced graph dogfood</summary>
            <label htmlFor="ingestion-candidate-graph-path">Candidate graph path</label>
            <input
              id="ingestion-candidate-graph-path"
              value={candidateGraphPath}
              onChange={(event) => setCandidateGraphPath(event.target.value)}
              placeholder="out/graph_memory/fixtures/candidate_graph.json"
            />
            <p className="module-muted">
              Optional preview-only candidate graph artifact. Required for preview union materialization until live graph extraction is wired.
            </p>
            <div className="ingestion-actions ingestion-manual-actions">
              <button type="button" onClick={buildGraphPreview} disabled={!canBuildGraphPreview}>
                {isBuildingGraphPreview ? "Building Graph Preview..." : "Build Graph Preview"}
              </button>
              <button type="button" onClick={materializePreviewSupergraph} disabled={!canMaterializePreviewSupergraph}>
                {isMaterializingPreviewSupergraph ? "Materializing Preview Supergraph..." : "Materialize Preview Supergraph"}
              </button>
              <button type="button" onClick={openGraphPreview} disabled={!hasPreviewUnionStore}>
                Open Graph Preview
              </button>
            </div>
            <div className="ingestion-action-explainer">
              {graphDisabledReason ? <p>{graphDisabledReason}</p> : null}
              {previewSupergraphDisabledReason ? <p>{previewSupergraphDisabledReason}</p> : null}
            </div>
          </details>

          <details className="ingestion-terminal-fold">
            <summary>Terminal path stays available</summary>
            <div className="ingestion-actions ingestion-manual-actions">
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
              <button
                type="button"
                onClick={buildFrontmatterSeed}
                disabled={!canBuildFrontmatterSeed || !validRecapSession}
              >
                {isBuildingFrontmatterSeed ? (
                  <>
                    <span className="button-inline-spinner" aria-hidden="true" />
                    Building Frontmatter Seed...
                  </>
                ) : (
                  "Build Frontmatter Seed"
                )}
              </button>
              <button
                type="button"
                onClick={runBreadcrumbIngest}
                disabled={!canRunBreadcrumbIngest || !validRecapSession}
              >
                {isRunningBreadcrumbIngest ? (
                  <>
                    <span className="button-inline-spinner" aria-hidden="true" />
                    Running Breadcrumb Ingest...
                  </>
                ) : (
                  "Run Breadcrumb Ingest"
                )}
              </button>
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
            <div className="ingestion-action-explainer">
              {applyDisabledReason ? <p>{applyDisabledReason}</p> : null}
              {frontmatterDisabledReason ? <p>{frontmatterDisabledReason}</p> : null}
              {breadcrumbDisabledReason ? <p>{breadcrumbDisabledReason}</p> : null}
              {materializeDisabledReason ? <p>{materializeDisabledReason}</p> : null}
            </div>
            <pre>
              <code>
                {[
                  `uv run python scripts/build_recap_frontmatter_seed.py --campaign ${terminalCampaign} --session ${recapSession}`,
                  "uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run --ingest-routing-only ...",
                  `uv run python scripts/materialize_session_memory.py --campaign ${terminalCampaign} --session ${recapSession} --check`,
                ].join("\n")}
              </code>
            </pre>
          </details>

          {state.status === "error" ? (
            <p className="module-error">{state.message ?? "Ingestion operation failed."}</p>
          ) : null}
          {state.status === "ready_for_planning_activation" ? (
            <div className="module-success">
              <p>Complete: session memory is ready for planning activation.</p>
              <button type="button" onClick={openRecapView} disabled={!canOpenRecapView}>
                Open Recap View
              </button>
            </div>
          ) : null}
        </section>

        <aside className="ingestion-evidence-pane" aria-label="Ingestion evidence and proof">
          <div className="ingestion-evidence-header">
            <div>
              <p className="ingestion-flow-kicker">Evidence / Preview</p>
              <strong>{hasMaterialized ? "Prove ingestion" : "Rendered markdown preview"}</strong>
            </div>
            <span className={`pill ${hasMaterialized ? "pill-success" : "pill-neutral"}`}>
              {hasMaterialized ? "ready" : "draft preview"}
            </span>
          </div>
          {hasMaterialized ? (
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
                    Apply + Normalize with a real session title first.
                  </p>
                )}
              </div>
            </div>
          ) : null}

          {latestResult?.status === "breadcrumb_required" ? (
            <div className="ingestion-boundary-card" role="status">
              <strong>Expected v1 boundary: breadcrumb required</strong>
              <p>
                Canonical recap and normalized recap are on disk. Retrieval is not ready until a blessed
                breadcrumb and session memory records exist.
              </p>
              <p>
                Build the deterministic frontmatter seed, review it, run routing-only breadcrumb tagging,
                then materialize session memory.
              </p>
            </div>
          ) : null}

          {latestResult?.states.includes("staged_raw_notes_conflict") ? (
            <div className="ingestion-boundary-card">
              <strong>Existing staged notes reused</strong>
              <p>
                Stage + Preview found staged raw notes already on disk, so the preview uses those notes and
                did not overwrite it with the pasted text.
              </p>
            </div>
          ) : null}

          <div
            className="md-content md-theme-command ingestion-rendered-preview"
            dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(rawText) }}
          />

          <section className="ingestion-proof-card" aria-label="Graph preview status">
            <h4>Graph</h4>
            <p className="module-muted">Preview supergraph only. No canon graph write.</p>
            <div className="ingestion-proof-metrics">
              <span className="pill pill-neutral">status: {graphPreview?.status ?? "missing"}</span>
              <span className="pill pill-neutral">nodes: {graphPreview?.node_count ?? 0}</span>
              <span className="pill pill-neutral">edges: {graphPreview?.edge_count ?? 0}</span>
            </div>
            {graphPreview?.blocked_reason ? <p className="module-muted">{graphPreview.blocked_reason}</p> : null}
            {graphPreview?.manifest_path ? <p><code>{graphPreview.manifest_path}</code></p> : null}
            {graphPreview?.preview_union_store_path ? <p><code>{graphPreview.preview_union_store_path}</code></p> : null}
          </section>

          <section className="ingestion-proof-card" aria-label="Ingestion proof artifacts">
            <h4>Prove</h4>
            <p className="module-muted">
              UI-first proof uses current API metadata: artifact paths, session-memory counts, and entity
              review rows.
            </p>
            <div className="ingestion-proof-metrics">
              <span className="pill pill-neutral">records: {sessionMemoryRecordCount}</span>
              <span className="pill pill-neutral">check: {sessionMemoryCheck}</span>
            </div>
            <ul className="ingestion-proof-paths">
              {proofPaths.map((key) => {
                const value = latestResult?.paths?.[key] ?? null;
                const statusLabel = pathStatus(latestResult, key);
                return (
                  <li key={key} className={`ingestion-proof-path ingestion-proof-path-${statusLabel}`}>
                    <span>{pathLabel(key)}</span>
                    <strong>{statusLabel === "done" ? "Found" : "Waiting"}</strong>
                    <code>{value ?? "not reported yet"}</code>
                  </li>
                );
              })}
            </ul>
          </section>

          {corpusImpact.length > 0 ? (
            <section className="ingestion-proof-card" aria-label="What was ingested">
              <h4>What was ingested?</h4>
              <p className="module-muted">
                Read-only corpus impact from the latest ingest/status check.
              </p>
              <div className="ingestion-impact-list">
                {corpusImpact.map((row) => (
                  <details key={`${row.key}-${row.relpath}`} className="ingestion-impact-row">
                    <summary>
                      <span>{pathLabel(row.key)}</span>
                      <strong>{row.exists ? "Found" : "Missing"}</strong>
                      {typeof row.record_count === "number" ? (
                        <span className="pill pill-neutral">records: {row.record_count}</span>
                      ) : null}
                    </summary>
                    <code>{row.relpath}</code>
                    {row.exists ? (
                      <p className="module-muted">
                        {formatBytes(row.size_bytes ?? 0)}
                        {row.modified_at ? ` - ${new Date(row.modified_at).toLocaleString()}` : ""}
                      </p>
                    ) : null}
                    {row.preview ? <pre>{row.preview}</pre> : null}
                  </details>
                ))}
              </div>
            </section>
          ) : null}

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
                  <h5>Errors</h5>
                  <ul>{evidenceRows(latestResult.errors)}</ul>
                </div>
                <div>
                  <h5>Next actions</h5>
                  <ul>{evidenceRows(latestResult.next_actions)}</ul>
                </div>
              </div>

              <details open>
                <summary>Canonical preview</summary>
                <ul>
                  <li>title_line_stripped: {String(report.title_line_stripped ?? false)}</li>
                  <li>paragraph_count_in: {String(report.paragraph_count_in ?? "-")}</li>
                  <li>paragraph_count_out: {String(report.paragraph_count_out ?? "-")}</li>
                  <li>duplicates_detected: {String(report.duplicates_detected ?? "-")}</li>
                  <li>duplicates_removed: {String(report.duplicates_removed ?? "-")}</li>
                  <li>session_memory_record_count: {sessionMemoryRecordCount}</li>
                  <li>session_memory_check: {sessionMemoryCheck}</li>
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
                  <li>breadcrumbed recap -&gt; {latestResult.authority.breadcrumbed_recap}</li>
                  <li>session memory -&gt; {latestResult.authority.session_memory}</li>
                </ul>
                <p className="module-muted">Raw notes are not normal retrieval evidence after a recap exists.</p>
                <p className="module-muted">Planning scaffold is not proof of what happened.</p>
                <p className="module-muted">Roll tables are reference tools, not play facts.</p>
              </details>

              <details open>
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
        </aside>
      </div>
    </div>
  );
}
