import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { getRecapArtifacts, getHistoricalRecapInspection, postWorldGraphRecapProjection, postCitationSource } from "../api/liveApi";
import { postRecapIngest } from "../api/recapIngestApi";
import type {
  NormalizedRecapCandidate,
  RecapArtifactRecord,
  RecapGraphPreviewReport,
  RecapIngestStatus,
  WorldGraphRecapProjection,
  WorldGraphProjection,
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
  ignoreDiskResume?: boolean;
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
    (result.status === "initialized" || result.status === "ready_for_planning_activation" || result.status === "recap_applied")
  ) {
    return null;
  }

  const warningSet = new Set(result.warnings);
  const {
    confirmed: recapSourceConfirmed,
    missing: recapSourceMissing,
    hasProofRows: hasRecapSourceProofRows,
    actionStateConfirmed: recapSourceActionConfirmed,
  } = recapSourceProof(result);
  const inspectedDiskStatus = result.states.includes("ingest_status_inspected");
  const breadcrumbSourceIncomplete =
    result.status === "breadcrumb_required" &&
    (recapSourceMissing ||
      ((inspectedDiskStatus || hasRecapSourceProofRows) && !recapSourceConfirmed) ||
      (!inspectedDiskStatus && !recapSourceConfirmed && !recapSourceActionConfirmed));
  const nextSteps = breadcrumbSourceIncomplete ? [] : [...result.next_actions];
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
    if (breadcrumbSourceIncomplete) {
      nextSteps.unshift(
        recapSourceMissing
          ? "The disk check did not find both canonical and normalized recap files. Restore or load the verified source before continuing."
          : "The latest status did not confirm both canonical and normalized recap files. Restore or load the source before continuing.",
      );
    } else {
      nextSteps.unshift(
        "Breadcrumb + session memory are not retrieval-ready yet.",
        "Bless the frontmatter seed and breadcrumb artifact, then inspect status before materializing session memory.",
      );
    }
  }

  if (result.status === "ready_for_planning_activation") {
    nextSteps.unshift("Review in workbench to read the recap and inspect graph chips.");
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
      ? "Session files and graph came from existing staged notes. The pasted text was not written."
      : result.status === "ready_for_planning_activation" && stagedRawConflict
        ? "Session files were packaged from existing staged notes. The pasted text was not written."
      : stagedRawConflict
        ? "Existing staged raw notes were found, so the preview uses those notes. The pasted text was not written."
      : frontmatterSeedReady
        ? "Frontmatter seed is ready for human review before breadcrumb ingest."
      : result.status === "ready_for_planning_activation" && graphBlocked
        ? `Session packaged. Graph extract was blocked: ${graphPreview?.blocked_reason ?? "unknown reason"}.`
      : result.status === "ready_for_planning_activation" && graphMaterialized
        ? "Session packaged and graph is on disk. Review in workbench."
      : result.status === "ready_for_planning_activation"
        ? "Session packaged. Next: Run ingest to extract the graph."
      : result.status === "breadcrumb_required"
      ? breadcrumbSourceIncomplete
        ? recapSourceMissing
          ? "The disk check found one or both recap files missing. Restore or load the verified recap before continuing."
          : "The latest status did not confirm both recap files. Restore or load the verified recap before continuing."
        : "Retrieval is waiting for breadcrumb + session memory. Check the per-file evidence for the next safe step."
      : result.errors.length > 0
        ? result.errors.join("; ")
        : result.warnings.length > 0
          ? result.warnings.join("; ")
          : "Operation completed.";

  return {
    tone,
    title:
      result.status === "ready_for_planning_activation" && stagedRawConflict
        ? "Prep complete using staged notes"
      : stagedRawConflict
        ? "Existing staged notes reused"
        : frontmatterSeedReady
          ? "Frontmatter seed ready"
        : result.status === "breadcrumb_required"
        ? breadcrumbSourceIncomplete
          ? recapSourceMissing
            ? "Recap source missing"
            : "Recap source needs confirmation"
          : "Breadcrumb required before retrieval"
        : result.status === "ready_for_planning_activation" && graphMaterialized
          ? "Ingest ready"
        : result.status === "ready_for_planning_activation"
          ? "Prep complete"
        : `Ingestion ${result.status}`,
    detail,
    nextSteps: uniqueNextSteps.filter((step) => step !== detail).slice(0, 4),
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
  const [activeStep, setActiveStep] = useState<number>(1);
  const [rawText, setRawText] = useState("");
  const rawRecapTextAreaRef = useRef<HTMLTextAreaElement | null>(null);
  const [recapSession, setRecapSession] = useState<number>(() => initialRecapSession);
  const selectedIngestTarget = JSON.stringify([ingestCampaignId, recapSession]);
  const selectedIngestTargetRef = useRef(selectedIngestTarget);
  selectedIngestTargetRef.current = selectedIngestTarget;
  const recapDraftEpochRef = useRef(0);
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [reviewSource, setReviewSource] = useState<{ prose: string; identity: string; session: number; nodes: number; edges: number; projection: WorldGraphRecapProjection | null; runId?: string } | null>(null);
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
  const [primaryOp, setPrimaryOp] = useState<"prep" | "ingest" | null>(null);
  const [candidateGraphPath, setCandidateGraphPath] = useState("");
  const [extractGraphWithModel, setExtractGraphWithModel] = useState(false);
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
  const [priorIngestionArtifacts, setPriorIngestionArtifacts] = useState<RecapArtifactRecord[]>([]);
  const [selectedPriorArtifactId, setSelectedPriorArtifactId] = useState("");
  const [loadingPriorIngestion, setLoadingPriorIngestion] = useState(false);
  const [priorSourceReadFailed, setPriorSourceReadFailed] = useState(false);
  const [ignoreDiskResume, setIgnoreDiskResume] = useState(false);
  const inspectedTargetRef = useRef("");
  const lastToastKeyRef = useRef<string | null>(null);
  /** When set, the result→toast effect skips one cycle so Prep/Run can own the toast. */
  const suppressResultToastRef = useRef(false);
  const hydrateInspectGenerationRef = useRef(0);
  const validRecapSession = Number.isInteger(recapSession) && recapSession > 0;
  const terminalCampaign = campaignNumberFromId(ingestCampaignId);

  function handleIngestCampaignSelect(nextCampaignId: string) {
    if (nextCampaignId === ingestCampaignId) return;
    invalidateInFlightRecapOperations();
    selectedIngestTargetRef.current = JSON.stringify([nextCampaignId, recapSession]);
    invalidateInFlightHydrateInspect();
    setIngestCampaignId(nextCampaignId);
    syncReviewCampaignUrl(nextCampaignId);
    setHydrated(false);
    setIgnoreDiskResume(false);
    setLatestResult(null);
    setState({ status: "idle" });
    setPreviewSignature(null);
    setSourceMode("raw");
    setLoadedArtifact(null);
    setProcessedPreviewText("");
    setSelectedPriorArtifactId("");
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
    invalidateInFlightHydrateInspect();
    setRecapSession(nextSession);
    setLatestResult(null);
    setState({ status: "idle" });
    setPreviewSignature(null);
    setSourceMode("raw");
    setLoadedArtifact(null);
    setProcessedPreviewText("");
    setSelectedPriorArtifactId("");
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
      const sanitizedResult = sanitizeLatestResult(inspected) ?? inspected;
      setLatestResult(sanitizedResult);
      inspectedTargetRef.current = identity;
      const synced = syncSlugTitleFromResult(sanitizedResult);
      if (synced) {
        setSlug(synced.slug);
        setTitle(synced.title);
      }
      setActiveStep((current) => Math.max(current, deriveStepFromResult(sanitizedResult)));
      setState(derivePaneStateFromResult(sanitizedResult));
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
  const currentPreviewSignature = useMemo(
    () => previewSourceSignature(recapSession, rawText, effectiveTitle || effectiveSlug),
    [recapSession, rawText, effectiveSlug, effectiveTitle],
  );
  const previewInvalidated =
    previewSignature != null && previewSignature !== currentPreviewSignature;
  const rawTextSatisfied = rawText.trim().length > 0;
  const matchingResult =
    latestResult?.campaign_id === ingestCampaignId && latestResult.session === recapSession
      ? latestResult
      : null;
  const resultOwnsSelection =
    hydrated &&
    matchingResult !== null;
  // Transient wizard actions require a result for the current selection;
  // saved-file proof additionally requires hydrated status for that selection.
  const proofResult = resultOwnsSelection ? matchingResult : null;
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
    (hasState(matchingResult, "recap_preview_created") &&
      !previewInvalidated &&
      previewSignature === currentPreviewSignature) ||
    hasState(matchingResult, "staged_raw_notes_reused");
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
    recapSourceNavigationProof.normalizedCurrent &&
    (!rawTextSatisfied ||
      (previewSignature === currentPreviewSignature && !previewInvalidated));
  const hasFrontmatterSeed = hasState(matchingResult, "frontmatter_seed_found");
  const hasBreadcrumb = hasState(matchingResult, "breadcrumb_found");
  const canResumeFromDisk = hasApplied || hasFrontmatterSeed || hasBreadcrumb;
  const processedSourceReady =
    sourceMode === "processed" &&
    loadedArtifact !== null &&
    processedPreviewText.trim().length > 0 &&
    hasCurrentNormalizedSource;
  const sourceInputSatisfied =
    rawTextSatisfied ||
    processedSourceReady ||
    (canResumeFromDisk && hasCurrentNormalizedSource);
  const canMaterialize =
    !busy &&
    !!matchingResult &&
    hasBreadcrumb;
  const canBuildFrontmatterSeed =
    !busy &&
    !!matchingResult &&
    hasApplied &&
    !hasFrontmatterSeed;
  const canRunBreadcrumbIngest =
    !busy &&
    !!matchingResult &&
    hasFrontmatterSeed &&
    !hasBreadcrumb;
  const hasMaterialized =
    hasState(matchingResult, "session_memory_materialized") ||
    (resultOwnsSelection && state.status === "ready_for_planning_activation");
  const isBuildingFrontmatterSeed = state.status === "building_frontmatter_seed";
  const isRunningBreadcrumbIngest = state.status === "running_breadcrumb_ingest";
  const isMaterializing = state.status === "materializing";
  const isRunningFullIngest = state.status === "running_full_ingest";
  const isBuildingGraphPreview = state.status === "building_graph_preview";
  const isMaterializingPreviewSupergraph = state.status === "materializing_preview_supergraph";
  const graphPreview = proofResult?.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
  const selectedReaderRun = readerRun?.campaign === ingestCampaignId && readerRun.session === `session-${recapSession}` ? readerRun.runId : null;
  const reviewIdentity = JSON.stringify([ingestCampaignId, recapSession, selectedReaderRun ?? (resultOwnsSelection ? graphPreview?.extraction_run_id : null) ?? null]);
  useLayoutEffect(() => {
    currentReviewIdentity.current = reviewIdentity;
    reviewEpoch.current += 1;
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
    (resultOwnsSelection && (hasCurrentNormalizedSource || hasPreview));
  const showRecapWelcome =
    hydrated &&
    !readerMode &&
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
  const ingestReadiness = useMemo(() => buildIngestReadiness(matchingResult), [matchingResult]);
  const workflowNextAction = (() => {
    if (!sourceInputSatisfied && !hasNormalizedRecap) {
      return "Load a processed recap or paste the verified source to continue.";
    }
    if (!validRecapSession) return "Choose a session number before preparing this recap.";
    if (!genericGuardPass) return "Add a specific session title before preparing this recap.";
    if (state.status === "running_full_ingest") {
      return primaryOp === "ingest"
        ? "Working: running ingest (LLM graph extract + party fill)."
        : "Working: prepping session files (normalize / package recap).";
    }
    if (state.status === "previewing") return "Working: staging raw notes and building the preview.";
    if (state.status === "applying") return "Working: writing canonical + normalized recap files.";
    if (state.status === "building_frontmatter_seed") return "Working: building the frontmatter seed.";
    if (state.status === "running_breadcrumb_ingest") return "Working: running breadcrumb ingest.";
    if (state.status === "materializing") return "Working: materializing session memory.";
    if (state.status === "building_graph_preview") return "Working: building the graph source-span preview bundle.";
    if (state.status === "materializing_preview_supergraph") return "Working: materializing the preview union supergraph.";
    if (hasPreviewUnionStore && forceGraphRun) {
      return "Ready to replace the existing graph: Run ingest to start a fresh extraction.";
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
    ? `Preview union on disk${previewUnionSizeHint}. Check "Replace existing graph" then Run ingest.`
    : !hasNormalizedRecap
      ? "Materialize Preview Supergraph waits for a normalized recap."
      : !hasCurrentNormalizedSource
        ? "Materialize Preview Supergraph waits for confirmed recap files and current normalized lineage."
      : !canMaterializePreviewSupergraph
        ? "Candidate graph path or Run ingest is required before preview union materialization."
        : null;
  // Run ingest = LLM graph extract from an already-packaged normalized recap.
  const canRunIngest =
    !busy &&
    validRecapSession &&
    hasCurrentNormalizedSource &&
    (!hasPreviewUnionStore || forceGraphRun) &&
    genericGuardPass;
  // Prep = package session files only (no LLM graph extract).
  const canPrepForIngest =
    !busy &&
    validRecapSession &&
    sourceInputSatisfied &&
    genericGuardPass;
  const runIngestDisabledReason =
    hasPreviewUnionStore && !forceGraphRun
      ? `Graph already on disk${previewUnionSizeHint}. Check "Replace existing graph" to re-run ingest.`
      : !hasNormalizedRecap
        ? "Prep for ingest first (package the normalized recap on disk)."
        : !validRecapSession
          ? "Run ingest needs a valid session number."
          : !genericGuardPass
            ? "Session title is required before running ingest."
            : null;
  useEffect(() => {
    let cancelled = false;

    async function hydrateFromStorageAndDisk() {
      const inspectGeneration = hydrateInspectGenerationRef.current;
      const draft = readDraft(storageKey);
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
        setIgnoreDiskResume(false);
      } else {
        setActiveStep(usableDraft.activeStep);
        setRawText(usableDraft.rawText);
        setRecapSession(usableDraft.recapSession);
        setSlug(usableDraft.slug);
        setTitle(usableDraft.title);
        setShowAdvanced(usableDraft.showAdvanced);
        setForceStage(usableDraft.forceStage);
        setForceRecap(usableDraft.forceRecap);
        setState(restoredIgnoreDiskResume ? usableDraft.state : { status: "idle" });
        setLatestResult(restoredIgnoreDiskResume ? usableDraft.latestResult : null);
        setPreviewSignature(usableDraft.previewSignature);
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
            const savedResult =
              usableDraft?.latestResult?.campaign_id === ingestCampaignId &&
              usableDraft.latestResult.session === defaultRecap
                ? usableDraft.latestResult
                : null;
            const mergedWithDraft = mergeInspectResult(savedResult, inspected);
            const sanitizedResult = sanitizeLatestResult(mergedWithDraft) ?? mergedWithDraft;
            setLatestResult((prev) => {
              const matchingPrevious =
                prev?.campaign_id === ingestCampaignId && prev.session === defaultRecap
                  ? prev
                  : savedResult;
              const merged = mergeInspectResult(matchingPrevious, inspected);
              return sanitizeLatestResult(merged) ?? merged;
            });
            if (inspected.campaign_id === ingestCampaignId && inspected.session === defaultRecap) {
              inspectedTargetRef.current = JSON.stringify([ingestCampaignId, defaultRecap]);
            }
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
                prev.status === "materializing"
              ) {
                return prev;
              }
              return derivePaneStateFromResult(sanitizedResult);
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
        if (cancelled) return;
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
        setPriorIngestionArtifacts(records);
        setSelectedPriorArtifactId((current) => current || (freshRecapEntry ? "" : records.at(-1)?.artifact_id || ""));
      })
      .catch(() => {
        if (!cancelled) {
          setPriorIngestionArtifacts([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [ingestCampaignId, hydrated, freshRecapEntry]);

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
      ignoreDiskResume,
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
    ignoreDiskResume,
  ]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    const maybeToast = buildToastForResult(latestResult, {
      fallbackErrorMessage: state.status === "error" ? state.message : undefined,
      forceStage,
      forceRecap,
      genericGuardPass,
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
      // Prep/Run already set an explicit toast; adopt the auto-toast key so
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
  }, [hydrated, latestResult, state, forceStage, forceRecap, genericGuardPass]);

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

  function resetWizardFlow(nextStep = 1) {
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
    setProcessedPreviewText("");
    setSelectedPriorArtifactId("");
    setToast(null);
    setState({ status: "idle" });
    setLatestResult(null);
    setPreviewSignature(null);
    setPrimaryOp(null);
    setReconciling(false);
    setLoadingPriorIngestion(false);
    jumpToStep(nextStep);
  }

  function startNewRecap(nextStep = 1) {
    setIgnoreDiskResume(true);
    resetWizardFlow(nextStep);
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
    setPreviewSignature(null);
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
      setActiveStep(Math.max(1, deriveStepFromResult(inspected)));
      setState(derivePaneStateFromResult(inspected));

      const normalizedPath =
        inspected.paths?.normalized_recap ??
        record.source_recap_path;
      const citationPath = corpusCitationPath(normalizedPath);
      const source = await postCitationSource({ path: citationPath });
      if (
        requestGeneration !== hydrateInspectGenerationRef.current ||
        selectedIngestTargetRef.current !== targetIdentity
      ) return;
      if (!source.content.trim()) throw new Error("The saved recap source was empty.");
      setProcessedPreviewText(source.content);

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
      setProcessedPreviewText("");
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

  async function runIngest() {
    if (!canRunIngest) return;
    const targetIdentity = selectedIngestTarget;
    const draftEpoch = recapDraftEpochRef.current;
    setReaderRun(null);
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setPrimaryOp("ingest");
    publishPrimaryToast({
      tone: "info",
      title: "Ingest started",
      detail: "Running LLM graph extract (and party fill) from the packaged recap.",
      nextSteps: [],
    });
    setState({ status: "running_full_ingest" });
    jumpToStep(2);

    try {
      const response = await postForSelectedIngestTarget({
          operation: "generate_recap_memory",
          campaign_id: ingestCampaignId,
          managed_world_id: managedWorldId,
          session: recapSession,
          slug: effectiveSlug || undefined,
          title: effectiveTitle || undefined,
          check: true,
          include_graph_extraction: true,
          include_legacy_breadcrumb: false,
          graph_model_id: "deepseek/deepseek-v4.1-flash",
          force_graph_run: forceGraphRun || undefined,
        }, targetIdentity);
      if (!response) return;
      const result = applyAutomatedResult(response);

      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Ingest failed") });
        return;
      }

      const candidate = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
      if (candidate?.status === "candidate_validation_ready" && !candidate.blocked_reason) {
        setState(derivePaneStateFromResult(result));
        publishPrimaryToast({
          tone: "success",
          title: "Extraction ready for review",
          detail: "The extracted candidate is saved. Review and admission are still required before it is written to the World Graph.",
          nextSteps: ["Review extracted candidate"],
          sticky: true,
        });
        jumpToStep(3);
        return;
      }

      if (result.status === "ready_for_planning_activation" || result.states.includes("session_memory_materialized")) {
        const preview = result.ingest_report?.graph_preview as RecapGraphPreviewReport | undefined;
        const graphBlocked =
          preview?.extraction_mode === "llm_blocked" ||
          Boolean(preview?.blocked_reason && preview?.status !== "preview_union_store_ready");
        const graphMaterialized = preview?.status === "preview_union_store_ready";
        const resultError = result.errors[0]?.trim() || "";
        const blockedReason = preview?.blocked_reason?.trim() || "";
        const ok = graphMaterialized && !graphBlocked && !resultError;
        setState({ status: "ready_for_planning_activation", result });
        publishPrimaryToast({
          tone: ok ? "success" : "warning",
          title: ok ? "Ingest complete" : "Ingest finished with warnings",
          detail: resultError
            ? resultError
            : graphBlocked
              ? `Graph extract was blocked: ${blockedReason || "unknown reason"}`
            : graphMaterialized
              ? forceGraphRun
                ? "Replaced the existing graph with a fresh extract from the packaged recap."
                : "Graph extract finished. Review the preview graph in the workbench."
              : "Ingest finished; review the Graph status panel for the next step.",
          nextSteps: ok
            ? ["Review in workbench"]
            : ["Check Graph status / errors", "Retry Run ingest after fixing"],
          sticky: true,
        });
        jumpToStep(3);
      } else {
        setState(derivePaneStateFromResult(result));
        publishPrimaryToast({
          tone: "warning",
          title: "Ingest finished with warnings",
          detail:
            result.errors[0]?.trim() ||
            `Unexpected ingest status: ${result.status}. Review the status panel.`,
          nextSteps: ["Check Graph status / errors"],
          sticky: true,
        });
      }
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      const message = error instanceof Error ? error.message : "Ingest failed";
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message,
      });
      publishPrimaryToast({
        tone: "error",
        title: "Ingest failed",
        detail: message,
        nextSteps: ["Retry Run ingest", "Check API / logs if it keeps failing"],
        sticky: true,
      });
    } finally {
      if (
        recapDraftEpochRef.current === draftEpoch &&
        selectedIngestTargetRef.current === targetIdentity
      ) setPrimaryOp(null);
    }
  }

  async function prepForIngest() {
    if (!canPrepForIngest) return;
    const targetIdentity = selectedIngestTarget;
    const draftEpoch = recapDraftEpochRef.current;
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setPrimaryOp("prep");
    publishPrimaryToast({
      tone: "info",
      title: "Prep started",
      detail: "Packaging the session recap on disk (no LLM graph extract yet).",
      nextSteps: [],
    });
    setState({ status: "running_full_ingest" });
    jumpToStep(2);

    try {
      const response = await postForSelectedIngestTarget({
          operation: "generate_recap_memory",
          campaign_id: ingestCampaignId,
          session: recapSession,
          raw_text: sourceMode === "raw" ? rawText : undefined,
          slug: effectiveSlug || undefined,
          title: effectiveTitle || undefined,
          force_stage: forceStage || undefined,
          force_recap: forceRecap || undefined,
          check: true,
          include_graph_extraction: false,
          include_legacy_breadcrumb: false,
        }, targetIdentity);
      if (!response) return;
      const result = applyAutomatedResult(response);
      const synced = result.session === recapSession ? syncSlugTitleFromResult(result) : null;
      setPreviewSignature(
        previewSourceSignature(
          recapSession,
          sourceMode === "raw" ? rawText : processedPreviewText,
          synced?.title ?? (effectiveTitle || effectiveSlug),
        ),
      );

      if (result.status === "error") {
        setState({ status: "error", result, message: resultErrorMessage(result, "Prep failed") });
        return;
      }
      if (result.states.includes("staged_raw_notes_conflict") && !forceStage && !result.states.includes("session_memory_materialized")) {
        setState({ status: "preview_ready", result });
        setToast({
          tone: "warning",
          title: "Prep paused",
          detail: "Existing staged notes were reused, so the pasted text was not written. Use Advanced only if the pasted text should replace them.",
          nextSteps: ["Review the staged preview, or use Advanced to replace saved raw notes and prep again."],
          sticky: true,
        });
        return;
      }

      if (
        result.status === "ready_for_planning_activation" ||
        result.states.includes("session_memory_materialized") ||
        result.states.includes("normalized_created") ||
        result.states.includes("normalized_reused") ||
        result.states.includes("recap_applied")
      ) {
        const stagedRawConflict = result.states.includes("staged_raw_notes_conflict");
        setState(derivePaneStateFromResult(result));
        publishPrimaryToast({
          tone: stagedRawConflict ? "warning" : "success",
          title: stagedRawConflict ? "Prep complete using staged notes" : "Prep complete",
          detail: stagedRawConflict
            ? "Session files were packaged from existing staged notes. The pasted text was not written. Next: Run ingest."
            : "Session recap is packaged on disk. Next: Run ingest to extract the graph.",
          nextSteps: ["Run ingest"],
        });
        jumpToStep(2);
      } else {
        setState(derivePaneStateFromResult(result));
      }
    } catch (error) {
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Prep failed",
      });
    } finally {
      if (
        recapDraftEpochRef.current === draftEpoch &&
        selectedIngestTargetRef.current === targetIdentity
      ) setPrimaryOp(null);
    }
  }

  async function stagePreview() {
    const targetIdentity = selectedIngestTarget;
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "previewing" });
    try {
      const result = await postForSelectedIngestTarget({
        operation: "stage_preview",
        campaign_id: ingestCampaignId,
        session: recapSession,
        raw_text: rawText,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
        force_stage: forceStage || undefined,
      }, targetIdentity);
      if (!result) return;
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
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Stage + Preview failed",
      });
    }
  }

  async function applyNormalize() {
    const targetIdentity = selectedIngestTarget;
    invalidateInFlightHydrateInspect();
    lastToastKeyRef.current = null;
    setState({ status: "applying" });
    try {
      const result = await postForSelectedIngestTarget({
        operation: "apply_normalize",
        campaign_id: ingestCampaignId,
        session: recapSession,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
        force_recap: forceRecap || undefined,
      }, targetIdentity);
      if (!result) return;
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
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Apply + Normalize failed",
      });
    }
  }

  async function buildFrontmatterSeed() {
    const targetIdentity = selectedIngestTarget;
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
      const result = await postForSelectedIngestTarget({
        operation: "build_frontmatter_seed",
        campaign_id: ingestCampaignId,
        session: recapSession,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
      }, targetIdentity);
      if (!result) return;
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
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Frontmatter seed build failed",
      });
    }
  }

  async function runBreadcrumbIngest() {
    const targetIdentity = selectedIngestTarget;
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
      const result = await postForSelectedIngestTarget({
        operation: "run_breadcrumb_ingest",
        campaign_id: ingestCampaignId,
        session: recapSession,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
      }, targetIdentity);
      if (!result) return;
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
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Breadcrumb ingest failed",
      });
    }
  }

  async function materializeSessionMemory() {
    const targetIdentity = selectedIngestTarget;
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
      const result = await postForSelectedIngestTarget({
        operation: "materialize_session_memory",
        campaign_id: ingestCampaignId,
        session: recapSession,
        slug: effectiveSlug || undefined,
        title: effectiveTitle || undefined,
        check: true,
      }, targetIdentity);
      if (!result) return;
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
      if (selectedIngestTargetRef.current !== targetIdentity) return;
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Session memory materialization failed",
      });
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
    const nodes = graphPreview?.candidate_node_count ?? 0;
    const edges = graphPreview?.candidate_edge_count ?? 0;
    const isCurrent = () => epoch === reviewEpoch.current && identity === currentReviewIdentity.current;
    setReviewLoading(true);
    setReviewError(null);
    setReviewSource(null);
    try {
      let prose: string;
      if (runId) {
        const inspection = await getHistoricalRecapInspection(runId);
        if (!isCurrent()) return;
        if (inspection.runId !== runId || inspection.campaignId !== ingestCampaignId || inspection.sessionId !== `session-${capturedSession}`) {
          throw new Error("Saved extraction does not match this session.");
        }
        if (inspection.sourceStatus !== "available" || !inspection.sourceProse) throw new Error(inspection.unavailableReason || "Saved source is unavailable.");
        prose = inspection.sourceProse;
      } else {
        const record = priorIngestionArtifacts.find((item) => item.campaign_id === ingestCampaignId && item.session_id === `session-${capturedSession}`);
        const path = resultOwnsSelection ? latestResult?.paths?.normalized_recap : null;
        if (!record && !path) throw new Error("No saved recap is available for this session.");
        const source = await postCitationSource({ path: corpusCitationPath(path || record!.source_recap_path) });
        if (!isCurrent()) return;
        prose = source.content;
      }
      setReviewSource({ prose, identity, session: capturedSession, nodes, edges, runId, projection: null });
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
        // Shared verifier reads only the common snapshot contract.
        response: projection as unknown as WorldGraphProjection,
        revisionKind: "head",
      });
      if (integrityError) throw new Error(integrityError);
      setReviewSource({ prose, identity, session: capturedSession, nodes, edges, runId, projection });
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
        nextSteps: result.states.includes("session_memory_materialized")
          ? []
          : ["Prep for ingest, then Run ingest."],
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
  const sessionMemoryRecordCount = String(report.session_memory_record_count ?? "-");
  const sessionMemoryCheck = String(report.session_memory_check ?? "-");
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
      matchingResult?.status === "breadcrumb_required" &&
      recapSourceUnconfirmed,
  );
  const showSavedWorkRecovery = showSourceProofRecovery && hasPriorIngestWork && recapSourceMissing;
  const showWorkflowFeedback =
    showWorkflowActions ||
    Boolean(toast) ||
    state.status === "error" ||
    showSourceProofRecovery;

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
            <button
              type="button"
              className="ingest-local-nav__primary-action"
              onClick={() => showRecapWelcome ? rawRecapTextAreaRef.current?.focus() : startNewRecap(1)}
            >
              {showRecapWelcome ? "Paste recap" : "New recap"}
            </button>
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
              <div className="ingest-local-nav__stages" role="group" aria-label="Extraction actions">
                <button
                  type="button"
                  aria-label={primaryOp === "prep" ? "Preparing recap" : "Prep for ingest"}
                  className={hasNormalizedRecap ? undefined : "primary"}
                  onClick={() => void prepForIngest()}
                  disabled={!canPrepForIngest}
                >
                  {primaryOp === "prep" ? <><span className="button-inline-spinner" aria-hidden="true" /> Prepping…</> : "Prepare"}
                </button>
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
                  aria-label={primaryOp === "ingest" ? "Extracting graph" : forceGraphRun && hasPreviewUnionStore ? "Run ingest (replace graph)" : "Run ingest"}
                  className={hasNormalizedRecap ? "primary" : undefined}
                  onClick={() => void runIngest()}
                  disabled={!canRunIngest}
                >
                  {primaryOp === "ingest" ? <><span className="button-inline-spinner" aria-hidden="true" /> Extracting…</> : "Extract"}
                </button>
                {hasNormalizedRecap ? (
                  <button type="button" aria-label={reviewLoading ? "Opening review…" : "Review recap canvas"} className="primary" disabled={reviewLoading} onClick={() => void reviewSavedSource()}>
                    {reviewLoading ? "Opening review…" : "Review"}
                  </button>
                ) : null}
                {isIngestSurfacePath() && hasPreviewUnionStore ? (
                  <button type="button" onClick={openGraphReviewWorkbench}>Review in workbench</button>
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
                : primaryOp === "ingest"
                  ? "Extracting graph…"
                  : primaryOp === "prep"
                    ? "Preparing recap…"
                    : isMaterializing
                      ? "Materializing graph…"
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

      <div className="ingestion-command-grid">
        <section className="ingestion-controls-pane" aria-label="Recap editor">
          <div className="ingestion-source-grid">
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
            ) : showPreparedSourceNotice ? (
              <div className="ingestion-prepared-source-notice" role="note" aria-label="Prepared recap source">
                <strong>Prepared recap · Session {recapSession}</strong>
                <p>
                  This recap is prepared on disk. Its text is not loaded in this editor.
                </p>
              </div>
            ) : (
              <div className="ingestion-raw-block">
                <label htmlFor="ingestion-raw-text">
                  Raw recap text <RequiredBadge satisfied={rawTextSatisfied} />
                </label>
                <textarea
                  id="ingestion-raw-text"
                  aria-label="Raw recap text"
                  ref={rawRecapTextAreaRef}
                  value={rawText}
                  onChange={(event) => {
                    setRawText(event.target.value);
                    setSourceMode("raw");
                    setPriorSourceReadFailed(false);
                  }}
                  rows={18}
                  placeholder="Paste or write the session recap here…"
                />
              </div>
            )}
          </div>

          <div className="ingestion-action-explainer">
            {hasNormalizedRecap && runIngestDisabledReason && !(hasPreviewUnionStore && !forceGraphRun) ? (
              <p>{runIngestDisabledReason}</p>
            ) : null}
            {previewInvalidated ? (
              <p>Preview invalidated by raw text/title edits. Prep for ingest again.</p>
            ) : null}
          </div>
        </section>

        <aside className="ingestion-evidence-pane" aria-label="Ingestion evidence and proof">
          {reviewError ? <p role="alert" className="module-error">{reviewError} {reviewError.includes("credential") || reviewError.includes("graph_auth_required") ? "Open Advanced → Native Graph access to connect the local Graph session." : ""}</p> : null}
          {reviewSource !== null && reviewSource.identity === reviewIdentity ? (
            <section aria-label="Saved extraction source review">
              {reviewSource.projection ? <>
              <p>{reviewSource.runId ? "Current World Graph context. This extraction is awaiting Graph admission." : "Canonical saved recap with current World Graph context."}</p>
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
              </> : <article aria-label="Loaded recap">
                <h3>Session {reviewSource.session}</h3>
                <div className="md-content md-theme-command" dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(reviewSource.prose.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "")) }} />
              </article>}
              <button type="button" onClick={closeSavedReader}>Close review</button>
            </section>
          ) : null}
          <details id="ingestion-evidence-details" ref={evidenceDetailsRef}><summary>Evidence &amp; details</summary>
          <NativeGraphAccessControl onChanged={(available) => {
            reviewEpoch.current += 1;
            setReviewSource(null);
            setReviewError(null);
            setReviewLoading(false);
            if (available && readerMode) void reviewSavedSource(true);
          }} />
          {reviewSource ? <pre aria-label="Recap frontmatter">{reviewSource.projection?.markdown.match(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/)?.[0] ?? "No frontmatter"}</pre> : null}
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
            <p className="module-muted">Manual artifact controls for testing graph extraction/materialization outside Prep → Run ingest.</p>
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
              <strong>
                {recapSourceUnconfirmed
                  ? recapSourceMissing
                    ? "Canonical and normalized recap files are not both present"
                    : "Canonical and normalized recap files need verification"
                  : "Expected v1 boundary: breadcrumb required"}
              </strong>
              {recapSourceUnconfirmed ? (
                <p>
                  Restore or load/paste the verified recap before continuing. Breadcrumb routing and
                  session-memory steps come after both recap files are confirmed present.
                </p>
              ) : (
                <p>
                  Retrieval is not retrieval-ready until a blessed breadcrumb and session memory records
                  exist. The per-file evidence below is the source of truth for canonical and normalized
                  recap availability.
                </p>
              )}
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
              <span className="pill pill-neutral">records: {sessionMemoryRecordCount}</span>
              <span className="pill pill-neutral">check: {sessionMemoryCheck}</span>
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
                      confirm both sources: restore or load the recap before following breadcrumb steps.
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
