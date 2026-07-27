import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { getRecapArtifacts, postCitationSource } from "../api/liveApi";
import { postRecapIngest } from "../api/recapIngestApi";
import type {
  NormalizedRecapCandidate,
  RecapArtifactRecord,
  RecapGraphPreviewReport,
  RecapIngestStatus,
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
import { buildIngestReadiness } from "./ingestReadiness";
import { mergeInspectResult } from "./ingestResultMerge";

interface IngestionModuleProps {
  campaignId: string;
  session: number;
}

const INGESTION_DRAFT_STORAGE_VERSION = 3;

type IngestionSourceMode = "raw" | "processed";

function isIngestSurfacePath(): boolean {
  if (typeof window === "undefined") return false;
  return window.location.pathname.replace(/\/+$/, "") === "/ingest";
}

function corpusCitationPath(relpath: string): string {
  const trimmed = relpath.trim().replace(/^\/+/, "");
  if (trimmed.startsWith("corpus/")) {
    return trimmed;
  }
  return `corpus/eldyrwild-markdown/${trimmed}`;
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

function requestedRecapSessionFromLocation(): number | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("session")?.trim();
  const match = raw?.match(/^session-(\d+)$/i);
  if (!match) return null;
  const session = Number.parseInt(match[1], 10);
  return Number.isFinite(session) && session > 0 ? session : null;
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
      result.status === "ready_for_planning_activation"
        ? "Existing staged notes were reused for the completed ingest."
        : "Existing staged notes were reused for this preview.",
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

  const graphPreview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const graphMaterialized = graphPreview?.status === "preview_union_store_ready";
  const graphBlocked = graphPreview?.extraction_mode === "llm_blocked" || Boolean(graphPreview?.blocked_reason && graphPreview.status !== "preview_union_store_ready");
  const uniqueNextSteps = [...new Set(nextSteps)].filter(Boolean);

  const tone: IngestionToastTone =
    result.status === "ready_for_planning_activation" && graphBlocked
      ? "warning"
      : result.status === "ready_for_planning_activation" && stagedRawConflict
        ? "warning"
      : result.status === "ready_for_planning_activation"
      ? "success"
      : frontmatterSeedReady
        ? "success"
      : stagedRawConflict
        ? "warning"
      : result.status === "error"
        ? "error"
        : "info";

  const detail =
    result.status === "ready_for_planning_activation" && stagedRawConflict && graphMaterialized
      ? "Recap memory and graph projection were generated from the existing staged notes. The pasted text was not written."
      : result.status === "ready_for_planning_activation" && stagedRawConflict
        ? "Recap memory was generated from the existing staged notes. The pasted text was not written."
      : stagedRawConflict
        ? "Existing staged raw notes were found, so the preview uses those notes. The pasted text was not written."
      : frontmatterSeedReady
        ? "Frontmatter seed is ready for human review before breadcrumb ingest."
      : result.status === "ready_for_planning_activation" && graphBlocked
        ? `Recap memory generated. Preview graph extraction was blocked: ${graphPreview?.blocked_reason ?? "unknown reason"}. Open Recap View for published World Graph memory; use Graph Review for unpublished candidates.`
      : result.status === "ready_for_planning_activation" && graphMaterialized
        ? "Recap memory generated and preview graph materialized. Open Recap View to inspect graph-backed chips."
      : result.status === "ready_for_planning_activation"
        ? "Recap memory generated. Open Recap View to read the recap."
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
      result.status === "ready_for_planning_activation" && stagedRawConflict
        ? "Full ingest complete using staged notes"
      : stagedRawConflict
        ? "Existing staged notes reused"
        : frontmatterSeedReady
          ? "Frontmatter seed ready"
        : result.status === "breadcrumb_required"
        ? "Breadcrumb required before retrieval"
        : `Ingestion ${result.status}`,
    detail,
    nextSteps: uniqueNextSteps.slice(0, 4),
    sticky: tone === "error" || (stagedRawConflict && result.status !== "ready_for_planning_activation"),
  };
}

function previewSourceSignature(recapSession: number, rawText: string, slug: string): string {
  return JSON.stringify({
    recapSession,
    rawText: rawText.trim(),
    slug: slug.trim(),
  });
}

export function IngestionModule({ campaignId: planCampaignId, session }: IngestionModuleProps) {
  const projection = useOptionalProjection();
  const [ingestCampaignId, setIngestCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(planCampaignId),
  );
  const storageKey = useMemo(
    () => draftStorageKey(ingestCampaignId, session),
    [ingestCampaignId, session],
  );
  const requestedRecapSession = requestedRecapSessionFromLocation();
  const initialRecapSession = requestedRecapSession ?? defaultRecapSession(session);
  const [activeStep, setActiveStep] = useState<number>(1);
  const [rawText, setRawText] = useState("");
  const [recapSession, setRecapSession] = useState<number>(() => initialRecapSession);
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [forceStage, setForceStage] = useState(false);
  const [forceRecap, setForceRecap] = useState(false);
  const [forceGraphRun, setForceGraphRun] = useState(false);
  const [candidateGraphPath, setCandidateGraphPath] = useState("");
  const [extractGraphWithMini, setExtractGraphWithMini] = useState(false);
  const [state, setState] = useState<IngestionPaneState>({ status: "idle" });
  const [latestResult, setLatestResult] = useState<RecapIngestStatus | null>(null);
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [toast, setToast] = useState<IngestionToast | null>(null);
  const [reconcileChoice, setReconcileChoice] = useState<string | null>(null);
  const [reconciling, setReconciling] = useState(false);
  const [sourceMode, setSourceMode] = useState<IngestionSourceMode>("raw");
  const [loadedArtifact, setLoadedArtifact] = useState<RecapArtifactRecord | null>(null);
  const [processedPreviewText, setProcessedPreviewText] = useState("");
  const [processedPreviewPath, setProcessedPreviewPath] = useState<string | null>(null);
  const [priorIngestionArtifacts, setPriorIngestionArtifacts] = useState<RecapArtifactRecord[]>([]);
  const [selectedPriorArtifactId, setSelectedPriorArtifactId] = useState("");
  const [loadingPriorIngestion, setLoadingPriorIngestion] = useState(false);
  const lastToastKeyRef = useRef<string | null>(null);
  const hydrateInspectGenerationRef = useRef(0);
  const validRecapSession = Number.isInteger(recapSession) && recapSession > 0;
  const terminalCampaign = campaignNumberFromId(ingestCampaignId);

  function handleIngestCampaignSelect(nextCampaignId: string) {
    if (nextCampaignId === ingestCampaignId) return;
    invalidateInFlightHydrateInspect();
    setIngestCampaignId(nextCampaignId);
    syncReviewCampaignUrl(nextCampaignId);
    setHydrated(false);
    window.dispatchEvent(new Event(GRAPH_REVIEW_RUNS_CHANGED_EVENT));
  }

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
  const canResumeFromDisk = hasApplied || hasFrontmatterSeed || hasBreadcrumb;
  const processedSourceReady = sourceMode === "processed" && hasApplied;
  const sourceInputSatisfied = rawTextSatisfied || processedSourceReady || canResumeFromDisk;
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
  // Trust live graph_preview.status only — draft states must not claim materialized.
  const hasPreviewUnionStore = graphPreview?.status === "preview_union_store_ready";
  const hasNormalizedRecap = hasApplied;
  const canBuildGraphPreview = hasNormalizedRecap && !busy && (!hasPreviewUnionStore || forceGraphRun);
  const canMaterializePreviewSupergraph = hasNormalizedRecap && !busy && (!hasPreviewUnionStore || forceGraphRun) && Boolean(
    extractGraphWithMini ||
    candidateGraphPath.trim() ||
    graphPreview?.candidate_graph_path ||
    graphPreview?.status === "candidate_validation_ready",
  );
  const ingestReadiness = useMemo(() => buildIngestReadiness(latestResult), [latestResult]);
  const readinessLanes = [ingestReadiness.memory, ingestReadiness.graph, ingestReadiness.attention];
  const workflowNextAction = (() => {
    if (state.status === "running_full_ingest") {
      return "Working: normalizing recap, then category graph extraction (actors → locations → collectives → objects → threads → beats → edges).";
    }
    if (state.status === "previewing") return "Working: staging raw notes and building the preview.";
    if (state.status === "applying") return "Working: writing canonical + normalized recap files.";
    if (state.status === "building_frontmatter_seed") return "Working: building the frontmatter seed.";
    if (state.status === "running_breadcrumb_ingest") return "Working: running breadcrumb ingest.";
    if (state.status === "materializing") return "Working: materializing session memory.";
    if (state.status === "building_graph_preview") return "Working: building the graph source-span preview bundle.";
    if (state.status === "materializing_preview_supergraph") return "Working: materializing the preview union supergraph.";
    if (hasPreviewUnionStore && forceGraphRun) {
      return "Ready to replace the preview graph: run category graph extraction to start a fresh extraction run.";
    }
    return ingestReadiness.nextAction;
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
  const graphDisabledReason = !hasNormalizedRecap
    ? "Build Graph Preview waits for a normalized recap (Apply + Normalize)."
    : null;
  const previewUnionSizeHint =
    typeof graphPreview?.node_count === "number"
      ? ` (${graphPreview.node_count} nodes${
          typeof graphPreview.edge_count === "number" ? `, ${graphPreview.edge_count} edges` : ""
        })`
      : "";
  const previewSupergraphDisabledReason = hasPreviewUnionStore && !forceGraphRun
    ? `Preview union on disk${previewUnionSizeHint}. Check "Replace existing preview graph" to start a new extraction run.`
    : !hasNormalizedRecap
      ? "Materialize Preview Supergraph waits for a normalized recap."
      : !canMaterializePreviewSupergraph
        ? "Candidate graph path or category graph extraction is required before preview union materialization."
        : null;
  const canRunGraphExtractionOnly =
    !busy &&
    validRecapSession &&
    hasNormalizedRecap &&
    (!hasPreviewUnionStore || forceGraphRun) &&
    genericGuardPass &&
    (sourceMode === "processed" || canResumeFromDisk);
  const canRunFullIngest =
    !busy &&
    validRecapSession &&
    sourceInputSatisfied &&
    genericGuardPass &&
    (!hasPreviewUnionStore || forceGraphRun);
  const graphExtractionDisabledReason =
    hasPreviewUnionStore && !forceGraphRun
      ? `Preview union on disk${previewUnionSizeHint}. Check "Replace existing preview graph" to re-extract with updated party context.`
      : !hasNormalizedRecap
        ? "Load a processed recap with a normalized file on disk first."
        : !validRecapSession
          ? "Graph extraction needs a valid recap/session number."
          : !genericGuardPass
            ? "Session title is required before running graph extraction."
            : sourceMode !== "processed" && !canResumeFromDisk
              ? "Load a prior ingestion or paste raw recap text."
              : null;
  const fullIngestDisabledReason =
    hasPreviewUnionStore && !forceGraphRun
      ? `Session memory ready; preview union on disk${previewUnionSizeHint}. Check "Replace existing preview graph" to re-run extraction.`
      : !sourceInputSatisfied && !hasMaterialized
        ? "Paste raw recap text or load a prior processed ingestion."
        : !validRecapSession
          ? "Generate Recap Memory needs a valid recap/source session."
          : !genericGuardPass
            ? "Session title is required. Use a clear table title, like \"Mireward Gate Battle\"."
            : null;

  useEffect(() => {
    let cancelled = false;

    async function hydrateFromStorageAndDisk() {
      const draft = readDraft(storageKey);
      const usableDraft =
        requestedRecapSession != null && draft?.recapSession !== requestedRecapSession
          ? null
          : draft;
      const defaultRecap = requestedRecapSession ?? usableDraft?.recapSession ?? defaultRecapSession(session);
      const restoredSlug = usableDraft?.slug ?? canonicalSlugTitleForRecapSession(defaultRecap)?.slug ?? "";
      const initialSlug =
        usableDraft?.showAdvanced && isNonGenericSlugOrTitle(restoredSlug, "") ? restoredSlug : "";
      const initialTitle = usableDraft?.title ?? canonicalSlugTitleForRecapSession(defaultRecap)?.title ?? "";

      if (!usableDraft) {
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
        setActiveStep(usableDraft.activeStep);
        setRawText(usableDraft.rawText);
        setRecapSession(usableDraft.recapSession);
        setSlug(usableDraft.slug);
        setTitle(usableDraft.title);
        setShowAdvanced(usableDraft.showAdvanced);
        setForceStage(usableDraft.forceStage);
        setForceRecap(usableDraft.forceRecap);
        setState(usableDraft.state);
        setLatestResult(usableDraft.latestResult);
        setPreviewSignature(usableDraft.previewSignature);
      }

      try {
        const inspectGeneration = hydrateInspectGenerationRef.current;
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
        const mergedWithDraft = mergeInspectResult(usableDraft?.latestResult ?? null, inspected);
        const sanitizedResult = sanitizeLatestResult(mergedWithDraft) ?? mergedWithDraft;
        setLatestResult((prev) => {
          const merged = mergeInspectResult(prev ?? usableDraft?.latestResult ?? null, inspected);
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
  }, [storageKey, session, ingestCampaignId, requestedRecapSession]);

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
        if (cancelled) return;
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
        setPriorIngestionArtifacts(records);
        setSelectedPriorArtifactId((current) => current || records.at(-1)?.artifact_id || "");
      })
      .catch(() => {
        if (!cancelled) {
          setPriorIngestionArtifacts([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [ingestCampaignId, hydrated]);

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
    setForceGraphRun(false);
    setSourceMode("raw");
    setLoadedArtifact(null);
    setProcessedPreviewText("");
    setProcessedPreviewPath(null);
    setSelectedPriorArtifactId("");
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

  async function loadPriorIngestion(record: RecapArtifactRecord) {
    const sessionNumber = recapSessionNumber(record.session_id);
    if (sessionNumber == null || sessionNumber <= 0) {
      setToast({
        tone: "error",
        title: "Could not load ingestion",
        detail: "Selected artifact has no numeric session id.",
        nextSteps: [],
        sticky: true,
      });
      return;
    }

    invalidateInFlightHydrateInspect();
    setLoadingPriorIngestion(true);
    setSourceMode("processed");
    setLoadedArtifact(record);
    setRawText("");
    setRecapSession(sessionNumber);
    setTitle(titleFromArtifact(record));
    setSlug("");
    setPreviewSignature(null);
    lastToastKeyRef.current = null;

    try {
      const inspected = await postRecapIngest({
        operation: "inspect_status",
        campaign_id: ingestCampaignId,
        session: sessionNumber,
        title: titleFromArtifact(record) || undefined,
      });
      applyResultAndSyncSlug(inspected);
      setActiveStep(Math.max(1, deriveStepFromResult(inspected)));
      setState(derivePaneStateFromResult(inspected));

      const normalizedPath =
        inspected.paths?.normalized_recap ??
        record.source_recap_path;
      const citationPath = corpusCitationPath(normalizedPath);
      try {
        const source = await postCitationSource({ path: citationPath });
        setProcessedPreviewText(source.content);
        setProcessedPreviewPath(source.path);
      } catch {
        setProcessedPreviewText("");
        setProcessedPreviewPath(citationPath);
      }

      setToast({
        tone: "info",
        title: "Loaded processed recap",
        detail: `Session ${sessionNumber} normalized recap is ready for category graph extraction without re-pasting raw notes.`,
        nextSteps: ["Run category graph extraction when upstream recap memory steps are already satisfied."],
      });
    } catch (error) {
      setSourceMode("raw");
      setLoadedArtifact(null);
      setProcessedPreviewText("");
      setProcessedPreviewPath(null);
      setToast({
        tone: "error",
        title: "Could not load prior ingestion",
        detail: error instanceof Error ? error.message : "Load failed",
        nextSteps: [],
        sticky: true,
      });
    } finally {
      setLoadingPriorIngestion(false);
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

  async function runGraphExtractionOnly() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setToast({
      tone: "info",
      title: "Category graph extraction started",
      detail: "Running graph extraction and preview union materialization from the on-disk normalized recap.",
      nextSteps: [],
    });
    setState({ status: "running_full_ingest" });
    jumpToStep(2);

    try {
      const result = applyAutomatedResult(
        await postRecapIngest({
          operation: "generate_recap_memory",
          campaign_id: ingestCampaignId,
          session: recapSession,
          slug: effectiveSlug || undefined,
          title: effectiveTitle || undefined,
          check: true,
          include_graph_extraction: true,
          include_legacy_breadcrumb: false,
          graph_model_id: "gpt-5.4-mini",
          force_graph_run: forceGraphRun || undefined,
        }),
      );

      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Graph extraction failed") });
        return;
      }

      if (result.status === "ready_for_planning_activation" || result.states.includes("session_memory_materialized")) {
        const preview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
        const graphBlocked =
          preview?.extraction_mode === "llm_blocked" ||
          Boolean(preview?.blocked_reason && preview?.status !== "preview_union_store_ready");
        const graphMaterialized = preview?.status === "preview_union_store_ready";
        setState({ status: "ready_for_planning_activation", result });
        setToast({
          tone: graphBlocked ? "warning" : "success",
          title: graphMaterialized ? "Graph extraction complete" : "Graph extraction finished with warnings",
          detail: graphBlocked
            ? `Preview graph extraction was blocked: ${preview?.blocked_reason ?? "unknown reason"}.`
            : graphMaterialized
              ? forceGraphRun
                ? "Replaced the preview graph with a fresh category extraction run from the loaded normalized recap."
                : "Category graph extraction and preview union materialization completed from the loaded normalized recap."
              : "Graph extraction finished; review the status panel for the next step.",
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
        message: error instanceof Error ? error.message : "Graph extraction failed",
      });
    }
  }

  async function runFullIngest() {
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setToast({
      tone: "info",
      title: "Recap + graph ingest started",
      detail: "Running recap memory generation, then preview graph extraction and materialization.",
      nextSteps: [],
    });
    setState({ status: "running_full_ingest" });
    jumpToStep(2);

    try {
      const result = applyAutomatedResult(
        await postRecapIngest({
          operation: "generate_recap_memory",
          campaign_id: ingestCampaignId,
          session: recapSession,
          raw_text: sourceMode === "raw" ? rawText : undefined,
          slug: effectiveSlug || undefined,
          title: effectiveTitle || undefined,
          force_stage: forceStage || undefined,
          force_recap: forceRecap || undefined,
          check: true,
          include_graph_extraction: true,
          include_legacy_breadcrumb: false,
          graph_model_id: "gpt-5.4-mini",
          force_graph_run: forceGraphRun || undefined,
        }),
      );
      const synced = result.session === recapSession ? syncSlugTitleFromResult(result) : null;
      setPreviewSignature(
        previewSourceSignature(
          recapSession,
          sourceMode === "raw" ? rawText : processedPreviewText,
          synced?.title ?? (effectiveTitle || effectiveSlug),
        ),
      );

      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Full ingest failed") });
        return;
      }
      if (result.states.includes("staged_raw_notes_conflict") && !forceStage && !result.states.includes("session_memory_materialized")) {
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

      if (result.status === "ready_for_planning_activation" || result.states.includes("session_memory_materialized")) {
        const graphPreview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
        const graphBlocked = graphPreview?.extraction_mode === "llm_blocked" || Boolean(graphPreview?.blocked_reason && graphPreview.status !== "preview_union_store_ready");
        const stagedRawConflict = result.states.includes("staged_raw_notes_conflict");
        const graphMaterialized = graphPreview?.status === "preview_union_store_ready";
        setState({ status: "ready_for_planning_activation", result });
        setToast({
          tone: graphBlocked || stagedRawConflict ? "warning" : "success",
          title: stagedRawConflict ? "Full ingest complete using staged notes" : "Full ingest complete",
          detail: graphBlocked
            ? `Recap memory generated. Preview graph extraction was blocked: ${graphPreview?.blocked_reason ?? "unknown reason"}. Open Recap View for published World Graph memory; use Graph Review for unpublished candidates.`
            : stagedRawConflict && graphMaterialized
              ? "Recap memory and graph projection were generated from the existing staged notes. The pasted text was not written."
            : stagedRawConflict
              ? "Recap memory was generated from the existing staged notes. The pasted text was not written."
            : "Recap memory generated and preview graph materialized. Open Recap View to inspect graph-backed chips.",
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
        campaign_id: ingestCampaignId,
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
        campaign_id: ingestCampaignId,
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
        campaign_id: ingestCampaignId,
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
        campaign_id: ingestCampaignId,
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
        campaign_id: ingestCampaignId,
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
        campaign_id: ingestCampaignId,
        session: recapSession,
        candidate_graph_path: extractGraphWithMini ? undefined : candidateGraphPath.trim() || undefined,
        extract_graph: extractGraphWithMini,
        graph_model_id: extractGraphWithMini ? "gpt-5.4-mini" : undefined,
        force_graph_run: forceGraphRun || undefined,
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
        campaign_id: ingestCampaignId,
        session: recapSession,
        candidate_graph_path: extractGraphWithMini ? undefined : candidateGraphPath.trim() || undefined,
        extract_graph: extractGraphWithMini,
        graph_model_id: extractGraphWithMini ? "gpt-5.4-mini" : undefined,
        materialize_after_extract: extractGraphWithMini,
        force_graph_run: forceGraphRun || undefined,
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
      window.location.assign(`/plan?tool=graph-preview&session=session-${recapSession}`);
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

  function openRecapView() {
    if (typeof window !== "undefined") {
      window.location.assign(
        `/plan?tool=recap&campaign=${encodeURIComponent(ingestCampaignId)}&session=session-${recapSession}`,
      );
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
        campaign_id: ingestCampaignId,
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
  const sessionMemoryRecordCount = String(report.session_memory_record_count ?? "-");
  const sessionMemoryCheck = String(report.session_memory_check ?? "-");
  const titlePlaceholder =
    inferredTitle || `Session ${recapSession || defaultRecapSession(session)} - Mireward Gate Battle`;
  const normalizedDuplicates = normalizedRecapCandidates(latestResult);
  const corpusImpact = corpusImpactRows(latestResult);
  const proofRows =
    corpusImpact.length > 0
      ? corpusImpact.map((row) => ({
          key: row.key,
          relpath: row.relpath,
          exists: row.exists,
          record_count: row.record_count,
        }))
      : proofPathKeys(latestResult).map((key) => ({
          key,
          relpath: latestResult?.paths?.[key] ?? null,
          exists: false,
          record_count: undefined as number | undefined,
        }));
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
  const canOpenRecapView =
    hasApplied && (state.status === "ready_for_planning_activation" || hasApplied);

  return (
    <div className="module-panel ingestion-module" data-module-id="ingestion">
      <header className="ingestion-module-header">
        <div>
          <h2 className="module-title">Raw Recap Ingestion</h2>
          <p className="module-muted">Operator prep tool over the PR92 ingestion orchestrator.</p>
          <div className="ingestion-module-header-meta">
            <ReviewCampaignPicker
              selectedCampaignId={ingestCampaignId}
              onSelect={handleIngestCampaignSelect}
              className="graph-preview-run-picker ingestion-campaign-picker"
            />
            <p className="module-muted">
              Live workspace session: <strong>{session}</strong>
            </p>
          </div>
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
          <p className="ingestion-flow-kicker">Readiness from on-disk inspect</p>
          <h3>Current next action</h3>
          <p role="status" aria-live="polite">{workflowNextAction}</p>
        </div>
        <ol className="ingestion-flow-steps ingestion-readiness-lanes">
          {readinessLanes.map((lane) => (
            <li
              key={lane.id}
              className={`ingestion-flow-step ingestion-flow-step-${lane.state === "ready" ? "done" : lane.state === "blocked" ? "active" : lane.state === "not_ready" ? "active" : "locked"}`}
            >
              <span>{lane.label}</span>
              <strong>
                {lane.state === "ready"
                  ? "Ready"
                  : lane.state === "blocked"
                    ? "Blocked"
                    : lane.state === "not_ready"
                      ? "Not ready"
                      : "Idle"}
              </strong>
              <p className="ingestion-readiness-detail">{lane.detail}</p>
            </li>
          ))}
        </ol>
      </section>

      <div className="ingestion-command-grid">
        <section className="ingestion-controls-pane" aria-label="Ingestion source and controls">
          <div className="ingestion-source-grid">
            <section className="ingestion-flow-card ingestion-prior-load-card">
              <p className="ingestion-flow-kicker">Load prior ingestion</p>
              <p className="module-muted">
                Resume from an on-disk normalized recap instead of re-pasting raw notes.
              </p>
              <div className="ingestion-prior-load-row">
                <label htmlFor="ingestion-prior-artifact">
                  Processed recap
                  <select
                    id="ingestion-prior-artifact"
                    aria-label="Prior processed recap"
                    value={selectedPriorArtifactId}
                    onChange={(event) => setSelectedPriorArtifactId(event.target.value)}
                    disabled={priorIngestionArtifacts.length === 0 || loadingPriorIngestion}
                  >
                    {priorIngestionArtifacts.length === 0 ? (
                      <option value="">No prior ingestions found</option>
                    ) : (
                      priorIngestionArtifacts.map((record) => (
                        <option key={record.artifact_id} value={record.artifact_id}>
                          {recapArtifactSessionLabel(record)}
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => void loadSelectedPriorIngestion()}
                  disabled={loadingPriorIngestion || priorIngestionArtifacts.length === 0}
                >
                  {loadingPriorIngestion ? "Loading…" : "Load processed recap"}
                </button>
              </div>
              {loadedArtifact ? (
                <p className="module-muted">
                  Loaded <code>{loadedArtifact.source_recap_path}</code>
                  {processedPreviewPath ? (
                    <>
                      {" "}
                      · preview from <code>{processedPreviewPath}</code>
                    </>
                  ) : null}
                </p>
              ) : null}
            </section>

            <div className="ingestion-source-mode-toggle">
              <button
                type="button"
                className={sourceMode === "raw" ? "active" : undefined}
                aria-pressed={sourceMode === "raw"}
                onClick={() => setSourceMode("raw")}
              >
                Paste raw recap
              </button>
              <button
                type="button"
                className={sourceMode === "processed" ? "active" : undefined}
                aria-pressed={sourceMode === "processed"}
                disabled={!loadedArtifact}
                onClick={() => setSourceMode("processed")}
              >
                Loaded processed recap
              </button>
            </div>

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
            {sourceMode === "processed" ? (
              <div className="ingestion-raw-block">
                <label htmlFor="ingestion-processed-preview">
                  Normalized recap preview <RequiredBadge satisfied={processedSourceReady} />
                </label>
                <textarea
                  id="ingestion-processed-preview"
                  aria-label="Normalized recap preview"
                  value={processedPreviewText}
                  readOnly
                  rows={18}
                  placeholder="Load a prior ingestion to preview the normalized recap that graph extraction will use."
                />
              </div>
            ) : (
              <div className="ingestion-raw-block">
                <label htmlFor="ingestion-raw-text">
                  Raw recap text <RequiredBadge satisfied={rawTextSatisfied} />
                </label>
                <textarea
                  id="ingestion-raw-text"
                  aria-label="Raw recap text"
                  value={rawText}
                  onChange={(event) => {
                    setRawText(event.target.value);
                    setSourceMode("raw");
                  }}
                  rows={18}
                  placeholder="Session 22 Recap&#10;&#10;The group turns their focus..."
                />
              </div>
            )}
          </div>

          <div className="ingestion-actions ingestion-primary-actions">
            {hasPreviewUnionStore ? (
              <label className="ingestion-checkbox-row ingestion-replace-graph-row">
                <input
                  type="checkbox"
                  checked={forceGraphRun}
                  onChange={(event) => setForceGraphRun(event.target.checked)}
                />
                Replace existing preview graph (new category extraction run)
              </label>
            ) : null}
            {(processedSourceReady || (hasPreviewUnionStore && hasNormalizedRecap)) ? (
              <button
                type="button"
                className="primary"
                onClick={() => void runGraphExtractionOnly()}
                disabled={!canRunGraphExtractionOnly}
              >
                {isRunningFullIngest ? (
                  <>
                    <span className="button-inline-spinner" aria-hidden="true" />
                    Running category graph extraction...
                  </>
                ) : forceGraphRun && hasPreviewUnionStore ? (
                  "Replace preview graph (re-extract)"
                ) : (
                  "Run category graph extraction"
                )}
              </button>
            ) : null}
            {isIngestSurfacePath() && hasPreviewUnionStore ? (
              <button
                type="button"
                className="primary"
                onClick={openGraphReviewWorkbench}
              >
                Review in workbench
              </button>
            ) : null}
            <button
              type="button"
              className={processedSourceReady ? undefined : "primary"}
              onClick={() => void runFullIngest()}
              disabled={!canRunFullIngest}
            >
              {isRunningFullIngest && !processedSourceReady ? (
                <>
                  <span className="button-inline-spinner" aria-hidden="true" />
                  Running recap + preview graph...
                </>
              ) : (
                "Generate Recap Memory"
              )}
            </button>
          </div>

          <div className="ingestion-action-explainer">
            {hasPreviewUnionStore && !forceGraphRun ? (
              <p>
                A preview graph already exists for this session. Check &quot;Replace existing preview graph&quot; to
                re-run category extraction — useful when testing party registry anchors or gold-alignment changes.
              </p>
            ) : null}
            {(processedSourceReady || forceGraphRun) && graphExtractionDisabledReason ? (
              <p>{graphExtractionDisabledReason}</p>
            ) : null}
            {fullIngestDisabledReason ? <p>{fullIngestDisabledReason}</p> : null}
            {previewInvalidated ? (
              <p>Preview invalidated by raw text/title edits. Re-run full ingest.</p>
            ) : null}
            <p className="ingestion-live-status" role="status" aria-live="polite">
              {isRunningFullIngest
                ? "Working: generating recap memory, then extracting and materializing preview graph."
                : isMaterializing
                  ? "Materialization in progress..."
                  : ""}
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
            <p className="module-muted">Manual artifact controls for testing graph extraction/materialization outside the one-click recap flow.</p>
            <label className="ingestion-checkbox-row">
              <input
                type="checkbox"
                checked={forceGraphRun}
                onChange={(event) => setForceGraphRun(event.target.checked)}
              />
              Replace existing preview graph before building or materializing
            </label>
            <label htmlFor="ingestion-candidate-graph-path">Candidate graph path</label>
            <input
              id="ingestion-candidate-graph-path"
              value={candidateGraphPath}
              onChange={(event) => setCandidateGraphPath(event.target.value)}
              placeholder="out/graph_memory/fixtures/candidate_graph.json"
              disabled={extractGraphWithMini}
            />
            <label className="ingestion-checkbox-row">
              <input
                type="checkbox"
                checked={extractGraphWithMini}
                onChange={(event) => {
                  const checked = event.target.checked;
                  setExtractGraphWithMini(checked);
                  if (checked) setCandidateGraphPath("");
                }}
              />
              Extract graph from recap with category extraction (gpt-5.4-mini)
            </label>
            <p className="module-muted">
              Optional preview-only candidate graph artifact. When category extraction is enabled, the backend runs seven structured passes over the normalized recap.
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
          {canOpenRecapView ? (
            <div className="module-success">
              <button type="button" onClick={openRecapView}>
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
            <p className="module-muted">Graph extraction: {graphPreview?.status === "preview_union_store_ready" ? "preview graph materialized" : graphPreview?.extraction_mode === "llm_blocked" ? "blocked" : graphPreview?.status === "candidate_validation_ready" ? "candidate ready" : graphPreview?.status === "source_span_bundle_ready" ? "candidate pending" : isRunningFullIngest ? "extracting" : graphPreview?.status ?? "pending"}</p>
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
              <span className="pill pill-neutral">records: {sessionMemoryRecordCount}</span>
              <span className="pill pill-neutral">check: {sessionMemoryCheck}</span>
            </div>
            <ul className="ingestion-proof-paths">
              {proofRows.map((row) => {
                const statusLabel = row.exists ? "done" : "waiting";
                return (
                  <li key={row.key} className={`ingestion-proof-path ingestion-proof-path-${statusLabel}`}>
                    <span>{pathLabel(row.key)}</span>
                    <strong>{row.exists ? "Found" : "Missing"}</strong>
                    <code>{row.relpath ?? "not reported yet"}</code>
                    {typeof row.record_count === "number" ? (
                      <span className="pill pill-neutral">records: {row.record_count}</span>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </section>

          {corpusImpact.length > 0 ? (
            <section className="ingestion-proof-card" aria-label="What was ingested">
              <h4>What was ingested?</h4>
              <p className="module-muted">
                Read-only corpus impact previews from the latest ingest/status check.
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
