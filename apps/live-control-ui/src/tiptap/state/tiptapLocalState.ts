import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { hasBlockingMarkdownImportDiagnostics } from "../markdown/markdownToTiptap";
import { migrateLegacyTiptapReferenceLabels } from "../references/runbookReferences";
import { preserveLeadingYamlFrontmatter } from "../markdown/stripLeadingYamlFrontmatter";

export const WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA = "dmb_workspace_document_local_state_v5" as const;
const WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA_V4 = "dmb_workspace_document_local_state_v4" as const;
const WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA_V3 = "dmb_workspace_document_local_state_v3" as const;
const WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA_V2 = "dmb_workspace_document_local_state_v2" as const;

export type WorkspaceDocumentLocalKind = "plan" | "runbook" | "worldbuilding_source";
export type WorkspaceDocumentLocalSurface = "plan" | "runbook" | "build";

export interface WorkspaceDocumentLocalState {
  schema_version: typeof WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA;
  document_id: string;
  title: string;
  campaign_id: string;
  kind: WorkspaceDocumentLocalKind;
  target_session: number | null;
  surface: WorkspaceDocumentLocalSurface;
  base_revision: number;
  base_content_sha256: string;
  tiptap_json: unknown;
  exported_markdown: string;
  /**
   * When true, `exported_markdown` is authoritative source text and must not be
   * re-derived from `tiptap_json`. Persists across parser upgrades that would
   * otherwise clear import-blocking diagnostics and reopen a lossy draft.
   */
  exported_markdown_authoritative: boolean;
  dirty: boolean;
  created_at: string;
  updated_at: string;
  last_local_save_at: string;
}

/** @deprecated Use WorkspaceDocumentLocalState */
export type TiptapWorkingBoardState = WorkspaceDocumentLocalState;

export function workspaceDocumentStorageKey(documentId: string): string {
  return `dmb.workspaceDocument.${documentId}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isWorkspaceDocumentLocalKind(value: unknown): value is WorkspaceDocumentLocalKind {
  return value === "plan" || value === "runbook" || value === "worldbuilding_source";
}

function isWorkspaceDocumentLocalSurface(value: unknown): value is WorkspaceDocumentLocalSurface {
  return value === "plan" || value === "runbook" || value === "build";
}

function migrateV2LocalState(value: Record<string, unknown>): WorkspaceDocumentLocalState | null {
  if (value.schema_version !== WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA_V2) return null;
  if (typeof value.document_id !== "string") return null;
  if (typeof value.title !== "string") return null;
  if (typeof value.campaign_id !== "string") return null;
  const kind = value.kind === "plan" ? "plan" : "runbook";
  const surface = value.surface === "plan" ? "plan" : "runbook";
  if (!isObject(value.tiptap_json)) return null;
  if (typeof value.exported_markdown !== "string") return null;
  if (typeof value.dirty !== "boolean") return null;
  if (typeof value.created_at !== "string") return null;
  if (typeof value.updated_at !== "string") return null;
  if (typeof value.last_local_save_at !== "string") return null;

  return {
    schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
    document_id: value.document_id,
    title: value.title,
    campaign_id: value.campaign_id,
    kind,
    target_session: value.target_session === null || typeof value.target_session === "number"
      ? value.target_session
      : null,
    surface,
    base_revision: 0,
    base_content_sha256: "",
    // v2→v5: heal legacy escaped reference labels once (schema provenance).
    tiptap_json: migrateLegacyTiptapReferenceLabels(value.tiptap_json),
    exported_markdown: value.exported_markdown,
    exported_markdown_authoritative: hasBlockingMarkdownImportDiagnostics(value.exported_markdown),
    dirty: value.dirty,
    created_at: value.created_at,
    updated_at: value.updated_at,
    last_local_save_at: value.last_local_save_at,
  };
}

function migrateV3LocalState(value: Record<string, unknown>): WorkspaceDocumentLocalState | null {
  if (value.schema_version !== WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA_V3) return null;
  if (typeof value.document_id !== "string") return null;
  if (typeof value.title !== "string") return null;
  if (typeof value.campaign_id !== "string") return null;
  if (!isWorkspaceDocumentLocalKind(value.kind)) return null;
  if (!(value.target_session === null || typeof value.target_session === "number")) return null;
  if (!isWorkspaceDocumentLocalSurface(value.surface)) return null;
  if (typeof value.base_revision !== "number") return null;
  if (typeof value.base_content_sha256 !== "string") return null;
  if (!isObject(value.tiptap_json)) return null;
  if (typeof value.exported_markdown !== "string") return null;
  if (typeof value.dirty !== "boolean") return null;
  if (typeof value.created_at !== "string") return null;
  if (typeof value.updated_at !== "string") return null;
  if (typeof value.last_local_save_at !== "string") return null;

  return {
    schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
    document_id: value.document_id,
    title: value.title,
    campaign_id: value.campaign_id,
    kind: value.kind,
    target_session: value.target_session,
    surface: value.surface,
    base_revision: value.base_revision,
    base_content_sha256: value.base_content_sha256,
    // v3→v5: heal legacy escaped reference labels once (schema provenance).
    tiptap_json: migrateLegacyTiptapReferenceLabels(value.tiptap_json),
    exported_markdown: value.exported_markdown,
    // Seal authority from the diagnostics at migration time so a later parser
    // upgrade cannot flip the guard and re-derive from lossy TipTap JSON.
    exported_markdown_authoritative: hasBlockingMarkdownImportDiagnostics(value.exported_markdown),
    dirty: value.dirty,
    created_at: value.created_at,
    updated_at: value.updated_at,
    last_local_save_at: value.last_local_save_at,
  };
}

function migrateV4LocalState(value: Record<string, unknown>): WorkspaceDocumentLocalState | null {
  if (value.schema_version !== WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA_V4) return null;
  if (typeof value.document_id !== "string") return null;
  if (typeof value.title !== "string") return null;
  if (typeof value.campaign_id !== "string") return null;
  if (!isWorkspaceDocumentLocalKind(value.kind)) return null;
  if (!(value.target_session === null || typeof value.target_session === "number")) return null;
  if (!isWorkspaceDocumentLocalSurface(value.surface)) return null;
  if (typeof value.base_revision !== "number") return null;
  if (typeof value.base_content_sha256 !== "string") return null;
  if (!isObject(value.tiptap_json)) return null;
  if (typeof value.exported_markdown !== "string") return null;
  if (typeof value.exported_markdown_authoritative !== "boolean") return null;
  if (typeof value.dirty !== "boolean") return null;
  if (typeof value.created_at !== "string") return null;
  if (typeof value.updated_at !== "string") return null;
  if (typeof value.last_local_save_at !== "string") return null;

  return {
    schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
    document_id: value.document_id,
    title: value.title,
    campaign_id: value.campaign_id,
    kind: value.kind,
    target_session: value.target_session,
    surface: value.surface,
    base_revision: value.base_revision,
    base_content_sha256: value.base_content_sha256,
    // v4→v5: heal legacy escaped reference labels once. Provenance is the
    // schema bump — never infer legacy from label characters on hot paths.
    tiptap_json: migrateLegacyTiptapReferenceLabels(value.tiptap_json),
    exported_markdown: value.exported_markdown,
    exported_markdown_authoritative: value.exported_markdown_authoritative,
    dirty: value.dirty,
    created_at: value.created_at,
    updated_at: value.updated_at,
    last_local_save_at: value.last_local_save_at,
  };
}

export function buildInitialWorkspaceDocumentLocalState(args: {
  documentId: string;
  title: string;
  campaignId: string;
  kind: WorkspaceDocumentLocalKind;
  targetSession: number | null;
  surface: WorkspaceDocumentLocalSurface;
  baseRevision: number;
  baseContentSha256: string;
  starterContent: unknown;
  now?: string;
}): WorkspaceDocumentLocalState {
  const now = args.now ?? new Date().toISOString();
  return {
    schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
    document_id: args.documentId,
    title: args.title,
    campaign_id: args.campaignId,
    kind: args.kind,
    target_session: args.targetSession,
    surface: args.surface,
    base_revision: args.baseRevision,
    base_content_sha256: args.baseContentSha256,
    tiptap_json: args.starterContent,
    exported_markdown: tiptapJsonToSemanticMarkdown(args.starterContent),
    exported_markdown_authoritative: false,
    dirty: false,
    created_at: now,
    updated_at: now,
    last_local_save_at: now,
  };
}

/** @deprecated Use buildInitialWorkspaceDocumentLocalState */
export function buildInitialWorkingBoardState(
  descriptor: {
    documentId: string;
    title: string;
    campaignId: string;
    kind?: "plan" | "runbook";
    targetSession?: number | null;
    session?: number;
    starterContent: unknown;
  },
  now = new Date().toISOString(),
): WorkspaceDocumentLocalState {
  return buildInitialWorkspaceDocumentLocalState({
    documentId: descriptor.documentId,
    title: descriptor.title,
    campaignId: descriptor.campaignId,
    kind: descriptor.kind ?? "runbook",
    targetSession: descriptor.targetSession ?? descriptor.session ?? null,
    surface: descriptor.kind ?? "runbook",
    baseRevision: 0,
    baseContentSha256: "",
    starterContent: descriptor.starterContent,
    now,
  });
}

export function isWorkspaceDocumentLocalState(value: unknown): value is WorkspaceDocumentLocalState {
  if (!isObject(value)) return false;

  return (
    value.schema_version === WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA
    && typeof value.document_id === "string"
    && typeof value.title === "string"
    && typeof value.campaign_id === "string"
    && isWorkspaceDocumentLocalKind(value.kind)
    && (value.target_session === null || typeof value.target_session === "number")
    && isWorkspaceDocumentLocalSurface(value.surface)
    && typeof value.base_revision === "number"
    && typeof value.base_content_sha256 === "string"
    && isObject(value.tiptap_json)
    && typeof value.exported_markdown === "string"
    && typeof value.exported_markdown_authoritative === "boolean"
    && typeof value.dirty === "boolean"
    && typeof value.created_at === "string"
    && typeof value.updated_at === "string"
    && typeof value.last_local_save_at === "string"
  );
}

/** @deprecated Use isWorkspaceDocumentLocalState */
export const isTiptapWorkingBoardState = isWorkspaceDocumentLocalState;

function deriveWorkspaceDocumentMarkdown(
  state: WorkspaceDocumentLocalState,
): WorkspaceDocumentLocalState {
  // Persisted authority bit — not live parser diagnostics — gates re-derivation.
  // A polish upgrade that learns previously unsupported syntax must not regenerate
  // exported_markdown from an older lossy TipTap projection.
  if (state.exported_markdown_authoritative) {
    return state;
  }
  const editableBody = tiptapJsonToSemanticMarkdown(state.tiptap_json);
  return {
    ...state,
    // Keep metadata that intentionally lives outside the TipTap document.
    exported_markdown: preserveLeadingYamlFrontmatter(state.exported_markdown, editableBody),
  };
}

function parseStoredWorkspaceDocumentLocalState(parsed: unknown): WorkspaceDocumentLocalState | null {
  if (isWorkspaceDocumentLocalState(parsed)) {
    return deriveWorkspaceDocumentMarkdown(parsed);
  }
  if (isObject(parsed)) {
    const migrated = migrateV4LocalState(parsed)
      ?? migrateV3LocalState(parsed)
      ?? migrateV2LocalState(parsed);
    if (migrated) return deriveWorkspaceDocumentMarkdown(migrated);
  }
  return null;
}

export function readWorkspaceDocumentLocalState(
  storage: Pick<Storage, "getItem">,
  documentId: string,
): WorkspaceDocumentLocalState | null {
  try {
    const stored = storage.getItem(workspaceDocumentStorageKey(documentId));
    if (stored === null) return null;
    const parsed: unknown = JSON.parse(stored);
    const state = parseStoredWorkspaceDocumentLocalState(parsed);
    if (!state) return null;
    if (state.document_id !== documentId) return null;
    return state;
  } catch {
    return null;
  }
}

/** @deprecated Use readWorkspaceDocumentLocalState */
export function readTiptapWorkingBoardState(
  storage: Pick<Storage, "getItem">,
  descriptor: { documentId: string },
): WorkspaceDocumentLocalState | null {
  return readWorkspaceDocumentLocalState(storage, descriptor.documentId);
}

export function writeWorkspaceDocumentLocalState(
  storage: Pick<Storage, "setItem">,
  state: WorkspaceDocumentLocalState,
): void {
  storage.setItem(workspaceDocumentStorageKey(state.document_id), JSON.stringify(state));
}

/** @deprecated Use writeWorkspaceDocumentLocalState */
export function writeTiptapWorkingBoardState(
  storage: Pick<Storage, "setItem">,
  _descriptor: { documentId: string },
  state: WorkspaceDocumentLocalState,
): void {
  writeWorkspaceDocumentLocalState(storage, state);
}

export function clearWorkspaceDocumentLocalState(
  storage: Pick<Storage, "removeItem">,
  documentId: string,
): void {
  storage.removeItem(workspaceDocumentStorageKey(documentId));
}

/** @deprecated Use clearWorkspaceDocumentLocalState */
export function clearTiptapWorkingBoardState(
  storage: Pick<Storage, "removeItem">,
  descriptor: { documentId: string },
): void {
  clearWorkspaceDocumentLocalState(storage, descriptor.documentId);
}
